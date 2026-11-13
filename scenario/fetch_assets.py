"""Download the prebuilt Scenario Lab library (layout in scenario/ASSETS.md).

Run at build time on the API host:
    python -m scenario.fetch_assets

`--pack` builds the archive from a local `scenario/assets/` for upload as a release asset.
The URL and SHA256 are pinned when the `scenario-assets-v1` release is published (C6);
until then the SHA256 is empty and fetching refuses to run.
"""

from __future__ import annotations

import argparse
import json
import os
import tarfile
from pathlib import Path

from research.fetch_assets import _sha256, fetch as _fetch

DATA_DIR = Path(os.getenv("SCENARIO_DATA_DIR", "scenario/assets"))
ASSET_URL = os.getenv(
    "SCENARIO_ASSET_URL",
    "https://github.com/shreyas1504/Arcus/releases/download/scenario-assets-v1/arcus-scenario-assets-v1.tar.gz",
)
ASSET_SHA256 = os.getenv(
    "SCENARIO_ASSET_SHA256",
    "f7bffba12059a0de26f9a1364592cb41c1ecafb8d6578c0c238d2a61ed492b0a",
)
MEMBERS = ("library.npz", "library.json", "factor_history.npz", "calibration.json")


def pack(data_dir: Path, output: Path) -> str:
    missing = [name for name in MEMBERS if not (data_dir / name).is_file()]
    if missing:
        raise SystemExit(f"Missing in {data_dir}: {', '.join(missing)}")
    with tarfile.open(output, "w:gz") as archive:
        for name in MEMBERS:
            archive.add(data_dir / name, arcname=name)
    return _sha256(output)


def fetch(data_dir: Path = DATA_DIR, url: str = ASSET_URL, sha256: str = ASSET_SHA256) -> dict:
    if not sha256:
        raise SystemExit("SCENARIO_ASSET_SHA256 is not set")
    return _fetch(data_dir, url, sha256, members=MEMBERS)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--pack", type=Path, metavar="ARCHIVE")
    args = parser.parse_args()
    if args.pack:
        print(pack(args.data_dir, args.pack))
    else:
        print(json.dumps(fetch(args.data_dir)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
