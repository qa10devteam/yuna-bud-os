"""S55/S56/S57 — Market Materials: GUS BDL ceny materiałów budowlanych + alerty."""
from __future__ import annotations

import uuid
from typing import Optional

import httpx
import sqlalchemy as sa
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from terra_db.session import get_engine
from ..auth.deps import AuthUser, TenantDep

router = APIRouter(prefix="/api/v2/market", tags=["market-materials"])

GUS_BDL_BASE = "https://bdl.stat.gov.pl/api/v1"

# Materiały budowlane: variableId → nazwa
MATERIAL_VARIABLES: dict[str, str] = {
    "cement": "282893",       # P2137 → ceny kruszyw i materiałów; 282893 cement
    "kruszywa": "282894",
    "steel": "282895",
    "drewno": "282896",
}

# Fallback: użyj P2137 jako default dla kategorii cement
CEMENT_VAR_ID = "282893"


def _fetch_gus_variable(var_id: str, years: list[int]) -> list[dict]:
    """Pobierz dane z GUS BDL dla podanego variableId i lat."""
    results = []
    try:
        with httpx.Client(timeout=20) as client:
            for year in years:
                try:
                    resp = client.get(
                        f"{GUS_BDL_BASE}/data/by-variable/{var_id}",
                        params={"year": year, "unitLevel": 0, "lang": "pl", "format": "json"},
                        headers={"X-ClientId": "yu-na-app"},
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    measure_unit = data.get("measureUnitName", "PLN/t")
                    for item in data.get("results", [])[:3]:
                        for v in item.get("values", []):
                            results.append({
                                "variable_id": var_id,
                                "unit": measure_unit,
                                "year": v.get("year", year),
                                "period": str(v.get("period", "")),
                                "value_pln": v.get("val"),
                            })
                except Exception:
                    results.append({"variable_id": var_id, "year": year, "value_pln": None, "error": "fetch_error"})
    except Exception as exc:
        results.append({"variable_id": var_id, "error": str(exc)})
    return results


# S55: GET /api/v2/market/materials?category=cement
@router.get("/materials")
def get_materials(
    user: AuthUser,
    category: str = Query("cement", description="Kategoria materiału: cement, kruszywa, steel, drewno"),
    year: Optional[int] = Query(None, description="Rok (domyślnie bieżący)"),
) -> dict:
    """Pobierz ceny materiałów budowlanych z GUS BDL."""
    import datetime
    current_year = year or datetime.date.today().year
    var_id = MATERIAL_VARIABLES.get(category, CEMENT_VAR_ID)
    items = _fetch_gus_variable(var_id, [current_year])
    return {
        "category": category,
        "variable_id": var_id,
        "year": current_year,
        "items": items,
        "source": "GUS BDL",
    }


# S56: GET /api/v2/market/materials/trend  — YoY z last 2 years
@router.get("/materials/trend")
def get_materials_trend(
    user: AuthUser,
    category: str = Query("cement"),
) -> dict:
    """Trend YoY cen materiałów budowlanych (ostatnie 2 lata)."""
    import datetime
    current_year = datetime.date.today().year
    years = [current_year - 1, current_year]
    var_id = MATERIAL_VARIABLES.get(category, CEMENT_VAR_ID)
    items = _fetch_gus_variable(var_id, years)

    # Wylicz YoY
    by_year: dict[int, list[float]] = {}
    for item in items:
        if item.get("value_pln") is not None:
            yr = item["year"]
            by_year.setdefault(yr, []).append(float(item["value_pln"]))

    avg_by_year = {yr: sum(vs) / len(vs) for yr, vs in by_year.items() if vs}
    yoy_change = None
    yoy_pct = None
    if len(avg_by_year) >= 2:
        sorted_years = sorted(avg_by_year.keys())
        prev_val = avg_by_year[sorted_years[-2]]
        curr_val = avg_by_year[sorted_years[-1]]
        yoy_change = round(curr_val - prev_val, 4)
        yoy_pct = round((yoy_change / prev_val) * 100, 2) if prev_val else None

    return {
        "category": category,
        "variable_id": var_id,
        "years": years,
        "avg_by_year": avg_by_year,
        "yoy_change": yoy_change,
        "yoy_pct": yoy_pct,
        "items": items,
    }


# S57: POST /api/v2/market/alerts — ustaw alert cenowy
class MaterialAlertCreate(BaseModel):
    material: str
    threshold_pln: float
    kosztorys_id: Optional[str] = None


@router.post("/alerts", status_code=201)
def create_material_price_alert(
    body: MaterialAlertCreate,
    user: AuthUser,
    tenant_id: TenantDep,
) -> dict:
    """Utwórz alert cenowy dla materiału budowlanego."""
    engine = get_engine()
    alert_id = str(uuid.uuid4())
    with engine.connect() as conn:
        conn.execute(
            sa.text("""
                INSERT INTO material_alert
                    (id, tenant_id, kosztorys_id, symbol, nazwa, baseline_price, current_price, change_pct, severity)
                VALUES
                    (:id, :tid, :kost_id, :symbol, :nazwa, :baseline, :current, 0.0, 'low')
            """),
            {
                "id": alert_id,
                "tid": tenant_id,
                "kost_id": body.kosztorys_id,
                "symbol": body.material,
                "nazwa": f"Alert: {body.material}",
                "baseline": body.threshold_pln,
                "current": body.threshold_pln,
            },
        )
        conn.commit()
    return {
        "id": alert_id,
        "material": body.material,
        "threshold_pln": body.threshold_pln,
        "status": "created",
    }
