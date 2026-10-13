"""
Alias and Re-export of Phase 7Q P3 Neutral-State Preservation Engine.
Ensures backward compatibility across all test suites and diagnostics.
"""

from src.phase7q_p3_neutral_state_preservation import (
    PRE_MODIFICATION_HASHES,
    make_synthetic_row,
    evaluate_innings_phase7o_vs_phase7q,
    run_synthetic_test_matrix,
    run_sensitivity_analysis,
    run_historical_backtest,
    run_real_case_studies,
    run_leakage_and_invariance_audit,
    verify_governance_and_backups,
    main,
)

if __name__ == "__main__":
    main()
