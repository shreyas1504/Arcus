"""Download the prebuilt Chroma index and ONNX embedder for the API server.

Run at build time on hosts without the SEC corpus:
    python -m research.fetch_assets

`--pack` builds the archive from a local index for upload as a release asset.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tarfile
import tempfile
from pathlib import Path

import requests

DATA_DIR = Path(os.getenv("RESEARCH_DATA_DIR", "research/data"))
ASSET_URL = os.getenv(
    "RESEARCH_ASSET_URL",
    "https://github.com/shreyas1504/Arcus/releases/download/research-index-v2/arcus-research-assets-v2.tar.gz",
)
ASSET_SHA256 = os.getenv(
    "RESEARCH_ASSET_SHA256",
    "fd8fd6da223fedcb05db97b171ef7f0742b0e2ba96926fe6b8d8d59dcebcd60c",
)
MEMBERS = ("chroma", "bge-small-en-v1.5-onnx")
MARKER = ".assets.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pack(data_dir: Path, output: Path) -> str:
    missing = [name for name in MEMBERS if not (data_dir / name).is_dir()]
    if missing:
        raise SystemExit(f"Missing in {data_dir}: {', '.join(missing)}")
    with tarfile.open(output, "w:gz") as archive:
        for name in MEMBERS:
            archive.add(data_dir / name, arcname=name)
    return _sha256(output)


def _remove(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def fetch(
    data_dir: Path = DATA_DIR,
    url: str = ASSET_URL,
    sha256: str = ASSET_SHA256,
    members: tuple[str, ...] = MEMBERS,
) -> dict:
    """Download, verify and extract `members` (files or directories) into `data_dir`."""
    if not sha256:
        raise SystemExit("RESEARCH_ASSET_SHA256 is not set")
    marker = data_dir / MARKER
    if marker.exists() and json.loads(marker.read_text()).get("sha256") == sha256:
        return {"status": "present", "data_dir": str(data_dir)}

    data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=data_dir) as tmp:
        archive_path = Path(tmp) / "assets.tar.gz"
        with requests.get(url, stream=True, timeout=120) as response:
            response.raise_for_status()
            with archive_path.open("wb") as handle:
                for block in response.iter_content(1 << 20):
                    handle.write(block)
        actual = _sha256(archive_path)
        if actual != sha256:
            raise SystemExit(f"Checksum mismatch for {url}: got {actual}")
        extract_dir = Path(tmp) / "extract"
        with tarfile.open(archive_path) as archive:
            archive.extractall(extract_dir, filter="data")
        for name in members:
            if not (extract_dir / name).exists():
                raise SystemExit(f"Archive is missing {name}")
        for name in members:
            _remove(data_dir / name)
            shutil.move(str(extract_dir / name), data_dir / name)
    marker.write_text(json.dumps({"sha256": sha256, "url": url}))
    return {"status": "downloaded", "data_dir": str(data_dir)}


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
