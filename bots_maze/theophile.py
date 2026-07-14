"""
Strategy: A* Search using Manhattan distance as the heuristic. 
Unlike the reference BFS bot, this actively reads the `terrain` grid 
to calculate the true 'turn cost' of every path. It will automatically 
detour around the heavy cost-5 patches if walking around is faster 
than walking through.
"""
import heapq
from engine.bot import Bot, Move

def manhattan_distance(p1, p2):
    """Calculates the minimum possible unweighted steps between two points."""
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def _a_star_next_step(position, goal, width, height, terrain):
    """
    Returns the next cell to move to along the lowest-cost path
    using the A* search algorithm.
    """
    if position == goal:
        return None

    # Priority queue stores tuples: (f_score, tie_breaker_count, (x, y))
    # Using a tie-breaker prevents heapq from crashing if f_scores are identical
    open_set = []
    count = 0
    heapq.heappush(open_set, (0, count, position))

    # Maps a cell to the cell that precedes it on the cheapest path
    came_from = {}

    # Tracks the exact cost from start to a given cell
    g_score = {position: 0}

    while open_set:
        _, _, current = heapq.heappop(open_set)

        # If we reached the goal, reconstruct the path backwards
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            # Return the very first step to take from our current position
            return path[-1] if path else None

        cx, cy = current

        for move in Move:
            nx, ny = cx + move.dx, cy + move.dy

            # Boundary check
            if not (0 <= nx < width and 0 <= ny < height):
                continue

            neighbor = (nx, ny)

            # Extract the actual movement cost from the game state.
            # The terrain grid is height x width (List of rows), so access is [y][x]
            step_cost = terrain[ny][nx]

            # Calculate the exact cost to reach the neighbor
            tentative_g_score = g_score[current] + step_cost

            # If we found a strictly cheaper path to this neighbor, record it
            if tentative_g_score < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                
                # Apply the A* formula: f(n) = g(n) + h(n)
                f_score = tentative_g_score + manhattan_distance(neighbor, goal)
                
                count += 1
                heapq.heappush(open_set, (f_score, count, neighbor))

    return None

class TheophileBot(Bot):
    def decide(self, state) -> Move:
        # Calculate the optimal next step based on real terrain weights
        target = _a_star_next_step(
            state.position, 
            state.goal, 
            state.width, 
            state.height, 
            state.terrain
        )
        
        # Fallback if no path exists (or we are already there)
        if target is None:
            return Move.UP

        # Convert the target coordinate back into a directional Move
        dx = target[0] - state.position[0]
        dy = target[1] - state.position[1]
        
        for move in Move:
            if (move.dx, move.dy) == (dx, dy):
                return move
                
        return Move.UP