#!/usr/bin/env python3
"""Compare two Lighthouse JSON reports and print a formatted score table.

Exit code 1 if any category regresses by more than 5 percentage points.
"""

import argparse
import json
import sys

CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]
REGRESSION_THRESHOLD = -0.05  # 5 percentage points


def load_scores(path: str) -> dict[str, float]:
    with open(path) as f:
        data = json.load(f)
    return {
        cat: (data["categories"].get(cat, {}).get("score", 0) or 0)
        for cat in CATEGORIES
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", help="Path to baseline Lighthouse JSON report")
    parser.add_argument("latest", help="Path to latest Lighthouse JSON report")
    args = parser.parse_args()

    baseline = load_scores(args.baseline)
    latest = load_scores(args.latest)

    print(f"{'Category':<20} {'Baseline':>10} {'Latest':>10} {'Delta':>10}")
    print("-" * 52)

    regressed = False
    for cat in CATEGORIES:
        bs = baseline[cat]
        ls = latest[cat]
        delta = ls - bs
        sign = "+" if delta > 0 else ""
        flag = " !!!" if delta < REGRESSION_THRESHOLD else ""
        if delta < REGRESSION_THRESHOLD:
            regressed = True
        print(f"{cat:<20} {bs * 100:>9.0f}% {ls * 100:>9.0f}% {sign}{delta * 100:>8.0f}%{flag}")

    if regressed:
        print("\nRegression detected (>5% drop in at least one category).")
        sys.exit(1)


if __name__ == "__main__":
    main()
