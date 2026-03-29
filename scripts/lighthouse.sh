#!/usr/bin/env bash
set -euo pipefail

LIGHTHOUSE_DIR="${1:-.}/lighthouse"
URL="${2:-https://mthds.ai/latest/}"
MODE="${3:-run}"  # run | baseline | compare

mkdir -p "$LIGHTHOUSE_DIR"

run_audit() {
    local output_path="$1"
    npx lighthouse@latest "$URL" \
        --output json --output html \
        --output-path "$output_path" \
        --chrome-flags="--headless=new --no-sandbox" \
        --quiet
}

case "$MODE" in
    baseline)
        run_audit "$LIGHTHOUSE_DIR/baseline"
        echo "Baseline saved to $LIGHTHOUSE_DIR/baseline.report.{json,html}"
        ;;
    run)
        TIMESTAMP=$(date +%Y%m%d-%H%M%S)
        run_audit "$LIGHTHOUSE_DIR/$TIMESTAMP"
        echo "Reports saved to $LIGHTHOUSE_DIR/$TIMESTAMP.report.{json,html}"
        ;;
    compare)
        if [ ! -f "$LIGHTHOUSE_DIR/baseline.report.json" ]; then
            echo "ERROR: No baseline found. Run 'make lighthouse-baseline' first."
            exit 1
        fi
        LATEST=$(ls -t "$LIGHTHOUSE_DIR"/*.report.json 2>/dev/null | grep -v baseline | head -1)
        if [ -z "$LATEST" ]; then
            echo "ERROR: No lighthouse reports found. Run 'make lighthouse' first."
            exit 1
        fi
        echo "Baseline: $LIGHTHOUSE_DIR/baseline.report.json"
        echo "Latest:   $LATEST"
        echo ""
        python3 -c "
import json
b = json.load(open('$LIGHTHOUSE_DIR/baseline.report.json'))
l = json.load(open('$LATEST'))
cats = ['performance', 'accessibility', 'best-practices', 'seo']
print(f'{\"Category\":<20} {\"Baseline\":>10} {\"Latest\":>10} {\"Delta\":>10}')
print('-' * 52)
for c in cats:
    bs = b['categories'].get(c, {}).get('score', 0) or 0
    ls = l['categories'].get(c, {}).get('score', 0) or 0
    d = ls - bs
    sign = '+' if d > 0 else ''
    flag = ' !!!' if d < -0.05 else ''
    print(f'{c:<20} {bs*100:>9.0f}% {ls*100:>9.0f}% {sign}{d*100:>8.0f}%{flag}')
"
        ;;
    *)
        echo "Usage: $0 <project_dir> <url> <run|baseline|compare>"
        exit 1
        ;;
esac
