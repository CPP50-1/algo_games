"""Reference bot for the maze race -- shows the minimum needed to
implement the Bot API against a MazeView.

Strategy: plain breadth-first search over the grid, treating every cell
transition as cost 1 and completely ignoring the `terrain` weights. This
finds the path with the fewest cells, which is exactly wrong the moment
terrain costs vary -- on the default map this bot confidently walks
straight through the expensive band because it "looks" shortest, and
loses to anything that instead finds the shortest path *by weight*
(Dijkstra, or A* with an admissible heuristic).
"""
import heapq
from collections import deque

from engine.bot import Bot, Move


class VictorMazeBot(Bot):
    """
    self_id - - your bot id
    width, height, turn
    position - - your(x, y)
    goal - - the shared target cell
    busy_for - - turns remaining before you can move again(always 0 when decide() is actually being called on you)
    terrain - - height x width grid of per - cell movement costs
    positions - - {bot_id: (x, y)} for every bot still racing
    
    
    visited : [(x, y)] 
    next_cells = heapq[(weight, (x, y), path)]
    grid = {(x, y) : [(neighbor, value)]}
    
    build grid OK
    start next_cells with starting pos OK
    while next_cells : pop next_cell and calculate neighbors + add them to next_cells
    when reaching objective, return path.
    Use paths next turns
    """
    _path : deque


    def decide(self, state) -> Move:

        my_pos = state.position

        def build_path(state):

            grid = {}
            w, h = state.width, state.height
            visited_cells = [state.position]

            # building grid
            for x in range(w):
                for y in range(h):
                    grid[(x, y)] = []
                    for i in range(-1, 2, 2):  # 2 loops (-1, +1)
                        if w > x + i >= 0:  # checking left and right cells as neighbors
                            grid[(x, y)].append(((x + i, y), state.terrain[y][x+i]))
                        if h > y + i >= 0:  # checking up and down cells as neighbors
                            grid[(x, y)].append(((x, y + i), state.terrain[y+i][x]))


            next_cells = [(0, my_pos, [])]
            heapq.heapify(next_cells)


            while next_cells:
                current_cell = heapq.heappop(next_cells)
                visited_cells.append(current_cell[1])
                if current_cell[1] == state.goal:
                    # if we reached the goal, we return the path
                    path = deque(current_cell[2])
                    self._path = path
                    break
                for neighbor_cell in grid[current_cell[1]]:
                    if neighbor_cell[0] not in visited_cells:
                        heapq.heappush(next_cells, (current_cell[0] + neighbor_cell[1], neighbor_cell[0],
                                                    current_cell[2] + [neighbor_cell[0]]))


        def step_toward(position, target):
            dx = target[0] - position[0]
            dy = target[1] - position[1]
            if dx > 0:
                return Move.RIGHT
            if dx < 0:
                return Move.LEFT
            if dy > 0:
                return Move.DOWN
            else:
                return Move.UP


        build_path(state)

        return step_toward(my_pos, self._path.popleft())


