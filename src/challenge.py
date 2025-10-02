import random
from .models import Symbol


def draw_challenge() -> tuple[int, Symbol]:
    # Distribution: +1 x6, 0 x10, -1 x7, -2 x1
    modifiers = [
        *([+1] * 6),
        *([0] * 10),
        *([-1] * 7),
        *([-2] * 1),
    ]
    mod = random.choice(modifiers)
    symbol = random.choice([Symbol.SUN, Symbol.MOUNTAIN, Symbol.CREST])  # uniform
    return mod, symbol

