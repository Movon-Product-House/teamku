from pathlib import Path

MAX_LINES = 600
ROOT = Path(__file__).resolve().parents[1]
# Temporary: legacy files split up and deleted in U12.
EXEMPT = {"src/movon_hr/modules/api.py", "src/movon_hr/core/persistence.py"}


def test_python_files_stay_under_max_lines() -> None:
    too_long = {
        rel: n
        for p in [*(ROOT / "src").rglob("*.py"), *(ROOT / "tests").rglob("*.py")]
        if (rel := p.relative_to(ROOT).as_posix()) not in EXEMPT
        and (n := len(p.read_text(encoding="utf-8").splitlines())) > MAX_LINES
    }
    assert not too_long, f"Split files over {MAX_LINES} lines: {too_long}"
