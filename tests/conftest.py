import sys
from pathlib import Path

# Find the actual project root regardless of where tests run from
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / "main.py").exists():
        if str(current) not in sys.path:
            sys.path.insert(0, str(current))
        break
    current = current.parent