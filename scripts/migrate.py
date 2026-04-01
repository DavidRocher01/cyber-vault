"""
migrate.py — Pilotage des migrations Alembic.
Usage :
  python scripts/migrate.py upgrade head
  python scripts/migrate.py downgrade -1
  python scripts/migrate.py revision --autogenerate -m "description"
"""
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).parent.parent / "backend"


def run_alembic(args: list[str]):
    result = subprocess.run(
        ["python", "-m", "alembic"] + args,
        cwd=BACKEND_DIR,
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <alembic command> [args]")
        print("  Ex: python scripts/migrate.py upgrade head")
        sys.exit(1)
    run_alembic(sys.argv[1:])
