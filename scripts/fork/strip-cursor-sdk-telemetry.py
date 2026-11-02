#!/usr/bin/env python3
"""Fork guard: switch off @cursor/sdk's analytics in its esm, cjs, and bun bundles.

The SDK buffers events and posts them to Cursor's AnalyticsService/TrackEvents, and
asks AnalyticsService/BootstrapStatsig for feature-gate config. Both get an early
return; without bootstrap config the SDK uses its built-in defaults.

Usage: strip-cursor-sdk-telemetry.py <sdk-dir>          patch in place (for `pnpm patch`)
       strip-cursor-sdk-telemetry.py --check <sdk-dir>  fail unless every bundle is patched
"""

import argparse
import os
from pathlib import Path
import re
import sys

ID = r"[\w$]+"
# `track(name, data, timestamp)` on the analytics buffer.
TRACK = re.compile(
    rf"(track\({ID},{ID},({ID})\)\{{)(return;)?"
    rf"(?=(?:const|let) {ID}=(?:\"number\"==typeof \2|typeof \2===\"number\")\?BigInt\(\2\))"
)
# The innermost async function that fetches BootstrapStatsig.
BOOTSTRAP = re.compile(
    rf"(async function(?: {ID})?\({ID}\)\{{)(return;)?"
    r"(?=(?:(?!async function).){0,400}?/aiserver\.v1\.AnalyticsService/BootstrapStatsig)",
    re.S,
)
FLAVORS = ("esm", "cjs", "bundled")

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument("--check", action="store_true")
parser.add_argument("sdk_dirs", type=Path, nargs="+")
args = parser.parse_args()

failures = []
for sdk in args.sdk_dirs:
    for flavor in FLAVORS:
        found = {"track": 0, "bootstrap": 0}
        unpatched = 0
        for path in sorted((sdk / "dist" / flavor).glob("*.js")):
            text = path.read_text()
            if ".trackEvents(" not in text and "AnalyticsService/BootstrapStatsig" not in text:
                continue
            for name, pattern in (("track", TRACK), ("bootstrap", BOOTSTRAP)):
                for match in pattern.finditer(text):
                    found[name] += 1
                    unpatched += match.group(len(match.groups())) is None
            if not args.check:
                patched = TRACK.sub(lambda m: m.group(1) + "return;", text)
                patched = BOOTSTRAP.sub(lambda m: m.group(1) + "return;", patched)
                if patched != text:
                    # A new file keeps pnpm's hardlinked store copy untouched.
                    temporary = path.with_suffix(".fork-tmp")
                    temporary.write_text(patched)
                    os.replace(temporary, path)
        for name, count in found.items():
            if count == 0:
                failures.append(f"{sdk}/dist/{flavor}: no {name} call site found")
        if args.check and unpatched:
            failures.append(f"{sdk}/dist/{flavor}: {unpatched} analytics call site(s) not patched")

if failures:
    print("Cursor SDK telemetry is not switched off:", *failures, sep="\n  ", file=sys.stderr)
    sys.exit(1)
print(f"Cursor SDK analytics {'verified off' if args.check else 'switched off'} in: {', '.join(map(str, args.sdk_dirs))}")
