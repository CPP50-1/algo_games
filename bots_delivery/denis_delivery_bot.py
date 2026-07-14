"""Delivery-game bot -- ranks candidate jobs with a priority queue
instead of always chasing whatever pickup is nearest.

Everything here is rebuilt from scratch every decide() call, because
the set of *feasible* jobs shifts turn to turn: new ones appear on
schedule, others expire, other bots claim things, and our own position
keeps changing what "time to reach it" even means.

While carrying a job there's only one sensible move -- head for its
dropoff. The game gives no way to release a job early: once you've
picked one up you're committed until you either deliver it or its
deadline passes and the game forcibly drops it from your hands for
zero value. That's exactly why *which* job to pick up matters so much
-- claiming one you can't actually finish in time doesn't just waste
that job, it locks you out of every other job for however long you're
stuck carrying deadweight.

While free, every unclaimed job gets scored by:
  - feasibility: walking straight to the pickup and then the dropoff
    from here, right now, would we beat the deadline? Anything that
    fails this is dropped outright -- claiming a job you can't finish
    is strictly worse than claiming nothing.
  - rate: value earned per turn of travel the job costs us
    (value / total travel time). This is the scheduling call the
    naive "nearest first" bot never makes -- a job twice as far but
    paying more than twice as much is a *better* use of our time, not
    a worse one.
  - slack (deadline minus turns needed) as the tie-break between
    similarly profitable jobs, favouring whichever is more likely to
    become infeasible if we hesitate.

Those go into a heapq so the best candidate is always one pop away,
then we walk one step toward its pickup cell. Recomputing this every
turn is what lets a better job that just appeared -- or a rival
claiming our current target -- change our mind immediately, instead of
committing to a plan made several turns ago on stale information.
"""
import heapq

from engine.bot import Bot, Move


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(position, target):
    dx = target[0] - position[0]
    dy = target[1] - position[1]
    # Bigger remaining gap moves first -- total distance covered is the
    # same either way on an open grid, this just avoids always
    # favouring x the way a naive walk would.
    if abs(dx) >= abs(dy):
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
        if dy > 0:
            return Move.DOWN
        if dy < 0:
            return Move.UP
    else:
        if dy > 0:
            return Move.DOWN
        if dy < 0:
            return Move.UP
        if dx > 0:
            return Move.RIGHT
        if dx < 0:
            return Move.LEFT
    return Move.UP  # already there -- direction doesn't matter this turn


def _best_job(state):
    """Push every feasible unclaimed job onto a min-heap ranked by
    (-rate, slack) and return the best one, or None if nothing on the
    board can be reached and delivered before its deadline from here.
    """
    heap = []
    for job in state.jobs:
        if job.claimed_by is not None:
            continue

        time_to_pickup = _dist(state.position, job.pickup)
        leg_time = _dist(job.pickup, job.dropoff)
        travel_time = time_to_pickup + leg_time
        eta_dropoff = state.turn + travel_time
        slack = job.deadline - eta_dropoff
        if slack < 0:
            continue  # can't make the deadline even heading straight there now

        rate = job.value / travel_time if travel_time > 0 else float(job.value)
        # heapq is a min-heap: negate rate so the highest-rate job pops
        # first; slack (not negated) then breaks ties toward whichever
        # job is more urgent. job.id makes every tuple unique so heapq
        # never has to fall back to comparing Job objects directly.
        heapq.heappush(heap, (-rate, slack, job.id, job))

    if not heap:
        return None
    return heap[0][3]


class DeliveryBot(Bot):
    def decide(self, state) -> Move:
        if state.carrying is not None:
            return _step_toward(state.position, state.carrying.dropoff)

        target = _best_job(state)
        if target is None:
            return Move.UP  # nothing reachable in time -- wait it out
        return _step_toward(state.position, target.pickup)

if __name__ == "__main__":
    from games.delivery import DeliveryView, Job
    state = DeliveryView(self_id = "denis_delivery_bot",
                         width = 21,
                         height = 21,
                         turn = 69,
                         position = [17, 4],
                         carrying = Job(id = "job1",
                                        pickup = [4, 16],
                                        dropoff = [17, 3],
                                        value = 260,
                                        deadline = 86,
                                        appear_turn = 6,
                                        claimed_by = "denis_delivery_bot"),
                         score = {"example_delivery_bot": 160, "denis_delivery_bot": 160},
                         jobs = [Job(id = "job1", pickup = [4, 16], dropoff = [17, 3],
                                     value = 260, deadline = 86, appear_turn = 6,
                                     claimed_by = "denis_delivery_bot"),
                                 Job(id = "job5", pickup = [3, 17], dropoff = [16, 4],
                                     value = 260, deadline = 110, appear_turn = 30,
                                     claimed_by = "example_delivery_bot"),
                                 Job(id = "job9", pickup = [2, 18], dropoff = [15, 5],
                                     value = 260, deadline = 134, appear_turn = 54,
                                     claimed_by = None),
                                 Job(id = "job10", pickup = [7, 13], dropoff = [20, 0],
                                     value = 260, deadline = 88, appear_turn = 60,
                                     claimed_by = None),
                                 Job(id = "job11", pickup = [12, 8], dropoff = [4, 16],
                                     value = 160, deadline = 116, appear_turn = 66,
                                     claimed_by = None),
                                 Job(id = "job1", pickup = [4, 16], dropoff = [17, 3],
                                     value = 260, deadline = 86, appear_turn = 6,
                                     claimed_by = "denis_delivery_bot")],
                         positions = {"example_delivery_bot": [3, 17], "denis_delivery_bot": [17, 4]})
    bot = DeliveryBot()
    print(bot.decide(state))