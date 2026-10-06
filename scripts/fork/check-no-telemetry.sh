#!/usr/bin/env bash
# Fork guard: fail if PostHog or Axiom endpoints come back in source or built output.
# Usage: check-no-telemetry.sh            scan apps and packages source
#        check-no-telemetry.sh path ...   scan build output, everything included
set -euo pipefail

pattern='posthog\.com|phc_[A-Za-z0-9]{20,}|axiom\.co'

if [[ $# -eq 0 ]]; then
  hits="$(grep -rEal "$pattern" apps packages \
    --exclude-dir=node_modules --exclude-dir=mobile --exclude-dir=marketing \
    --exclude='*.test.ts' --exclude='*.test.tsx' --exclude='*.md' || true)"
  scanned="apps packages (source)"
else
  hits="$(grep -rEal "$pattern" "$@" || true)"
  scanned="$*"
fi

if [[ -n "$hits" ]]; then
  echo "Telemetry endpoints found in:" >&2
  echo "$hits" >&2
  exit 1
fi
echo "No telemetry endpoints found in: $scanned"
