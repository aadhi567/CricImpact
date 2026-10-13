"""
Bowling classification module.
Provides verified mapping of all bowlers in the dataset to Pace or Spin.
"""

import json
from pathlib import Path
from typing import Dict, Optional

# Load verified classification generated from Cricsheet bowler roster
_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
_JSON_PATH = _DATA_DIR / "bowler_classification.json"

_BOWLER_TYPE_CACHE: Optional[Dict[str, str]] = None


def get_bowler_classification() -> Dict[str, str]:
    """Returns dictionary mapping bowler names to 'Pace' or 'Spin'."""
    global _BOWLER_TYPE_CACHE
    if _BOWLER_TYPE_CACHE is None:
        if _JSON_PATH.exists():
            with open(_JSON_PATH, "r", encoding="utf-8") as f:
                _BOWLER_TYPE_CACHE = json.load(f)
        else:
            raise FileNotFoundError(f"Bowler classification file not found at {_JSON_PATH}")
    return _BOWLER_TYPE_CACHE


def classify_bowler(bowler_name: str) -> str:
    """Returns 'Pace' or 'Spin' for a given bowler."""
    classification = get_bowler_classification()
    return classification.get(bowler_name, "Pace")
