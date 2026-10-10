import pytest

from podcast_pipeline.archive.wayback import Capture, Snapshot, SnapshotError
from podcast_pipeline.charts import archive_import, archived_pages as ap
from podcast_pipeline.charts.capture import ChartCaptureError, ChartSourceError


def podcharts_page(day, prev, rows, country="us", genre="allcategories"):
    body = "".join(f"""
            <div class="podcast ">
              <div class="podcast-position">
                {rank}
              </div>
              <div class="podcast-previous-position-box"><div class="previous-position">--</div></div>
              <div class="podcast-name" id{f'="{pid}"' if pid is not None else ''}>
                <a href="/graphs/{pid}/us/allcategories">
                  {name}
                </a>
              </div>
              <div class="author-name">
                Pub &amp; Co
              </div>
            </div>""" for rank, pid, name in rows)
    return f"""<select><option value="{country}" selected>X</option></select>
        <select id="genreSelector"><option value="{genre}" selected> All </option></select>
        <div class="day-picker">
          <a class="button button-clear" href="/charts/us/{prev}/allcategories">&lt;</a> {day}
        </div><div class="podcast-list">{body}</div>""".encode()


FULL = [(r, str(1000 + r), f"Show {r}") for r in range(1, 201)]


def test_parse_podcharts_checks_country_genre_and_day():
    entries = ap.parse_podcharts(podcharts_page("Oct 10th", "2019-10-09", FULL), "2019-10-10")
    assert len(entries) == 200 and entries[0].apple_id == "1001" and entries[0].name == "Show 1"
    assert entries[0].publisher == "Pub & Co"
    with pytest.raises(ChartSourceError, match="shows 2019-10-09"):
        ap.parse_podcharts(podcharts_page("x", "2019-10-08", FULL), "2019-10-10")
    with pytest.raises(ChartSourceError, match="not US"):
        ap.parse_podcharts(podcharts_page("x", "2019-10-09", FULL, country="gb"), "2019-10-10")
    with pytest.raises(ChartSourceError, match="All Categories"):
        ap.parse_podcharts(podcharts_page("x", "2019-10-09", FULL, genre="comedy"), "2019-10-10")
    with pytest.raises(ChartSourceError, match="login"):
        ap.parse_podcharts(b"<p>To access charts older than a week Log in</p>", "2019-10-10")
    holed = ap.parse_podcharts(podcharts_page("x", "2019-10-09", [(1, None, ""), *FULL[1:]]), "2019-10-10")
    assert holed[0].apple_id is None and holed[0].name is None and len(holed) == 200


def insights_page(stamp, n=100):
    items = "".join(f"""<li><a href="https://podcasts.apple.com/us/podcast/s/id{500 + i}?at=1">img</a>
        <p>Podcast Name: <strong>Show {i}</strong><br> Network/Artist: Net {i}</p>
        <a href="https://podcasts.apple.com/us/podcast/s/id{500 + i}?at=1">badge</a></li>""" for i in range(1, n + 1))
    head = f"<p><em>Updated {stamp}</em></p>" if stamp else ""
    return f"<p>intro</p>{head}<ol>{items}</ol>".encode()


def test_parse_podcast_insights_needs_the_stamp():
    when, entries = ap.parse_podcast_insights(insights_page("Tue, 11 Oct 2022 01:56:17 +0000"))
    assert when.isoformat() == "2022-10-11T01:56:17+00:00"
    assert [(e.rank, e.apple_id, e.name, e.publisher) for e in entries[:1]] == [(1, "501", "Show 1", "Net 1")]
    assert len(entries) == 100
    with pytest.raises(ChartSourceError, match="stamp"):
        ap.parse_podcast_insights(insights_page(None))


class FakeClient:
    def __init__(self, cache_dir, captures, bodies):
        self.cache_dir, self.captures, self.bodies = cache_dir, captures, bodies
        self.fetched = []

    def list_captures(self, url, refresh=False, prefix=False):
        return self.captures[url]

    def fetch_snapshot(self, capture):
        self.fetched.append(capture.timestamp)
        body = self.bodies[capture.timestamp]
        if body is None:
            raise SnapshotError("HTTP 503")
        return Snapshot(capture, "x", body)


def cap(ts, url, length=50000):
    return Capture(ts, url, "200", "text/html", length, "d" + ts)


def test_run_imports_the_first_usable_capture_per_day(config, conn, monkeypatch):
    day_url = "https://podcharts.co/charts/us/2020-11-22"
    captures = {
        ap.PODCHARTS_PREFIX: [
            cap("20201121000000", day_url),                              # before the day: skipped
            cap("20201129000000", day_url + "/allcategories"),           # login page
            cap("20201130000000", day_url),                              # usable
            cap("20201201000000", day_url),                              # not needed
            cap("20201202000000", "https://podcharts.co/charts/us/2020-11-22/comedy"),
            cap("20201203000000", "https://podcharts.co/charts/us/2020-11-25", length=900),
        ],
        ap.PODCAST_INSIGHTS_URL: [cap("20221014060508", ap.PODCAST_INSIGHTS_URL),
                                  cap("20221015000000", ap.PODCAST_INSIGHTS_URL),
                                  cap("20210611005830", ap.PODCAST_INSIGHTS_URL)],
    }
    bodies = {
        "20201129000000": b"To access charts older than a week Log in",
        "20201130000000": podcharts_page("Nov 22nd", "2020-11-21", FULL),
        "20221014060508": insights_page("Tue, 11 Oct 2022 01:56:17 +0000"),
        "20221015000000": insights_page("Tue, 11 Oct 2022 01:56:17 +0000"),
        "20210611005830": insights_page(None),
    }
    client = FakeClient(config.wayback_cache_dir, captures, bodies)
    monkeypatch.setattr(ap, "WaybackClient", lambda *a, **k: client)
    result = ap.run(config, conn)
    assert result["podcharts"]["snapshots"] == 1 and result["podcast_insights"]["snapshots"] == 1
    assert "20201201000000" not in client.fetched and "20201121000000" not in client.fetched
    rows = {r["source"]: dict(r) for r in conn.execute("SELECT * FROM chart_snapshots")}
    assert rows["podcharts"]["captured_on"] == "2020-11-22" and rows["podcharts"]["complete_to"] == 200
    assert rows["podcharts"]["captured_at"] is None and rows["podcharts"]["origin"] == "wayback"
    assert rows["podcast_insights"]["captured_on"] == "2022-10-11"
    assert rows["podcast_insights"]["captured_at"] == "2022-10-11T01:56:17Z"
    assert rows["podcharts"]["raw_path"].startswith("wayback/snapshots/20201130000000_")

    ap.run(config, conn)                                     # idempotent
    assert conn.execute("SELECT COUNT(*) FROM chart_snapshots").fetchone()[0] == 2
    assert archive_import._delete_archive(conn)["snapshots"] == 0     # archive re-import keeps them


def test_unfetchable_captures_raise_after_importing_the_rest(config, conn, monkeypatch):
    url = "https://podcharts.co/charts/us/2020-11-22"
    captures = {ap.PODCHARTS_PREFIX: [cap("20201123000000", url), cap("20201124000000", url)]}
    bodies = {"20201123000000": None, "20201124000000": podcharts_page("x", "2020-11-21", FULL)}
    monkeypatch.setattr(ap, "WaybackClient", lambda *a, **k: FakeClient(config.wayback_cache_dir, captures, bodies))
    with pytest.raises(ChartCaptureError, match="could not be fetched"):
        ap.run(config, conn, sources=["podcharts"])
    assert conn.execute("SELECT captured_on FROM chart_snapshots").fetchone()[0] == "2020-11-22"
    with pytest.raises(ValueError, match="unknown source"):
        ap.run(config, conn, sources=["podtail"])
