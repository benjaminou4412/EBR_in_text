import random
from typing import Tuple


def draw_challenge() -> Tuple[int, str]:
    # Distribution: +1 x6, 0 x10, -1 x7, -2 x1
    modifiers = [
        *([+1] * 6),
        *([0] * 10),
        *([-1] * 7),
        *([-2] * 1),
    ]
    mod = random.choice(modifiers)
    symbol = random.choice(["sun", "mountain", "crest"])  # uniform
    return mod, symbol

