from engine.bot import Bot, Move


class SergioBot(Bot):
    def decide(self, state):

        return Move.UP
