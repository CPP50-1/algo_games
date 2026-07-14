"""
Implements a depth-limited path search (Orienteering Problem approach) to find
the most valuable combination of items reachable within the remaining move budget.
Actively prunes targets that opponents are closer to.
"""
from engine.bot import Bot, Move


def manhattan(p1, p2):
    """Calculates Manhattan distance between two points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def _step_toward(position, target):
    """Takes a single step toward the target position."""
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


class TheophileBot(Bot):
    def decide(self, state) -> Move:
        if not state.items or state.moves_left <= 0:
            return Move.UP  # nothing left to do

        my_pos = state.position
        my_id = state.self_id
        budget = state.moves_left

        # Extract opponent positions to predict race conditions
        opp_positions = [
            pos for b_id, pos in state.positions.items() if b_id != my_id
        ]

        # Depth-limited search to find the optimal sequence of items
        best_value = -1
        best_path = []

        def search(current_pos, remaining_items, budget_left, current_value, depth):
            nonlocal best_value, best_path
            
            # Base condition: Update best known path if this branch is superior
            if current_value > best_value:
                best_value = current_value
                # We don't save the full path here, we just need to know it works. 
                # The actual path tracking happens during the recursive unwinding below.

            # Stop if out of budget, out of depth, or board is clear
            if budget_left <= 0 or depth == 0 or not remaining_items:
                return current_value, []

            local_best_val = current_value
            local_best_path = []

            for i, item in enumerate(remaining_items):
                dist = manhattan(current_pos, item.position)
                
                # Prune 1: Can we afford this item?
                if dist > budget_left:
                    continue
                    
                # Prune 2: Will an opponent beat us to this item?
                # If an opponent is strictly closer, abandon to avoid wasting moves.
                opp_dist = min([manhattan(op, item.position) for op in opp_positions], default=float('inf'))
                if opp_dist < dist:
                    continue 

                # Recursive search deeper into the tree
                next_items = remaining_items[:i] + remaining_items[i+1:]
                val, path = search(
                    item.position, 
                    next_items, 
                    budget_left - dist, 
                    current_value + item.value, 
                    depth - 1
                )
                
                if val > local_best_val:
                    local_best_val = val
                    local_best_path = [item] + path

            return local_best_val, local_best_path

        # Initial search call. A depth of 4-5 is usually optimal for game loops 
        # to prevent timeout while providing deep enough combination reasoning.
        val, optimal_path = search(my_pos, state.items, budget, current_value=0, depth=4)

        # If a safe, profitable path was found, move toward the first item in the sequence
        if optimal_path:
            return _step_toward(my_pos, optimal_path[0].position)
        
        # --- Fallback Logic ---
        # If all items are closer to opponents or out of budget, fallback to a greedy approach
        # based on value density (value per unit of distance) to scavenge remaining points.
        reachable = [it for it in state.items if manhattan(my_pos, it.position) <= budget]
        
        if not reachable:
            # If nothing is reachable within the budget, just step toward the absolute closest
            # item as a final effort.
            nearest = min(state.items, key=lambda it: manhattan(my_pos, it.position))
            return _step_toward(my_pos, nearest.position)
        
        # Scavenge: target the item with the highest value-to-distance ratio
        best_fallback = max(reachable, key=lambda it: it.value / max(1, manhattan(my_pos, it.position)))
        return _step_toward(my_pos, best_fallback.position)