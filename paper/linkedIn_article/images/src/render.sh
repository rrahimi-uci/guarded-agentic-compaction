#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Render the LinkedIn article figures.
#
# Headless Chrome performs the text layout, so a string that is too long for
# its box wraps instead of spilling.  The previous hand-authored SVGs hard-coded
# every line break with no text measurement, which is why four of six images
# overflowed their cards.
#
# --force-device-scale-factor=2 gives a 2x (retina) PNG: a 1800x1080 page is
# written as 3600x2160, which LinkedIn downsamples cleanly.
#
# Usage:  ./render.sh            # all figures
#         ./render.sh 03_results # one figure
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "Chrome not found at $CHROME" >&2; exit 1; }
OUT=".."

shot () {                       # shot <name> <width> <height>
  local name=$1 w=$2 h=$3
  "$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
            --force-device-scale-factor=2 \
            --screenshot="$OUT/$name.png" --window-size="$w,$h" \
            "$name.html" 2>/dev/null
  printf '  %-34s %sx%s @2x\n' "$name.png" "$w" "$h"
}

only="${1:-}"
run () { [ -z "$only" ] || [ "$only" = "$1" ] && shot "$@"; }

echo "Rendering figures:"
run 01_hero                     1920 1080
run 02_pipeline                 1800 820
run 03_results                  1800 1080
run 04_refusal                  1800 1080
run 05_compaction_vs_compression 1800 1120
run 06_takeaway                 1800 940
echo "Done."
