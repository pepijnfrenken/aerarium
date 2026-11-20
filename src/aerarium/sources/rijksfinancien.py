"""rijksfinancien.nl open-data adapter.

Three endpoints matter and only one of them carries the edge:

  budgettaire_tabellen        the appropriation spine, one row per line, in EUR thousand
  v2/financiele_instrumenten  chart feeds: flat aggregate lists, no edge, EUR not thousands
  Financiele_instrumenten_*.csv  the row-level register: scheme -> recipient -> amount -> KvK

Every fetch is recorded with url, params, retrieval timestamp, sha256 and byte count before a single row is
loaded, because a figure without its retrieval is not a figure.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE = "https://www.rijksfinancien.nl"
BUDGET_URL = f"{BASE}/open-data/api/json/budgettaire_tabellen"
RECIPIENTS_CSV_URL = (
    f"{BASE}/sites/default/files/bestanden/open_data/Financiele_instrumenten_2017-2024.csv"
)
SWAGGER_URL = f"{BASE}/swagger.json"
LICENCE = "CC-0 / publiek domein (Ministerie van Financien)"
USER_AGENT = "aerarium/0.1 (public-register join; provenance research)"

PHASES_SERVED = ("OWB", "JV")
PHASES_DECLARED = ("OWB", "O1", "O2", "JV")


@dataclass
class Fetched:
    source: str
    url: str
    params: dict[str, Any]
    retrieved_at: datetime
    status: int
    sha256: str
    n_bytes: int
    raw_path: str | None = None
    body: bytes | None = None
    note: str = ""
    extra: dict[str, Any] = field(default_factory=dict)

    def json(self) -> Any:
        if self.body is None:
            raise ValueError("no body retained on this fetch")
        return json.loads(self.body)


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _retrieve(url: str, params: dict[str, Any] | None, *, stream_to: Path | None = None,
              timeout: int = 180, attempts: int = 4) -> tuple[int, bytes | None, str, int]:
    """GET with bounded exponential backoff. Returns (status, body, sha256, n_bytes)."""
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with _session().get(url, params=params, timeout=timeout, stream=stream_to is not None) as r:
                status = r.status_code
                if status >= 500 and attempt < attempts:
                    raise requests.HTTPError(f"{status} from {url}")
                r.raise_for_status()
                h = hashlib.sha256()
                n = 0
                if stream_to is not None:
                    stream_to.parent.mkdir(parents=True, exist_ok=True)
                    tmp = stream_to.with_suffix(stream_to.suffix + ".part")
                    with tmp.open("wb") as fh:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            if not chunk:
                                continue
                            h.update(chunk)
                            fh.write(chunk)
                            n += len(chunk)
                    tmp.replace(stream_to)
                    return status, None, h.hexdigest(), n
                body = r.content
                h.update(body)
                return status, body, h.hexdigest(), len(body)
        except Exception as exc:  # noqa: BLE001 - retried, then surfaced
            last = exc
            if attempt < attempts:
                time.sleep(min(2 ** attempt, 30))
    raise RuntimeError(f"fetch failed after {attempts} attempts: {url} {params} :: {last}")


def budget(year: int, chapter: str, phase: str | None = None, *, raw_dir: Path) -> Fetched:
    """One call returns every phase the endpoint serves for that chapter-year.

    `phase` is passed through only when explicitly requested, and the response is filtered client-side,
    because an unrecognised phase value is silently ignored by the server and returns the full set.
    """
    params: dict[str, Any] = {"year": year, "chapter": chapter}
    if phase:
        params["phase"] = phase
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    raw = raw_dir / "budget" / f"{year}-{chapter}-{phase or 'all'}.json"
    status, body, sha, n = _retrieve(BUDGET_URL, params, timeout=180)
    raw.parent.mkdir(parents=True, exist_ok=True)
    raw.write_bytes(body or b"")
    return Fetched(
        source="rijksfinancien:budgettaire_tabellen",
        url=BUDGET_URL,
        params=params,
        retrieved_at=stamp,
        status=status,
        sha256=sha,
        n_bytes=n,
        raw_path=str(raw),
        body=body,
        note=f"phase={phase or 'unfiltered'}",
    )


def recipients_csv(*, raw_dir: Path, refresh: bool = False) -> Fetched:
    """The row-level recipient register. ~70 MB, re-fetched only when absent or refresh=True."""
    raw = raw_dir / "recipients" / Path(RECIPIENTS_CSV_URL).name
    stamp = datetime.now(timezone.utc).replace(microsecond=0)
    if raw.exists() and not refresh:
        h = hashlib.sha256()
        n = 0
        with raw.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
                n += len(chunk)
        return Fetched(
            source="rijksfinancien:financiele_instrumenten",
            url=RECIPIENTS_CSV_URL,
            params={},
            retrieved_at=stamp,
            status=200,
            sha256=h.hexdigest(),
            n_bytes=n,
            raw_path=str(raw),
            note="cache hit; retrieval timestamp is the read, not the original download",
        )
    status, _, sha, n = _retrieve(RECIPIENTS_CSV_URL, None, stream_to=raw, timeout=600)
    return Fetched(
        source="rijksfinancien:financiele_instrumenten",
        url=RECIPIENTS_CSV_URL,
        params={},
        retrieved_at=stamp,
        status=status,
        sha256=sha,
        n_bytes=n,
        raw_path=str(raw),
        note="downloaded",
    )


def recipients_dataset_available() -> dict[str, Any]:
    """Probe whether a later vintage of the row-level file exists, without downloading it.

    The file name carries its coverage window, and the window only moves when the dataset is refreshed,
    so a HEAD on the next vintage answers 'is this dataset current' with one request.
    """
    out: dict[str, Any] = {}
    for years in ("2017-2024", "2018-2025", "2017-2025", "2019-2026"):
        url = (
            f"{BASE}/sites/default/files/bestanden/open_data/"
            f"Financiele_instrumenten_{years}.csv"
        )
        try:
            r = _session().head(url, timeout=30, allow_redirects=True)
            out[years] = r.status_code
        except Exception as exc:  # noqa: BLE001
            out[years] = f"error: {exc}"
        time.sleep(0.3)
    return out


def default_raw_dir() -> Path:
    """Repo-rooted data/raw, found by walking up to pyproject.toml, never by counting parents."""
    env = os.environ.get("AERARIUM_RAW")
    if env:
        return Path(env).expanduser()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists():
            return parent / "data" / "raw"
    return Path.cwd() / "data" / "raw"
