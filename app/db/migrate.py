from __future__ import annotations

import os
import pathlib
import subprocess
import sys

from app.config import Settings


def run() -> int:
    settings = Settings.from_env()
    migration_file = pathlib.Path(__file__).parent / "migrations" / "0001_bootstrap.sql"
    if not migration_file.exists():
        print(f"Migration file missing: {migration_file}")
        return 1

    psql_bin = os.getenv("PSQL_BIN", "psql")
    cmd = [psql_bin, settings.database_url, "-v", "ON_ERROR_STOP=1", "-f", str(migration_file)]
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode != 0:
        print(completed.stdout)
        print(completed.stderr)
        return completed.returncode
    print(completed.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
