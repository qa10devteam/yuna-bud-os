"""TED EU v3 connector — fetches Polish construction notices via CELLAR search API.

State-of-art upgrade (v2):
  - Async httpx via scraper_base.AsyncHTTPClient
  - Retry/backoff/circuit-breaker unified z scraper_base
  - ScraperMetrics (latency, requests, bytes)
  - Sync wrapper dla backward compat z pipeline.py
  - Connection pool config
  - Structured logging
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any

import httpx

from .scraper_base import AsyncHTTPClient, RetryPolicy

logger = logging.getLogger(__name__)

TED_SEARCH_URL = "https://api.ted.europa.eu/v3/notices/search"

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "dispatch-date",
    "BT-21-Lot",
    "BT-21-Part",
    "BT-24-Lot",
    "BT-300-Lot",
    "title-part",
    "description-part",
    "organisation-name-buyer",
    "organisation-city-buyer",
    "classification-cpv",
    "estimated-value-lot",
    "estimated-value-cur-lot",
    "estimated-value-glo",
    "estimated-value-cur-glo",
    "deadline-receipt-tender-date-lot",
    "place-performance-streetline1-part",
    "place-of-performance-post-code-part",
    "contract-nature",
]

_PAGE_SIZE = 100

_TED_RETRY = RetryPolicy(
    max_attempts=4,
    base_delay=2.0,
    max_delay=60.0,
    backoff_factor=2.0,
    jitter=0.2,
)
_TED_TIMEOUT = httpx.Timeout(connect=8.0, read=45.0, write=10.0, pool=8.0)
_TED_LIMITS = httpx.Limits(
    max_connections=5,
    max_keepalive_connections=3,
    keepalive_expiry=60,
)


class TEDConnector:
    """Fetches construction notices from TED EU v3 API for Poland.

    Sync API (backward compat) wrapping async httpx internals.
    """

    def __init__(self, timeout: int = 45) -> None:
        pass  # timeout arg kept for compat

    def fetch_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[dict[str, Any]]:
        d_from = date_from or (date.today() - timedelta(days=7))
        d_to = date_to or date.today()
        return asyncio.run(self._fetch_async(d_from, d_to))

    def close(self) -> None:
        pass  # no persistent client

    async def _fetch_async(self, d_from: date, d_to: date) -> list[dict[str, Any]]:
        date_from_s = d_from.strftime("%Y%m%d")
        date_to_s = d_to.strftime("%Y%m%d")
        query = (
            f"organisation-country-buyer=POL "
            f"AND contract-nature=works "
            f"AND publication-date>={date_from_s} "
            f"AND publication-date<={date_to_s}"
        )

        async with AsyncHTTPClient(
            source="ted",
            timeout=_TED_TIMEOUT,
            limits=_TED_LIMITS,
            retry=_TED_RETRY,
            rate_per_second=1.5,
            burst=4,
            headers={"Accept": "application/json"},
        ) as http:
            all_notices: dict[str, dict] = {}
            page = 1

            while True:
                payload = {
                    "query": query,
                    "fields": TED_FIELDS,
                    "limit": _PAGE_SIZE,
                    "page": page,
                }
                try:
                    resp = await http.post(TED_SEARCH_URL, json=payload)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPStatusError as exc:
                    logger.warning("source=ted page=%d http_status=%d", page, exc.response.status_code)
                    break
                except Exception as exc:
                    logger.warning("source=ted page=%d error=%s", page, exc)
                    break

                notices = data.get("notices", [])
                if not notices:
                    break

                added = 0
                for n in notices:
                    pub_num = n.get("publication-number")
                    if pub_num and pub_num not in all_notices:
                        all_notices[pub_num] = n
                        added += 1

                http.metrics.record_items(fetched=added)
                total = data.get("totalNoticeCount", 0)
                logger.debug("source=ted page=%d new=%d total_declared=%d", page, added, total)

                if page * _PAGE_SIZE >= total or len(notices) < _PAGE_SIZE:
                    break
                page += 1

            m = http.metrics
            logger.info(
                "source=ted days=%d fetched=%d requests=%d errors=%d p50=%.0fms",
                (d_to - d_from).days + 1,
                len(all_notices),
                m.requests_total,
                m.requests_error,
                m.p50_ms,
            )
            return list(all_notices.values())
