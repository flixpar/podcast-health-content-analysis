"""My Podcast Data backfill (charts/mypodcastdata.py): fetch, import, re-run."""

import json
from datetime import date

import pytest
import requests

from podcast_pipeline.charts import archive_import, mypodcastdata
from podcast_pipeline.charts.capture import ChartCaptureError, ChartSourceError


def show(rank, key, name, slug=None):
    return {"rank": str(rank), "key": key, "name": name, "artist": f"{name} Inc",
            "slug": slug or name.lower().replace(" ", "-")}


DAY1 = [show(1, "1200361736", "The Daily"), show(2, "360084272", "The Joe Rogan Experience")]
DAY2 = [show(1, "360084272", "The Joe Rogan Experience"), show(2, "1200361736", "The Daily")]


class FakeResponse:
    def __init__(self, payload):
        self.content = json.dumps(payload).encode()

    def raise_for_status(self):
        pass


class FakeSession:
    """Answers by (category, DD/MM/YYYY); unknown days get an empty chart."""

    def __init__(self, charts):
        self.charts, self.calls = charts, []

    def get(self, url, timeout, params):
        assert url == mypodcastdata.API_URL
        self.calls.append((params["category"], params["datestring"]))
        answer = self.charts.get((params["category"], params["datestring"]), [])
        if isinstance(answer, Exception):
            raise answer
        return FakeResponse(answer)


@pytest.fixture
def net(monkeypatch, config):
    config.charts.mypodcastdata_delay_seconds = 0

    def install(charts):
        session = FakeSession(charts)
        monkeypatch.setattr(mypodcastdata, "make_session", lambda: session)
        return session
    return install


def snapshots(conn):
    return conn.execute("""SELECT * FROM chart_snapshots WHERE source = 'mypodcastdata'
                           ORDER BY chart, captured_on""").fetchall()


def test_parse_rejects_bad_payloads():
    assert [e.apple_id for e in mypodcastdata.parse(json.dumps(DAY1).encode())] == [
        "1200361736", "360084272"]
    with pytest.raises(ChartSourceError):
        mypodcastdata.parse(b"<html>Just a moment...</html>")
    with pytest.raises(ChartSourceError):
        mypodcastdata.parse(json.dumps({"rows": DAY1}).encode())
    with pytest.raises(ChartSourceError):
        mypodcastdata.parse(json.dumps([show(1, "abc", "No Id")]).encode())


def test_backfill_imports_keeps_raw_and_skips_empty_days(config, conn, net):
    session = net({("26", "01/09/2024"): DAY1, ("26", "03/09/2024"): DAY2,
                   ("1512", "02/09/2024"): DAY2})
    result = mypodcastdata.run(config, conn, start=date(2024, 9, 1), end=date(2024, 9, 3))

    assert result["26"]["fetched"] == 2 and result["26"]["empty"] == ["2024-09-02"]
    assert result["26"]["missing_days"] == ["2024-09-02"]
    snaps = snapshots(conn)
    assert [(s["chart"], s["captured_on"]) for s in snaps] == [
        ("apple:us:podcast:all", "2024-09-01"), ("apple:us:podcast:all", "2024-09-03"),
        ("apple:us:podcast:health-fitness", "2024-09-02")]
    first = snaps[0]
    assert (first["origin"], first["captured_at"], first["trusted"]) == ("mirror_api", None, 1)
    assert (first["depth"], first["n_entries"], first["complete_to"]) == (2, 2, 2)
    assert first["raw_path"] == "charts/raw/mypodcastdata/26/2024-09-01.json"
    assert json.loads((config.data_path / first["raw_path"]).read_bytes()) == DAY1
    rows = conn.execute("SELECT * FROM chart_entries WHERE snapshot_id = ? ORDER BY rank",
                        (first["id"],)).fetchall()
    assert (rows[0]["apple_id"], rows[0]["title_key"], rows[0]["publisher"]) == (
        "1200361736", "thedaily", "The Daily Inc")
    assert rows[0]["entity_url"] == "https://www.mypodcastdata.com/podcast/show/the-daily"

    # a re-run asks only for the days with nothing on disk, and replaces its rows
    session.calls.clear()
    again = mypodcastdata.run(config, conn, start=date(2024, 9, 1), end=date(2024, 9, 3))
    assert session.calls == [("26", "02/09/2024"), ("1512", "01/09/2024"), ("1512", "03/09/2024")]
    assert again["26"]["replaced"] == 2
    assert len(snapshots(conn)) == 3
    assert conn.execute("SELECT COUNT(*) FROM chart_entries").fetchone()[0] == 6


def test_identical_consecutive_day_is_untrusted(config, conn, net):
    net({("26", "01/09/2024"): DAY1, ("26", "02/09/2024"): DAY1, ("26", "03/09/2024"): DAY2})
    result = mypodcastdata.run(config, conn, genres=["26"], start=date(2024, 9, 1),
                               end=date(2024, 9, 3))
    assert result["26"]["stale"] == ["2024-09-02"]
    assert [(s["captured_on"], s["trusted"]) for s in snapshots(conn)] == [
        ("2024-09-01", 1), ("2024-09-02", 0), ("2024-09-03", 1)]
    # a partial re-import still compares its first day with the day before
    mypodcastdata.run(config, conn, genres=["26"], start=date(2024, 9, 2),
                      end=date(2024, 9, 2), fetch=False)
    assert snapshots(conn)[1]["note"] == mypodcastdata.STALE_NOTE


def test_failed_day_is_recorded_and_the_rest_imported(config, conn, net):
    net({("26", "01/09/2024"): DAY1, ("26", "02/09/2024"): requests.ConnectionError("down"),
         ("26", "03/09/2024"): DAY2})
    with pytest.raises(ChartCaptureError, match="2024-09-02"):
        mypodcastdata.run(config, conn, genres=["26"], start=date(2024, 9, 1),
                          end=date(2024, 9, 3))
    assert [s["captured_on"] for s in snapshots(conn)] == ["2024-09-01", "2024-09-03"]
    assert not mypodcastdata.raw_path(config, "26", date(2024, 9, 2)).exists()


def test_unknown_genre_and_dates_before_the_api_starts(config, conn, net):
    session = net({})
    with pytest.raises(ValueError, match="unknown genre"):
        mypodcastdata.run(config, conn, genres=["1489"], start=date(2024, 9, 1),
                          end=date(2024, 9, 1))
    assert session.calls == []
    mypodcastdata.run(config, conn, genres=["26"], start=date(2024, 8, 30), end=date(2024, 9, 1))
    assert session.calls == [("26", "01/09/2024")]


def test_archive_reimport_leaves_mirror_rows(tmp_path, config, conn, net):
    import pandas as pd

    net({("26", "01/09/2024"): DAY1})
    mypodcastdata.run(config, conn, genres=["26"], start=date(2024, 9, 1), end=date(2024, 9, 1))
    parsed = tmp_path / "archive" / "parsed"
    parsed.mkdir(parents=True)
    pd.DataFrame([{
        "source": "podbay", "platform": "apple", "unit": "podcast", "chart": "top",
        "region": "us", "genre": "all-podcasts", "rank": 1, "name": "Old Show",
        "publisher": "Pub", "entity_id": "42", "entity_url": None,
        "captured_at": "2015-01-01T10:00:00+00:00", "capture_ts": "20150101100000",
        "slug": None, "path": "p", "archive": "wayback", "page": None, "rank_move": None,
    }]).to_parquet(parsed / "chart_rows.parquet")
    archive_import.run(config, conn, archive_dir=tmp_path / "archive")
    archive_import.run(config, conn, archive_dir=tmp_path / "archive")
    counts = conn.execute("SELECT origin, COUNT(*) FROM chart_snapshots GROUP BY origin").fetchall()
    assert dict(map(tuple, counts)) == {"mirror_api": 1, "wayback": 1}
