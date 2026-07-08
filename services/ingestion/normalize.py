"""M1 — Normalize: converts raw BZP/TED/BK notices to canonical TenderIn model."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from .bzp_connector import BZPRawNotice, _cpv_matches, is_construction_scope

logger = logging.getLogger(__name__)

# Mapping of Polish voivodeship names/codes to canonical lowercase strings
_VOIVODESHIP_ALIASES: dict[str, str] = {
    "dolnośląskie": "dolnośląskie",
    "dolnoslaskie": "dolnośląskie",
    "lower silesian": "dolnośląskie",
    "kujawsko-pomorskie": "kujawsko-pomorskie",
    "lubelskie": "lubelskie",
    "lubuskie": "lubuskie",
    "łódzkie": "łódzkie",
    "lodzkie": "łódzkie",
    "małopolskie": "małopolskie",
    "malopolskie": "małopolskie",
    "mazowieckie": "mazowieckie",
    "opolskie": "opolskie",
    "podkarpackie": "podkarpackie",
    "podlaskie": "podlaskie",
    "pomorskie": "pomorskie",
    "śląskie": "śląskie",
    "slaskie": "śląskie",
    "świętokrzyskie": "świętokrzyskie",
    "swietokrzyskie": "świętokrzyskie",
    "warmińsko-mazurskie": "warmińsko-mazurskie",
    "warminsko-mazurskie": "warmińsko-mazurskie",
    "wielkopolskie": "wielkopolskie",
    "zachodniopomorskie": "zachodniopomorskie",
}


def normalize_voivodeship(raw: str | None) -> str | None:
    if not raw:
        return None
    cleaned = raw.strip().lower()
    return _VOIVODESHIP_ALIASES.get(cleaned, cleaned)


def normalize_cpv(raw_cpv: Any) -> list[str]:
    """Normalize CPV codes from various formats to list of strings."""
    if not raw_cpv:
        return []
    if isinstance(raw_cpv, str):
        # BZP format: "45000000-7 (Roboty budowlane),45400000-1 (Roboty wykończeniowe)"
        # Split by comma, then extract leading digits-dash-digit pattern
        codes_raw = [c.strip() for c in raw_cpv.split(",")]
    elif isinstance(raw_cpv, list):
        codes_raw = [str(c).strip() for c in raw_cpv]
    else:
        return []
    # Extract numeric CPV code from each entry (ignore description in parentheses)
    result = []
    for code in codes_raw:
        code = code.strip()
        # Try to extract "XXXXXXXX-X" pattern from start of string
        m = re.match(r'^(\d{8}-\d)', code)
        if m:
            result.append(m.group(1))
            continue
        # Plain 8-digit code without check digit
        m = re.match(r'^(\d{8})\b', code)
        if m:
            result.append(m.group(1))
            continue
        # Fallback: use as-is if non-empty
        stripped = re.sub(r'\s*\(.*', '', code).strip()
        if stripped:
            result.append(stripped)
    return result


def parse_datetime(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(raw[:len(fmt)].replace("Z", ""), fmt.replace("%z", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    logger.debug("Cannot parse datetime: %r", raw)
    return None


def parse_value(raw: Any) -> Decimal | None:
    if raw is None:
        return None
    try:
        return Decimal(str(raw)).quantize(Decimal("0.01"))
    except Exception:
        return None


def _parse_value_from_html(html: str | None) -> Decimal | None:
    """Extract estimated value from BZP htmlBody field."""
    if not html:
        return None
    for pattern in [
        r'([\d\s]{4,}[,\.]\d{2})\s*(?:PLN|zł)',
        r'Wartość.*?([\d\s]{4,}[,\.]\d{2})',
        r'szacunkow[a-z]*.*?([\d\s]{4,}[,\.]\d{2})',
    ]:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            raw = m.group(1).replace("\xa0", "").replace(" ", "").replace(",", ".")
            try:
                v = float(raw)
                if 1_000 < v < 5_000_000_000:
                    return Decimal(str(v)).quantize(Decimal("0.01"))
            except ValueError:
                pass
    return None



class TenderIn:
    """Canonical representation of a tender before DB upsert.

    This is NOT a SQLAlchemy model — it's a pure data transfer object.
    """

    __slots__ = (
        "source",
        "external_id",
        "title",
        "buyer",
        "cpv",
        "voivodeship",
        "nuts_code",
        "value_pln",
        "deadline_at",
        "published_at",
        "url",
        "raw",
    )

    def __init__(
        self,
        *,
        source: str,
        external_id: str,
        title: str,
        buyer: str | None,
        cpv: list[str],
        voivodeship: str | None,
        nuts_code: str | None = None,
        value_pln: Decimal | None,
        deadline_at: datetime | None,
        published_at: datetime | None,
        url: str | None,
        raw: dict,
    ) -> None:
        self.source = source
        self.external_id = external_id
        self.title = title
        self.buyer = buyer
        self.cpv = cpv
        self.voivodeship = voivodeship
        self.nuts_code = nuts_code
        self.value_pln = value_pln
        self.deadline_at = deadline_at
        self.published_at = published_at
        self.url = url
        self.raw = raw


def normalize_bzp_notice(notice: BZPRawNotice) -> TenderIn | None:
    """Convert raw BZP notice to TenderIn. Returns None if notice should be skipped."""
    # BZP API uses orderType: "Works" for roboty budowlane
    order_type = notice.get("orderType", "")
    if order_type and order_type not in ("Works", "RC", "RB", ""):
        return None  # skip Supplies / Services

    # BZP API uses "cpvCode" (string, comma-separated), not "cpvCodes"
    cpv = normalize_cpv(notice.get("cpvCode", "") or notice.get("cpvCodes", []))
    if not cpv:
        return None
    if not is_construction_scope(cpv):
        return None

    # External ID: bzpNumber is canonical (e.g. "2026/BZP 00315918")
    external_id = (notice.get("bzpNumber") or notice.get("noticeNumber", "")).strip()
    if not external_id:
        return None

    # Title: BZP uses "orderObject", fallback to "name" or "title"
    title = (
        notice.get("orderObject") or notice.get("procurementObject") or
        notice.get("name") or notice.get("title") or ""
    ).strip()
    if not title:
        return None

    # Buyer: BZP uses "organizationName"
    buyer = (
        notice.get("organizationName") or notice.get("orderingPartyName") or
        notice.get("buyer") or ""
    ).strip() or None

    # Voivodeship: BZP uses "organizationProvince" as PL code (e.g. "PL32")
    raw_voiv = notice.get("organizationProvince") or notice.get("executionPlace") or notice.get("voivodeship")
    # Map NUTS-2 PL code → Polish name
    _PROVINCE_MAP = {
        "PL02": "dolnośląskie", "PL04": "kujawsko-pomorskie",
        "PL06": "lubelskie", "PL08": "lubuskie",
        "PL10": "łódzkie", "PL12": "małopolskie",
        "PL14": "mazowieckie", "PL16": "opolskie",
        "PL18": "podkarpackie", "PL20": "podlaskie",
        "PL22": "pomorskie", "PL24": "śląskie",
        "PL26": "świętokrzyskie", "PL28": "warmińsko-mazurskie",
        "PL30": "wielkopolskie", "PL32": "zachodniopomorskie",
    }
    if raw_voiv and raw_voiv.upper() in _PROVINCE_MAP:
        voivodeship = _PROVINCE_MAP[raw_voiv.upper()]
    else:
        voivodeship = normalize_voivodeship(raw_voiv)

    # Value: parse from htmlBody (BZP doesn't return structured value in list endpoint)
    value_pln = (
        parse_value(notice.get("estimatedValue")) or
        parse_value(notice.get("estimatedValueFrom")) or
        _parse_value_from_html(notice.get("htmlBody", ""))
    )

    # Deadline: BZP uses "submittingOffersDate"
    deadline_at = parse_datetime(
        notice.get("submittingOffersDate") or notice.get("submissionDeadlineDate") or notice.get("deadline")
    )
    # Published: BZP uses "publicationDate"
    published_at = parse_datetime(
        notice.get("publicationDate") or notice.get("noticePublicationDate") or notice.get("publishedAt")
    )

    # Build URL using tenderId (deep link to e-zamowienia)
    tender_id = notice.get("tenderId", "")
    notice_number = notice.get("noticeNumber") or notice.get("bzpNumber", "")
    if tender_id:
        url = f"https://ezamowienia.gov.pl/mp-client/tenders/{tender_id}"
    elif notice_number:
        url = f"https://ezamowienia.gov.pl/mo-client-board/bzp/notice-details/id/{notice_number}"
    else:
        url = None

    return TenderIn(
        source="bzp",
        external_id=external_id,
        title=title,
        buyer=buyer,
        cpv=cpv,
        voivodeship=voivodeship,
        value_pln=value_pln,
        deadline_at=deadline_at,
        published_at=published_at,
        url=url,
        raw=notice.raw,
    )


# ---------------------------------------------------------------------------
# TED EU normalizer
# ---------------------------------------------------------------------------

def _ted_str(val: Any, lang: str = "pol") -> str | None:
    """Extract string from TED multilingual dict like {'pol': 'text'} or list."""
    if not val:
        return None
    if isinstance(val, str):
        return val.strip() or None
    if isinstance(val, dict):
        # Prefer Polish, fall back to English, then first available
        for lng in (lang, "eng", "ENG"):
            if lng in val and val[lng]:
                v = val[lng]
                if isinstance(v, list):
                    return str(v[0]).strip() or None
                return str(v).strip() or None
        # any key
        for v in val.values():
            if v:
                s = v[0] if isinstance(v, list) else v
                return str(s).strip() or None
    if isinstance(val, list) and val:
        return _ted_str(val[0], lang)
    return None


def _ted_value(notice: dict, *keys: str) -> Decimal | None:
    """Extract first non-null numeric value from TED notice by key list."""
    for k in keys:
        raw = notice.get(k)
        if raw is None:
            continue
        if isinstance(raw, list):
            raw = raw[0] if raw else None
        if raw is None:
            continue
        try:
            return Decimal(str(raw))
        except Exception:
            continue
    return None


def _ted_deadline(notice: dict) -> datetime | None:
    raw = notice.get("deadline-receipt-tender-date-lot")
    if not raw:
        return None
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if not raw:
        return None
    try:
        # Format: "2026-07-06+02:00" — strip tz offset and parse
        date_str = str(raw).split("+")[0].split("-0")[0]  # naive strip
        # Try ISO with tz first
        from datetime import timezone as tz_
        import re as re_
        m = re_.match(r"(\d{4}-\d{2}-\d{2})", str(raw))
        if m:
            return datetime.fromisoformat(m.group(1) + "T23:59:59").replace(tzinfo=timezone.utc)
    except Exception:
        pass
    return None


def normalize_ted_notice(notice: dict[str, Any]) -> TenderIn | None:
    """Normalize a TED v3 notice dict to TenderIn.

    Returns None if notice lacks required fields or is not construction scope.
    Field names validated against TED v3 API 2026-07-08.
    """
    pub_num = notice.get("publication-number")
    if not pub_num:
        return None

    external_id = f"TED/{pub_num}"

    # CPV — list of 8-digit strings e.g. ["45210000", "45111300"]
    raw_cpv: list = notice.get("classification-cpv") or []
    cpv = normalize_cpv(raw_cpv)
    # Skip non-construction only if we have CPV data — if empty, still keep notice
    if cpv and not is_construction_scope(cpv):
        return None

    # Title — eForms BT-21-Lot/Part (most common), fallback to description or fallback string
    title = (
        _ted_str(notice.get("BT-21-Lot"))
        or _ted_str(notice.get("BT-21-Part"))
        or _ted_str(notice.get("BT-24-Lot"))
        or _ted_str(notice.get("title-part"))
        or _ted_str(notice.get("description-part"))
        or f"TED notice {pub_num}"
    )

    # Buyer — {"pol": ["Gmina Warszawa"]} or list
    buyer = _ted_str(notice.get("organisation-name-buyer"))

    # NUTS code + voivodeship — try NUTS fields from raw, then city name fallback
    from .nuts_mapping import extract_nuts_from_raw  # local import to avoid circular deps
    nuts_code, voivodeship = extract_nuts_from_raw(notice)

    # Value — lot level first, global fallback
    value_pln = _ted_value(
        notice,
        "estimated-value-lot",
        "estimated-value-glo",
    )

    # Deadline
    deadline_at = _ted_deadline(notice)

    # Published date — "2024-03-15" or "20240315"
    pub_date_raw = notice.get("publication-date", "")
    try:
        pub_date_str = str(pub_date_raw).replace("-", "")[:8]  # normalise to YYYYMMDD
        published_at = datetime(
            int(pub_date_str[:4]), int(pub_date_str[4:6]), int(pub_date_str[6:8]),
            tzinfo=timezone.utc,
        )
    except Exception:
        published_at = datetime.now(tz=timezone.utc)

    url = f"https://ted.europa.eu/pl/notice/{pub_num}/html"

    return TenderIn(
        source="ted",
        external_id=external_id,
        title=title,
        buyer=buyer,
        cpv=cpv,
        voivodeship=voivodeship,
        nuts_code=nuts_code,
        value_pln=value_pln,
        deadline_at=deadline_at,
        published_at=published_at,
        url=url,
        raw=notice,
    )


# ---------------------------------------------------------------------------
# BIP normalizer (Faza 8)
# ---------------------------------------------------------------------------

def normalize_bip_notice(notice: dict) -> "TenderIn | None":
    """Normalize a BIPTender (as dict) or raw BIP notice dict to TenderIn.

    BIP notices are scraped from decentralized municipal BIP sites, so the
    structure varies. We support two inputs:
    1. A dict produced by dataclasses.asdict(BIPTender) — keys: title, url,
       published, description, bip_site_id, bip_site_name, region
    2. A raw dict from ezamowienia Board API or similar structured source

    Returns None if the notice lacks a title or URL.
    """
    if not notice:
        return None

    # --- Title ---
    title = (
        notice.get("title")
        or notice.get("orderObject")
        or notice.get("name")
        or notice.get("subject")
        or ""
    ).strip()
    if not title:
        return None

    # --- URL / External ID ---
    url = (
        notice.get("url")
        or notice.get("link")
        or notice.get("procurementUrl")
        or ""
    ).strip() or None

    # External ID: use URL hash (deterministic, same logic as BIPTender.external_id)
    import hashlib
    raw_id = (
        notice.get("external_id")
        or notice.get("id")
        or notice.get("bipNumber")
    )
    if raw_id:
        external_id = str(raw_id).strip()
    elif url:
        external_id = "bip:" + hashlib.md5(url.encode()).hexdigest()[:16]
    else:
        return None  # Cannot create a unique identifier

    # --- Buyer ---
    buyer = (
        notice.get("buyer")
        or notice.get("bip_site_name")
        or notice.get("organizationName")
        or notice.get("orderingPartyName")
        or ""
    ).strip() or None

    # --- CPV codes ---
    # BIP sub-threshold tenders often lack CPV; accept empty list (will pass filter)
    cpv_raw = (
        notice.get("cpv")
        or notice.get("cpvCode")
        or notice.get("cpv_code")
        or notice.get("cpvCodes")
        or ""
    )
    cpv = normalize_cpv(cpv_raw)

    # --- Voivodeship ---
    raw_voiv = (
        notice.get("voivodeship")
        or notice.get("region")
        or notice.get("bip_region")
        or notice.get("organizationProvince")
        or ""
    )
    voivodeship = normalize_voivodeship(raw_voiv) if raw_voiv else None

    # --- Value ---
    value_pln = (
        parse_value(notice.get("value_pln"))
        or parse_value(notice.get("estimatedValue"))
        or parse_value(notice.get("contractValue"))
        or _parse_value_from_html(notice.get("description", ""))
    )

    # --- Deadline ---
    deadline_raw = (
        notice.get("deadline")
        or notice.get("deadline_at")
        or notice.get("submittingOffersDate")
        or notice.get("submissionDeadlineDate")
    )
    deadline_at = parse_datetime(str(deadline_raw)) if deadline_raw else None

    # --- Published ---
    published_raw = (
        notice.get("published")
        or notice.get("published_at")
        or notice.get("publicationDate")
        or notice.get("pub_date")
    )
    if published_raw:
        # BIPTender.published is a date object — convert to datetime
        if hasattr(published_raw, "year"):
            # Already a date/datetime
            from datetime import timezone as _tz
            published_at = datetime(
                published_raw.year, published_raw.month, published_raw.day,
                tzinfo=timezone.utc,
            )
        else:
            published_at = parse_datetime(str(published_raw))
    else:
        published_at = None

    return TenderIn(
        source="bip",
        external_id=external_id,
        title=title,
        buyer=buyer,
        cpv=cpv,
        voivodeship=voivodeship,
        value_pln=value_pln,
        deadline_at=deadline_at,
        published_at=published_at,
        url=url,
        raw=notice,
    )
