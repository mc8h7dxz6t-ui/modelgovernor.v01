import sys
from pathlib import Path

# finance-governor/ on sys.path for platforms.common imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
