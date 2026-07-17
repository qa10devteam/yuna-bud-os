"""AI Bid Writing — generowanie szkieletu oferty technicznej przy użyciu Claude/Bedrock.

POST /api/v2/bid-writing/generate
  - Przyjmuje tender_id + profil firmy
  - Pobiera dane przetargu z DB (tytuł, opis, CPV, zamawiający, SWZ chunki)
  - Wywołuje AWS Bedrock Claude (boto3)
  - Zwraca szkielet oferty: opis_podejscia, metodologia, doswiadczenie, propozycja_wartosci, podsumowanie

GET /api/v2/bid-writing/history?tender_id={id}
  - Zwraca listę wygenerowanych bid writingów (z bid_writing_log lub pustą listę)
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/bid-writing", tags=["bid-writing"])

# ─── Konfiguracja Bedrock ─────────────────────────────────────────────────────

AWS_REGION = os.getenv("AWS_REGION", "eu-central-1")
MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "eu.anthropic.claude-sonnet-4-20250514-v1:0")

# ─── Schematy ─────────────────────────────────────────────────────────────────


class BidWritingRequest(BaseModel):
    tender_id: str = Field(..., description="UUID przetargu")
    company_name: str = Field(..., description="Nazwa firmy")
    company_nip: str = Field(..., description="NIP firmy")
    company_description: str = Field("", description="Opis firmy, doświadczenie")
    key_projects: list[str] = Field(default_factory=list, description="Lista kluczowych realizacji")
    certifications: list[str] = Field(default_factory=list, description="Certyfikaty, uprawnienia")
    tone: str = Field("professional", description="Tonacja: professional | technical | concise")


class BidWritingSections(BaseModel):
    opis_podejscia: str = Field(..., description="Opis podejścia do realizacji (300-500 słów)")
    metodologia: str = Field(..., description="Metodologia i harmonogram prac (200-400 słów)")
    doswiadczenie: str = Field(..., description="Opis doświadczenia firmy (200-300 słów)")
    propozycja_wartosci: str = Field(..., description="Dlaczego nasza oferta = najlepsza (100-200 słów)")
    podsumowanie: str = Field(..., description="Podsumowanie oferty (100 słów)")


class BidWritingResponse(BaseModel):
    tender_id: str
    tender_title: str
    company_name: str
    sections: BidWritingSections
    word_count: int
    source: str = Field(..., description="'ai' lub 'template'")
    generated_at: str = Field(..., description="ISO datetime")


class BidWritingHistoryItem(BaseModel):
    id: str
    tender_id: str
    company_name: str
    source: str
    word_count: int
    generated_at: str


# ─── Prompty ──────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Jesteś ekspertem ds. zamówień publicznych i copywriterem technicznym. 
Piszesz profesjonalne oferty techniczne dla firm budowlanych w Polsce.
Zasady:
- Pisz konkretnie, unikaj ogólników
- Nawiązuj do wymagań SWZ (jeśli dostępne)
- Używaj języka branżowego (KNR, CPV, SWZ, FIDIC)
- Tonacja: profesjonalna i techniczna
- Podkreślaj przewagi konkurencyjne firmy
- Każda sekcja to osobny, gotowy do wklejenia tekst"""


def _build_user_prompt(
    tender_title: str,
    buyer: str,
    cpv_main: str,
    estimated_value: Any,
    description: str,
    company_name: str,
    company_nip: str,
    company_description: str,
    key_projects: list[str],
    certifications: list[str],
    historical_context: str,
    cpv_prefix: str,
) -> str:
    return f"""Przetarg: {tender_title}
Zamawiający: {buyer}
CPV: {cpv_main}
Wartość szacunkowa: {estimated_value} PLN
Opis zamówienia: {description[:2000]}

Dane firmy:
- Nazwa: {company_name}
- NIP: {company_nip}
- Opis firmy: {company_description}
- Kluczowe realizacje: {key_projects}
- Certyfikaty: {certifications}

Historyczne wyniki podobnych przetargów (CPV {cpv_prefix}):
{historical_context}

Wygeneruj 5 sekcji oferty. Zwróć WYŁĄCZNIE JSON:
{{
  "opis_podejscia": "...",
  "metodologia": "...",
  "doswiadczenie": "...",
  "propozycja_wartosci": "...",
  "podsumowanie": "..."
}}"""


# ─── DB helpers ───────────────────────────────────────────────────────────────


def _fetch_tender_data(tenant_id: str, tender_id: str) -> dict | None:
    """Pobiera dane przetargu z DB."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT id, title, buyer, cpv_main, estimated_value, description "
                "FROM tender "
                "WHERE id = :tid AND tenant_id = :tenant_id"
            ),
            {"tid": tender_id, "tenant_id": tenant_id},
        ).fetchone()
    if row is None:
        return None
    return {
        "id": str(row[0]),
        "title": row[1] or "",
        "buyer": row[2] or "",
        "cpv_main": row[3] or "",
        "estimated_value": row[4],
        "description": row[5] or "",
    }


def _fetch_swz_chunks(tenant_id: str, tender_id: str, limit: int = 30) -> str:
    """Pobiera chunki SWZ z DB, zwraca połączony tekst."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT dc.content "
                    "FROM document_chunk dc "
                    "JOIN tender_document td ON td.id = dc.document_id "
                    "WHERE td.tenant_id = :tid AND td.tender_id = :tender_id "
                    "AND td.parsed_ok = true "
                    "ORDER BY dc.ordinal "
                    "LIMIT :limit"
                ),
                {"tid": tenant_id, "tender_id": tender_id, "limit": limit},
            ).fetchall()
        return "\n\n".join(r[0] for r in rows if r[0])[:6000]
    except Exception as exc:
        logger.warning("Błąd pobierania SWZ chunks: %s", exc)
        return ""


def _fetch_historical_context(cpv_prefix: str, limit: int = 5) -> str:
    """Pobiera historyczne wyniki przetargów dla danego CPV."""
    if not cpv_prefix:
        return "Brak danych historycznych."
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT buyer_name, contractor_name, winning_price_pln, offers_count "
                    "FROM market_results "
                    "WHERE :cpv = ANY(cpv_codes) "
                    "ORDER BY winning_price_pln DESC NULLS LAST "
                    "LIMIT :limit"
                ),
                {"cpv": cpv_prefix, "limit": limit},
            ).fetchall()
        if not rows:
            return "Brak danych historycznych dla tego CPV."
        lines = []
        for r in rows:
            buyer, contractor, price, offers = r
            lines.append(
                f"- Zamawiający: {buyer or 'N/A'}, Zwycięzca: {contractor or 'N/A'}, "
                f"Cena: {price or 'N/A'} PLN, Liczba ofert: {offers or 'N/A'}"
            )
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Błąd pobierania historical context: %s", exc)
        return "Brak danych historycznych (błąd zapytania)."


# ─── Bedrock AI helper ────────────────────────────────────────────────────────


def _call_bedrock(prompt: str) -> dict | None:
    """Wywołuje AWS Bedrock Claude i zwraca sparsowany JSON.
    
    Zwraca None przy błędzie (graceful degradation).
    """
    try:
        client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
        response = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": full_prompt}],
            }),
            contentType="application/json",
            accept="application/json",
        )
        result = json.loads(response["body"].read())
        text_out = result["content"][0]["text"]

        # Wyodrębnij JSON z odpowiedzi
        json_match = re.search(r"\{.*\}", text_out, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        logger.warning("Bedrock zwrócił non-JSON — używam fallback")
        return None

    except (BotoCoreError, ClientError) as exc:
        logger.warning("Bedrock niedostępny (%s) — używam szablonu fallback", exc)
        return None
    except json.JSONDecodeError as exc:
        logger.warning("Błąd parsowania JSON z Bedrock (%s) — używam fallback", exc)
        return None
    except Exception as exc:
        logger.error("Nieoczekiwany błąd Bedrock: %s", exc)
        return None


# ─── Fallback template ────────────────────────────────────────────────────────


def _build_fallback_sections(
    tender_title: str,
    buyer: str,
    cpv_main: str,
    company_name: str,
    company_description: str,
    key_projects: list[str],
    certifications: list[str],
) -> dict:
    """Szablon oferty używany gdy Bedrock niedostępny."""
    projects_text = (
        ", ".join(key_projects[:3]) if key_projects else "liczne realizacje budowlane"
    )
    certs_text = (
        ", ".join(certifications[:3]) if certifications else "odpowiednie uprawnienia"
    )
    company_desc = company_description or f"firma budowlana działająca na rynku polskim"

    return {
        "opis_podejscia": (
            f"Firma {company_name} przystepuje do realizacji zamowienia pn. '{tender_title}' "
            f"z pełnym zrozumieniem wymagań Zamawiającego ({buyer}). "
            f"Nasze podejście opiera się na sprawdzonej metodyce realizacji robót "
            f"w zakresie CPV {cpv_main}, zapewniając najwyższą jakość wykonania "
            f"przy zachowaniu terminowości i zgodności z dokumentacją techniczną. "
            f"Posiadamy doświadczone zespoły robocze oraz nowoczesny sprzęt umożliwiający "
            f"sprawną realizację każdego etapu prac. Nadzór nad inwestycją sprawują "
            f"wykwalifikowani kierownicy budowy z uprawnieniami w odpowiedniej specjalności."
        ),
        "metodologia": (
            f"Realizację zamówienia planujemy w następujących etapach:\n"
            f"1. Etap przygotowawczy (tydzień 1-2): mobilizacja sprzętu i ekip, "
            f"przejęcie placu budowy, weryfikacja dokumentacji projektowej.\n"
            f"2. Etap realizacji głównej: zgodnie z harmonogramem rzeczowo-finansowym "
            f"załączonym do oferty, z zachowaniem wymogów SWZ i SIWZ.\n"
            f"3. Etap końcowy: odbiory częściowe i końcowy, usunięcie usterek, "
            f"przekazanie dokumentacji powykonawczej Zamawiającemu.\n"
            f"Komunikacja z Zamawiającym realizowana będzie przez dedykowanego "
            f"kierownika projektu — cotygodniowe raporty postępu i narady koordynacyjne."
        ),
        "doswiadczenie": (
            f"{company_name} to {company_desc}. "
            f"W naszym portfolio znajdują się m.in.: {projects_text}. "
            f"Posiadamy certyfikaty i uprawnienia: {certs_text}. "
            f"Przez lata działalności zdobyliśmy zaufanie licznych zamawiających "
            f"publicznych, realizując kontrakty terminowo i zgodnie z wymogami prawa "
            f"zamówień publicznych. Nasi pracownicy posiadają aktualne uprawnienia "
            f"budowlane i regularnie podnoszą kwalifikacje zawodowe."
        ),
        "propozycja_wartosci": (
            f"Wybierając ofertę {company_name}, Zamawiający zyskuje partnera "
            f"z udokumentowanym doświadczeniem w realizacji podobnych inwestycji. "
            f"Gwarantujemy terminowość wykonania, transparentność kosztów oraz "
            f"pełną zgodność z wymaganiami SWZ. Oferujemy stały nadzór techniczny, "
            f"szybką reakcję na ewentualne problemy i wsparcie w okresie gwarancji."
        ),
        "podsumowanie": (
            f"Firma {company_name} spełnia wszystkie wymagania formalne i techniczne "
            f"okreslone w SWZ dla zamowienia '{tender_title}'. "
            f"Posiadamy niezbędne zasoby ludzkie, sprzętowe i finansowe do prawidłowej "
            f"realizacji przedmiotu zamówienia. Zachęcamy do zapoznania się "
            f"z pełną dokumentacją ofertową i wyrażamy gotowość do udzielenia "
            f"wszelkich wyjaśnień."
        ),
    }


# ─── Endpointy ────────────────────────────────────────────────────────────────


@router.post(
    "/generate",
    response_model=BidWritingResponse,
    summary="Generuj szkielet oferty technicznej (AI Bid Writing)",
)
async def generate_bid_writing(
    req: BidWritingRequest,
    user: AuthUser,
) -> BidWritingResponse:
    """Generuje profesjonalny szkielet oferty technicznej dla przetargu.

    Wywołuje AWS Bedrock Claude. Przy niedostępności AI zwraca szablon fallback.
    """
    tenant_id = user.tenant_id

    # 1. Pobierz dane przetargu z DB
    tender = _fetch_tender_data(tenant_id, req.tender_id)
    if tender is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Przetarg o ID {req.tender_id} nie istnieje lub brak dostępu.",
        )

    tender_title = tender["title"]
    buyer = tender["buyer"]
    cpv_main = tender["cpv_main"]
    estimated_value = tender["estimated_value"]
    description = tender["description"]

    # 2. Pobierz chunki SWZ (opcjonalnie)
    swz_chunks = _fetch_swz_chunks(tenant_id, req.tender_id)
    if swz_chunks:
        description = f"{description}\n\nFragmenty SWZ:\n{swz_chunks}"

    # 3. Pobierz historyczny kontekst
    cpv_prefix = (cpv_main or "")[:8]
    historical_context = _fetch_historical_context(cpv_prefix)

    # 4. Zbuduj prompt i wywołaj Bedrock
    source = "ai"
    sections_raw: dict | None = None

    prompt = _build_user_prompt(
        tender_title=tender_title,
        buyer=buyer,
        cpv_main=cpv_main,
        estimated_value=estimated_value,
        description=description,
        company_name=req.company_name,
        company_nip=req.company_nip,
        company_description=req.company_description,
        key_projects=req.key_projects,
        certifications=req.certifications,
        historical_context=historical_context,
        cpv_prefix=cpv_prefix,
    )

    sections_raw = _call_bedrock(prompt)

    if sections_raw is None:
        # Graceful degradation — fallback do szablonu
        logger.info(
            "Używam fallback template dla tender_id=%s (Bedrock niedostępny)",
            req.tender_id,
        )
        source = "template"
        sections_raw = _build_fallback_sections(
            tender_title=tender_title,
            buyer=buyer,
            cpv_main=cpv_main,
            company_name=req.company_name,
            company_description=req.company_description,
            key_projects=req.key_projects,
            certifications=req.certifications,
        )

    # 5. Zbuduj obiekt sekcji
    try:
        sections = BidWritingSections(
            opis_podejscia=sections_raw.get("opis_podejscia", ""),
            metodologia=sections_raw.get("metodologia", ""),
            doswiadczenie=sections_raw.get("doswiadczenie", ""),
            propozycja_wartosci=sections_raw.get("propozycja_wartosci", ""),
            podsumowanie=sections_raw.get("podsumowanie", ""),
        )
    except Exception as exc:
        logger.error("Błąd budowania BidWritingSections: %s", exc)
        # Ostatni fallback
        source = "template"
        fallback = _build_fallback_sections(
            tender_title=tender_title,
            buyer=buyer,
            cpv_main=cpv_main,
            company_name=req.company_name,
            company_description=req.company_description,
            key_projects=req.key_projects,
            certifications=req.certifications,
        )
        sections = BidWritingSections(**fallback)

    # 6. Policz słowa
    all_text = " ".join([
        sections.opis_podejscia,
        sections.metodologia,
        sections.doswiadczenie,
        sections.propozycja_wartosci,
        sections.podsumowanie,
    ])
    word_count = len(all_text.split())

    # 7. Opcjonalnie: zapisz do bid_writing_log (graceful — tabela może nie istnieć)
    _try_log_bid_writing(
        tenant_id=tenant_id,
        tender_id=req.tender_id,
        company_name=req.company_name,
        source=source,
        word_count=word_count,
        sections_json=sections.model_dump(),
    )

    return BidWritingResponse(
        tender_id=req.tender_id,
        tender_title=tender_title,
        company_name=req.company_name,
        sections=sections,
        word_count=word_count,
        source=source,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get(
    "/history",
    response_model=list[BidWritingHistoryItem],
    summary="Historia wygenerowanych ofert dla przetargu",
)
async def get_bid_writing_history(
    user: AuthUser,
    tender_id: str = Query(..., description="UUID przetargu"),
) -> list[BidWritingHistoryItem]:
    """Zwraca listę wygenerowanych bid writingów dla danego przetargu.

    Jeśli tabela bid_writing_log nie istnieje — zwraca pustą listę.
    """
    tenant_id = user.tenant_id
    engine = get_engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id::text, tender_id::text, company_name, source, "
                    "word_count, generated_at "
                    "FROM bid_writing_log "
                    "WHERE tenant_id = :tenant_id AND tender_id = :tender_id "
                    "ORDER BY generated_at DESC "
                    "LIMIT 50"
                ),
                {"tenant_id": tenant_id, "tender_id": tender_id},
            ).fetchall()
        return [
            BidWritingHistoryItem(
                id=str(r[0]),
                tender_id=str(r[1]),
                company_name=r[2] or "",
                source=r[3] or "unknown",
                word_count=r[4] or 0,
                generated_at=str(r[5]) if r[5] else "",
            )
            for r in rows
        ]
    except Exception as exc:
        # Tabela bid_writing_log może nie istnieć — graceful fallback
        logger.debug("bid_writing_log niedostępna: %s", exc)
        return []


# ─── Log helper ───────────────────────────────────────────────────────────────


def _try_log_bid_writing(
    tenant_id: str,
    tender_id: str,
    company_name: str,
    source: str,
    word_count: int,
    sections_json: dict,
) -> None:
    """Próbuje zapisać wynik do bid_writing_log. Ignoruje błędy (tabela może nie istnieć)."""
    engine = get_engine()
    try:
        with engine.connect() as conn:
            conn.execute(
                text(
                    "INSERT INTO bid_writing_log "
                    "(tenant_id, tender_id, company_name, source, word_count, sections, generated_at) "
                    "VALUES (:tenant_id, :tender_id, :company_name, :source, :word_count, "
                    ":sections::jsonb, NOW())"
                ),
                {
                    "tenant_id": tenant_id,
                    "tender_id": tender_id,
                    "company_name": company_name,
                    "source": source,
                    "word_count": word_count,
                    "sections": json.dumps(sections_json, ensure_ascii=False),
                },
            )
            conn.commit()
    except Exception as exc:
        logger.debug("Nie udało się zapisać do bid_writing_log (tabela może nie istnieć): %s", exc)
