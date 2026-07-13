"""M1 — BZP connector: fetches notices from ezamowienia.gov.pl public API.

State-of-art upgrade (v2):
  - Async httpx.AsyncClient z retry/backoff/circuit-breaker (via scraper_base)
  - Per-domain rate limiting (2 req/s, burst=8)
  - ScraperMetrics — latency p50/p99, items_fetched, bytes_downloaded
  - sync wrapper dla backward compat z pipeline.py
  - Structured logging z kontekstem (window, page, count)
  - Connection pool (max 10 keepalive)
  - Half-day windowing (BZP cap = 500 results/request)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from .scraper_base import (
    AsyncHTTPClient,
    DEFAULT_LIMITS,
    DOWNLOAD_TIMEOUT,
    RetryPolicy,
    ScraperBase,
    normalize_cpv,
    parse_pln,
    safe_date,
)

logger = logging.getLogger(__name__)

BZP_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1"
_NOTICE_EP = f"{BZP_BASE}/notice"

# CPV codes — pełne budownictwo (CPV 45)
EARTHWORKS_CPV = [
    "45111200-0",
    "45111000-8",
    "45112000-5",
    "45112700-2",
    "45233120-6",
    "45233200-1",
    "45233140-2",
    "45231300-8",
    "45232410-9",
    "45246000-3",
    "45112500-0",
]

CONSTRUCTION_CPV_PREFIXES = ["45"]
EARTHWORKS_CPV_PREFIXES = {"45111", "45112", "45233", "45231", "45232", "45246"}

_BZP_RETRY = RetryPolicy(
    max_attempts=5,
    base_delay=2.0,
    max_delay=90.0,
    backoff_factor=2.5,
    jitter=0.4,
)

_BZP_LIMITS = httpx.Limits(
    max_connections=8,
    max_keepalive_connections=4,
    keepalive_expiry=60,
)

_BZP_TIMEOUT = httpx.Timeout(connect=8.0, read=60.0, write=10.0, pool=8.0)


def is_construction_scope(cpv_codes: list[str]) -> bool:
    return any(c.startswith("45") for c in cpv_codes)


class BZPRawNotice:
    """Typed wrapper around a raw BZP API notice dict."""

    __slots__ = ("_d",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    @property
    def raw(self) -> dict[str, Any]:
        return self._d


def _cpv_matches(cpv_list: list[str]) -> bool:
    return is_construction_scope(cpv_list)


# ---------------------------------------------------------------------------
# Async implementation
# ---------------------------------------------------------------------------

async def _fetch_windows_async(
    http: AsyncHTTPClient,
    *,
    date_from: date,
    date_to: date,
    notice_type: str = "ContractNotice",
    page_size: int = 500,
) -> list[BZPRawNotice]:
    """Core async fetch — half-day windowing to stay under BZP 500-result cap."""
    seen: dict[str, BZPRawNotice] = {}
    current = date_from

    while current <= date_to:
        windows = [
            (f"{current}T00:00:00", f"{current}T11:59:59"),
            (f"{current}T12:00:00", f"{current}T23:59:59"),
        ]
        for win_from, win_to in windows:
            params: dict[str, Any] = {
                "pageSize": page_size,
                "pageNumber": 0,
                "NoticeType": notice_type,
                "PublicationDateFrom": win_from,
                "PublicationDateTo": win_to,
            }
            try:
                resp = await http.get(_NOTICE_EP, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "source=bzp notice_type=%s window=%s http_status=%d",
                    notice_type, win_from[:10], exc.response.status_code,
                )
                continue
            except Exception as exc:
                logger.warning("source=bzp window=%s error=%s", win_from[:10], exc)
                continue

            notices = (
                data if isinstance(data, list)
                else data.get("notices", data.get("content", []))
            )
            added = 0
            for n in notices:
                raw = BZPRawNotice(n)
                key = raw.get("bzpNumber") or raw.get("noticeNumber") or raw.get("id")
                if key and key not in seen:
                    seen[key] = raw
                    added += 1

            http.metrics.record_items(fetched=added)
            logger.debug(
                "source=bzp type=%s window=%s new=%d total=%d",
                notice_type, win_from[:10], added, len(seen),
            )

        current += timedelta(days=1)

    return list(seen.values())


# ---------------------------------------------------------------------------
# Public connector (sync API, async internals)
# ---------------------------------------------------------------------------

class BZPConnector:
    """Fetches notices from the public BZP API.

    Backward-compatible sync API wrapping async httpx internals.
    All requests use retry/backoff/circuit-breaker from scraper_base.
    """

    def __init__(
        self,
        *,
        timeout: float = 60.0,   # kept for compat — unused (uses _BZP_TIMEOUT)
        page_size: int = 500,
        max_pages: int = 100,     # kept for compat
    ) -> None:
        self._page_size = page_size

    # ------------------------------------------------------------------
    # Public sync API
    # ------------------------------------------------------------------

    def fetch_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        cpv_codes: list[str] | None = None,
        voivodeship: str | None = None,
        order_type: str = "RC",
    ) -> list[BZPRawNotice]:
        today = date.today()
        d_from = date_from or (today - timedelta(days=7))
        d_to = date_to or today
        return asyncio.run(self._fetch_async("ContractNotice", d_from, d_to))

    def fetch_result_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[BZPRawNotice]:
        today = date.today()
        d_from = date_from or (today - timedelta(days=30))
        d_to = date_to or today
        return asyncio.run(self._fetch_async("ResultNotice", d_from, d_to))

    def sync_result_notices_to_historical_bids(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        return asyncio.run(
            self._sync_result_notices_async(
                date_from=date_from, date_to=date_to, dry_run=dry_run
            )
        )

    # ------------------------------------------------------------------
    # Async internals
    # ------------------------------------------------------------------

    async def _fetch_async(
        self, notice_type: str, d_from: date, d_to: date
    ) -> list[BZPRawNotice]:
        async with AsyncHTTPClient(
            source="bzp",
            timeout=_BZP_TIMEOUT,
            limits=_BZP_LIMITS,
            retry=_BZP_RETRY,
            rate_per_second=2.0,
            burst=8,
            headers={"Accept": "application/json"},
        ) as http:
            results = await _fetch_windows_async(
                http,
                date_from=d_from,
                date_to=d_to,
                notice_type=notice_type,
                page_size=self._page_size,
            )
            m = http.metrics
            logger.info(
                "source=bzp type=%s days=%d fetched=%d "
                "requests=%d errors=%d p50=%.0fms",
                notice_type,
                (d_to - d_from).days + 1,
                len(results),
                m.requests_total,
                m.requests_error,
                m.p50_ms,
            )
            return results

    async def _sync_result_notices_async(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        dry_run: bool,
    ) -> dict[str, int]:
        today = date.today()
        d_from = date_from or (today - timedelta(days=30))
        d_to = date_to or today

        notices = await self._fetch_async("ResultNotice", d_from, d_to)
        fetched = len(notices)

        records: list[dict[str, Any]] = []
        skipped = 0
        for notice in notices:
            rec = self._parse_result_notice_record(notice)
            if rec and rec.get("winner_name"):
                records.append(rec)
            else:
                skipped += 1

        logger.info("source=bzp parsed=%d valid=%d skipped=%d", fetched, len(records), skipped)

        if dry_run or not records:
            return {"fetched": fetched, "parsed": len(records), "saved": 0, "skipped": skipped}

        try:
            from sqlalchemy import text as sa_text
            from terra_db.session import get_engine
        except ImportError:
            logger.error("terra_db not available — cannot upsert to historical_bids")
            return {"fetched": fetched, "parsed": len(records), "saved": 0, "skipped": skipped}

        upsert_sql = sa_text("""
            INSERT INTO historical_bids (cpv, region, winning_price, bid_date)
            SELECT :cpv, :region, :winning_price, :bid_date
            WHERE NOT EXISTS (
                SELECT 1 FROM historical_bids
                WHERE cpv IS NOT DISTINCT FROM :cpv
                  AND bid_date IS NOT DISTINCT FROM :bid_date
                  AND winning_price IS NOT DISTINCT FROM :winning_price
            )
        """)

        engine = get_engine()
        saved = 0
        with engine.begin() as conn:
            for rec in records:
                try:
                    conn.execute(upsert_sql, {
                        "cpv": rec["cpv_code"],
                        "region": None,
                        "winning_price": rec["awarded_value"],
                        "bid_date": rec["publication_date"],
                    })
                    saved += 1
                except Exception as exc:
                    logger.warning("source=bzp upsert_skip cpv=%s exc=%s", rec.get("cpv_code"), exc)
                    skipped += 1

        logger.info("source=bzp historical_bids saved=%d", saved)
        return {"fetched": fetched, "parsed": len(records), "saved": saved, "skipped": skipped}

    @staticmethod
    def _parse_result_notice_record(notice: BZPRawNotice) -> dict[str, Any] | None:
        d = notice.raw
        low = {k.lower(): v for k, v in d.items()}

        def _get(*keys: str, default: Any = None) -> Any:
            for k in keys:
                v = low.get(k.lower())
                if v is not None and v != "":
                    return v
            return default

        buyer = str(_get("buyername", "buyer_name", "zamawiajacy", default="")).strip() or None
        title = str(_get("orderobject", "order_object", "title", "przedmiot", default="")).strip() or None
        cpv_raw = _get("cpvcode", "cpv_code", "cpv", "maincpvcode")
        if isinstance(cpv_raw, list):
            cpv_raw = cpv_raw[0] if cpv_raw else None
        cpv_code = str(cpv_raw).strip()[:8] if cpv_raw else None

        winner_name = str(_get(
            "contractorname", "contractor_name", "wykonawca", "winnername",
            "selectedcontractorname", default=""
        )).strip() or None

        winner_nip = _get("contractornip", "contractor_nip", "nip", "contractortaxnumber")
        if winner_nip:
            winner_nip = str(winner_nip).replace("-", "").replace(" ", "").strip() or None

        value_raw = _get(
            "contractvalue", "contract_value", "awardedvalue", "offervalue",
            "bestofferprice", "wartosczamowienia"
        )
        awarded_value = parse_pln(value_raw)

        pub_raw = _get("publicationdate", "publication_date", "datapublikacji")
        publication_date: date | None = None
        if pub_raw:
            for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%d.%m.%Y"):
                try:
                    publication_date = datetime.strptime(str(pub_raw)[:19], fmt).date()
                    break
                except ValueError:
                    continue

        return {
            "buyer": buyer,
            "title": title,
            "cpv_code": cpv_code,
            "winner_name": winner_name,
            "winner_nip": winner_nip,
            "awarded_value": awarded_value,
            "publication_date": publication_date,
        }

    # kept for compat — no longer used internally
    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={"Accept": "application/json", "User-Agent": "TerraOS/2.0"},
            follow_redirects=True,
        )
