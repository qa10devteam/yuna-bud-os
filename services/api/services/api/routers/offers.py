"""Faza 7 — Oferty: pełny CRUD + generowanie PDF (reportlab).

Endpoints:
  GET    /api/v1/offers                   → {next_cursor, items}
  POST   /api/v1/offers                   → nowa oferta
  GET    /api/v1/offers/{id}              → szczegóły oferty
  PATCH  /api/v1/offers/{id}             → aktualizacja
  DELETE /api/v1/offers/{id}             → usunięcie
  GET    /api/v1/offers/{id}/pdf          → StreamingResponse (application/pdf)
"""
from __future__ import annotations

import base64
import io
import json
import uuid
from datetime import date, datetime
from typing import Any, Optional

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])

# ─── Pydantic models ──────────────────────────────────────────────────────────

class OfferCreate(BaseModel):
    title: str
    tender_id: Optional[str] = None
    estimate_id: Optional[str] = None
    status: str = "draft"
    contractor_name: Optional[str] = None
    contractor_nip: Optional[str] = None
    contractor_address: Optional[str] = None
    delivery_days: int = 60
    warranty_months: int = 36
    payment_terms: str = "30 dni od faktury"
    notes: Optional[str] = None
    price_gross_pln: Optional[float] = None
    vat_pct: float = 23.0
    metadata: dict = {}
    source: Optional[str] = None  # bzp / ted / bip


class OfferUpdate(BaseModel):
    title: Optional[str] = None
    tender_id: Optional[str] = None
    estimate_id: Optional[str] = None
    status: Optional[str] = None
    contractor_name: Optional[str] = None
    contractor_nip: Optional[str] = None
    contractor_address: Optional[str] = None
    delivery_days: Optional[int] = None
    warranty_months: Optional[int] = None
    payment_terms: Optional[str] = None
    notes: Optional[str] = None
    price_gross_pln: Optional[float] = None
    vat_pct: Optional[float] = None
    metadata: Optional[dict] = None
    source: Optional[str] = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

VALID_STATUSES = {"draft", "ready", "submitted", "won", "lost"}
VALID_SOURCES = {"bzp", "ted", "bip"}


def _row_to_dict(row: Any) -> dict:
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "tender_id": row.tender_id,
        "estimate_id": str(row.estimate_id) if row.estimate_id else None,
        "title": row.title,
        "status": row.status,
        "source": row.source if hasattr(row, "source") else None,
        "contractor_name": row.contractor_name,
        "contractor_nip": row.contractor_nip,
        "contractor_address": row.contractor_address,
        "delivery_days": row.delivery_days,
        "warranty_months": row.warranty_months,
        "payment_terms": row.payment_terms,
        "notes": row.notes,
        "price_gross_pln": float(row.price_gross_pln) if row.price_gross_pln is not None else None,
        "vat_pct": float(row.vat_pct) if row.vat_pct is not None else None,
        "metadata": row.metadata if isinstance(row.metadata, dict) else {},
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# ─── Cursor pagination helpers ────────────────────────────────────────────────

def _encode_cursor(created_at: Any, row_id: Any) -> str:
    """Encode (created_at, id) into a base64 cursor string."""
    ts = created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at)
    payload = json.dumps({"created_at": ts, "id": str(row_id)})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, str]:
    """Decode cursor string → (created_at_iso, id_str). Raises HTTPException on bad input."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return payload["created_at"], payload["id"]
    except Exception:
        raise HTTPException(status_code=400, detail={"error": "invalid_cursor", "message": "Nieprawidłowy cursor paginacji"})


# ─── CRUD endpoints ───────────────────────────────────────────────────────────

@router.get("")
def list_offers(
    user: AuthUser,
    status: Optional[str] = Query(None, description="Filtr statusu (draft/ready/submitted/won/lost)"),
    tender_id: Optional[str] = Query(None),
    source: Optional[str] = Query(None, description="Źródło przetargu: bzp / ted / bip"),
    limit: int = Query(50, ge=1, le=200),
    cursor: Optional[str] = Query(None, description="Cursor paginacji (next_cursor z poprzedniego zapytania)"),
) -> dict:
    """Lista ofert z cursor paginacją i opcjonalnym filtrowaniem."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail={"error": "invalid_status", "message": f"Dozwolone statusy: {sorted(VALID_STATUSES)}"})
    if source and source not in VALID_SOURCES:
        raise HTTPException(status_code=422, detail={"error": "invalid_source", "message": f"Dozwolone źródła: {sorted(VALID_SOURCES)}"})

    conditions = ["tenant_id = :tid"]
    params: dict[str, Any] = {"tid": tenant_id, "limit": limit}

    if status:
        conditions.append("status = :status")
        params["status"] = status
    if tender_id:
        conditions.append("tender_id = :tender_id")
        params["tender_id"] = tender_id
    if source:
        conditions.append("source = :source")
        params["source"] = source

    # Cursor-based pagination: rows strictly before (created_at, id) tuple
    if cursor:
        cur_ts, cur_id = _decode_cursor(cursor)
        conditions.append(
            "(created_at < :cur_ts OR (created_at = :cur_ts AND id < CAST(:cur_id AS UUID)))"
        )
        params["cur_ts"] = cur_ts
        params["cur_id"] = cur_id

    where = " AND ".join(conditions)

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                f"SELECT * FROM offers WHERE {where} ORDER BY created_at DESC, id DESC LIMIT :limit"
            ),
            params,
        ).fetchall()

    items = [_row_to_dict(r) for r in rows]
    next_cursor = None
    if len(rows) == limit:
        last = rows[-1]
        next_cursor = _encode_cursor(last.created_at, last.id)

    return {"next_cursor": next_cursor, "items": items}


@router.post("", status_code=201)
def create_offer(body: OfferCreate, user: AuthUser) -> dict:
    """Utwórz nową ofertę."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {body.status}. Dozwolone: {sorted(VALID_STATUSES)}"})
    if body.source and body.source not in VALID_SOURCES:
        raise HTTPException(status_code=422, detail={"error": "invalid_source", "message": f"Nieprawidłowe źródło: {body.source}. Dozwolone: {sorted(VALID_SOURCES)}"})

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sa.text("""
                INSERT INTO offers (
                    tenant_id, tender_id, estimate_id, title, status, source,
                    contractor_name, contractor_nip, contractor_address,
                    delivery_days, warranty_months, payment_terms, notes,
                    price_gross_pln, vat_pct, metadata
                ) VALUES (
                    :tenant_id, :tender_id, :estimate_id, :title, :status, :source,
                    :contractor_name, :contractor_nip, :contractor_address,
                    :delivery_days, :warranty_months, :payment_terms, :notes,
                    :price_gross_pln, :vat_pct, CAST(:metadata AS jsonb)
                )
                RETURNING *
            """),
            {
                "tenant_id": tenant_id,
                "tender_id": body.tender_id,
                "estimate_id": body.estimate_id,
                "title": body.title,
                "status": body.status,
                "source": body.source,
                "contractor_name": body.contractor_name,
                "contractor_nip": body.contractor_nip,
                "contractor_address": body.contractor_address,
                "delivery_days": body.delivery_days,
                "warranty_months": body.warranty_months,
                "payment_terms": body.payment_terms,
                "notes": body.notes,
                "price_gross_pln": body.price_gross_pln,
                "vat_pct": body.vat_pct,
                "metadata": json.dumps(body.metadata),
            },
        ).fetchone()

    return _row_to_dict(row)


@router.get("/{offer_id}")
def get_offer(offer_id: str, user: AuthUser) -> dict:
    """Pobierz szczegóły oferty."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            sa.text("SELECT * FROM offers WHERE id = :id AND tenant_id = :tid"),
            {"id": offer_id, "tid": tenant_id},
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Oferta nie znaleziona"})

    return _row_to_dict(row)


@router.patch("/{offer_id}")
def update_offer(offer_id: str, body: OfferUpdate, user: AuthUser) -> dict:
    """Zaktualizuj ofertę (częściowa aktualizacja)."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    if body.status and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail={"error": "invalid_status", "message": f"Nieprawidłowy status: {body.status}"})
    if body.source and body.source not in VALID_SOURCES:
        raise HTTPException(status_code=422, detail={"error": "invalid_source", "message": f"Nieprawidłowe źródło: {body.source}"})

    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=422, detail={"error": "no_fields", "message": "Brak pól do aktualizacji"})

    set_parts = []
    params: dict[str, Any] = {"id": offer_id, "tid": tenant_id}

    for key, val in updates.items():
        if key == "metadata":
            set_parts.append(f"{key} = CAST(:{key} AS jsonb)")
            params[key] = json.dumps(val)
        else:
            set_parts.append(f"{key} = :{key}")
            params[key] = val

    set_parts.append("updated_at = NOW()")
    set_clause = ", ".join(set_parts)

    engine = get_engine()
    with engine.begin() as conn:
        row = conn.execute(
            sa.text(f"UPDATE offers SET {set_clause} WHERE id = :id AND tenant_id = :tid RETURNING *"),
            params,
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Oferta nie znaleziona"})

    return _row_to_dict(row)


@router.delete("/{offer_id}", status_code=204)
def delete_offer(offer_id: str, user: AuthUser) -> None:
    """Usuń ofertę."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(
            sa.text("DELETE FROM offers WHERE id = :id AND tenant_id = :tid RETURNING id"),
            {"id": offer_id, "tid": tenant_id},
        ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Oferta nie znaleziona"})


# ─── PDF Generation ───────────────────────────────────────────────────────────

def _build_pdf(offer: dict, lines: list[dict]) -> bytes:
    """Buduje profesjonalny PDF oferty (3 strony) z reportlab."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm, cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            PageBreak, HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": "pdf_unavailable", "message": f"Biblioteka reportlab nie jest zainstalowana: {exc}"},
        )

    # ── Kolory brandowe ──────────────────────────────────────────────────────
    NAVY    = colors.HexColor("#1a1a6c")
    GOLD    = colors.HexColor("#d4a017")
    LIGHT   = colors.HexColor("#f0f4ff")
    WHITE   = colors.white
    GREY    = colors.HexColor("#555555")
    LGREY   = colors.HexColor("#e8e8e8")

    buf = io.BytesIO()

    # ── Numeracja stron (footer) ─────────────────────────────────────────────
    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(GREY)
        w, h = A4
        canvas.setStrokeColor(NAVY)
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 15*mm, w - 15*mm, 15*mm)
        canvas.drawString(15*mm, 10*mm, "TERRA.OS — Platforma Decyzyjna dla Wykonawców Robót Budowlanych")
        canvas.drawRightString(w - 15*mm, 10*mm, f"Strona {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=25*mm,
        bottomMargin=25*mm,
    )

    styles = getSampleStyleSheet()

    # ── Style ────────────────────────────────────────────────────────────────
    s_logo = ParagraphStyle("logo",
        fontSize=28, textColor=NAVY, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=2*mm)
    s_tagline = ParagraphStyle("tagline",
        fontSize=10, textColor=GOLD, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=8*mm)
    s_title = ParagraphStyle("title",
        fontSize=20, textColor=NAVY, fontName="Helvetica-Bold",
        alignment=TA_CENTER, spaceAfter=6*mm, spaceBefore=10*mm)
    s_subtitle = ParagraphStyle("subtitle",
        fontSize=13, textColor=GREY, fontName="Helvetica",
        alignment=TA_CENTER, spaceAfter=4*mm)
    s_section = ParagraphStyle("section",
        fontSize=13, textColor=NAVY, fontName="Helvetica-Bold",
        spaceBefore=6*mm, spaceAfter=3*mm)
    s_body = ParagraphStyle("body",
        fontSize=10, textColor=colors.black, fontName="Helvetica",
        spaceAfter=2*mm, leading=14)
    s_small = ParagraphStyle("small",
        fontSize=9, textColor=GREY, fontName="Helvetica",
        spaceAfter=1*mm, leading=12)
    s_th = ParagraphStyle("th",
        fontSize=9, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER)
    s_td = ParagraphStyle("td",
        fontSize=8, textColor=colors.black, fontName="Helvetica",
        alignment=TA_LEFT, leading=11)
    s_td_r = ParagraphStyle("td_r",
        fontSize=8, textColor=colors.black, fontName="Helvetica",
        alignment=TA_RIGHT, leading=11)

    # ─────────────────────────────────────────────────────────────────────────
    story = []

    # ══════════════════════════════════════════════════════════════════════════
    # STRONA 1 — Strona tytułowa
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 20*mm))
    story.append(Paragraph("TERRA.OS", s_logo))
    story.append(Paragraph("Platforma Decyzyjna dla Wykonawców Robót Budowlanych", s_tagline))
    story.append(HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=6*mm))

    story.append(Paragraph("OFERTA PRZETARGOWA", s_title))
    story.append(Paragraph(offer["title"], s_subtitle))

    story.append(Spacer(1, 8*mm))

    # ── Karta informacyjna ───────────────────────────────────────────────────
    status_pl = {
        "draft": "Roboczy", "ready": "Gotowy do złożenia",
        "submitted": "Złożony", "won": "Wygrany", "lost": "Przegrany",
    }
    source_pl = {"bzp": "BZP", "ted": "TED", "bip": "BIP"}
    info_data = [
        ["Status oferty", status_pl.get(offer.get("status", "draft"), offer.get("status", ""))],
        ["Data sporządzenia", date.today().strftime("%d.%m.%Y")],
        ["Numer oferty", str(offer["id"])[:8].upper()],
    ]
    if offer.get("source"):
        info_data.append(["Źródło", source_pl.get(offer["source"], offer["source"].upper())])
    if offer.get("tender_id"):
        info_data.append(["ID przetargu", str(offer["tender_id"])[:40]])
    if offer.get("price_gross_pln"):
        price = f"{float(offer['price_gross_pln']):,.2f} PLN brutto".replace(",", " ")
        info_data.append(["Cena ofertowa", price])

    info_tbl = Table(info_data, colWidths=[55*mm, 110*mm])
    info_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("BACKGROUND", (1, 0), (1, -1), WHITE),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT, WHITE]),
        ("GRID", (0, 0), (-1, -1), 0.5, LGREY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(info_tbl)

    # ── Dane wykonawcy ───────────────────────────────────────────────────────
    if any([offer.get("contractor_name"), offer.get("contractor_nip"), offer.get("contractor_address")]):
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("Wykonawca", s_section))
        contractor_data = []
        if offer.get("contractor_name"):
            contractor_data.append(["Nazwa", offer["contractor_name"]])
        if offer.get("contractor_nip"):
            contractor_data.append(["NIP", offer["contractor_nip"]])
        if offer.get("contractor_address"):
            contractor_data.append(["Adres", offer["contractor_address"]])

        if contractor_data:
            c_tbl = Table(contractor_data, colWidths=[55*mm, 110*mm])
            c_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), LIGHT),
                ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, LGREY),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(c_tbl)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # STRONA 2 — Tabela pozycji kosztorysowych
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Pozycje kosztorysowe", s_section))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=4*mm))

    if lines:
        # Nagłówek tabeli
        header = [
            Paragraph("Lp.", s_th),
            Paragraph("Opis", s_th),
            Paragraph("Jm.", s_th),
            Paragraph("Ilość", s_th),
            Paragraph("Cena jedn.\n[PLN]", s_th),
            Paragraph("Robocizna\n[PLN]", s_th),
            Paragraph("Materiały\n[PLN]", s_th),
            Paragraph("Razem\n[PLN]", s_th),
        ]
        rows_data = [header]

        total_net = 0.0
        for idx, line in enumerate(lines, 1):
            lt = float(line.get("line_total_pln") or 0)
            total_net += lt

            def _fmt(v):
                if v is None:
                    return "—"
                try:
                    return f"{float(v):,.2f}".replace(",", " ")
                except Exception:
                    return str(v)

            rows_data.append([
                Paragraph(str(idx), s_td),
                Paragraph(str(line.get("description") or "")[:80], s_td),
                Paragraph(str(line.get("unit") or ""), s_td),
                Paragraph(_fmt(line.get("quantity")), s_td_r),
                Paragraph(_fmt(line.get("unit_price")), s_td_r),
                Paragraph(_fmt(line.get("labor_pln")), s_td_r),
                Paragraph(_fmt(line.get("material_pln")), s_td_r),
                Paragraph(_fmt(lt), s_td_r),
            ])

        # Wiersz sumy
        rows_data.append([
            Paragraph("", s_td),
            Paragraph("SUMA NETTO", ParagraphStyle("sum",
                fontSize=9, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_LEFT)),
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph("", s_td),
            Paragraph(f"{total_net:,.2f}".replace(",", " "), ParagraphStyle("sum_r",
                fontSize=9, textColor=NAVY, fontName="Helvetica-Bold", alignment=TA_RIGHT)),
        ])

        col_w = [8*mm, 62*mm, 10*mm, 16*mm, 18*mm, 18*mm, 18*mm, 18*mm]
        lines_tbl = Table(rows_data, colWidths=col_w, repeatRows=1)
        lines_tbl.setStyle(TableStyle([
            # Nagłówek
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            # Naprzemienne wiersze
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [WHITE, LIGHT]),
            # Wiersz sumy
            ("BACKGROUND", (0, -1), (-1, -1), LGREY),
            ("LINEBELOW", (0, -1), (-1, -1), 1, NAVY),
            # Ogólne
            ("GRID", (0, 0), (-1, -2), 0.3, LGREY),
            ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(lines_tbl)

        # Podsumowanie cenowe
        vat_pct = float(offer.get("vat_pct") or 23)
        vat_val = total_net * vat_pct / 100
        total_gross = total_net + vat_val

        story.append(Spacer(1, 5*mm))
        summary_data = [
            ["Suma netto [PLN]", f"{total_net:,.2f}".replace(",", " ")],
            [f"VAT {vat_pct:.0f}% [PLN]", f"{vat_val:,.2f}".replace(",", " ")],
            ["Suma brutto [PLN]", f"{total_gross:,.2f}".replace(",", " ")],
        ]
        sum_tbl = Table(summary_data, colWidths=[100*mm, 65*mm])
        sum_tbl.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, LGREY),
            ("BACKGROUND", (0, -1), (-1, -1), LIGHT),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(sum_tbl)
    else:
        story.append(Paragraph(
            "Brak pozycji kosztorysowych. Powiąż ofertę z kosztorysem (estimate_id) aby uzupełnić tabelę.",
            s_body,
        ))
        if offer.get("price_gross_pln"):
            price_str = f"{float(offer['price_gross_pln']):,.2f}".replace(",", " ")
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(f"Cena ofertowa (łączna): <b>{price_str} PLN brutto</b>", s_body))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # STRONA 3 — Warunki oferty
    # ══════════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Warunki oferty", s_section))
    story.append(HRFlowable(width="100%", thickness=1, color=NAVY, spaceAfter=4*mm))

    conditions_data = [
        ["Termin realizacji", f"{offer.get('delivery_days', 60)} dni kalendarzowych od podpisania umowy"],
        ["Gwarancja", f"{offer.get('warranty_months', 36)} miesięcy od daty odbioru końcowego"],
        ["Warunki płatności", offer.get("payment_terms") or "30 dni od faktury"],
        ["Ważność oferty", "30 dni od daty złożenia"],
    ]

    cond_tbl = Table(conditions_data, colWidths=[55*mm, 110*mm])
    cond_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), NAVY),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, LGREY),
        ("ROWBACKGROUNDS", (1, 0), (1, -1), [WHITE, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cond_tbl)

    if offer.get("notes"):
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("Uwagi dodatkowe", s_section))
        story.append(Paragraph(offer["notes"], s_body))

    # ── Oświadczenia ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph("Oświadczenia wykonawcy", s_section))
    story.append(HRFlowable(width="100%", thickness=0.5, color=LGREY, spaceAfter=3*mm))

    declarations = [
        "Wykonawca oświadcza, że zapoznał się z warunkami zamówienia i nie wnosi zastrzeżeń.",
        "Wykonawca oświadcza, że posiada niezbędne uprawnienia, kwalifikacje i doświadczenie do realizacji zamówienia.",
        "Wykonawca oświadcza, że ceny podane w ofercie obejmują wszystkie koszty związane z realizacją zamówienia.",
        "Wykonawca zobowiązuje się do zawarcia umowy na warunkach określonych w niniejszej ofercie.",
    ]
    for decl in declarations:
        story.append(Paragraph(f"• {decl}", s_body))

    story.append(Spacer(1, 12*mm))

    # ── Podpis ───────────────────────────────────────────────────────────────
    sign_data = [
        ["Data:", date.today().strftime("%d.%m.%Y"), "Podpis i pieczątka:"],
        ["", "", ""],
        ["", "", "_" * 30],
    ]
    sign_tbl = Table(sign_data, colWidths=[25*mm, 65*mm, 80*mm])
    sign_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (2, 0), (2, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(sign_tbl)

    # ── Build ─────────────────────────────────────────────────────────────────
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


@router.get("/{offer_id}/pdf")
def get_offer_pdf(offer_id: str, user: AuthUser) -> StreamingResponse:
    """Generuj PDF oferty."""
    tenant_id = user.org_id
    if not tenant_id:
        raise HTTPException(status_code=403, detail={"error": "no_tenant", "message": "Brak tenant_id w tokenie"})

    engine = get_engine()
    with engine.connect() as conn:
        offer_row = conn.execute(
            sa.text("SELECT * FROM offers WHERE id = :id AND tenant_id = :tid"),
            {"id": offer_id, "tid": tenant_id},
        ).fetchone()

    if not offer_row:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Oferta nie znaleziona"})

    offer = _row_to_dict(offer_row)

    # Pobierz pozycje kosztorysowe (jeśli powiązany estimate)
    lines: list[dict] = []
    if offer.get("estimate_id"):
        with engine.connect() as conn:
            line_rows = conn.execute(
                sa.text("""
                    SELECT description, unit, quantity, unit_price,
                           labor_pln, material_pln, equipment_pln, line_total_pln
                    FROM estimate_line
                    WHERE estimate_id = :eid AND tenant_id = :tid
                    ORDER BY created_at
                """),
                {"eid": offer["estimate_id"], "tid": tenant_id},
            ).fetchall()
        lines = [
            {
                "description": r.description,
                "unit": r.unit,
                "quantity": r.quantity,
                "unit_price": r.unit_price,
                "labor_pln": r.labor_pln,
                "material_pln": r.material_pln,
                "equipment_pln": r.equipment_pln,
                "line_total_pln": r.line_total_pln,
            }
            for r in line_rows
        ]

    pdf_bytes = _build_pdf(offer, lines)

    import unicodedata
    safe_title = "".join(
        c for c in unicodedata.normalize("NFD", offer["title"])
        if unicodedata.category(c) != "Mn"
    ).replace(" ", "_").replace("/", "-")[:40]
    safe_title = "".join(c if c.isalnum() or c in "_-" else "" for c in safe_title)
    filename = f"oferta_{safe_title}_{date.today().isoformat()}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
