
from engine.bot import Bot, Move

ALL_MOVES = (Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT)


def _manhattan(a, b) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(position, target) -> Move:

    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if abs(dx) >= abs(dy):
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    return Move.UP  # déjà sur place, sans conséquence


class DeliveryBot(Bot):
    def decide(self, state) -> Move:
        # 1. If I'm already carrying a package, I'll deliver it—I have no other choice
        #    This applies as long as I haven't dropped it off yet.
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        # 2. Otherwise, I look for the best unclaimed job among those
        #    that are still actually available before their deadline.
        available = [job for job in state.jobs if job.claimed_by is None]

        best_job = None
        best_rate = float("-inf")

        for job in available:
            turns_to_pickup = _manhattan(state.position, job.pickup)
            turns_to_dropoff = _manhattan(job.pickup, job.dropoff)
            total_turns = turns_to_pickup + turns_to_dropoff

            arrival_turn = state.turn + total_turns
            if arrival_turn > job.deadline:
                continue

            rate = job.value / max(total_turns, 1)

            if rate > best_rate:
                best_rate = rate
                best_job = job

        if best_job is not None:
            return _step_toward(state.position, best_job.pickup)

        if available:
            nearest = min(available, key=lambda j: _manhattan(state.position, j.pickup))
            return _step_toward(state.position, nearest.pickup)

        return Move.UP