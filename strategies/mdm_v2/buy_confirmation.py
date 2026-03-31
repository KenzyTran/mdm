"""
BUY Confirmation Module (v5.0, BUY-02)

Stateful post-FTD confirmation window tracker. After an FTD signal
passes the BuyFilter, the engine waits N days before committing BUY.

During the confirmation window:
- If DD count exceeds max_dd, the FTD is canceled (rejected).
- If the window completes cleanly, BUY is confirmed at the day-N close price
  (not the original FTD price, per D-05).

CRITICAL: DD check order -- cancellation is checked BEFORE completion
on each day (per pitfall 4). A DD on the final day that pushes count
over max_dd results in rejection, not confirmation.

When disabled (buy_confirmation_enabled=False), submit_ftd() is a no-op
and process_day() always returns (False, False, 0.0).
"""

from .config import MDMV2Config


class BuyConfirmation:
    """Tracks post-FTD confirmation window."""

    def __init__(self, config: MDMV2Config):
        self.config = config
        self._pending = False
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = None

    def submit_ftd(self, date):
        """Start a new confirmation window for an FTD signal.

        If disabled, this is a no-op. If already pending, resets the window.

        Args:
            date: The date of the FTD signal.
        """
        if not self.config.buy_confirmation_enabled:
            return

        self._pending = True
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = date

    def process_day(self, is_dd: bool, close: float) -> tuple:
        """Process one day during the confirmation window.

        Args:
            is_dd: Whether today is a distribution day (computed side-effect-free
                   by the engine, NOT via dd_counter.check_distribution_day).
            close: Today's closing price.

        Returns:
            Tuple of (confirmed, rejected, entry_price):
            - (True, False, close) if confirmation window completed cleanly
            - (False, True, 0.0) if FTD canceled due to DD threshold
            - (False, False, 0.0) if still pending or disabled
        """
        if not self.config.buy_confirmation_enabled or not self._pending:
            return (False, False, 0.0)

        self._days_elapsed += 1

        if is_dd:
            self._dd_count += 1

        # CRITICAL ORDER (per pitfall 4): Check cancellation FIRST
        if self._dd_count > self.config.confirmation_max_dd:
            self.reset()
            return (False, True, 0.0)

        # Then check completion
        if self._days_elapsed >= self.config.confirmation_window_days:
            self.reset()
            return (True, False, close)

        return (False, False, 0.0)

    def is_pending(self) -> bool:
        """Return True if a confirmation window is active."""
        return self._pending

    def reset(self):
        """Reset all state to initial values."""
        self._pending = False
        self._days_elapsed = 0
        self._dd_count = 0
        self._original_ftd_date = None
