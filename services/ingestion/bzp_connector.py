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
        max_pages: int = 100,
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
        """Fetch raw notices from BZP API.

        BZP API does NOT support true pagination — pageNumber always returns the same set.
        We work around this by iterating in half-day windows (AM/PM) within the date range.
        pageSize=500 is the effective BZP max. Each half-day window returns up to 500 results.
        Results are deduplicated by bzpNumber.
        """
        from datetime import timedelta

        today = date.today()
        d_from = date_from or (today - timedelta(days=7))
        d_to = date_to or today

        seen: dict[str, BZPRawNotice] = {}  # bzpNumber → notice (dedup)
        page_size = 500  # BZP effective max (1000 breaks, 500 works)

        with self._get_client() as client:
            current = d_from
            while current <= d_to:
                # Split each day into 2 windows (AM: 00-12, PM: 12-24) to stay under 500 limit
                windows = [
                    (f"{current}T00:00:00", f"{current}T11:59:59"),
                    (f"{current}T12:00:00", f"{current}T23:59:59"),
                ]
                for win_from, win_to in windows:
                    params: dict[str, Any] = {
                        "pageSize": page_size,
                        "pageNumber": 0,
                        "NoticeType": "ContractNotice",
                        "PublicationDateFrom": win_from,
                        "PublicationDateTo": win_to,
                    }
                    try:
                        resp = client.get(_NOTICE_EP, params=params, timeout=self._timeout)
                        resp.raise_for_status()
                        data = resp.json()
                    except httpx.HTTPError as exc:
                        logger.warning("BZP API error (%s): %s", win_from, exc)
                        continue

                    notices = data if isinstance(data, list) else data.get("notices", data.get("content", []))
                    win_count = 0
                    for n in notices:
                        raw = BZPRawNotice(n)
                        key = raw.get("bzpNumber") or raw.get("noticeNumber") or raw.get("id")
                        if key and key not in seen:
                            seen[key] = raw
                            win_count += 1
                    if win_count:
                        logger.debug("BZP %s: %d new (total %d)", win_from[:10], win_count, len(seen))

                current += timedelta(days=1)

        results = list(seen.values())
        logger.info("BZP fetch complete: %d unique notices over %d days", len(results), (d_to - d_from).days + 1)
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
        # BZP API (ezamowienia.gov.pl) expects these exact parameter names
        params: dict[str, Any] = {
            "pageSize": size,
            "pageNumber": page,
            "NoticeType": "ContractNotice",
        }
        if date_from:
            params["PublicationDateFrom"] = date_from.strftime("%Y-%m-%dT00:00:00")
        if date_to:
            params["PublicationDateTo"] = date_to.strftime("%Y-%m-%dT23:59:59")
        # NOTE: BZP API does NOT support cpvCodes or voivodeship filters in list endpoint.
        # CPV/scope filtering is done in normalize_bzp_notice() after fetching.
        return params

    # ------------------------------------------------------------------ #
    # ResultNotice → historical_bids
    # ------------------------------------------------------------------ #

    def fetch_result_notices(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[BZPRawNotice]:
        """Fetch ResultNotice documents from BZP API (award announcements).

        Uses the same half-day windowing strategy as fetch_notices() to stay
        below the BZP 500-result-per-request cap.
        """
        from datetime import timedelta

        today = date.today()
        d_from = date_from or (today - timedelta(days=30))
        d_to = date_to or today

        seen: dict[str, BZPRawNotice] = {}
        page_size = 500

        with self._get_client() as client:
            current = d_from
            while current <= d_to:
                windows = [
                    (f"{current}T00:00:00", f"{current}T11:59:59"),
                    (f"{current}T12:00:00", f"{current}T23:59:59"),
                ]
                for win_from, win_to in windows:
                    params: dict[str, Any] = {
                        "pageSize": page_size,
                        "pageNumber": 0,
                        "NoticeType": "ResultNotice",
                        "PublicationDateFrom": win_from,
                        "PublicationDateTo": win_to,
                    }
                    try:
                        resp = client.get(_NOTICE_EP, params=params, timeout=self._timeout)
                        resp.raise_for_status()
                        data = resp.json()
                    except Exception as exc:
                        logger.warning("BZP ResultNotice API error (%s): %s", win_from, exc)
                        continue

                    notices = data if isinstance(data, list) else data.get("notices", data.get("content", []))
                    for n in notices:
                        raw = BZPRawNotice(n)
                        key = raw.get("bzpNumber") or raw.get("noticeNumber") or raw.get("id")
                        if key and key not in seen:
                            seen[key] = raw

                current += timedelta(days=1)

        results = list(seen.values())
        logger.info(
            "BZP ResultNotice fetch: %d unique over %d days",
            len(results),
            (d_to - d_from).days + 1,
        )
        return results

    @staticmethod
    def _parse_result_notice_record(notice: BZPRawNotice) -> dict[str, Any] | None:
        """Extract winner data from a single ResultNotice into a flat dict.

        Returns None if mandatory fields are missing.
        """
        d = notice.raw
        # Normalise keys to lowercase for resilience against API casing changes
        low = {k.lower(): v for k, v in d.items()}

        def _get(*keys: str, default: Any = None) -> Any:
            for k in keys:
                v = low.get(k.lower())
                if v is not None and v != "":
                    return v
            return default

        # Buyer
        buyer = str(_get("buyername", "buyer_name", "zamawiajacy", default="")).strip() or None

        # Title / order object
        title = str(_get("orderobject", "order_object", "title", "przedmiot", default="")).strip() or None

        # CPV
        cpv_raw = _get("cpvcode", "cpv_code", "cpv", "maincpvcode")
        if isinstance(cpv_raw, list):
            cpv_raw = cpv_raw[0] if cpv_raw else None
        cpv_code = str(cpv_raw).strip()[:8] if cpv_raw else None

        # Winner data
        winner_name = str(_get(
            "contractorname", "contractor_name", "wykonawca", "winnername",
            "selectedcontractorname", default=""
        )).strip() or None

        winner_nip = _get("contractornip", "contractor_nip", "nip", "contractortaxnumber")
        if winner_nip:
            winner_nip = str(winner_nip).replace("-", "").replace(" ", "").strip() or None

        # Awarded value
        value_raw = _get(
            "contractvalue", "contract_value", "awardedvalue", "offervalue",
            "bestofferprice", "wartosczamowienia"
        )
        awarded_value: float | None = None
        if value_raw is not None:
            try:
                awarded_value = float(
                    str(value_raw).replace(" ", "").replace(",", ".").replace("PLN", "").strip()
                )
            except (ValueError, TypeError):
                pass

        # Publication date
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

    def sync_result_notices_to_historical_bids(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        dry_run: bool = False,
    ) -> dict[str, int]:
        """Fetch ResultNotice documents and upsert winner data into historical_bids.

        Maps:
            awarded_value  → winning_price
            cpv_code       → cpv
            publication_date → bid_date

        org_id / tender_id are left NULL (external market data, not our own bids).
        Uses (cpv, bid_date, winning_price) as a natural dedup key since
        historical_bids has no unique constraint on external identifiers.

        Returns stats dict: {fetched, parsed, saved, skipped}.
        """
        from sqlalchemy import text as sa_text
        try:
            from terra_db.session import get_engine
        except ImportError:
            logger.error("terra_db not available — cannot upsert to historical_bids")
            return {"fetched": 0, "parsed": 0, "saved": 0, "skipped": 0}

        notices = self.fetch_result_notices(date_from=date_from, date_to=date_to)
        fetched = len(notices)
        logger.info("Parsing %d ResultNotice records…", fetched)

        records: list[dict[str, Any]] = []
        skipped = 0
        for notice in notices:
            rec = self._parse_result_notice_record(notice)
            if rec and rec.get("winner_name"):
                records.append(rec)
            else:
                skipped += 1

        logger.info("Parsed %d valid, %d skipped", len(records), skipped)

        if dry_run or not records:
            return {"fetched": fetched, "parsed": len(records), "saved": 0, "skipped": skipped}

        # Upsert into historical_bids
        # There's no unique constraint on external identifiers, so we use
        # INSERT … ON CONFLICT DO NOTHING keyed on (cpv, bid_date, winning_price).
        upsert_sql = sa_text("""
            INSERT INTO historical_bids (
                cpv,
                region,
                winning_price,
                bid_date
            )
            SELECT
                :cpv,
                :region,
                :winning_price,
                :bid_date
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
                        "region": None,          # voivodeship not in ContractNotice list endpoint
                        "winning_price": rec["awarded_value"],
                        "bid_date": rec["publication_date"],
                    })
                    saved += 1
                except Exception as exc:
                    logger.warning("Skip ResultNotice record: %s", exc)
                    skipped += 1

        logger.info("Saved %d records to historical_bids", saved)
        return {"fetched": fetched, "parsed": len(records), "saved": saved, "skipped": skipped}

    def _get_client(self) -> httpx.Client:
        return httpx.Client(
            headers={
                "Accept": "application/json",
                "User-Agent": "TerraOS/0.1 (terra-os.qa10.io)",
            },
            follow_redirects=True,
        )
