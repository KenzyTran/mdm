"""Tests for CooldownRegistry semantics (PORT-07, D-20/D-21).

Per D-21, earliest re-entry = exit_bar + cooldown_days + 1 (bar D+6 when
cooldown_days=5). Per D-20, MDM-SELL-driven exits are EXEMPT from cooldown;
that exemption is enforced at the ENGINE layer by simply not calling
register() for MDM SELL exits. This class has no special casing — the engine
plan must respect this contract.
"""
from strategies.portfolio.state import CooldownRegistry


def test_cooldown_blocks_d_plus_5():
    reg = CooldownRegistry()
    reg.register(ticker="AAA", exit_bar_idx=10)
    # bar 15 = D+5, still blocked (earliest re-entry = 10 + 5 + 1 = 16)
    assert reg.is_cooling("AAA", current_bar_idx=15, cooldown_days=5) is True


def test_cooldown_allows_d_plus_6():
    reg = CooldownRegistry()
    reg.register(ticker="AAA", exit_bar_idx=10)
    assert reg.is_cooling("AAA", current_bar_idx=16, cooldown_days=5) is False


def test_cooldown_unknown_ticker():
    reg = CooldownRegistry()
    assert reg.is_cooling("BBB", 20, 5) is False


def test_cooldown_mdm_sell_exempt():
    # Per D-20, MDM SELL exits do NOT get registered by the engine.
    # Simulating that: never call register() → is_cooling must return False.
    reg = CooldownRegistry()
    # (no register call — this is what the engine does on MDM SELL exit)
    assert reg.is_cooling("AAA", current_bar_idx=12, cooldown_days=5) is False
