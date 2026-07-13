"""Reference bot for the delivery game -- shows the minimum needed to
implement the Bot API against a DeliveryView.

Strategy: always head for the nearest unclaimed job's pickup cell (or
your own dropoff if you're already carrying something). This ignores
deadlines completely -- it's the naive "closest first" trap this game
module is built to expose. Trainees should be able to beat it easily by
weighing urgency (deadline minus time-to-reach) alongside distance,
e.g. with a small heapq of candidate jobs re-ranked every turn.
"""
from engine.bot import Bot, Move
from games.delivery import Job


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    if dx > 0:
        return Move.RIGHT
    if dx < 0:
        return Move.LEFT
    return Move.UP  # already there -- direction doesn't matter this turn


class VictorDeliveryBot(Bot):
    def decide(self, state) -> Move:
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        def get_best_job():
            best_ratio = 0.0
            best_job: Job | None = None
            position = state.position
            for job in available:
                first_to_job = True
                distance_to_reach = abs(job.pickup[0] - position[0]) + abs(job.pickup[1] - position[1])
                for enemy in state.positions.keys():
                    if enemy != state.self_id:
                        enemy_position = state.positions[enemy]
                        distance_from_enemy = abs(job.pickup[0] - enemy_position[0]) + abs(job.pickup[1] - enemy_position[1])
                        if distance_to_reach > distance_from_enemy:
                            first_to_job = False
                if not first_to_job:
                    continue
                distance_to_complete = abs(job.pickup[0] - job.dropoff[0]) + abs(job.pickup[1] - job.dropoff[0])
                if job.deadline > distance_to_reach + distance_to_complete:
                    time_value_ratio = job.value / (distance_to_reach + distance_to_complete)
                    if time_value_ratio > best_ratio:
                        best_ratio = time_value_ratio
                        best_job = job
            return best_job

        available = [j for j in state.jobs if j.claimed_by is None]
        if not available:
            return _step_toward(state.position, (int(state.height/2), int(state.width/2)))

        target_job = get_best_job()

        if target_job:
            return _step_toward(state.position, target_job.pickup)
        else:
            return _step_toward(state.position, (int(state.height/2), int(state.width/2)))
