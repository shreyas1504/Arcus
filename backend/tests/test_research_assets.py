import pytest

from research import fetch_assets


class FakeResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, _size):
        yield self.payload


@pytest.fixture
def archive(tmp_path):
    source = tmp_path / "source"
    for name in fetch_assets.MEMBERS:
        (source / name).mkdir(parents=True)
        (source / name / "file.bin").write_bytes(name.encode())
    path = tmp_path / "assets.tar.gz"
    return path, fetch_assets.pack(source, path)


def serve(monkeypatch, path):
    calls = []

    def fake_get(url, **_):
        calls.append(url)
        return FakeResponse(path.read_bytes())

    monkeypatch.setattr(fetch_assets.requests, "get", fake_get)
    return calls


def test_fetch_extracts_verified_archive_once(tmp_path, monkeypatch, archive):
    path, sha = archive
    calls = serve(monkeypatch, path)
    target = tmp_path / "data"

    assert fetch_assets.fetch(target, "https://example.test/a.tgz", sha)["status"] == "downloaded"
    assert (target / "chroma" / "file.bin").read_bytes() == b"chroma"
    assert fetch_assets.fetch(target, "https://example.test/a.tgz", sha)["status"] == "present"
    assert len(calls) == 1


def test_fetch_rejects_checksum_mismatch(tmp_path, monkeypatch, archive):
    path, _ = archive
    serve(monkeypatch, path)
    target = tmp_path / "data"

    with pytest.raises(SystemExit, match="Checksum mismatch"):
        fetch_assets.fetch(target, "https://example.test/a.tgz", "0" * 64)
    assert not (target / "chroma").exists()


def test_pack_requires_index_and_embedder(tmp_path):
    (tmp_path / "chroma").mkdir()
    with pytest.raises(SystemExit, match="bge-small-en-v1.5-onnx"):
        fetch_assets.pack(tmp_path, tmp_path / "out.tar.gz")
