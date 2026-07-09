"""Grid delivery / task scheduling.

Bots move around a shared grid picking up and delivering jobs before
their deadlines. Each job has a pickup cell, a dropoff cell, a value,
and a deadline (an absolute turn number). Landing on an available job's
pickup cell claims it automatically -- each bot can carry at most one
job at a time. Landing on your carried job's dropoff cell on or before
its deadline delivers it and adds its value to your score. Miss the
deadline, whether the job is still unclaimed or you're carrying it, and
it expires for zero value.

The trap this is built to expose: always heading for the *nearest*
available job (naive greedy-by-distance) regularly loses, because
"close" and "urgent" are different things. A job that looks cheap to
reach but has no deadline pressure is often worth skipping in favour of
a farther job that's about to expire and pays more. That's a
scheduling problem, not a pathfinding problem -- the natural tool is a
priority queue (heapq) ranked by something like slack time (deadline
minus turns needed to reach it), recomputed as jobs appear and expire,
not a single "distance to everything" scan repeated every turn.

Movement uses the same four-direction Move enum as every other game
module. There are no walls and bots cannot die here -- moving into the
board edge is simply a no-op, which doubles as a legal "wait in place"
if a bot decides the best move this turn is no move at all.

No randomness: the full job schedule is a fixed function of the board
size and --num-jobs, generated with a golden-ratio scatter (see
`_generate_jobs`) instead of Python's random module, so the exact same
match replays identically every time and a round-robin's side-swap
still cancels out only positional advantage, not schedule variance.

State handed to each bot's decide() is a `DeliveryView`:
    self_id     -- your bot id
    width, height, turn
    position    -- your (x, y)
    carrying    -- the Job you're currently carrying, or None
    score       -- {bot_id: current score}
    jobs        -- every job that has appeared and not yet expired or
                    been delivered, claimed or not (see `Job` below)
    positions   -- {bot_id: (x, y)} for every bot, so you can see who
                    else might be racing you to a pickup

A `Job` is:
    id            -- str
    pickup        -- (x, y)
    dropoff       -- (x, y)
    value         -- int, added to score on delivery
    deadline      -- int, absolute turn number; turn > deadline expires it
    appear_turn   -- int, the turn this job became visible
    claimed_by    -- bot id currently carrying it, or None if unclaimed
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List, Optional, Tuple

from engine.bot import Move
from games.base import Game

Position = Tuple[int, int]

_GOLDEN_RATIO = 0.6180339887498949  # for a deterministic, well-spread scatter


@dataclass(frozen=True)
class Job:
    id: str
    pickup: Position
    dropoff: Position
    value: int
    deadline: int
    appear_turn: int
    claimed_by: Optional[str]


@dataclass(frozen=True)
class DeliveryView:
    self_id: str
    width: int
    height: int
    turn: int
    position: Position
    carrying: Optional[Job]
    score: Dict[str, int]
    jobs: List[Job]
    positions: Dict[str, Position]


def _scatter_point(index: int, width: int, height: int) -> Position:
    """Deterministic, well-spread pseudo-random-looking point -- no RNG,
    just the golden ratio's classic low-discrepancy scatter property."""
    fx = (index * _GOLDEN_RATIO) % 1.0
    fy = (index * _GOLDEN_RATIO * _GOLDEN_RATIO) % 1.0
    x = min(int(fx * width), width - 1)
    y = min(int(fy * height), height - 1)
    return (x, y)


def _manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _generate_jobs(width: int, height: int, num_jobs: int, spawn_every: int) -> List[Job]:
    """Fixed, deterministic job schedule. Jobs appear evenly spaced over
    time (every `spawn_every` turns) at scattered pickup/dropoff pairs.
    Deadlines are deliberately mixed: some jobs get generous slack, some
    get tight slack relative to their own pickup-to-dropoff distance --
    that mix is what makes pure nearest-first greedy lose to anything
    that accounts for urgency.
    """
    jobs = []
    for i in range(num_jobs):
        pickup = _scatter_point(2 * i, width, height)
        dropoff = _scatter_point(2 * i + 1, width, height)
        if dropoff == pickup:
            dropoff = ((dropoff[0] + 1) % width, dropoff[1])

        distance = max(_manhattan(pickup, dropoff), 1)
        appear_turn = i * spawn_every

        # Alternate tight vs generous slack so the schedule always mixes
        # urgent and relaxed jobs, rather than trending toward one or
        # the other as more jobs appear.
        slack_factor = 1 if i % 2 == 0 else 3
        deadline = appear_turn + distance * slack_factor + 2

        # Farther jobs pay more -- otherwise there's no reason to ever
        # prefer a long haul over a short one, which would collapse the
        # scheduling decision back into pure distance minimisation.
        value = distance * 10

        jobs.append(
            Job(
                id=f"job{i}",
                pickup=pickup,
                dropoff=dropoff,
                value=value,
                deadline=deadline,
                appear_turn=appear_turn,
                claimed_by=None,
            )
        )
    return jobs


def _starting_positions(width: int, height: int, bot_ids: List[str]) -> Dict[str, Position]:
    """Fixed, deterministic starting spot per bot -- spread along the
    top edge, evenly spaced. No randomness, no dependence on bot_ids'
    content, only on how many there are and the board size."""
    n = len(bot_ids)
    positions = {}
    for i, bot_id in enumerate(bot_ids):
        x = round((i + 1) * width / (n + 1))
        x = min(max(x, 0), width - 1)
        positions[bot_id] = (x, 0)
    return positions


class DeliveryGame(Game):
    def __init__(
        self,
        width: int = 20,
        height: int = 20,
        num_jobs: int = 12,
        spawn_every: int = 6,
        max_turns: int = 150,
    ) -> None:
        self.width = width
        self.height = height
        self.num_jobs = num_jobs
        self.spawn_every = spawn_every
        self.max_turns = max_turns

        self._turn = 0
        self._bot_ids: List[str] = []
        self._positions: Dict[str, Position] = {}
        self._carrying: Dict[str, Optional[str]] = {}  # bot_id -> job_id or None
        self._score: Dict[str, int] = {}
        self._schedule: List[Job] = []
        self._jobs_by_id: Dict[str, Job] = {}
        self._active_job_ids: List[str] = []  # revealed, not yet resolved

    def setup(self, bot_ids: List[str]) -> None:
        self._turn = 0
        self._bot_ids = list(bot_ids)
        self._positions = _starting_positions(self.width, self.height, self._bot_ids)
        self._carrying = {b: None for b in self._bot_ids}
        self._score = {b: 0 for b in self._bot_ids}
        self._schedule = _generate_jobs(self.width, self.height, self.num_jobs, self.spawn_every)
        self._jobs_by_id = {j.id: j for j in self._schedule}
        self._active_job_ids = []
        self._reveal_new_jobs()

    def _reveal_new_jobs(self) -> None:
        for job in self._schedule:
            if job.appear_turn <= self._turn and job.id not in self._active_job_ids:
                if not self._jobs_by_id[job.id].claimed_by:
                    self._active_job_ids.append(job.id)

    def view_for(self, bot_id: str) -> DeliveryView:
        carried_job_id = self._carrying[bot_id]
        carrying = self._jobs_by_id[carried_job_id] if carried_job_id else None
        visible_jobs = [self._jobs_by_id[jid] for jid in self._active_job_ids]
        if carrying is not None:
            visible_jobs = visible_jobs + [carrying]
        return DeliveryView(
            self_id=bot_id,
            width=self.width,
            height=self.height,
            turn=self._turn,
            position=self._positions[bot_id],
            carrying=carrying,
            score=dict(self._score),
            jobs=visible_jobs,
            positions=dict(self._positions),
        )

    def step(self, moves: Dict[str, Optional[Move]]) -> None:
        self._turn += 1

        # 1. Move every bot; walking into the board edge is a no-op.
        for bot_id in self._bot_ids:
            move = moves.get(bot_id)
            if not isinstance(move, Move):
                continue  # forfeit this turn -- just don't move
            x, y = self._positions[bot_id]
            nx, ny = x + move.dx, y + move.dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                self._positions[bot_id] = (nx, ny)

        # 2. Reveal any jobs whose appear_turn has arrived.
        self._reveal_new_jobs()

        # 3. Expire anything overdue, whether claimed or not.
        for job_id in list(self._active_job_ids):
            job = self._jobs_by_id[job_id]
            if self._turn > job.deadline:
                if job.claimed_by:
                    self._carrying[job.claimed_by] = None
                self._active_job_ids.remove(job_id)

        # 4. Deliveries: a bot carrying a job that reaches its dropoff.
        for bot_id in self._bot_ids:
            job_id = self._carrying[bot_id]
            if job_id is None:
                continue
            job = self._jobs_by_id[job_id]
            if self._positions[bot_id] == job.dropoff:
                self._score[bot_id] += job.value
                self._carrying[bot_id] = None
                if job_id in self._active_job_ids:
                    self._active_job_ids.remove(job_id)

        # 5. Pickups: free bots landing on an available job's pickup
        # cell. Simultaneous claims on the same job are broken by bot id
        # order, deterministically -- never by which bot happened to be
        # processed first in an arbitrary dict/list order.
        available = [
            self._jobs_by_id[jid]
            for jid in self._active_job_ids
            if self._jobs_by_id[jid].claimed_by is None
        ]
        free_bots = [b for b in self._bot_ids if self._carrying[b] is None]
        for job in available:
            claimants = sorted(b for b in free_bots if self._positions[b] == job.pickup)
            if not claimants:
                continue
            winner = claimants[0]
            self._jobs_by_id[job.id] = Job(**{**job.__dict__, "claimed_by": winner})
            self._carrying[winner] = job.id
            free_bots.remove(winner)

    def alive_bots(self) -> List[str]:
        return list(self._bot_ids)  # nobody ever "dies" in this game

    def is_over(self) -> bool:
        return self._turn >= self.max_turns

    def winners(self) -> List[str]:
        if not self.is_over():
            return []
        best = max(self._score.values())
        return [b for b in self._bot_ids if self._score[b] == best]

    def frame(self) -> Dict:
        return {
            "turn": self._turn,
            "width": self.width,
            "height": self.height,
            "positions": {b: list(p) for b, p in self._positions.items()},
            "score": dict(self._score),
            "carrying": dict(self._carrying),
            "jobs": [
                {
                    "id": j.id,
                    "pickup": list(j.pickup),
                    "dropoff": list(j.dropoff),
                    "value": j.value,
                    "deadline": j.deadline,
                    "claimed_by": j.claimed_by,
                }
                for j in (self._jobs_by_id[jid] for jid in self._active_job_ids)
            ],
        }

    def serialize_view(self, view: DeliveryView) -> Dict:
        def job_to_dict(j: Job) -> Dict:
            return {
                "id": j.id,
                "pickup": list(j.pickup),
                "dropoff": list(j.dropoff),
                "value": j.value,
                "deadline": j.deadline,
                "appear_turn": j.appear_turn,
                "claimed_by": j.claimed_by,
            }

        return {
            "self_id": view.self_id,
            "width": view.width,
            "height": view.height,
            "turn": view.turn,
            "position": list(view.position),
            "carrying": job_to_dict(view.carrying) if view.carrying else None,
            "score": dict(view.score),
            "jobs": [job_to_dict(j) for j in view.jobs],
            "positions": {b: list(p) for b, p in view.positions.items()},
        }

    @staticmethod
    def deserialize_view(data: Dict) -> DeliveryView:
        def dict_to_job(d: Dict) -> Job:
            return Job(
                id=d["id"],
                pickup=tuple(d["pickup"]),
                dropoff=tuple(d["dropoff"]),
                value=d["value"],
                deadline=d["deadline"],
                appear_turn=d["appear_turn"],
                claimed_by=d["claimed_by"],
            )

        return DeliveryView(
            self_id=data["self_id"],
            width=data["width"],
            height=data["height"],
            turn=data["turn"],
            position=tuple(data["position"]),
            carrying=dict_to_job(data["carrying"]) if data["carrying"] else None,
            score=dict(data["score"]),
            jobs=[dict_to_job(j) for j in data["jobs"]],
            positions={b: tuple(p) for b, p in data["positions"].items()},
        )

    @staticmethod
    def serialize_action(action) -> str:
        return action.name  # raises AttributeError for anything that isn't a Move -- treated as forfeit

    @staticmethod
    def deserialize_action(data) -> Move:
        return Move[data]
