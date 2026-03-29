#!/usr/bin/env bash
set -euo pipefail

LIGHTHOUSE_DIR="${1:-.}/lighthouse"
URL="${2:-https://mthds.ai/latest/}"
MODE="${3:-run}"  # run | baseline | compare

mkdir -p "$LIGHTHOUSE_DIR"

run_audit() {
    local output_path="$1"
    npx lighthouse@12 "$URL" \
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
        LATEST=$(ls -t "$LIGHTHOUSE_DIR"/*.report.json 2>/dev/null | grep -v baseline | head -1 || true)
        if [ -z "$LATEST" ]; then
            echo "ERROR: No lighthouse reports found. Run 'make lighthouse' first."
            exit 1
        fi
        echo "Baseline: $LIGHTHOUSE_DIR/baseline.report.json"
        echo "Latest:   $LATEST"
        echo ""
        SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
        "$SCRIPT_DIR/../.venv/bin/python" "$SCRIPT_DIR/lighthouse_compare.py" \
            "$LIGHTHOUSE_DIR/baseline.report.json" "$LATEST"
        ;;
    *)
        echo "Usage: $0 <project_dir> <url> <run|baseline|compare>"
        exit 1
        ;;
esac
