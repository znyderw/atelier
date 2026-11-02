#!/usr/bin/env python3
"""Read-only compatibility report. --baseline explicitly saves an app-local baseline."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from atelier.core import *
parser=argparse.ArgumentParser();parser.add_argument('--baseline',action='store_true'); args=parser.parse_args()
p=Paths(); report=diagnostics(p,Desktop(p,Store(p)))
if args.baseline: atomic_json(p.data/'compatibility-baseline.json',report)
print(json.dumps(report,ensure_ascii=False,indent=2))
