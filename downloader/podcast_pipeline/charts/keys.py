"""Canonical chart ids and title keys.

A chart id is ``'<platform>:<region>:<unit>:<genre>'``. It names *which
ranking* a snapshot is of; *who published the copy* is ``chart_snapshots.source``.
Two mirrors of the same ranking share a chart id and differ in source, which is
what lets Podbay, Chartable, Apple's page and the live feed form one series.

* ``platform``: ``apple`` | ``spotify`` | ``chartable`` (Chartable's own
  reach/trending charts are its measurement, not Apple's or Spotify's chart).
* ``region``: ISO 3166 alpha-2, lowercase (``us``), or ``global``. Chartable's
  bare /charts/chartable page names no region and is ``default``.
* ``unit``: what is ranked, with a qualifier for a different list of the same
  thing: ``podcast``, ``episode``, ``channel``, ``series``,
  ``subscriber_podcast``, ``trending_podcast``, ``trending_episode``,
  ``bestseller_podcast``, ``explicit_podcast``. Spotify's ``show`` is ``podcast``.
* ``genre``: a lowercase slug (``genre_slug``), ``all`` for the overall chart.
  Every source's own genre names are kept; taxonomies are not reconciled
  (Podbay's pre-2019 ``health`` is not Apple's 2019 ``health-fitness``).

Mapping from the parsed archive (``analysis/chart_archive/parse.py`` columns):

=================  ==========================================  ==================================
source             parsed chart / genre                        chart id
=================  ==========================================  ==================================
podbay             genre ``all-podcasts``                      ``apple:us:podcast:all``
podbay             genre ``news-and-politics``                 ``apple:us:podcast:news-politics``
podbay -> podbay_itunes  genre ``comedy_itunes``               ``apple:us:podcast:comedy``
chartable_itunes   ``us-all-podcasts-podcasts``                ``apple:us:podcast:all``
chartable_itunes   ``us-all-podcasts-episodes``                ``apple:us:episode:all``
chartable_itunes   ``us-history-podcasts-d6c80344-...``        ``apple:us:podcast:history-d6c80344``
chartable_itunes   ``us-politics-all-time-bestsellers``        ``apple:us:bestseller_podcast:politics``
apple_charts_page  ``Top Shows`` / ``All Podcasts``            ``apple:us:podcast:all``
apple_charts_page  ``Top Shows`` / ``Health & Fitness``        ``apple:us:podcast:health-fitness``
apple_charts_page  ``Top Episodes``                            ``apple:us:episode:<genre>``
apple_charts_page  ``Trending Episodes``                       ``apple:us:trending_episode:<genre>``
apple_charts_page  ``Top Subscriber Shows``                    ``apple:us:subscriber_podcast:all``
apple_charts_page  ``Top Subscriber Channels``                 ``apple:us:channel:all``
apple_charts_page  ``Top Series``                              ``apple:us:series:all``
itunes_rss         ``us_rss_toppodcasts_limit=300_xml``        ``apple:us:podcast:all``
itunes_rss         ``..._limit=10_explicit=true_xml``          ``apple:us:explicit_podcast:all``
itunes_rss         ``..._sf=143442_limit=300_genre=1310_xml``  ``apple:fr:podcast:music``
itunes_rss         ``api_v2_us_podcasts_top_10_podcast-episodes.rss``  ``apple:us:episode:all``
chartable_spotify  ``united-states-of-america-top-podcasts``   ``spotify:us:podcast:all``
chartable_spotify  ``great-britain-trending``                  ``spotify:gb:trending_podcast:all``
spotify_api        ``top`` / ``top-podcasts`` (show)           ``spotify:us:podcast:all``
spotify_api        ``top`` / ``top-episodes`` (episode)        ``spotify:us:episode:all``
spotify_api        ``trending`` (show)                         ``spotify:us:trending_podcast:all``
chartable_reach    ``podcast-us-all-podcasts-reach``           ``chartable:us:podcast:all``
chartable_reach    ``podcasts-global-news-trending``           ``chartable:global:trending_podcast:news``
=================  ==========================================  ==================================

Live captures: ``apple_marketing_tools`` -> ``apple:us:podcast:all``,
``spotify_api`` -> ``spotify:us:podcast:all`` (``LIVE_CHARTS``).

Decisions worth knowing:

* itunes_rss keeps ``source = 'itunes_rss'`` even where its chart id is the
  flagship: the archive analysis found it disagrees with Podbay historically.
  ``limit=N`` variants are one chart at different depths and merge per day;
  ``explicit=true``, storefronts (``sf=``) and genre ids do not.
* Podbay's ``<genre>_itunes`` pages are a different list from its plain genre
  pages in 2012-2013 (4% rank agreement on shared days), so they are kept as
  source ``podbay_itunes``.
* Chartable's uuid-suffixed genre slugs coexist with an unsuffixed slug of
  the same name (``us-history-podcasts`` and ``us-history-podcasts-d6c8...``),
  so the first uuid block stays in the genre.
* Spotify ids are stored bare (``spotify:show:XYZ`` -> ``XYZ``), the form
  ``podcasts.spotify_id`` uses.
"""

from __future__ import annotations

import re

ALL = "all"

# Spellings of "the overall chart" across sources.
_ALL_ALIASES = {"all-podcasts", "top-podcasts", "top", "all"}

UUID_SUFFIX = re.compile(r"-([0-9a-f]{8})-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

APPLE_PAGE_UNITS = {
    "Top Shows": "podcast",
    "Top Episodes": "episode",
    "Trending Episodes": "trending_episode",
    "Top Subscriber Shows": "subscriber_podcast",
    "Top Subscriber Channels": "channel",
    "Top Series": "series",
}

# Podbay's genre pages (Apple's pre-2019 top-level genres). Anything else under
# podbay.fm/browse/ is a URL artifact (browse/h, browse/SOCIALMEDIA, ...) that
# served the overall chart; the research did not use those pages either.
PODBAY_GENRES = {
    "all-podcasts", "arts", "business", "comedy", "education", "games-and-hobbies",
    "government-and-organizations", "health", "kids-and-family", "music",
    "news-and-politics", "religion-and-spirituality", "science-and-medicine",
    "society-and-culture", "sports-and-recreation", "technology", "tv-and-film",
}

# Apple's legacy (pre-2019) genre ids as they appear in iTunes RSS URLs.
APPLE_GENRE_IDS = {
    "26": "All Podcasts", "1301": "Arts", "1302": "Personal Journals", "1303": "Comedy",
    "1304": "Education", "1305": "Kids & Family", "1307": "Health", "1309": "TV & Film",
    "1310": "Music", "1311": "News & Politics", "1314": "Religion & Spirituality",
    "1315": "Science & Medicine", "1316": "Sports & Recreation", "1318": "Technology",
    "1321": "Business", "1323": "Games & Hobbies", "1324": "Society & Culture",
    "1325": "Government & Organizations",
}

# iTunes Store front ids (the ``sf=`` URL parameter).
ITUNES_STOREFRONTS = {
    "143441": "us", "143442": "fr", "143443": "de", "143444": "gb", "143445": "at",
    "143446": "be", "143447": "fi", "143448": "gr", "143449": "ie", "143450": "it",
    "143451": "lu", "143452": "nl", "143453": "pt", "143454": "es", "143455": "ca",
    "143456": "se", "143457": "no", "143458": "dk", "143459": "ch", "143460": "au",
    "143461": "nz", "143462": "jp", "143463": "hk", "143464": "sg", "143465": "cn",
    "143466": "kr", "143467": "in", "143468": "mx", "143469": "ru", "143470": "tw",
    "143471": "vn", "143472": "za", "143473": "my", "143474": "ph", "143475": "th",
    "143476": "id", "143477": "pk", "143478": "pl", "143479": "sa", "143480": "tr",
    "143481": "ae",
}

# Country names in Chartable chart slugs (spelling theirs: "hungaria").
CHARTABLE_COUNTRIES = {
    "argentina": "ar", "australia": "au", "austria": "at", "belgium": "be",
    "bolivia": "bo", "brazil": "br", "bulgaria": "bg", "canada": "ca", "chile": "cl",
    "china": "cn", "colombia": "co", "costa-rica": "cr", "cyprus": "cy",
    "czech-republic": "cz", "denmark": "dk", "dominican-republic": "do",
    "ecuador": "ec", "estonia": "ee", "finland": "fi", "france": "fr", "germany": "de",
    "global": "global", "great-britain": "gb", "greece": "gr", "hong-kong": "hk",
    "hungaria": "hu", "hungary": "hu", "iceland": "is", "india": "in",
    "indonesia": "id", "ireland": "ie", "israel": "il", "italy": "it", "japan": "jp",
    "latvia": "lv", "luxembourg": "lu", "malaysia": "my", "malta": "mt", "mexico": "mx",
    "netherlands": "nl", "new-zealand": "nz", "norway": "no", "panama": "pa",
    "paraguay": "py", "peru": "pe", "philippines": "ph", "poland": "pl",
    "portugal": "pt", "romania": "ro", "singapore": "sg", "slovakia": "sk",
    "south-africa": "za", "spain": "es", "sweden": "se", "switzerland": "ch",
    "taiwan": "tw", "thailand": "th", "turkey": "tr", "united-states-of-america": "us",
    "usa": "us",
}

LIVE_CHARTS = {
    "apple_marketing_tools": ("apple", "podcast", ALL),
    "spotify_api": ("spotify", "podcast", ALL),
}


class Unmapped(ValueError):
    """A parsed archive chart that has no defensible chart id (recorded, skipped)."""


def chart_id(platform: str, region: str, unit: str, genre: str) -> str:
    parts = (platform, region, unit, genre)
    for part in parts:
        if not part or ":" in part:
            raise ValueError(f"bad chart id component {part!r} in {parts}")
    return ":".join(parts)


def live_chart(source: str, country: str) -> str:
    platform, unit, genre = LIVE_CHARTS[source]
    return chart_id(platform, country.lower(), unit, genre)


def title_key(name) -> str | None:
    """Lowercase name with everything but [a-z0-9] removed; matches population.key()."""
    if not isinstance(name, str):
        return None
    key = re.sub(r"[^a-z0-9]+", "", name.lower())
    return key or None


def genre_slug(text: str) -> str:
    """``'Health & Fitness'`` -> ``health-fitness``; ``news-and-politics`` ->
    ``news-politics``; any spelling of the overall chart -> ``all``."""
    words = [w for w in re.split(r"[^a-z0-9]+", text.lower()) if w and w != "and"]
    slug = "-".join(words)
    if not slug:
        raise Unmapped(f"empty genre {text!r}")
    return ALL if slug in _ALL_ALIASES else slug


def bare_spotify_id(uri: str | None) -> str | None:
    """``spotify:show:XYZ`` -> ``XYZ`` (other strings unchanged)."""
    if not isinstance(uri, str) or not uri:
        return None
    return uri.rsplit(":", 1)[-1] if uri.startswith("spotify:") else uri


def archive_chart(source: str, unit: str, chart: str, region: str | None,
                  genre: str) -> tuple[str, str]:
    """``(snapshot source, chart id)`` for one parsed archive chart.

    Raises ``Unmapped`` for charts that cannot be named honestly.
    """
    match source:
        case "podbay":
            return _podbay(genre)
        case "chartable_itunes":
            return source, _chartable_itunes(chart)
        case "chartable_spotify":
            return source, _chartable_spotify(chart)
        case "chartable_reach":
            return source, _chartable_reach(chart)
        case "apple_charts_page":
            return source, _apple_page(chart, region, genre)
        case "itunes_rss":
            return source, _itunes_rss(chart)
        case "spotify_api":
            return source, _spotify_api(unit, chart, region)
    raise Unmapped(f"unknown archive source {source!r}")


def _podbay(genre: str) -> tuple[str, str]:
    source = "podbay"
    if genre.endswith("_itunes"):
        source, genre = "podbay_itunes", genre[: -len("_itunes")]
    if genre not in PODBAY_GENRES:
        raise Unmapped("podbay page under a non-genre URL (serves the overall chart; "
                       "not used by the research)")
    return source, chart_id("apple", "us", "podcast", genre_slug(genre))


def _chartable_itunes(chart: str) -> str:
    m = UUID_SUFFIX.search(chart)
    body, uuid8 = (chart[: m.start()], m.group(1)) if m else (chart, None)
    m = re.fullmatch(r"([a-z]{2})-(.+)-(podcasts|episodes|all-time-bestsellers)", body)
    if not m:
        raise Unmapped("unrecognised chartable_itunes chart slug")
    unit = {"podcasts": "podcast", "episodes": "episode",
            "all-time-bestsellers": "bestseller_podcast"}[m.group(3)]
    genre = genre_slug(m.group(2))
    if uuid8:
        genre = f"{genre}-{uuid8}"
    return chart_id("apple", m.group(1), unit, genre)


def _country_prefix(body: str) -> tuple[str, str]:
    for name in sorted(CHARTABLE_COUNTRIES, key=len, reverse=True):
        if body.startswith(name + "-"):
            return CHARTABLE_COUNTRIES[name], body[len(name) + 1:]
    m = re.fullmatch(r"([a-z]{2})-(.+)", body)
    if m:
        return m.group(1), m.group(2)
    raise Unmapped("no recognisable country in Chartable chart slug")


def _chartable_spotify(chart: str) -> str:
    region, rest = _country_prefix(chart)
    if rest == "trending":
        return chart_id("spotify", region, "trending_podcast", ALL)
    return chart_id("spotify", region, "podcast", genre_slug(rest))


def _chartable_reach(chart: str) -> str:
    if chart == "":
        # chartable.com/charts/chartable: the default reach chart, region unnamed
        return chart_id("chartable", "default", "podcast", ALL)
    body = re.sub(r"^podcasts?-", "", chart)
    m = re.fullmatch(r"(.+)-(reach|trending)", body)
    if not m:
        raise Unmapped("unrecognised chartable_reach chart slug")
    region, genre = _country_prefix(m.group(1))
    unit = "podcast" if m.group(2) == "reach" else "trending_podcast"
    return chart_id("chartable", region, unit, genre_slug(genre))


def _apple_page(chart: str, region: str | None, genre: str) -> str:
    unit = APPLE_PAGE_UNITS.get(chart)
    if unit is None:
        raise Unmapped(f"unknown Apple charts-page shelf {chart!r}")
    return chart_id("apple", region or "us", unit, genre_slug(genre))


def _itunes_rss(chart: str) -> str:
    # Some captured URLs carry escaped '=' (\075 or \x3d) in the path.
    norm = re.sub(r"_5C(?:075|x3d)", "=", chart)
    norm = norm.replace("limit_075", "limit=")
    m = re.match(r"api_v2_([a-z]{2})_podcasts_top_\d+_(podcasts|podcast-episodes)\.", norm)
    if m:   # Apple Marketing Tools RSS
        unit = "podcast" if m.group(2) == "podcasts" else "episode"
        return chart_id("apple", m.group(1), unit, ALL)
    if "toppodcasts" not in norm.lower():
        raise Unmapped("unrecognised itunes_rss chart")
    m = re.match(r"([a-z]{2})_rss_", norm)
    if m:
        region = m.group(1)
    elif "sf=" in norm:
        sf = re.search(r"sf=(\d*)", norm).group(1)
        if sf not in ITUNES_STOREFRONTS:
            raise Unmapped("itunes_rss storefront id not recognised")
        region = ITUNES_STOREFRONTS[sf]
    else:
        region = "us"   # MZStoreServices without sf= serves the US store
    g = re.search(r"genre=(\d+)", norm)
    genre = ALL
    if g:
        if g.group(1) not in APPLE_GENRE_IDS:
            raise Unmapped("itunes_rss genre id not recognised")
        genre = genre_slug(APPLE_GENRE_IDS[g.group(1)])
    unit = "explicit_podcast" if "explicit=true" in norm else "podcast"
    return chart_id("apple", region, unit, genre)


def _spotify_api(unit: str, chart: str, region: str | None) -> str:
    if not region:
        raise Unmapped("spotify_api row without a region")
    if unit == "episode":
        genre = ALL if chart in ("top", "top-episodes") else genre_slug(chart)
        return chart_id("spotify", region, "episode", genre)
    if chart == "trending":
        return chart_id("spotify", region, "trending_podcast", ALL)
    return chart_id("spotify", region, "podcast", genre_slug(chart))
