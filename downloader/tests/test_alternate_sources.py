"""The alternate-source research tools (tools/alternate_sources): pure parts, no network."""

from __future__ import annotations

import struct
from datetime import date

import pytest
import requests

from tools.alternate_sources import archived_alt_feed, common, gap_windows, wayback_prefix_audio


def _id3(title: str, pad: int = 0) -> bytes:
    body = b"\x03" + title.encode()
    frame = b"TIT2" + struct.pack(">I", len(body)) + b"\x00\x00" + body + b"\x00" * pad
    size = len(frame)
    synchsafe = bytes([(size >> 21) & 0x7F, (size >> 14) & 0x7F, (size >> 7) & 0x7F, size & 0x7F])
    return b"ID3\x03\x00\x00" + synchsafe + frame


# MPEG-1 layer III, 128 kbps, 44.1 kHz, joint stereo, no CRC.
FRAME_128K = bytes([0xFF, 0xFB, 0x90, 0x44])


def test_id3_title_and_size():
    tag = _id3("Tally: Who Would Do This?", pad=5)
    assert common.id3_size(tag) == len(tag)
    assert common.id3_text(tag + FRAME_128K) == "Tally: Who Would Do This?"
    assert common.id3_text(b"\xff\xfb\x90\x44") is None


def test_mp3_duration_cbr_counts_bytes_after_the_tag():
    tag = _id3("x")
    head = tag + FRAME_128K + b"\x00" * 200
    total = len(tag) + 16_000 * 60          # one minute of 128 kbps audio
    got = common.mp3_duration(head, total)
    assert got["method"] == "cbr" and got["kbps"] == 128
    assert got["seconds"] == pytest.approx(60, abs=0.1)


def test_mp3_duration_reads_xing_frame_count():
    side = 32  # MPEG-1 stereo side information
    xing = b"Xing" + struct.pack(">I", 1) + struct.pack(">I", 2297)   # frames flag, 2297 frames
    head = FRAME_128K + b"\x00" * side + xing + b"\x00" * 100
    got = common.mp3_duration(head, total_size=None)
    assert got["method"] == "xing"
    assert got["seconds"] == pytest.approx(2297 * 1152 / 44100, abs=0.1)


def test_mp3_duration_from_bytes_after_a_large_tag():
    got = common.mp3_duration(FRAME_128K + b"\x00" * 100, total_size=1_000_000 + 16_000 * 10,
                              audio_start=1_000_000)
    assert got["seconds"] == pytest.approx(10, abs=0.1)


def test_mp3_duration_none_without_a_frame():
    assert common.mp3_duration(b"<html>" + b"\x00" * 100, 1000) is None


def test_is_audio_head_rejects_markup():
    assert common.is_audio_head(b"ID3\x04", "text/html")
    assert not common.is_audio_head(b"<!DOCTYPE html>", "audio/mpeg")
    assert common.is_audio_head(b"\x00\x00\x00\x18ftypM4A ", "")


def test_duration_matches_is_lopsided_toward_inserted_ads():
    probe = common.Probe("u", "u", 206, "audio/mpeg", 1, True, {"seconds": 1200.0})
    assert common.duration_matches(probe, 1000) is True        # +20%: ads
    assert common.duration_matches(probe, 1500) is False       # -20%: truncated
    assert common.duration_matches(probe, None) is None


@pytest.mark.parametrize("url, inner", [
    ("https://claritaspod.com/measure/dts.podtrac.com/redirect.mp3/mgln.ai/e/205/pscrb.fm/rss/p/"
     "traffic.omny.fm/d/clips/a/b.mp3?x=1", "https://traffic.omny.fm/d/clips/a/b.mp3?x=1"),
    ("https://pdrl.fm/55dc8e/chrt.fm/track/8G441/traffic.megaphone.fm/W.mp3?u=1",
     "https://traffic.megaphone.fm/W.mp3?u=1"),
    ("https://s.gum.fm/s-5fe37a10f0786e0025359373/traffic.megaphone.fm/L.mp3",
     "https://traffic.megaphone.fm/L.mp3"),
    ("https://www.claritaspod.com/measure/op3.dev/e/rss.art19.com/episodes/c.mp3",
     "https://rss.art19.com/episodes/c.mp3"),
    ("https://traffic.megaphone.fm/plain.mp3", "https://traffic.megaphone.fm/plain.mp3"),
])
def test_deep_unwrap(url, inner):
    assert common.deep_unwrap(url) == inner


def test_strip_query():
    assert common.strip_query("https://rss.art19.com/episodes/x.mp3?rss_browser=A&b=1") == \
        "rss.art19.com/episodes/x.mp3"


def test_prefixes_cover_the_enclosure_and_its_inner_url():
    got = wayback_prefix_audio.prefixes(
        "https://dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/rss.art19.com/episodes/x.mp3?q=1")
    assert got == ["rss.art19.com/episodes/x.mp3",
                   "dts.podtrac.com/redirect.mp3/chtbl.com/track/9EE2G/rss.art19.com/episodes/x.mp3"]


def test_rank_captures_prefers_direct_audio_then_nearest_and_dedupes():
    caps = [
        {"timestamp": "20211012000000", "original": "a", "statuscode": "302", "digest": "d1"},
        {"timestamp": "20190301000000", "original": "a", "statuscode": "302", "digest": "d2"},
        {"timestamp": "20230101000000", "original": "b", "statuscode": "200", "digest": "d3"},
        {"timestamp": "20230102000000", "original": "b", "statuscode": "200", "digest": "d3"},
        {"timestamp": "20190302000000", "original": "a", "statuscode": "404", "digest": "d4"},
    ]
    ranked = wayback_prefix_audio.rank_captures(caps, "2019-02-14T08:05:00")
    assert [c["timestamp"] for c in ranked] == ["20230101000000", "20190301000000", "20211012000000"]


class _Resp:
    def __init__(self, status, headers=None, body=b"", url=""):
        self.status_code, self.headers, self._body, self.url = status, headers or {}, body, url

    def iter_content(self, n):
        yield self._body

    def close(self):
        pass


class _Session:
    def __init__(self, routes):
        self.routes, self.headers, self.calls = routes, {}, []

    def get(self, url, **kwargs):
        self.calls.append(url)
        r = self.routes[url]
        if isinstance(r, Exception):
            raise r
        r.url = url
        return r


def _fetcher(routes):
    return common.Fetcher(session=_Session(routes), sleep=lambda s: None, clock=lambda: 0.0)


def test_wayback_resolve_follows_hops_and_probes_the_last():
    root = "https://web.archive.org/web"
    a = f"{root}/2020id_/https://rss.art19.com/episodes/x.mp3"
    b = f"{root}/2020id_/https://cdn/x.mp3"
    body = _id3("Ep 3") + FRAME_128K + b"\x00" * 100
    f = _fetcher({a: _Resp(302, {"Location": b}),
                  b: _Resp(206, {"Content-Type": "audio/mpeg",
                                 "Content-Range": f"bytes 0-65535/{len(_id3('Ep 3')) + 16_000 * 30}"}, body)})
    probe, hops, problem = common.wayback_resolve(f, root, "2020", "https://rss.art19.com/episodes/x.mp3")
    assert problem == "" and hops == [a, b]
    assert probe.is_audio and probe.id3_title == "Ep 3"
    assert probe.duration["seconds"] == pytest.approx(30, abs=0.1)


def test_wayback_resolve_stops_on_a_loop():
    root = "https://web.archive.org/web"
    a, b = f"{root}/1id_/https://x/a", f"{root}/1id_/https://x/b"
    f = _fetcher({a: _Resp(302, {"Location": b}), b: _Resp(302, {"Location": a})})
    probe, hops, problem = common.wayback_resolve(f, root, "1", "https://x/a")
    assert probe is None and problem == "redirect loop" and len(hops) == 2


def test_fetcher_waits_out_a_refused_connection_then_raises():
    waits = []
    refused = requests.ConnectionError("Failed to establish a new connection: [Errno 111] Connection refused")
    f = common.Fetcher(session=_Session({"https://h/x": refused}), sleep=waits.append, clock=lambda: 0.0)
    with pytest.raises(requests.ConnectionError):
        f.get("https://h/x")
    assert [w for w in waits if w >= 100] == list(common.REFUSED_WAITS)


def test_choose_capture_prefers_just_after_the_point():
    caps = [{"timestamp": t} for t in ("20160110000000", "20160203000000", "20160410000000")]
    point, floor = date(2016, 2, 1), date(2016, 1, 1)
    assert archived_alt_feed.choose_capture(caps, point, floor, set())["timestamp"] == "20160203000000"
    # Used up -> the latest one inside the window.
    assert archived_alt_feed.choose_capture(caps, point, floor, {"20160203000000"})["timestamp"] == \
        "20160110000000"
    assert archived_alt_feed.choose_capture(caps, point, floor, {"20160203000000", "20160110000000"}) is None


def test_gap_window_classify():
    weekly = [date(2016, 1, 1 + 7 * i) for i in range(4)] + [date(2016, 3, 7 + 7 * i) for i in range(3)]
    assert gap_windows.classify([date(2016, 1, 1) + (d - date(2016, 1, 1)) for d in weekly],
                                date(2016, 2, 1), date(2016, 3, 1))["label"] == "bracketed"
    assert gap_windows.classify(weekly, date(2015, 11, 1), date(2015, 12, 1))["label"] == "predates_catalog"
    sparse = [date(2016, 1, 1), date(2016, 6, 1)]
    assert gap_windows.classify(sparse, date(2016, 3, 1), date(2016, 4, 1))["label"] == "sparse"


def test_check_rows_holds_contradicted_rows():
    from tools.alternate_sources import check_rows

    def row(title, **probe):
        return {"title": title, "replaces_episode_id": 1, "evidence": {"probe": probe}}

    assert check_rows.problems(row("“Who Would Do This?” | 3", is_audio=True,
                                   id3_title="Tally: “Who Would Do This?” | 3",
                                   estimated_seconds=2514, declared_seconds=2276)) == []
    assert check_rows.problems(row("US boosts troops", is_audio=True, id3_title="Weather in Ghana"))
    assert check_rows.problems(row("x", is_audio=True, estimated_seconds=500, declared_seconds=1000))
    assert check_rows.problems(row("x", is_audio=False, error="HTTP 404"))
    # A new episode with a dead enclosure is still worth recording.
    assert check_rows.problems({"title": "x", "evidence": {"probe": {"is_audio": False}}}) == []


def test_origin_url_rewrites_npr_triton_paths():
    url = ("http://npr.mc.tritondigital.com/NPR_510289/media/anon.npr-mp3/npr/pmoney/2016/01/"
           "20160101_pmoney_pmpod.mp3?orgId=1&d=1211")
    assert common.origin_url(url) == ("https://edge1.pod.npr.org/anon.npr-mp3/npr/pmoney/2016/01/"
                                      "20160101_pmoney_pmpod.mp3?orgId=1&d=1211")
    assert common.origin_url("https://traffic.megaphone.fm/x.mp3") == "https://traffic.megaphone.fm/x.mp3"


def test_origin_url_other_npr_mounts_and_pmt():
    assert common.origin_url(
        "http://npr.mc.tritondigital.com/WAITWAIT_PODCAST/media/anon.npr-podcasts/podcast/344098539/1/npr_1.mp3"
    ) == "https://edge1.pod.npr.org/anon.npr-podcasts/podcast/344098539/1/npr_1.mp3"
    assert common.origin_url("http://podone.noxsolutions.com/launchpod/pardonmytake/mp3/pmt323.mp3") == \
        "https://landmark.barstoolsports.net/pardon-my-take/pmt323.mp3"
    stitched = "http://podone.noxsolutions.com/launchpod/stitched/2703020_2016-03-14-115020.64k.mp3"
    assert common.origin_url(stitched) == stitched


def test_host_catalog_detects_hosts_and_refuses_paywalled_archives(conn):
    from tools.alternate_sources import host_catalog
    conn.execute("INSERT INTO podcasts (id, title, rss_url) VALUES (1, 'O', "
                 "'https://www.omnycontent.com/d/playlist/e73c998e-6e60-432f-8610-ae210140c5b1/"
                 "21bd98b3-8cc6-4565-a21e-b4c9014d00dd/x/podcast.rss')")
    conn.execute("INSERT INTO podcasts (id, title, rss_url) VALUES (2, 'S', 'https://feeds.simplecast.com/a')")
    conn.execute("INSERT INTO podcasts (id, title, rss_url) VALUES (3, 'N', 'https://feeds.simplecast.com/b')")
    for pid, url in ((2, "https://dts.podtrac.com/redirect.mp3/rsv.simplecastaudio.com/"
                         "2a2884e1-4e6e-4659-91ce-9127efa5ac6f/episodes/a/audio/128/default.mp3"),
                     (3, "https://nyt.simplecastaudio.com/03d8b493-87fc-4bd1-931f-8a8e9b945d8a/episodes/b/audio.mp3")):
        conn.execute("INSERT INTO episodes (podcast_id, episode_guid, title, audio_url, published_date) "
                     "VALUES (?, ?, 't', ?, '2024-01-01')", (pid, f"g{pid}", url))
    assert host_catalog.detect_host(conn, 1) == ("omny", {"org": "e73c998e-6e60-432f-8610-ae210140c5b1",
                                                         "program": "21bd98b3-8cc6-4565-a21e-b4c9014d00dd"})
    assert host_catalog.detect_host(conn, 2) == ("simplecast", {"podcast": "2a2884e1-4e6e-4659-91ce-9127efa5ac6f",
                                                               "audio_host": "rsv.simplecastaudio.com"})
    host, why = host_catalog.detect_host(conn, 3)
    assert host is None and "subscriber-only" in why
