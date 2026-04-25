from __future__ import annotations

import json
import pathlib

from app.eval.harness import EvalHarness
from app.main import Application


def main() -> int:
    app = Application()
    root = pathlib.Path.cwd()
    harness = EvalHarness(app, root / "eval" / "datasets")
    summary = harness.run()
    thresholds = json.loads((root / "eval" / "release_gates.json").read_text(encoding="utf-8"))
    gate = harness.release_gate(summary, thresholds)
    print(json.dumps({"summary": summary, "gate": gate}, indent=2))
    return 0 if gate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
