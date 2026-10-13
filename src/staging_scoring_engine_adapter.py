"""
Phase 9.1: Staging-Only Scoring Engine Adapter.

Provides an isolated, configuration-validated interface for invoking:
1. Approved Phase 7U scoring engine (src.contribution_framework).
2. Research-only Phase 8.5.1 Strategy 4 engine (src.phase8_5_hyper_score_damping).

Governance Rules:
- Defaults strictly to Phase 7U (APPROVED_PRODUCTION).
- Unknown engine versions raise explicit ValueError.
- Fails safely if candidate module is disabled or unavailable.
- Zero modification to src/contribution_framework.py.
"""

from enum import Enum
import hashlib
from pathlib import Path
from typing import Any, Dict, Optional


# Approved governance checksum for Phase 7U production
EXPECTED_PHASE7U_CHECKSUM = "8C5CFBC613D583CB7B70887C9F8BCE489912C8370FCBD96EF56FBE7E9C8AA277"
PROD_FRAMEWORK_PATH = Path(__file__).resolve().parent / "contribution_framework.py"


class ScoringEngineVersion(str, Enum):
    """Supported scoring engine version identifiers."""
    PHASE_7U = "phase7u"
    PHASE_8_5_STRATEGY_4 = "v8.5.1-strategy4-hybrid"


class ScoringEngineError(Exception):
    """Base error for scoring engine adapter failures."""
    pass


class UnknownEngineError(ScoringEngineError):
    """Raised when an unrecognized engine version identifier is requested."""
    pass


class CandidateEngineUnavailableError(ScoringEngineError):
    """Raised when candidate engine cannot be loaded or is disabled."""
    pass


class ProductionChecksumMismatchError(ScoringEngineError):
    """Raised when production file checksum differs from approved governance baseline."""
    pass


def verify_production_checksum() -> str:
    """
    Verifies that src/contribution_framework.py exactly matches the approved SHA256.
    Raises ProductionChecksumMismatchError if altered.
    """
    if not PROD_FRAMEWORK_PATH.exists():
        raise FileNotFoundError(f"Production framework not found at {PROD_FRAMEWORK_PATH}")
    
    with open(PROD_FRAMEWORK_PATH, "rb") as f:
        actual_sha256 = hashlib.sha256(f.read()).hexdigest().upper()
        
    if actual_sha256 != EXPECTED_PHASE7U_CHECKSUM:
        raise ProductionChecksumMismatchError(
            f"Production checksum mismatch! Expected: {EXPECTED_PHASE7U_CHECKSUM}, Got: {actual_sha256}"
        )
    return actual_sha256


class StagingScoringEngineAdapter:
    """
    Staging-only adapter executing either Phase 7U (Production) or Strategy 4 (Candidate).
    """

    def __init__(
        self,
        engine_version: ScoringEngineVersion = ScoringEngineVersion.PHASE_7U,
        strict_checksum_verification: bool = True
    ):
        if strict_checksum_verification:
            verify_production_checksum()

        # Validate engine version
        if not isinstance(engine_version, ScoringEngineVersion):
            try:
                engine_version = ScoringEngineVersion(engine_version)
            except ValueError:
                raise UnknownEngineError(f"Unsupported scoring engine version: {engine_version}")

        self.engine_version = engine_version

    def calculate_score(self, row: Any) -> Dict[str, Any]:
        """
        Calculates contribution score using the configured engine.
        Returns a standardized dictionary with metadata and scores.
        """
        # Always verify production integrity
        verify_production_checksum()

        if self.engine_version == ScoringEngineVersion.PHASE_7U:
            return self._calculate_phase7u(row)
        elif self.engine_version == ScoringEngineVersion.PHASE_8_5_STRATEGY_4:
            return self._calculate_strategy4(row)
        else:
            raise UnknownEngineError(f"Unhandled engine version: {self.engine_version}")

    def _calculate_phase7u(self, row: Any) -> Dict[str, Any]:
        """Invokes approved Phase 7U production scoring engine."""
        from src.contribution_framework import compute_production_contribution

        res = compute_production_contribution(row)
        return {
            "engine_version": ScoringEngineVersion.PHASE_7U.value,
            "final_contribution_score": res.get("final_contribution_score"),
            "raw_contribution": res.get("raw_contribution"),
            "adjusted_p2": res.get("adjusted_p2"),
            "adjusted_p3": res.get("adjusted_p3"),
            "score_perf": res.get("score_perf"),
            "score_state": res.get("score_state"),
            "leverage": res.get("leverage"),
            "is_valid": res.get("is_valid", True),
            "is_negligible": res.get("is_negligible", False),
            "diagnostic_info": {
                "engine_type": "production_phase7u",
                "checksum": EXPECTED_PHASE7U_CHECKSUM,
            }
        }

    def _calculate_strategy4(self, row: Any) -> Dict[str, Any]:
        """Invokes research-only Phase 8.5 Strategy 4 engine."""
        try:
            from src.phase8_5_hyper_score_damping import compute_phase8_5_unified_contribution
        except ImportError as e:
            raise CandidateEngineUnavailableError(
                f"Candidate Strategy 4 engine module unavailable: {e}"
            ) from e

        res = compute_phase8_5_unified_contribution(row, strategy="hybrid", apply_preservation=True)
        return {
            "engine_version": ScoringEngineVersion.PHASE_8_5_STRATEGY_4.value,
            "final_contribution_score": res.get("final_contribution_score"),
            "raw_p3": res.get("raw_p3"),
            "p3_score": res.get("p3_score"),
            "adjusted_p2": res.get("adjusted_p2"),
            "adjusted_p3": res.get("adjusted_p3"),
            "shift": res.get("shift", 0.0),
            "production_final": res.get("production_final"),
            "is_valid": res.get("is_valid", True),
            "diagnostic_info": {
                "engine_type": "candidate_strategy4_hybrid",
                "strategy": "hybrid",
                "preservation_floor": 64.0,
            }
        }
