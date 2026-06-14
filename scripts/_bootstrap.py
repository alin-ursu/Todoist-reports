"""Make the project root importable when scripts are run directly.

Run scripts from the project root:
    python scripts/report_yesterday.py
"""
import sys
from pathlib import Path

# scripts/ is one level below the project root
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
