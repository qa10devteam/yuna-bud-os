"""M1 — BZP connector: fetches notices from ezamowienia.gov.pl public API."""
from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

BZP_BASE = "https://ezamowienia.gov.pl/mo-board/api/v1"
_NOTICE_EP = f"{BZP_BASE}/notice"

# CPV codes — pełne budownictwo (CPV 45)
# Zachowane dla kompatybilności wstecznej
EARTHWORKS_CPV = [
    "45111200-0",  # Przygotowanie terenu + roboty ziemne — PRIMARY
    "45111000-8",  # Roboty ziemne ogólne
    "45112000-5",  # Usuwanie gleby
    "45112700-2",  # Kształtowanie terenu
    "45233120-6",  # Budowa dróg — PRIMARY
    "45233200-1",  # Różne nawierzchnie
    "45233140-2",  # Roboty drogowe
    "45231300-8",  # Wodociągi i rurociągi (+ roboty ziemne)
    "45232410-9",  # Kanalizacja ściekowa
    "45246000-3",  # Regulacja rzek, wały
    "45112500-0",  # Tereny poprzemysłowe
]

# CPV codes — pełne budownictwo (CPV 45)
CONSTRUCTION_CPV_PREFIXES = [
    "45",  # Cała dywizja 45 — Roboty budowlane
]

# CPV prefixes for broader matching (first 5 digits = division)
# Zachowane dla kompatybilności wstecznej
EARTHWORKS_CPV_PREFIXES = {"45111", "45112", "45233", "45231", "45232", "45246"}


def is_construction_scope(cpv_codes: list[str]) -> bool:
    """Return True if any CPV code is in construction scope (division 45)."""
    return any(c.startswith("45") for c in cpv_codes)


class BZPRawNotice:
    """Raw notice from BZP API — just a typed dict wrapper."""

    def __init__(self, data: dict[str, Any]) -> None:
        self._d = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    @property
    def raw(self) -> dict[str, Any]:
        return self._d


def _cpv_matches(cpv_list: list[str]) -> bool:
    """Return True if any CPV code is in construction scope (backward compat alias)."""
    return is_construction_scope(cpv_list)


class BZPConnector:
    """Fetches notices from the public BZP API.

    Endpoint: GET https://ezamowienia.gov.pl/mo-board/api/v1/notice
    Auth: None (public endpoint)
    Format: JSON

    Reference: https://ezamowienia.gov.pl/pl/integracja/
    Attachment 3: Instrukcja integracji z API BZP
    """

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        page_size: int = 50,
        max_pages: int = 20,
    ) -> None:
        self._timeout = timeout
        self._page_size = page_size
        self._max_pages = max_pages
        self._client: httpx.Client | None = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def fetch_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        cpv_codes: list[str] | None = None,
        voivodeship: str | None = None,
        order_type: str = "RC",  # RC = roboty budowlane
    ) -> list[BZPRawNotice]:
        """Fetch raw notices from BZP API with optional filters.

        Returns all matching notices (paginated internally).
        """
        cpv_codes = cpv_codes or EARTHWORKS_CPV  # fallback to earthworks for backward compat
        results: list[BZPRawNotice] = []
        page = 0

        with self._get_client() as client:
            while page < self._max_pages:
                params = self._build_params(
                    date_from=date_from,
                    date_to=date_to,
                    cpv_codes=cpv_codes,
                    voivodeship=voivodeship,
                    order_type=order_type,
                    page=page,
                    size=self._page_size,
                )
                try:
                    resp = client.get(_NOTICE_EP, params=params, timeout=self._timeout)
                    resp.raise_for_status()
                    data = resp.json()
                except httpx.HTTPError as exc:
                    logger.warning("BZP API error (page=%d): %s", page, exc)
                    break

                notices = data if isinstance(data, list) else data.get("notices", data.get("content", []))
                if not notices:
                    break

                results.extend(BZPRawNotice(n) for n in notices)
                logger.debug("BZP page=%d got %d notices", page, len(notices))

                # Check if last page
                if isinstance(data, dict):
                    total_pages = data.get("totalPages", data.get("total_pages", 1))
                    if page + 1 >= int(total_pages):
                        break
                elif len(notices) < self._page_size:
                    break

                page += 1

        logger.info("BZP fetch complete: %d raw notices", len(results))
        return results

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _build_params(
        self,
        *,
        date_from: date | None,
        date_to: date | None,
        cpv_codes: list[str],
        voivodeship: str | None,
        order_type: str,
        page: int,
        size: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "orderType": order_type,
            "page": page,
            "size": size,
            "sort": "noticePublicationDate,desc",
        }
        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()
        if cpv_codes:
            # API accepts comma-separated or repeated param
            params["cpvCodes"] = ",".join(cpv_codes[:10])  # API limit
        if voivodeship:
            params["executionPlace"] = voivodeship
        return params

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "Accept": "application/json",
                "User-Agent": "TerraOS/0.1 (terra-os.qa10.io)",
            },
            follow_redirects=True,
        )
