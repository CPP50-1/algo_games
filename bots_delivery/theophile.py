import heapq
import random
from engine.bot import Bot, Move

# The game's deterministic scatter constant
_GOLDEN_RATIO = 0.6180339887498949

def _manhattan(p1, p2) -> int:
    """Calculates the L1 norm (Manhattan distance) between two points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

class TheophileBot(Bot):
    """
    A precognitive delivery bot.
    Uses DFS + B&B to evaluate deep optimal paths, tracks exact enemy arrival 
    bounds to avoid theft, and exploits the game's deterministic golden ratio 
    scatter to camp directly on top of future job spawns.
    """
    def __init__(self):
        super().__init__()
        self.urgency_alpha = 2.0 
        self.max_chain_depth = 4 
        self.highest_seen_job_idx = -1

    def _step_toward(self, position, target) -> Move:
        dx = target[0] - position[0]
        dy = target[1] - position[1]
        
        optimal_moves = []
        if dx > 0: optimal_moves.append(Move.RIGHT)
        if dx < 0: optimal_moves.append(Move.LEFT)
        if dy > 0: optimal_moves.append(Move.DOWN)
        if dy < 0: optimal_moves.append(Move.UP)
        
        if not optimal_moves:
            return None 
                
        return random.choice(optimal_moves)

    def _calculate_score(self, value, time, min_slack) -> float:
        if time <= 0: return 0
        roi = value / time
        urgency_multiplier = 1 + (self.urgency_alpha / (min_slack + 1))
        return roi * urgency_multiplier

    def _evaluate_chain(self, start_pos, start_turn, chain, enemy_states, state):
        current_pos = start_pos
        current_turn = start_turn
        total_val = 0
        min_slack = float('inf')

        for job in chain:
            dist_pickup = _manhattan(current_pos, job.pickup)
            dist_drop = _manhattan(job.pickup, job.dropoff)
            arrival_at_pickup = current_turn + dist_pickup
            
            # --- Robust Mathematical Bounds instead of Intent Guessing ---
            winnable = True
            for e_id, (e_free_turn, e_free_pos) in enemy_states.items():
                # The absolute earliest this enemy can reach this pickup
                e_arrival = max(start_turn, e_free_turn) + _manhattan(e_free_pos, job.pickup)
                
                # We surrender if they strictly beat us, or if they tie and have alphabetical priority
                if e_arrival < arrival_at_pickup or (e_arrival == arrival_at_pickup and e_id < state.self_id):
                    winnable = False
                    break
            
            if not winnable:
                return False, 0, 0, 0

            # --- Deadline Check ---
            current_turn += dist_pickup + dist_drop
            slack = job.deadline - current_turn
            
            if slack < 0:
                return False, 0, 0, 0 
                
            min_slack = min(min_slack, slack)
            total_val += job.value
            current_pos = job.dropoff

        time_invested = current_turn - start_turn
        return True, time_invested, min_slack, total_val

    def _predict_next_spawn(self, state) -> tuple[int, int]:
        """
        Exploits the game's deterministic PRNG to calculate the exact coordinate 
        of the next job's pickup location before it spawns.
        """
        # Parse the highest active job ID to figure out where we are in the schedule
        for job in state.jobs:
            if job.id.startswith('job'):
                try:
                    idx = int(job.id[3:])
                    if idx > self.highest_seen_job_idx:
                        self.highest_seen_job_idx = idx
                except ValueError:
                    pass
        
        # Calculate the next pickup in the sequence
        next_idx = max(0, self.highest_seen_job_idx + 1)
        
        # Mirror the game's internal `_scatter_point` mathematical logic exactly
        fx = ((2 * next_idx) * _GOLDEN_RATIO) % 1.0
        fy = ((2 * next_idx) * _GOLDEN_RATIO * _GOLDEN_RATIO) % 1.0
        
        x = min(int(fx * state.width), state.width - 1)
        y = min(int(fy * state.height), state.height - 1)
        
        return (x, y)
    
    def decide(self, state) -> Move:
        my_pos = state.position
        turn = state.turn

        if state.carrying is not None:
            return self._step_toward(my_pos, state.carrying.dropoff)

        available_jobs = [j for j in state.jobs if j.claimed_by is None]
        
        # Track EXACT free-turns for enemies to ensure our chains are fully collision-proof
        enemy_states = {}
        for e_id, e_pos in state.positions.items():
            if e_id == state.self_id: 
                continue
            e_carried = next((j for j in state.jobs if j.claimed_by == e_id), None)
            if e_carried:
                free_turn = turn + _manhattan(e_pos, e_carried.dropoff)
                enemy_states[e_id] = (free_turn, e_carried.dropoff)
            else:
                enemy_states[e_id] = (turn, e_pos)

        pq = []
        best_score_found = -1.0 

        def build_chains(current_chain):
            nonlocal best_score_found
            
            valid, time, slack, val = self._evaluate_chain(
                my_pos, turn, current_chain, enemy_states, state
            )
            
            if not valid:
                return 
                
            score = self._calculate_score(val, time, slack)
            chain_id = "-".join(j.id for j in current_chain)
            
            if score > best_score_found:
                best_score_found = score
                
            heapq.heappush(pq, (-score, chain_id, current_chain))
            
            if len(current_chain) >= self.max_chain_depth:
                return
                
            remaining_jobs = [j for j in available_jobs if j not in current_chain]
            if not remaining_jobs:
                return
                
            max_remaining_val = max(j.value for j in remaining_jobs)
            optimistic_score = self._calculate_score(val + max_remaining_val, time + 1, slack)
            
            if optimistic_score <= best_score_found:
                return 

            current_dropoff = current_chain[-1].dropoff
            for next_job in remaining_jobs:
                dist_to_next = _manhattan(current_dropoff, next_job.pickup)
                if turn + time + dist_to_next > next_job.deadline:
                    continue 
                build_chains(current_chain + [next_job])

        for job in available_jobs:
            build_chains([job])

        # Execute
        if pq:
            _, _, best_chain = heapq.heappop(pq)
            target = best_chain[0].pickup
        else:
            # The Oracle fallback: Walk directly to the next spawn tile.
            target = self._predict_next_spawn(state)

        return self._step_toward(my_pos, target)
