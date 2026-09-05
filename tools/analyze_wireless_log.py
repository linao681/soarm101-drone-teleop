#!/usr/bin/env python3
"""Summarize a CSV produced by wireless_teleoperate.py."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from tools.soarm_wireless.metrics import summarize_rows
except ModuleNotFoundError:
    from soarm_wireless.metrics import summarize_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()
    with args.csv_path.open(newline="", encoding="utf-8") as stream:
        summary = summarize_rows(csv.DictReader(stream))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
