import json, subprocess, sys
from pathlib import Path
ROOT = Path(r"F:\github\ziwei-network-analyst")
CONV = ROOT / "packages" / "hypergraph" / "chart2hypergraph.py"
REAL = ROOT / "fixtures" / "real-1990"
charts = sorted([p for p in REAL.glob("1990-*.json") if "hypergraph" not in p.name])
for i, c in enumerate(charts, 1):
    subprocess.check_call([sys.executable, str(CONV), str(c)], cwd=str(ROOT), stdout=subprocess.DEVNULL)
    print(f"{i}/{len(charts)}", c.name)
print("done")