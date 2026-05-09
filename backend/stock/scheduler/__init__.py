"""
Backward-compatibility re-exports for refactored stock scheduler module.
All original function names remain importable from their original paths.
"""
from stock.infrastructure.order_execution import (
    wait_for_target_position,
    check_min_position_requirement,
    execute_two_step_opening,
)
from stock.infrastructure.order_signals import (
    is_trading,
    execute_entry_order,
    execute_add_on_order,
    execute_exit_order,
    execute_rollover_order,
    process_signals_by_type,
)
from stock.infrastructure.stop_loss_executor import (
    execute_stop_loss_exit,
    check_and_execute_stop_loss,
)
from stock.core.atr import (
    calculate_atr,
    price_gap_protection,
)
from stock.core.position_sizing import (
    calculate_unit_lots,
)
from stock.core.performance import (
    save_daily_snapshot,
    calculate_rolling_metrics,
    update_account_summary,
    update_all_performance_metrics,
    get_dashboard_metrics,
    _get_default_dashboard_metrics,
)
