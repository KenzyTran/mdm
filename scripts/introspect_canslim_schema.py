"""Introspect Postgres + MySQL schemas to lock CANSLIM column names.

Phase 29 plan 29-01 Task 2. Writes a JSON artifact with the discovered
columns and "best guess" locked names for downstream plans (29-02..29-09).

Exit codes:
    0 - all locked fields resolved unambiguously
    2 - one or more locked fields ambiguous (see `notes` in JSON output)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import text

from connectors.postgres import get_engine as pg_get_engine
from connectors.mysql import get_engine as my_get_engine


PG_TABLES = [
    "stock_list",
    "stock_eod",
    "stock_foreign_eod",
    "index_eod",
    "stock_rs",
]

MY_TABLES = [
    "is_quarter_nonbank",
    "is_quarter_bank",
    "is_quarter_insurance",
    "is_quarter_stock",
    "ratios_stock",
    "rank_top_stocks",
]


def _safe_query(engine, sql: str, params: dict | None = None) -> list[dict]:
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql), params or {}).mappings().all()
            return [dict(r) for r in rows]
    except Exception as exc:  # pragma: no cover - introspection best-effort
        return [{"__error__": str(exc)}]


def introspect_postgres() -> dict[str, Any]:
    engine = pg_get_engine()
    out: dict[str, Any] = {}
    for tbl in PG_TABLES:
        rows = _safe_query(
            engine,
            """
            SELECT column_name AS name, data_type AS type
            FROM information_schema.columns
            WHERE table_name = :tbl
            ORDER BY ordinal_position
            """,
            {"tbl": tbl},
        )
        out[tbl] = rows
    return out


def introspect_mysql() -> dict[str, Any]:
    engine = my_get_engine()
    out: dict[str, Any] = {}
    for tbl in MY_TABLES:
        rows = _safe_query(
            engine,
            """
            SELECT column_name AS name, data_type AS type
            FROM information_schema.columns
            WHERE table_schema = DATABASE() AND table_name = :tbl
            ORDER BY ordinal_position
            """,
            {"tbl": tbl},
        )
        out[tbl] = rows
    return out


def _names(cols: list[dict]) -> list[str]:
    return [c["name"] for c in cols if "name" in c]


def _match(cols: list[dict], substrings: list[str]) -> list[str]:
    names = _names(cols)
    out = []
    for n in names:
        ln = n.lower()
        if any(s in ln for s in substrings):
            out.append(n)
    return out


def lock_columns(pg: dict, my: dict) -> tuple[dict, list[str]]:
    notes: list[str] = []
    locked: dict[str, Any] = {}

    # stock_list sector column
    sector_cands = _match(
        pg.get("stock_list", []),
        ["sector", "nganh", "industry", "nhom"],
    )
    if len(sector_cands) == 1:
        locked["stock_list_sector_column"] = sector_cands[0]
    elif len(sector_cands) > 1:
        locked["stock_list_sector_column"] = sector_cands[0]
        notes.append(
            f"AMBIGUOUS: stock_list sector candidates={sector_cands}; "
            f"chose first."
        )
    else:
        locked["stock_list_sector_column"] = None
        notes.append("AMBIGUOUS: no sector-like column found in stock_list")

    # is_quarter_nonbank EPS column
    eps_nonbank = _match(
        my.get("is_quarter_nonbank", []),
        ["eps", "loi_nhuan", "lai_co_ban"],
    )
    if eps_nonbank:
        locked["is_quarter_nonbank_eps_column"] = eps_nonbank[0]
        if len(eps_nonbank) > 1:
            notes.append(
                f"is_quarter_nonbank EPS candidates={eps_nonbank}; chose first"
            )
    else:
        locked["is_quarter_nonbank_eps_column"] = None
        notes.append("AMBIGUOUS: no EPS-like column in is_quarter_nonbank")

    # is_quarter_bank PPOP column
    ppop_bank = _match(
        my.get("is_quarter_bank", []),
        ["ppop", "pre_provision", "loi_nhuan_truoc_du_phong", "eps"],
    )
    if ppop_bank:
        locked["is_quarter_bank_ppop_column"] = ppop_bank[0]
        if len(ppop_bank) > 1:
            notes.append(
                f"is_quarter_bank PPOP candidates={ppop_bank}; chose first"
            )
    else:
        locked["is_quarter_bank_ppop_column"] = None
        notes.append("AMBIGUOUS: no PPOP-like column in is_quarter_bank")

    # publish/period date column (search both nonbank and bank)
    pub_cands = set()
    for tbl in ("is_quarter_nonbank", "is_quarter_bank"):
        for n in _match(
            my.get(tbl, []),
            ["publish", "period", "date", "ngay", "quy", "ky"],
        ):
            pub_cands.add(n)
    pub_list = sorted(pub_cands)
    if pub_list:
        locked["publish_date_column"] = pub_list[0]
        if len(pub_list) > 1:
            notes.append(
                f"publish/date candidates={pub_list}; chose first"
            )
    else:
        locked["publish_date_column"] = None
        notes.append("AMBIGUOUS: no publish/date column found")

    return locked, notes


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--output",
        type=Path,
        default=Path(
            ".planning/phases/29-vn100-universe-canslim-scorer/schema_lock.json"
        ),
    )
    args = p.parse_args()

    print("[introspect] Postgres...")
    pg = introspect_postgres()
    print("[introspect] MySQL...")
    my = introspect_mysql()

    locked, notes = lock_columns(pg, my)

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "postgres": pg,
        "mysql": my,
        "locked": locked,
        "notes": notes,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(f"[introspect] wrote {args.output}")
    print("[introspect] locked:")
    for k, v in locked.items():
        print(f"  {k} = {v!r}")
    if notes:
        print("[introspect] notes:")
        for n in notes:
            print(f"  - {n}")
        ambiguous = any(n.startswith("AMBIGUOUS") for n in notes)
        return 2 if ambiguous else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
