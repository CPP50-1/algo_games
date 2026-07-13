import heapq
import json
from collections import deque
from pathlib import Path

from engine.bot import Bot, Move


class VictorMazeBot(Bot):
    """
    calculate the path to follow in turn 0, then save it to a json in /tmp. Then load the path in subsequent turns,
    following it.
    will work with more complex mazes where you could have to go left for the fastest path
    """


    def decide(self, state) -> Move:

        my_pos = state.position
        scratch = Path(f"/tmp/{state.self_id}_memory.json")
        memory = json.loads(scratch.read_text()) if scratch.exists() else []

        def build_path(state):

            grid = {}
            w, h = state.width, state.height
            visited_cells = set()

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
                if current_cell[1] in visited_cells:
                    continue
                visited_cells.add(current_cell[1])
                if current_cell[1] == state.goal:
                    # if we reached the goal, we save the path
                    memory.extend(current_cell[2])
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


        if state.turn == 0:
            build_path(state)

        final_path = deque(memory)
        move = step_toward(my_pos, final_path.popleft())
        scratch.write_text(json.dumps(list(final_path)))


        return move

