from collections import deque
from engine.bot import Bot, Move

class TheophileBot(Bot):
    """
    Uses Voronoi partitioning via Breadth-First Search (BFS) 
    to evaluate the strictly uncontested open space reachable from every potential move,
    while explicitly avoiding head-on collisions.
    """
    def decide(self, state) -> Move:
        me_x, me_y = state.positions[state.self_id]
        
        # Get current positions of all living enemies
        enemies = [pos for bot_id, pos in state.positions.items() 
                   if bot_id != state.self_id and bot_id in state.alive]
        
        def get_safe_moves(x, y):
            """Yields adjacent cells that are within bounds and not walls."""
            for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
                nx, ny = x + move.dx, y + move.dy
                if 0 <= nx < state.width and 0 <= ny < state.height:
                    if (nx, ny) not in state.walls:
                        yield move, nx, ny

        # 1. Identify contested cells to prevent head-on collisions
        enemy_next_steps = set()
        for ex, ey in enemies:
            for _, nx, ny in get_safe_moves(ex, ey):
                enemy_next_steps.add((nx, ny))

        def evaluate_voronoi(start_x, start_y) -> int:
            """
            Calculates territory that belongs strictly to this bot.
            A cell is counted only if we can reach it in fewer steps than any enemy.
            """
            # Treat our current position as a wall since we leave a trail
            virtual_walls = state.walls | {(me_x, me_y)}
            
            # Phase 1: BFS for enemies
            # Determine how quickly any enemy can reach every open cell on the board.
            enemy_queue = deque([(ex, ey, 0) for ex, ey in enemies])
            enemy_visited = {(ex, ey): 0 for ex, ey in enemies}
            
            while enemy_queue:
                cx, cy, dist = enemy_queue.popleft()
                for _, nx, ny in get_safe_moves(cx, cy):
                    if (nx, ny) not in virtual_walls and (nx, ny) not in enemy_visited:
                        enemy_visited[(nx, ny)] = dist + 1
                        enemy_queue.append((nx, ny, dist + 1))

            # Phase 2: BFS for us
            # Flood-fill outward, but STOP expanding if an enemy can reach a cell faster.
            my_queue = deque([(start_x, start_y, 0)])
            my_visited = {(start_x, start_y): 0}
            
            score = 0
            
            while my_queue:
                cx, cy, dist = my_queue.popleft()
                enemy_dist = enemy_visited.get((cx, cy), float('inf'))
                
                # If we beat the enemy to this cell, claim it and keep exploring past it
                if dist < enemy_dist:
                    score += 1
                    for _, nx, ny in get_safe_moves(cx, cy):
                        if (nx, ny) not in virtual_walls and (nx, ny) not in my_visited:
                            my_visited[(nx, ny)] = dist + 1
                            my_queue.append((nx, ny, dist + 1))
                            
            return score

        best_move = Move.UP
        max_space = -1
        
        safe_moves = list(get_safe_moves(me_x, me_y))
        
        # Fallback if no safe moves exist
        if not safe_moves:
            return Move.UP 
            
        # 2. Filter out moves that step directly into enemy crosshairs 
        # unless they are the absolute ONLY options left.
        non_contested_moves = [(m, nx, ny) for m, nx, ny in safe_moves if (nx, ny) not in enemy_next_steps]
        moves_to_evaluate = non_contested_moves if non_contested_moves else safe_moves

        # 3. Evaluate each candidate move and pick the one with the most exclusive territory
        for move, nx, ny in moves_to_evaluate:
            space_available = evaluate_voronoi(nx, ny)
            
            if space_available > max_space:
                max_space = space_available
                best_move = move

        return best_move