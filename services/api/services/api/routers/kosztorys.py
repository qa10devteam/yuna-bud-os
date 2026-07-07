"""Faza 46 — Norma PRO Interop: import/export formatu ATH (kosztorys).
Faza 47 — Kosztorys Editor: CRUD pozycji kosztorysu.
"""
from __future__ import annotations

import sys
sys.path.insert(0, "/home/ubuntu/terra-os/packages/vendor")

import io
import uuid
import xml.etree.ElementTree as ET
from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v1/kosztorys", tags=["kosztorys"])


class KosztorysItemCreate(BaseModel):
    lp: int = 1
    kst_code: str | None = None
    description: str
    unit: str = "szt"
    quantity: float = 1.0
    unit_price: float = 0.0
    category: str = "material"


class KosztorysItemUpdate(BaseModel):
    lp: int | None = None
    kst_code: str | None = None
    description: str | None = None
    unit: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    category: str | None = None


def _parse_ath_xml(content: bytes) -> list[dict]:
    """Parse Norma PRO ATH/XML format into kosztorys items."""
    items = []
    try:
        root = ET.fromstring(content)
        ns = {"": root.tag.split("}")[0][1:] if "}" in root.tag else ""}

        # Try common ATH element names
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag.lower() in ("pozycja", "item", "row", "element", "ath_row"):
                item = {
                    "kst_code": elem.get("kod") or elem.findtext("Kod") or elem.findtext("kod") or "",
                    "description": (
                        elem.findtext("Nazwa") or elem.findtext("nazwa") or
                        elem.findtext("Opis") or elem.get("opis") or tag
                    ),
                    "unit": elem.findtext("Jm") or elem.findtext("jm") or elem.findtext("Jednostka") or "szt",
                    "quantity": float(elem.findtext("Ilosc") or elem.findtext("ilosc") or elem.get("ilosc", "1") or "1"),
                    "unit_price": float(elem.findtext("CenaJm") or elem.findtext("cena") or elem.get("cena", "0") or "0"),
                    "category": elem.get("kategoria") or "material",
                    "ath_xml": ET.tostring(elem, encoding="unicode"),
                }
                items.append(item)
    except ET.ParseError:
        pass
    return items


def _generate_ath_xml(items: list[dict]) -> bytes:
    """Generate ATH XML format from kosztorys items."""
    root = ET.Element("Kosztorys")
    root.set("xmlns:ath", "http://norma.com.pl/ath/2.0")
    root.set("version", "2.0")
    for item in items:
        pos = ET.SubElement(root, "Pozycja")
        pos.set("kod", item.get("kst_code") or "")
        ET.SubElement(pos, "Nazwa").text = item.get("description", "")
        ET.SubElement(pos, "Jm").text = item.get("unit", "szt")
        ET.SubElement(pos, "Ilosc").text = str(item.get("quantity", 1))
        ET.SubElement(pos, "CenaJm").text = str(item.get("unit_price", 0))
        ET.SubElement(pos, "CenaCalkowita").text = str(
            float(item.get("quantity", 1)) * float(item.get("unit_price", 0))
        )
        pos.set("kategoria", item.get("category", "material"))
    tree = ET.ElementTree(root)
    buf = io.BytesIO()
    ET.indent(tree, space="  ")
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


# ──────────────────────────────────────────────────────────────────────────────
# CRUD endpoints (Faza 47)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/{tender_id}")
def list_kosztorys_items(tender_id: str, user: AuthUser) -> dict:
    """Lista pozycji kosztorysu dla przetargu."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT id, lp, kst_code, description, unit, quantity, unit_price,
                       quantity * unit_price AS total_price, category, created_at
                FROM kosztorys_items
                WHERE tender_id = :tid
                ORDER BY lp ASC
            """),
            {"tid": tender_id},
        ).fetchall()
    total = sum(float(r.quantity) * float(r.unit_price) for r in rows)
    return {
        "tender_id": tender_id,
        "items": [
            {
                "id": str(r.id),
                "lp": r.lp,
                "kst_code": r.kst_code,
                "description": r.description,
                "unit": r.unit,
                "quantity": float(r.quantity),
                "unit_price": float(r.unit_price),
                "total_price": float(r.quantity) * float(r.unit_price),
                "category": r.category,
            }
            for r in rows
        ],
        "total": round(total, 2),
        "count": len(rows),
    }


@router.post("/{tender_id}")
def create_kosztorys_item(tender_id: str, item: KosztorysItemCreate, user: AuthUser) -> dict:
    """Dodaj pozycję do kosztorysu."""
    engine = get_engine()
    rec_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO kosztorys_items
                    (id, tender_id, org_id, lp, kst_code, description, unit, quantity, unit_price, category)
                VALUES (:id, :tender_id, :org_id, :lp, :kst_code, :desc, :unit, :qty, :price, :cat)
            """),
            {
                "id": rec_id,
                "tender_id": tender_id,
                "org_id": user.org_id or None,
                "lp": item.lp,
                "kst_code": item.kst_code,
                "desc": item.description,
                "unit": item.unit,
                "qty": item.quantity,
                "price": item.unit_price,
                "cat": item.category,
            },
        )
        conn.commit()
    return {"id": rec_id, "status": "created"}


@router.patch("/{tender_id}/{item_id}")
def update_kosztorys_item(
    tender_id: str, item_id: str, patch: KosztorysItemUpdate, user: AuthUser
) -> dict:
    """Aktualizuj pozycję kosztorysu (inline editing)."""
    engine = get_engine()
    updates = {k: v for k, v in patch.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="Brak pól do aktualizacji")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["item_id"] = item_id
    updates["tender_id"] = tender_id
    with engine.connect() as conn:
        result = conn.execute(
            sa.text(f"""
                UPDATE kosztorys_items SET {set_clause}, updated_at = now()
                WHERE id = :item_id AND tender_id = :tender_id
            """),
            updates,
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pozycja nie istnieje")
        # Return updated row so client can confirm reflected values
        row = conn.execute(
            sa.text("""
                SELECT id, tender_id, description, unit, quantity, unit_price,
                       (quantity * unit_price) AS total_price, updated_at
                FROM kosztorys_items WHERE id = :item_id
            """),
            {"item_id": item_id},
        ).fetchone()
    if not row:
        return {"id": item_id, "status": "updated"}
    return {
        "id": str(row[0]),
        "tender_id": str(row[1]),
        "description": row[2],
        "unit": row[3],
        "quantity": float(row[4]) if row[4] is not None else None,
        "unit_price": float(row[5]) if row[5] is not None else None,
        "total_price": float(row[6]) if row[6] is not None else None,
        "status": "updated",
    }


@router.delete("/{tender_id}/{item_id}")
def delete_kosztorys_item(tender_id: str, item_id: str, user: AuthUser) -> dict:
    """Usuń pozycję kosztorysu."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            sa.text("DELETE FROM kosztorys_items WHERE id = :id AND tender_id = :tid"),
            {"id": item_id, "tid": tender_id},
        )
        conn.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Pozycja nie istnieje")
    return {"status": "deleted"}


# ──────────────────────────────────────────────────────────────────────────────
# ATH Import/Export (Faza 46)
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/{tender_id}/import/ath")
async def import_ath(
    tender_id: str,
    user: AuthUser,
    file: UploadFile = File(...),
) -> dict:
    """Import kosztorysu z formatu ATH/XML (Norma PRO)."""
    content = await file.read()
    items = _parse_ath_xml(content)
    if not items:
        raise HTTPException(status_code=400, detail="Nie znaleziono pozycji w pliku ATH. Sprawdź format XML.")

    engine = get_engine()
    imported = 0
    for idx, item in enumerate(items, start=1):
        with engine.connect() as conn:
            conn.execute(
                sa.text("""
                    INSERT INTO kosztorys_items
                        (id, tender_id, org_id, lp, kst_code, description, unit, quantity, unit_price, category, ath_xml)
                    VALUES (:id, :tender_id, :org_id, :lp, :kst_code, :desc, :unit, :qty, :price, :cat, :ath_xml)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "tender_id": tender_id,
                    "org_id": user.org_id or None,
                    "lp": idx,
                    "kst_code": item.get("kst_code"),
                    "desc": item.get("description", f"Pozycja {idx}"),
                    "unit": item.get("unit", "szt"),
                    "qty": item.get("quantity", 1),
                    "price": item.get("unit_price", 0),
                    "cat": item.get("category", "material"),
                    "ath_xml": item.get("ath_xml"),
                },
            )
            conn.commit()
        imported += 1
    return {"imported": imported, "tender_id": tender_id, "filename": file.filename}


@router.get("/{tender_id}/export/ath")
def export_ath(tender_id: str, user: AuthUser) -> StreamingResponse:
    """Eksport kosztorysu do formatu ATH/XML (Norma PRO)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("""
                SELECT lp, kst_code, description, unit, quantity, unit_price, category
                FROM kosztorys_items WHERE tender_id = :tid ORDER BY lp
            """),
            {"tid": tender_id},
        ).fetchall()
    items = [
        {
            "lp": r.lp,
            "kst_code": r.kst_code or "",
            "description": r.description,
            "unit": r.unit,
            "quantity": float(r.quantity),
            "unit_price": float(r.unit_price),
            "category": r.category,
        }
        for r in rows
    ]
    xml_bytes = _generate_ath_xml(items)
    return StreamingResponse(
        io.BytesIO(xml_bytes),
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="kosztorys_{tender_id}.ath.xml"'},
    )
