import heapq

from engine.bot import Bot, Move
from games.delivery import _manhattan, DeliveryView, Job, Position

URGENCY_WEIGHT = 0.5
COMPETITION_WEIGHT = 0.3
TOP_K = 3


def _step_toward(
    position: Position,
    target: Position,
) -> Move:
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    if dx > 0:
        return Move.RIGHT
    if dx < 0:
        return Move.LEFT
    if dy > 0:
        return Move.DOWN
    if dy < 0:
        return Move.UP
    return Move.UP


def _score_job(
    job: Job,
    my_distance: int,
    remaining_turns: int,
    free_opponents: dict[str, Position],
) -> float:
    total_distance: int = my_distance + _manhattan(job.pickup, job.dropoff)
    slack_time: int = job.deadline - remaining_turns - total_distance

    if slack_time < 0:
        return -1

    urgency: float = 1.0 / (1.0 + slack_time)
    value_for_distance: float = job.value / max(total_distance, 1)

    return (
        value_for_distance
        * (1.0 + URGENCY_WEIGHT * urgency)
        * (
            1.0
            + COMPETITION_WEIGHT
            * _competition_factor(job.pickup, my_distance, free_opponents)
        )
    )


def _competition_factor(
    target_position: Position,
    my_distance: int,
    free_opponents: dict[str, Position],
) -> float:
    if not free_opponents:
        return 0.0

    factors: list[float] = [
        (_manhattan(opponent_position, target_position) - my_distance)
        / max(my_distance, 1)
        for opponent_position in free_opponents.values()
    ]

    return sum(factors) / len(factors)


def _top_scored_jobs(
    state: DeliveryView,
    available_jobs: list[Job],
    free_opponents: dict[str, Position],
    k: int = TOP_K,
) -> list[tuple[float, Job]]:
    heap: list[tuple[float, Job]] = []

    for job in available_jobs:
        score: float = _score_job(
            job,
            _manhattan(job.pickup, state.position),
            state.turn,
            free_opponents,
        )

        if score == -1:
            continue

        if len(heap) < k:
            heapq.heappush(heap, (score, job))
        elif score > heap[0][0]:
            heapq.heappushpop(heap, (score, job))

    return heap


def _pick_job(
    available_jobs: list[Job],
    free_opponents: dict,
    state: DeliveryView,
) -> Job | None:
    current: Job | None = next((j for j in available_jobs if j == state.carrying), None)
    if current is not None:
        if not _competition_factor(
            current.pickup, _manhattan(current.pickup, state.position), free_opponents
        ):
            return current

    job_candidates: list[tuple[float, Job]] = _top_scored_jobs(
        state, available_jobs, free_opponents
    )
    if not job_candidates:
        return None

    best_job: Job | None = None
    best_score: float = -1.0

    for score, job in job_candidates:
        if score > best_score:
            best_score = score
            best_job = job

    return best_job


class MithirsanDeliveryBot(Bot):
    def decide(self, state: DeliveryView) -> Move:
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        available_jobs = []
        free_opponents = state.positions.copy()
        free_opponents.pop(state.self_id)

        for job in state.jobs:
            if job.claimed_by is None:
                available_jobs.append(job)
            else:
                free_opponents.pop(job.claimed_by)

        if not available_jobs:
            return Move.UP

        target = _pick_job(available_jobs, free_opponents, state)
        if target is None:
            return _step_toward(state.position, (state.height // 2, state.width // 2))

        return _step_toward(state.position, target.pickup)
