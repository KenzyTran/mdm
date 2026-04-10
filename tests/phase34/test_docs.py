"""Smoke tests for Phase 34 documentation requirements."""
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def test_rules_doc_has_locked_params():
    """DOC-01: rules doc reflects locked rank-1 params."""
    content = (REPO / "docs" / "rules_canslim_mdm.md").read_text()
    assert "c_yoy" in content, "Missing c_yoy parameter"
    assert "0.25" in content, "Missing locked c_yoy value 0.25"
    assert "rank-1" in content, "Missing rank-1 reference"
    assert "OOS Performance" in content, "Missing OOS Performance section"
    assert "0.448" in content, "Missing Sharpe_rf3 value"


def test_rules_doc_has_all_sections():
    """DOC-01: rules doc preserves all required sections."""
    content = (REPO / "docs" / "rules_canslim_mdm.md").read_text()
    for section in ["MDM Gate", "Entry Feed", "Exit Priority Chain",
                    "Cooldown", "Costs", "NAV Rule", "Locked Parameters"]:
        assert section in content, f"Missing section: {section}"


def test_data_dict_exists():
    """DOC-02: data dictionary exists."""
    path = REPO / "docs" / "data_dictionary.md"
    assert path.exists(), "docs/data_dictionary.md does not exist"


def test_data_dict_covers_connectors():
    """DOC-02: data dictionary documents all connectors."""
    content = (REPO / "docs" / "data_dictionary.md").read_text()
    for module in ["connectors/postgres.py", "connectors/mysql.py",
                   "connectors/adjust.py", "connectors/eps.py"]:
        assert module in content, f"Missing connector: {module}"


def test_data_dict_covers_scorer():
    """DOC-02: data dictionary documents CANSLIM scorer."""
    content = (REPO / "docs" / "data_dictionary.md").read_text()
    assert "CanslimScorer" in content, "Missing CanslimScorer"
    assert "CanslimConfig" in content or "canslim/config" in content, "Missing config reference"


def test_data_dict_has_data_sources():
    """DOC-02: data dictionary has data sources section."""
    content = (REPO / "docs" / "data_dictionary.md").read_text()
    assert "stock_eod" in content, "Missing stock_eod table reference"
    assert "ratios_stock" in content, "Missing ratios_stock table reference"
