import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "clinical-evidence" / "shared" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))


@pytest.fixture
def workspace(tmp_path):
    """A throwaway workspace holding copies of the fixture files."""
    for name in ("ledger_a.yaml", "refs_b.yaml", "ledger_v1_0.yaml"):
        shutil.copy(FIXTURES / name, tmp_path / name)
    return tmp_path
