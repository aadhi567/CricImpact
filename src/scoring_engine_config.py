"""
CricImpact Production Scoring Engine Configuration.
Defines active scoring engine version, routing parameters, and governance metadata.
"""

import os
import json
from pathlib import Path
from enum import Enum

class ScoringEngineVersion(str, Enum):
    PHASE_7U = "phase7u"
    PHASE_8_5_STRATEGY_4 = "v8.5.1-strategy4-hybrid"

CONFIG_FILE = Path("data/scoring_engine_config.json")
_DEFAULT_ENGINE = ScoringEngineVersion.PHASE_7U.value

def get_active_scoring_engine() -> str:
    """Returns the currently active scoring engine version identifier."""
    # Priority 1: Environment variable
    if "CRICIMPACT_SCORING_ENGINE" in os.environ:
        return os.environ["CRICIMPACT_SCORING_ENGINE"]
    
    # Priority 2: Persistent config file
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return data.get("active_engine", _DEFAULT_ENGINE)
        except Exception:
            pass
            
    return _DEFAULT_ENGINE

def set_active_scoring_engine(engine_version: str) -> None:
    """Sets the active scoring engine version both in environment and persistent config."""
    os.environ["CRICIMPACT_SCORING_ENGINE"] = str(engine_version)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active_engine": str(engine_version),
        "target_engine": ScoringEngineVersion.PHASE_8_5_STRATEGY_4.value,
        "baseline_engine": ScoringEngineVersion.PHASE_7U.value,
    }
    CONFIG_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

