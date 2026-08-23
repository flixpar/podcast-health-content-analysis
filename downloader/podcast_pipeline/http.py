"""HTTP session factory with the retry policy every network stage uses."""

from __future__ import annotations

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

USER_AGENT = "Mozilla/5.0 (compatible; PodcastTranscriber/1.0)"


def make_session(pool_size: int = 8, retries: int = 3) -> requests.Session:
    """A session that retries transient failures and identifies itself.

    ``pool_size`` should match the number of threads sharing the session; a
    ``requests.Session`` is safe to share across threads for plain GETs.
    """
    retry = Retry(total=retries, backoff_factor=1,
                  status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_size,
                          pool_maxsize=pool_size * 2)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": USER_AGENT})
    return session
