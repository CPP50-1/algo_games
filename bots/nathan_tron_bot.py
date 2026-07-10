from collections import deque
from engine.bot import Bot, Move

ALL_MOVES = [Move.UP, Move.DOWN, Move.LEFT, Move.RIGHT]


class MonBot(Bot):
    def decide(self, state) -> Move:
        me = state.positions[state.self_id]
        opponents = [bid for bid in state.alive if bid != state.self_id]

        def is_safe(pos) -> bool:
            x, y = pos
            if not (0 <= x < state.width and 0 <= y < state.height):
                return False
            return pos not in state.walls

        def flood_fill(start) -> int:
            """Combien de cases j'atteins depuis `start` (BFS)."""
            visited = {start}
            queue = deque([start])
            count = 0
            while queue:
                x, y = queue.popleft()
                count += 1
                for move in ALL_MOVES:
                    neighbor = (x + move.dx, y + move.dy)
                    if neighbor in visited:
                        continue
                    if is_safe(neighbor):
                        visited.add(neighbor)
                        queue.append(neighbor)
            return count

        def collision_risk(pos) -> bool:
            """
            Vrai si un adversaire est juste à côté de `pos` -- il pourrait
            s'y déplacer ce même tour, ce qui nous tuerait tous les deux
            (collision frontale = cause n°1 d'égalité). On évite ça en
            priorité.
            """
            for opp_id in opponents:
                ox, oy = state.positions[opp_id]
                if abs(ox - pos[0]) + abs(oy - pos[1]) == 1:
                    return True
            return False

        candidates = []  # (move, next_pos)
        for move in (Move.UP, Move.RIGHT, Move.DOWN, Move.LEFT):
            next_pos = (me[0] + move.dx, me[1] + move.dy)
            if is_safe(next_pos):
                candidates.append((move, next_pos))

        if not candidates:
            return Move.UP  # rien n'est sûr, on meurt de toute façon

        # On écarte d'abord les mouvements risqués de collision frontale,
        # sauf s'il ne reste vraiment que ça.
        safe = [c for c in candidates if not collision_risk(c[1])]
        pool = safe if safe else candidates

        # Parmi ce qui reste, on prend celui qui laisse le plus d'espace.
        best_move, best_score = None, -1
        for move, next_pos in pool:
            score = flood_fill(next_pos)
            if score > best_score:
                best_score = score
                best_move = move

        return best_move