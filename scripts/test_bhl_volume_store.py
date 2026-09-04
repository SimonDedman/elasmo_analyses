#!/usr/bin/env python3
"""Tests for the BHL harvester's content store.

The bug being fixed: one scanned volume is the match for many articles, and
the harvester fetched and stored it once per article.  Sixteen copies of a
40.7 MB 1880 volume is 610 MB and sixteen needless downloads.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_bhl_archive as bhl

VOLUME = b"%PDF-1.4 scanned volume" + b"x" * 60_000


class FakeResponse:
    def __init__(self, data, status=200):
        self.status_code = status
        self._data = data

    def iter_content(self, chunk_size=1):
        yield self._data


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(bhl, "DOWNLOAD_DIR", tmp_path / "bhl_downloads")
    monkeypatch.setattr(bhl, "VOLUME_STORE", tmp_path / "bhl_downloads" / "_volumes")
    monkeypatch.setattr(bhl, "polite_sleep", lambda: None)
    return tmp_path / "bhl_downloads"


@pytest.fixture
def counting_get(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(VOLUME)

    monkeypatch.setattr(bhl.requests, "get", fake_get)
    return calls


def test_one_volume_is_fetched_once_for_many_articles(store, counting_get):
    url = "https://archive.org/download/bulletin1880/bulletin1880.pdf"
    dests = [store / f"{i}.pdf" for i in range(16)]

    results = [bhl.download_pdf(url, d) for d in dests]

    assert all(ok for ok, _ in results)
    assert len(counting_get) == 1, "the volume should be downloaded once"
    assert [r[1] for r in results] == ["downloaded"] + ["linked"] * 15
    assert all(d.read_bytes() == VOLUME for d in dests)
    assert len({d.stat().st_ino for d in dests}) == 1, "one inode for sixteen names"


def test_disk_cost_is_one_copy_not_sixteen(store, counting_get):
    url = "https://archive.org/download/bulletin1880/bulletin1880.pdf"
    for i in range(16):
        bhl.download_pdf(url, store / f"{i}.pdf")

    # Count blocks once per inode: resolve() follows symlinks, not hardlinks,
    # so deduplicating by path would count the same storage seventeen times.
    by_inode = {p.stat().st_ino: p.stat().st_blocks
                for p in store.rglob("*.pdf")}
    assert len(by_inode) == 1, "sixteen names, one inode"
    assert sum(by_inode.values()) * 512 < 2 * len(VOLUME), \
        "storage should be one volume, not sixteen"


def test_different_urls_stay_separate(store, monkeypatch):
    payloads = {
        "https://archive.org/a.pdf": VOLUME,
        "https://archive.org/b.pdf": b"%PDF-1.4 other volume" + b"y" * 60_000,
    }
    monkeypatch.setattr(bhl.requests, "get",
                        lambda url, **kw: FakeResponse(payloads[url]))

    bhl.download_pdf("https://archive.org/a.pdf", store / "1.pdf")
    bhl.download_pdf("https://archive.org/b.pdf", store / "2.pdf")

    assert (store / "1.pdf").read_bytes() != (store / "2.pdf").read_bytes()
    assert (store / "1.pdf").stat().st_ino != (store / "2.pdf").stat().st_ino


def test_a_rejected_download_stores_nothing(store, monkeypatch):
    monkeypatch.setattr(bhl.requests, "get",
                        lambda url, **kw: FakeResponse(b"<html>not a pdf</html>"))
    ok, reason = bhl.download_pdf("https://archive.org/c.pdf", store / "3.pdf")
    assert not ok and reason == "not_a_pdf"
    assert not (store / "3.pdf").exists()
    assert not list((store / "_volumes").glob("*.pdf")) if (store / "_volumes").exists() else True


def test_prune_drops_only_unreferenced_volumes(store, counting_get):
    kept = "https://archive.org/kept.pdf"
    dropped = "https://archive.org/dropped.pdf"
    bhl.download_pdf(kept, store / "keep.pdf")
    bhl.download_pdf(dropped, store / "gone.pdf")
    (store / "gone.pdf").unlink()

    removed, freed = bhl.prune_volume_store(log=lambda *_: None)

    assert removed == 1
    assert freed == len(VOLUME)
    assert (store / "keep.pdf").exists()
    assert bhl.store_path_for(kept).exists()
    assert not bhl.store_path_for(dropped).exists()


def test_link_or_copy_falls_back_across_devices(tmp_path, monkeypatch):
    import errno
    src = tmp_path / "src.pdf"
    src.write_bytes(VOLUME)
    dest = tmp_path / "dest.pdf"

    def refuse(*a, **kw):
        raise OSError(errno.EXDEV, "Invalid cross-device link")

    monkeypatch.setattr(bhl.os, "link", refuse)
    bhl.link_or_copy(src, dest)

    assert dest.read_bytes() == VOLUME
    assert dest.stat().st_ino != src.stat().st_ino
