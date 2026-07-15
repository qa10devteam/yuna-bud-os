"""M-EXPORT — DOCX / XLSX / ZIP export router.

Endpoints:
  POST /api/v1/estimates/{id}/export/docx     → StreamingResponse (.docx)
  POST /api/v1/estimates/{id}/export/xlsx     → StreamingResponse (.xlsx)
  POST /api/v1/tenders/{id}/estimate/export/zip → StreamingResponse (.zip, doc+owner × 2 formats)
  POST /api/v1/estimates/{id}/export/preview  → {pages, sheets, sections, warnings, estimated_size_kb}
"""
from __future__ import annotations

import io
import re
import zipfile
from decimal import Decimal
from typing import Any, Optional

import sqlalchemy
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine

router = APIRouter(prefix="/api/v1", tags=["export"])

# ── helpers ──────────────────────────────────────────────────────────────────

_SAFE = re.compile(r"[^\w\-]")


def _slug(s: str) -> str:
    ascii_s = (s or "kosztorys").encode("ascii", "ignore").decode("ascii")
    return _SAFE.sub("_", ascii_s)[:60]


def _get_estimate(conn: Any, estimate_id: str) -> dict:
    row = conn.execute(
        sqlalchemy.text(
            "SELECT id, tender_id, variant, total_net_pln, params, lines "
            "FROM estimate WHERE id = :id"
        ),
        {"id": estimate_id},
    ).fetchone()
    if not row:
        raise HTTPException(404, f"Estimate {estimate_id!r} not found")
    return dict(row._mapping)


def _get_tender(conn: Any, tender_id: str) -> dict:
    row = conn.execute(
        sqlalchemy.text(
            "SELECT id, title, buyer, cpv, external_id FROM tender WHERE id = :id"
        ),
        {"id": tender_id},
    ).fetchone()
    return dict(row._mapping) if row else {}


def _get_owner(conn: Any) -> dict:
    row = conn.execute(
        sqlalchemy.text("SELECT company_name FROM owner_profile LIMIT 1")
    ).fetchone()
    return dict(row._mapping) if row else {}


def _validate_lines(lines: list) -> list[str]:
    """Return list of warning strings (non-fatal); raise 422 if empty."""
    if not lines:
        raise HTTPException(422, "Estimate has no lines — nothing to export")
    warnings: list[str] = []
    for i, ln in enumerate(lines, 1):
        if not ln.get("unit_price") or float(ln.get("unit_price", 0)) == 0:
            warnings.append(f"Pozycja {i}: brak ceny jednostkowej — użyto 0,00")
        if not ln.get("unit"):
            warnings.append(f"Pozycja {i}: brak jednostki miary — użyto 'kpl'")
            ln["unit"] = "kpl"
    return warnings


def _check_sum(lines: list, total_net_pln: Any) -> None:
    """Raise 500 if sum of lines deviates > 0.10 PLN from stored total."""
    if total_net_pln is None:
        return
    computed = sum(Decimal(str(ln.get("line_total_pln", 0))) for ln in lines)
    stored = Decimal(str(total_net_pln))
    if abs(computed - stored) > Decimal("0.10"):
        raise HTTPException(
            500,
            f"Sum reconciliation failed: computed {computed} ≠ stored {stored}. "
            "Re-run estimate before exporting.",
        )


# ── request body ─────────────────────────────────────────────────────────────


class ExportRequest(BaseModel):
    template: str = "kosztorys_ofertowy"
    include_cover_page: bool = True
    include_summary: bool = True
    watermark: Optional[str] = None
    hide_unit_prices: bool = False
    sign_fields: list[str] = ["Sporządził", "Sprawdził", "Zatwierdził"]
    orientation: str = "portrait"
    font_size_pt: int = 9
    protection_password: Optional[str] = None
    kp_percent: float = 12.0
    zysk_percent: float = 8.0
    vat_percent: float = 23.0


# ── DOCX endpoint ─────────────────────────────────────────────────────────────


@router.post("/estimates/{estimate_id}/export/docx")
def export_docx(
    estimate_id: str,
    req: ExportRequest = Body(default_factory=ExportRequest),
):
    from services.estimator.export_docx import DocxExportConfig, export_estimate_docx

    engine = get_engine()
    with engine.connect() as conn:
        est = _get_estimate(conn, estimate_id)
        lines = est["lines"] or []
        warnings = _validate_lines(lines)
        _check_sum(lines, est.get("total_net_pln"))
        tender = _get_tender(conn, str(est["tender_id"]))
        owner = _get_owner(conn)

    # Strip legacy prefix 'kosztorys_' if present
    template_val = req.template.replace("kosztorys_", "")

    cfg = DocxExportConfig(
        template=template_val,  # type: ignore[arg-type]
        watermark=req.watermark,
        signatures=req.sign_fields,
        page_orientation=req.orientation,
        kp_percent=Decimal(str(req.kp_percent)),
        zysk_percent=Decimal(str(req.zysk_percent)),
        vat_percent=Decimal(str(req.vat_percent)),
    )
    data = export_estimate_docx(lines, tender, owner, cfg)
    fname = f"kosztorys_{_slug(tender.get('title', estimate_id))}.docx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── XLSX endpoint ─────────────────────────────────────────────────────────────


@router.post("/estimates/{estimate_id}/export/xlsx")
def export_xlsx(
    estimate_id: str,
    req: ExportRequest = Body(default_factory=ExportRequest),
):
    from services.estimator.export_xlsx import XlsxExportConfig, export_estimate_xlsx

    engine = get_engine()
    with engine.connect() as conn:
        est = _get_estimate(conn, estimate_id)
        lines = est["lines"] or []
        _validate_lines(lines)
        _check_sum(lines, est.get("total_net_pln"))
        tender = _get_tender(conn, str(est["tender_id"]))
        owner = _get_owner(conn)

    cfg = XlsxExportConfig(
        kp_pct=req.kp_percent,
        zysk_pct=req.zysk_percent,
        vat_pct=req.vat_percent,
        protection_password=req.protection_password,
        orientation="landscape",
    )
    data = export_estimate_xlsx(lines, tender, owner, cfg)
    fname = f"kosztorys_{_slug(tender.get('title', estimate_id))}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── ZIP endpoint (doc + owner × DOCX + XLSX) ─────────────────────────────────


@router.post("/tenders/{tender_id}/estimate/export/zip")
def export_zip(
    tender_id: str,
    req: ExportRequest = Body(default_factory=ExportRequest),
):
    from services.estimator.export_docx import DocxExportConfig, export_estimate_docx
    from services.estimator.export_xlsx import XlsxExportConfig, export_estimate_xlsx

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sqlalchemy.text(
                "SELECT id, variant, total_net_pln, lines "
                "FROM estimate WHERE tender_id = :tid ORDER BY variant"
            ),
            {"tid": tender_id},
        ).fetchall()
        tender = _get_tender(conn, tender_id)
        owner = _get_owner(conn)

    if not rows:
        raise HTTPException(404, f"No estimates found for tender {tender_id!r}")

    slug = _slug(tender.get("title", tender_id))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            est = dict(row._mapping)
            lines = est["lines"] or []
            if not lines:
                continue
            variant = est.get("variant", "doc")

            dcfg = DocxExportConfig(
                template=req.template.replace("kosztorys_", ""),  # type: ignore[arg-type]
                watermark=req.watermark,
                kp_percent=Decimal(str(req.kp_percent)),
                zysk_percent=Decimal(str(req.zysk_percent)),
                vat_percent=Decimal(str(req.vat_percent)),
            )
            zf.writestr(
                f"kosztorys_{variant}_{slug}.docx",
                export_estimate_docx(lines, tender, owner, dcfg),
            )

            xcfg = XlsxExportConfig(
                kp_pct=req.kp_percent,
                zysk_pct=req.zysk_percent,
                vat_pct=req.vat_percent,
            )
            zf.writestr(
                f"kosztorys_{variant}_{slug}.xlsx",
                export_estimate_xlsx(lines, tender, owner, xcfg),
            )

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="kosztorysy_{slug}.zip"'},
    )


# ── Preview endpoint ──────────────────────────────────────────────────────────


@router.post("/estimates/{estimate_id}/export/preview")
def export_preview(
    estimate_id: str,
    req: ExportRequest = Body(default_factory=ExportRequest),
):
    from services.estimator.export_docx import DocxExportConfig, export_estimate_docx
    from services.estimator.export_xlsx import XlsxExportConfig, export_estimate_xlsx

    engine = get_engine()
    with engine.connect() as conn:
        est = _get_estimate(conn, estimate_id)
        lines = est["lines"] or []
        warnings = _validate_lines(lines)
        tender = _get_tender(conn, str(est["tender_id"]))
        owner = _get_owner(conn)

    # Generate both to get real sizes
    dcfg = DocxExportConfig(
        template=req.template.replace("kosztorys_", ""),  # type: ignore[arg-type]
        watermark=req.watermark,
        kp_percent=Decimal(str(req.kp_percent)),
        zysk_percent=Decimal(str(req.zysk_percent)),
    )
    docx_bytes = export_estimate_docx(lines, tender, owner, dcfg)

    xcfg = XlsxExportConfig(kp_pct=req.kp_percent, zysk_pct=req.zysk_percent)
    xlsx_bytes = export_estimate_xlsx(lines, tender, owner, xcfg)

    # Estimate page count: ~30 lines per A4 page for DOCX
    estimated_pages = max(1, len(lines) // 30 + (2 if req.include_cover_page else 1))

    sections = []
    if req.include_cover_page:
        sections.append("Strona tytułowa")
    sections.append("Tabela kosztorysu")
    if req.include_summary:
        sections.append("Podsumowanie (netto/VAT/brutto)")
    sections.append("Podpisy")

    return {
        "pages": estimated_pages,
        "sheets": ["Kosztorys", "Podsumowanie", "Zestawienie RMS", "Dane"],
        "sections": sections,
        "warnings": warnings,
        "line_count": len(lines),
        "estimated_docx_size_kb": round(len(docx_bytes) / 1024, 1),
        "estimated_xlsx_size_kb": round(len(xlsx_bytes) / 1024, 1),
        "template": req.template,
        "watermark": req.watermark,
    }


# ─── S43/S44 — Tender list export (CSV + XLSX) ──────────────────────────────
from fastapi import Depends  # noqa: E402 (already imported above but ensure available)
from sqlalchemy import text as _text  # noqa: E402
try:
    from ..auth.deps import AuthUser, get_current_user
    from terra_db.session import get_engine as _get_export_engine

    def _export_engine():
        return _get_export_engine()

except Exception:
    AuthUser = None  # type: ignore
    get_current_user = None  # type: ignore


@router.get("/tenders/csv", tags=["export"])
def export_tenders_csv(
    user: AuthUser,
):
    """S43: Eksport przetargów tenant do CSV."""
    import csv, io
    from fastapi.responses import StreamingResponse
    from terra_db.session import get_engine as _eng
    from sqlalchemy import text as _t

    org_id = str(user.org_id)
    with _eng().connect() as conn:
        rows = conn.execute(
            _t(
                "SELECT id, title, source, value_pln, match_score, deadline_at, created_at "
                "FROM tender WHERE tenant_id=:tid ORDER BY created_at DESC LIMIT 1000"
            ),
            {"tid": org_id},
        ).fetchall()

    buf = io.StringIO()
    w = csv.DictWriter(
        buf,
        fieldnames=["id", "title", "source", "value_pln", "match_score", "deadline_at", "created_at"],
    )
    w.writeheader()
    for r in rows:
        w.writerow({k: str(v) if v is not None else "" for k, v in dict(r._mapping).items()})

    return StreamingResponse(
        io.BytesIO(buf.getvalue().encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="tenders.csv"'},
    )


@router.get("/tenders/xlsx", tags=["export"])
def export_tenders_xlsx(
    user: AuthUser,
):
    """S44: Eksport przetargów tenant do XLSX (openpyxl)."""
    import io
    from fastapi.responses import Response
    from terra_db.session import get_engine as _eng
    from sqlalchemy import text as _t

    org_id = str(user.org_id)
    with _eng().connect() as conn:
        rows = conn.execute(
            _t(
                "SELECT id, title, source, value_pln, match_score, deadline_at "
                "FROM tender WHERE tenant_id=:tid ORDER BY match_score DESC LIMIT 1000"
            ),
            {"tid": org_id},
        ).fetchall()

    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Przetargi"
        ws.append(["ID", "Tytuł", "Source", "Wartość PLN", "Score", "Termin"])
        for r in rows:
            ws.append([str(v) if v is not None else "" for v in r])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return Response(
            content=buf.read(),
            media_type=content_type,
            headers={"Content-Disposition": 'attachment; filename="tenders.xlsx"'},
        )
    except ImportError:
        # Fallback: CSV z nagłówkiem xlsx
        import csv
        buf2 = io.StringIO()
        w = csv.DictWriter(buf2, fieldnames=["id", "title", "source", "value_pln", "match_score", "deadline_at"])
        w.writeheader()
        for r in rows:
            w.writerow(dict(r._mapping))
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(buf2.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="tenders.csv"'},
        )
