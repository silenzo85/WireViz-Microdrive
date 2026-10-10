# -*- coding: utf-8 -*-
import shutil
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[1] / "demo"


@pytest.fixture
def demo_dir(tmp_path):
    """Kopia danych demonstracyjnych - test moze je psuc."""
    k = tmp_path / "dane"
    shutil.copytree(DEMO, k)
    return k


@pytest.fixture
def dopisz():
    def _dopisz(katalog, plik, *linie):
        p = Path(katalog) / plik
        if not p.exists():
            raise FileNotFoundError(p)
        with open(p, "a", encoding="utf-8") as f:
            for l in linie:
                f.write(l + "\n")
    return _dopisz


@pytest.fixture
def zastap():
    def _zastap(katalog, plik, stare, nowe):
        p = Path(katalog) / plik
        t = p.read_text(encoding="utf-8-sig")
        assert stare in t, f"brak '{stare}' w {plik}"
        p.write_text(t.replace(stare, nowe, 1), encoding="utf-8")
    return _zastap
