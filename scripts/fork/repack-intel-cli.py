#!/usr/bin/env python3
"""Use the regular Node 24 runtime for Intel Macs instead of the crashing SEA."""

import argparse
from pathlib import Path
import shutil
import tarfile
import tempfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--archive", type=Path, required=True)
parser.add_argument("--server-dist", type=Path, required=True)
parser.add_argument("--node", type=Path, required=True)
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix="t3-intel-runtime-") as temporary:
    stage = Path(temporary)
    with tarfile.open(args.archive) as archive:
        archive.extractall(stage, filter="data")
    roots = list(stage.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise SystemExit("Expected exactly one archive root")
    root = roots[0]
    shutil.copy2(args.node, root / "node")
    shutil.copytree(
        args.server_dist,
        root / "server",
        ignore=shutil.ignore_patterns("*.map", "client", "resource-monitor"),
    )
    if not (root / "server/bin.mjs").is_file():
        raise SystemExit("The compiled server entry is missing")
    (root / "server/client").symlink_to("../client", target_is_directory=True)
    (root / "t3").write_text(
        '#!/bin/sh\n'
        'set -eu\n'
        'T3_BUNDLE_DIR=${0%/*}\n'
        'exec "$T3_BUNDLE_DIR/node" "$T3_BUNDLE_DIR/server/bin.mjs" "$@"\n'
    )
    (root / "t3").chmod(0o755)
    (root / "node").chmod(0o755)
    rebuilt = stage / "rebuilt.tar.gz"
    with tarfile.open(rebuilt, "w:gz") as archive:
        archive.add(root, arcname=root.name)
    shutil.copy2(rebuilt, args.archive)
    print(f"Repacked {args.archive} with Node 24 for Intel Macs")
