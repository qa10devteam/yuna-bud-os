"""Kosztorys v2 Router — CRUD kosztorys / działy / pozycje + ATH import/export.

/api/v2/kosztorys:
  POST   /                     — utwórz kosztorys
  GET    /                     — lista kosztorysów (tenant)
  GET    /{id}                 — szczegóły + sumy
  PUT    /{id}                 — aktualizacja nagłówka
  DELETE /{id}                 — usuń
  POST   /{id}/recalc          — przelicz sumy (engine)
  POST   /{id}/intelligence    — uruchom intelligence (benchmark+win_prob+anomaly)

  POST   /{id}/dzialy          — dodaj dział
  GET    /{id}/dzialy          — lista działów
  DELETE /{id}/dzialy/{did}    — usuń dział

  POST   /{id}/pozycje         — dodaj pozycję
  GET    /{id}/pozycje         — lista pozycji
  PUT    /{id}/pozycje/{pid}   — aktualizacja pozycji
  DELETE /{id}/pozycje/{pid}   — usuń pozycję

  POST   /{id}/import-ath      — import ATH XML (Norma PRO)
  GET    /{id}/export-ath      — eksport ATH XML
"""
from __future__ import annotations

import uuid
from typing import Any
import logging

import sqlalchemy as sa
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from terra_db.session import get_engine
from ..auth.deps import AuthUser

router = APIRouter(prefix="/api/v2/kosztorys", tags=["kosztorys-v2"])
logger = logging.getLogger(__name__)


# ─── Models ───────────────────────────────────────────────────────────────────

class KosztorysCreate(BaseModel):
    nazwa: str = Field(..., min_length=1, max_length=300)
    tender_id: str | None = None
    inwestor: str | None = None
    obiekt: str | None = None
    lokalizacja: str | None = None
    typ: str = Field(default="ofertowy", pattern=r"^(ofertowy|inwestorski|zamienny|powykonawczy)$")
    kwartalnr: int = Field(default=2, ge=1, le=4)
    kwartalrok: int = Field(default=2026, ge=2000, le=2100)
    ko_r_pct: float = Field(default=70.0, ge=0, le=500)
    ko_s_pct: float = Field(default=30.0, ge=0, le=500)
    z_pct: float = Field(default=12.5, ge=0, le=100)
    kz_pct: float = Field(default=7.1, ge=0, le=100)
    vat_pct: float = Field(default=23.0, ge=0, le=100)
    notes: str | None = None


class KosztorysUpdate(BaseModel):
    nazwa: str | None = None
    inwestor: str | None = None
    obiekt: str | None = None
    lokalizacja: str | None = None
    status: str | None = None
    ko_r_pct: float | None = None
    ko_s_pct: float | None = None
    z_pct: float | None = None
    kz_pct: float | None = None
    vat_pct: float | None = None
    notes: str | None = None


class DzialCreate(BaseModel):
    lp: int = 1
    nazwa: str
    ko_r_pct: float | None = None
    ko_s_pct: float | None = None
    z_pct: float | None = None
    kz_pct: float | None = None
    cpv_hint: str | None = None


class PozycjaCreate(BaseModel):
    lp: int = Field(default=1, ge=1)
    dzial_id: str | None = None
    kst_code: str | None = None
    katalog: str | None = None
    pozycja_nr: str | None = None
    opis: str = Field(..., min_length=1, max_length=500)
    jednostka: str = Field(default="m2", min_length=1, max_length=20)
    ilosc: float = Field(default=1.0, ge=0)
    r_jcena: float = Field(default=0.0, ge=0)
    m_jcena: float = Field(default=0.0, ge=0)
    s_jcena: float = Field(default=0.0, ge=0)
    icb_id_r: int | None = None
    icb_id_m: int | None = None
    icb_id_s: int | None = None
    uwagi: str | None = None


class PozycjaUpdate(BaseModel):
    lp: int | None = None
    opis: str | None = None
    jednostka: str | None = None
    ilosc: float | None = None
    r_jcena: float | None = None
    m_jcena: float | None = None
    s_jcena: float | None = None
    icb_id_r: int | None = None
    icb_id_m: int | None = None
    icb_id_s: int | None = None
    uwagi: str | None = None
    dzial_id: str | None = None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _require_tenant(user: AuthUser) -> str:
    if not user.org_id:
        raise HTTPException(403, "Wymagany tenant")
    return user.org_id


def _get_kosztorys_or_404(conn: Any, kid: str, tenant_id: str) -> Any:
    row = conn.execute(sa.text("""
        SELECT * FROM kosztorys WHERE id = :id AND tenant_id = :tid
    """), {"id": kid, "tid": tenant_id}).fetchone()
    if not row:
        raise HTTPException(404, f"Kosztorys {kid} nie znaleziony")
    return row


def _to_narzuty(row: Any):
    from ..intelligence.kosztorys_engine import Narzuty
    return Narzuty(
        ko_r_pct=float(row.ko_r_pct),
        ko_s_pct=float(row.ko_s_pct),
        z_pct=float(row.z_pct),
        kz_pct=float(row.kz_pct),
        vat_pct=float(row.vat_pct),
    )


# ─── Kosztorys CRUD ───────────────────────────────────────────────────────────

@router.post("/", status_code=201)
def create_kosztorys(body: KosztorysCreate, user: AuthUser) -> dict:
    """Utwórz nowy kosztorys."""
    tenant_id = _require_tenant(user)
    engine = get_engine()
    kid = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO kosztorys
                (id, tenant_id, tender_id, nazwa, inwestor, obiekt, lokalizacja,
                 typ, kwartalnr, kwartalrok,
                 ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct, notes)
            VALUES
                (:id, :tid, :tender_id, :nazwa, :inwestor, :obiekt, :lokalizacja,
                 :typ, :kwartalnr, :kwartalrok,
                 :ko_r, :ko_s, :z, :kz, :vat, :notes)
        """), {
            "id": kid, "tid": tenant_id,
            "tender_id": body.tender_id,
            "nazwa": body.nazwa, "inwestor": body.inwestor,
            "obiekt": body.obiekt, "lokalizacja": body.lokalizacja,
            "typ": body.typ, "kwartalnr": body.kwartalnr, "kwartalrok": body.kwartalrok,
            "ko_r": body.ko_r_pct, "ko_s": body.ko_s_pct,
            "z": body.z_pct, "kz": body.kz_pct, "vat": body.vat_pct,
            "notes": body.notes,
        })

    return {"id": kid, "status": "created"}


@router.get("/")
def list_kosztorysy(user: AuthUser, limit: int = 50, offset: int = 0) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, nazwa, status, typ, tender_id, kwartalrok, kwartalnr,
                   suma_netto, suma_brutto, win_probability, anomaly_score,
                   created_at, updated_at
            FROM kosztorys
            WHERE tenant_id = :tid
            ORDER BY updated_at DESC
            LIMIT :lim OFFSET :off
        """), {"tid": tenant_id, "lim": limit, "off": offset}).fetchall()

        total = conn.execute(sa.text(
            "SELECT count(*) FROM kosztorys WHERE tenant_id = :tid"
        ), {"tid": tenant_id}).scalar()

    return {
        "items": [_kosztorys_row(r) for r in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{kid}")
def get_kosztorys(kid: str, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        row = _get_kosztorys_or_404(conn, kid, tenant_id)
        dzial_count = conn.execute(sa.text(
            "SELECT count(*) FROM kosztorys_dzial WHERE kosztorys_id=:k AND tenant_id=:t"
        ), {"k": kid, "t": tenant_id}).scalar()
        poz_count = conn.execute(sa.text(
            "SELECT count(*) FROM kosztorys_pozycja WHERE kosztorys_id=:k AND tenant_id=:t"
        ), {"k": kid, "t": tenant_id}).scalar()

    return {
        **_kosztorys_row(row),
        "ko_r_pct": float(row.ko_r_pct),
        "ko_s_pct": float(row.ko_s_pct),
        "z_pct": float(row.z_pct),
        "kz_pct": float(row.kz_pct),
        "vat_pct": float(row.vat_pct),
        "n_dzialy": dzial_count,
        "n_pozycje": poz_count,
        "suma_r": float(row.suma_r),
        "suma_m": float(row.suma_m),
        "suma_s": float(row.suma_s),
        "suma_ko": float(row.suma_ko),
        "suma_z": float(row.suma_z),
        "inwestor": row.inwestor,
        "obiekt": row.obiekt,
        "lokalizacja": row.lokalizacja,
        "notes": row.notes,
    }


@router.put("/{kid}")
def update_kosztorys(kid: str, body: KosztorysUpdate, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    updates: dict[str, Any] = {}

    for field_name in body.__class__.model_fields:
        val = getattr(body, field_name)
        if val is not None:
            updates[field_name] = val

    if not updates:
        raise HTTPException(400, "Brak pól do aktualizacji")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    with engine.begin() as conn:
        result = conn.execute(sa.text(f"""
            UPDATE kosztorys SET {set_clause}, updated_at=NOW()
            WHERE id=:id AND tenant_id=:tid
        """), {"id": kid, "tid": tenant_id, **updates})
        if result.rowcount == 0:
            raise HTTPException(404, "Kosztorys nie znaleziony")

    return {"id": kid, "updated": list(updates.keys())}


@router.delete("/{kid}", status_code=204)
def delete_kosztorys(kid: str, user: AuthUser) -> None:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.begin() as conn:
        r = conn.execute(sa.text(
            "DELETE FROM kosztorys WHERE id=:id AND tenant_id=:tid"
        ), {"id": kid, "tid": tenant_id})
        if r.rowcount == 0:
            raise HTTPException(404)


@router.post("/{kid}/recalc")
def recalc(kid: str, user: AuthUser) -> dict:
    """Przelicz sumy kosztorysu (engine CJ = R+M+S+Ko+Z+Kz)."""
    tenant_id = _require_tenant(user)
    try:
        from ..intelligence.kosztorys_engine import recalc_kosztorys_db
        result = recalc_kosztorys_db(kid, tenant_id, get_engine())
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {
        "suma_r": result.suma_r,
        "suma_m": result.suma_m,
        "suma_s": result.suma_s,
        "suma_ko": result.suma_ko,
        "suma_z": result.suma_z,
        "suma_kz": result.suma_kz,
        "suma_netto": result.suma_netto,
        "suma_vat": result.suma_vat,
        "suma_brutto": result.suma_brutto,
        "n_pozycje": len(result.pozycje),
    }


@router.post("/{kid}/intelligence")
def run_intelligence(kid: str, user: AuthUser) -> dict:
    """Uruchom intelligence dla kosztorysu (benchmark + win_prob + anomaly_score)."""
    tenant_id = _require_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        hdr = _get_kosztorys_or_404(conn, kid, tenant_id)
        total_netto = float(hdr.suma_netto or 0)
        tender_id = str(hdr.tender_id) if hdr.tender_id else None

        # Pobierz CPV z przetargu
        cpv = "45"
        if tender_id:
            t = conn.execute(sa.text(
                "SELECT cpv_code FROM historical_tenders WHERE id=:id LIMIT 1"
            ), {"id": tender_id}).fetchone()
            if t and t.cpv_code:
                cpv = t.cpv_code[:5].rstrip("0").rstrip("-")

    results: dict[str, Any] = {"kosztorys_id": kid}

    if total_netto > 0:
        # Win probability
        try:
            from ..intelligence.bid_intelligence import estimate_win_probability
            wp = estimate_win_probability(
                our_price=total_netto,
                estimated_value=total_netto,
                cpv_prefix=cpv,
                n_competitors=4,
            )
            results["win_probability"] = wp.get("p_win")
            results["win_analysis"] = wp
        except Exception as e:
            results["win_probability_error"] = str(e)

        # Anomaly detection na pozycjach
        try:
            engine2 = get_engine()
            with engine2.connect() as conn2:
                poz_rows = conn2.execute(sa.text("""
                    SELECT opis, jednostka, ilosc, m_jcena, category
                    FROM kosztorys_pozycja
                    WHERE kosztorys_id=:kid AND tenant_id=:tid
                    LIMIT 200
                """), {"kid": kid, "tid": tenant_id}).fetchall()

            items = [
                {"description": r.opis, "unit": r.jednostka or "szt",
                 "quantity": float(r.ilosc or 1),
                 "unit_price": float(r.m_jcena or 0),
                 "category": "inne"}
                for r in poz_rows
            ]
            if items:
                from ..intelligence.bid_intelligence import detect_kosztorys_anomalies
                anomaly = detect_kosztorys_anomalies(items, cpv)
                results["anomaly_score"] = anomaly.get("anomaly_rate", 0)
                results["anomaly_analysis"] = anomaly

                # Zapisz do kosztorys
                engine2 = get_engine()
                with engine2.begin() as conn3:
                    conn3.execute(sa.text("""
                        UPDATE kosztorys SET
                            win_probability = :wp,
                            anomaly_score = :as_,
                            intelligence_at = NOW()
                        WHERE id=:kid AND tenant_id=:tid
                    """), {
                        "wp": results.get("win_probability"),
                        "as_": results.get("anomaly_score"),
                        "kid": kid, "tid": tenant_id,
                    })
        except Exception as e:
            results["anomaly_error"] = str(e)

    return results


@router.get("/{kid}/anomalies")
def get_kosztorys_anomalies(kid: str, user: AuthUser) -> dict:
    """Pobierz listę pozycji z anomaliami cenowymi."""
    tenant_id = _require_tenant(user)
    with get_engine().connect() as conn:
        _get_kosztorys_or_404(conn, kid, tenant_id)
        rows = conn.execute(sa.text("""
            SELECT id::text, lp, kst_code, opis, jednostka,
                   ilosc::float, r_jcena::float, m_jcena::float, s_jcena::float,
                   is_anomaly
            FROM kosztorys_pozycja
            WHERE kosztorys_id=:kid AND tenant_id=:tid AND is_anomaly=TRUE
            ORDER BY lp
        """), {"kid": kid, "tid": tenant_id}).fetchall()
    return {
        "kosztorys_id": kid,
        "anomalies": [dict(r._mapping) for r in rows],
        "count": len(rows),
    }


@router.get("/{kid}/win-probability")
def get_win_probability(kid: str, cpv: str | None = None, user: AuthUser = None) -> dict:  # type: ignore[assignment]
    """Pobierz szacowaną szansę wygrania przetargu dla tego kosztorysu."""
    tenant_id = _require_tenant(user)
    with get_engine().connect() as conn:
        hdr = _get_kosztorys_or_404(conn, kid, tenant_id)
        total_netto = float(hdr.suma_netto or 0)
        wp_stored = float(hdr.win_probability) if hdr.win_probability else None

    if wp_stored is not None:
        return {
            "kosztorys_id": kid,
            "win_probability": wp_stored,
            "total_netto": total_netto,
            "cached": True,
        }

    # Compute on-the-fly
    cpv_prefix = cpv or "45"
    try:
        from ..intelligence.bid_intelligence import estimate_win_probability
        wp = estimate_win_probability(
            our_price=total_netto,
            estimated_value=total_netto,
            cpv_prefix=cpv_prefix,
            n_competitors=4,
        )
        return {
            "kosztorys_id": kid,
            "win_probability": wp.get("p_win"),
            "win_analysis": wp,
            "total_netto": total_netto,
            "cached": False,
        }
    except Exception as e:
        return {
            "kosztorys_id": kid,
            "win_probability": None,
            "error": str(e),
            "total_netto": total_netto,
        }



# ─── Material Alerts ──────────────────────────────────────────────────────────

@router.get("/material-alerts")
def get_material_alerts(user: AuthUser, limit: int = 50) -> list[dict]:
    """Pobierz aktywne alerty cen materiałów dla tenanta."""
    tenant_id = _require_tenant(user)
    try:
        from ..intelligence.material_risk import get_active_alerts
        return get_active_alerts(tenant_id, limit=limit)
    except Exception as e:
        logger.exception("material alerts failed: %s", e, exc_info=True)
        return []


@router.post("/material-alerts/{alert_id}/acknowledge")
def acknowledge_material_alert(alert_id: str, user: AuthUser) -> dict:
    """Oznacz alert jako przeczytany."""
    tenant_id = _require_tenant(user)
    try:
        from ..intelligence.material_risk import acknowledge_alert
        ok = acknowledge_alert(alert_id, tenant_id)
        return {"ok": ok}
    except Exception as e:
        logger.exception("acknowledge alert failed: %s", exc_info=True)
        return {"ok": False}


# ─── Działy ───────────────────────────────────────────────────────────────────

@router.post("/{kid}/dzialy", status_code=201)
def add_dzial(kid: str, body: DzialCreate, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    did = str(uuid.uuid4())

    with engine.begin() as conn:
        _get_kosztorys_or_404(conn, kid, tenant_id)
        conn.execute(sa.text("""
            INSERT INTO kosztorys_dzial
                (id, tenant_id, kosztorys_id, lp, nazwa, ko_r_pct, ko_s_pct, z_pct, kz_pct, cpv_hint)
            VALUES (:id, :tid, :kid, :lp, :nazwa, :ko_r, :ko_s, :z, :kz, :cpv)
        """), {
            "id": did, "tid": tenant_id, "kid": kid,
            "lp": body.lp, "nazwa": body.nazwa,
            "ko_r": body.ko_r_pct, "ko_s": body.ko_s_pct,
            "z": body.z_pct, "kz": body.kz_pct, "cpv": body.cpv_hint,
        })

    return {"id": did, "status": "created"}


@router.get("/{kid}/dzialy")
def list_dzialy(kid: str, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, lp, nazwa, suma_netto, cpv_hint
            FROM kosztorys_dzial
            WHERE kosztorys_id=:k AND tenant_id=:t
            ORDER BY lp
        """), {"k": kid, "t": tenant_id}).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}


@router.delete("/{kid}/dzialy/{did}", status_code=204)
def delete_dzial(kid: str, did: str, user: AuthUser) -> None:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.begin() as conn:
        r = conn.execute(sa.text("""
            DELETE FROM kosztorys_dzial
            WHERE id=:did AND kosztorys_id=:kid AND tenant_id=:tid
        """), {"did": did, "kid": kid, "tid": tenant_id})
        if r.rowcount == 0:
            raise HTTPException(404)


# ─── Pozycje ──────────────────────────────────────────────────────────────────

@router.post("/{kid}/pozycje", status_code=201)
def add_pozycja(kid: str, body: PozycjaCreate, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    pid = str(uuid.uuid4())

    with engine.begin() as conn:
        _get_kosztorys_or_404(conn, kid, tenant_id)
        conn.execute(sa.text("""
            INSERT INTO kosztorys_pozycja
                (id, tenant_id, kosztorys_id, dzial_id, lp,
                 kst_code, katalog, pozycja_nr, opis, jednostka, ilosc,
                 r_jcena, m_jcena, s_jcena,
                 icb_id_r, icb_id_m, icb_id_s, uwagi)
            VALUES
                (:id, :tid, :kid, :did, :lp,
                 :kst, :katalog, :nr, :opis, :jm, :ilosc,
                 :r, :m, :s, :ir, :im, :is_, :uwagi)
        """), {
            "id": pid, "tid": tenant_id, "kid": kid,
            "did": body.dzial_id, "lp": body.lp,
            "kst": body.kst_code, "katalog": body.katalog,
            "nr": body.pozycja_nr, "opis": body.opis,
            "jm": body.jednostka, "ilosc": body.ilosc,
            "r": body.r_jcena, "m": body.m_jcena, "s": body.s_jcena,
            "ir": body.icb_id_r, "im": body.icb_id_m, "is_": body.icb_id_s,
            "uwagi": body.uwagi,
        })

    # Trigger material risk check asynchronicznie (nie blokuje odpowiedzi)
    if body.icb_id_m:
        try:
            from ..intelligence.material_risk import check_material_risks
            check_material_risks(kosztorys_id=kid, tenant_id=tenant_id)
        except Exception as _e:
            logger.exception("material_risk trigger failed after add_pozycja: %s", exc_info=True)

    return {"id": pid, "status": "created"}


@router.get("/{kid}/pozycje")
def list_pozycje(kid: str, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, lp, kst_code, opis, jednostka, ilosc,
                   r_jcena, m_jcena, s_jcena,
                   r_total, m_total, s_total,
                   ko_total, z_total, kz_total,
                   jcena_netto, wartosc_netto,
                   is_anomaly, dzial_id
            FROM kosztorys_pozycja
            WHERE kosztorys_id=:k AND tenant_id=:t
            ORDER BY lp
        """), {"k": kid, "t": tenant_id}).fetchall()
    return {"items": [dict(r._mapping) for r in rows]}


@router.put("/{kid}/pozycje/{pid}")
def update_pozycja(kid: str, pid: str, body: PozycjaUpdate, user: AuthUser) -> dict:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    updates: dict[str, Any] = {}
    field_map = {
        "lp": "lp", "opis": "opis", "jednostka": "jednostka",
        "ilosc": "ilosc", "r_jcena": "r_jcena", "m_jcena": "m_jcena",
        "s_jcena": "s_jcena", "icb_id_r": "icb_id_r", "icb_id_m": "icb_id_m",
        "icb_id_s": "icb_id_s", "uwagi": "uwagi", "dzial_id": "dzial_id",
    }
    for py_field, col in field_map.items():
        val = getattr(body, py_field)
        if val is not None:
            updates[col] = val

    if not updates:
        raise HTTPException(400, "Brak pól do aktualizacji")

    set_clause = ", ".join(f"{k}=:{k}" for k in updates)
    with engine.begin() as conn:
        r = conn.execute(sa.text(f"""
            UPDATE kosztorys_pozycja SET {set_clause}, updated_at=NOW()
            WHERE id=:pid AND kosztorys_id=:kid AND tenant_id=:tid
        """), {"pid": pid, "kid": kid, "tid": tenant_id, **updates})
        if r.rowcount == 0:
            raise HTTPException(404)

    # Trigger material risk check jeśli zmieniono cenę materiału
    if "m_jcena" in updates or "icb_id_m" in updates:
        try:
            from ..intelligence.material_risk import check_material_risks
            check_material_risks(kosztorys_id=kid, tenant_id=tenant_id)
        except Exception as _e:
            logger.exception("material_risk trigger failed after update_pozycja: %s", exc_info=True)

    return {"id": pid, "updated": list(updates.keys())}


@router.delete("/{kid}/pozycje/{pid}", status_code=204)
def delete_pozycja(kid: str, pid: str, user: AuthUser) -> None:
    tenant_id = _require_tenant(user)
    engine = get_engine()
    with engine.begin() as conn:
        r = conn.execute(sa.text("""
            DELETE FROM kosztorys_pozycja
            WHERE id=:pid AND kosztorys_id=:kid AND tenant_id=:tid
        """), {"pid": pid, "kid": kid, "tid": tenant_id})
        if r.rowcount == 0:
            raise HTTPException(404)


# ─── ATH Import / Export ──────────────────────────────────────────────────────

@router.post("/{kid}/import-ath")
async def import_ath(kid: str, file: UploadFile = File(...), user: AuthUser = None) -> dict:  # type: ignore[assignment]
    """Importuj plik ATH XML z Normy PRO — dodaje pozycje do kosztorysu."""
    tenant_id = _require_tenant(user)
    content = await file.read()

    try:
        from ..intelligence.ath_parser import parse_ath, ath_to_pozycje_dicts
        ath = parse_ath(content)
        pozycje = ath_to_pozycje_dicts(ath)
    except ValueError as e:
        raise HTTPException(400, f"Błąd parsowania ATH: {e}")

    engine = get_engine()
    inserted = 0

    with engine.begin() as conn:
        _get_kosztorys_or_404(conn, kid, tenant_id)
        # Pobierz max lp
        max_lp = conn.execute(sa.text(
            "SELECT COALESCE(max(lp), 0) FROM kosztorys_pozycja WHERE kosztorys_id=:k AND tenant_id=:t"
        ), {"k": kid, "t": tenant_id}).scalar() or 0

        for i, poz in enumerate(pozycje, start=max_lp + 1):
            pid = str(uuid.uuid4())
            conn.execute(sa.text("""
                INSERT INTO kosztorys_pozycja
                    (id, tenant_id, kosztorys_id, lp, kst_code, katalog, pozycja_nr,
                     opis, jednostka, ilosc, r_jcena, m_jcena, s_jcena, ath_pozycja_xml)
                VALUES
                    (:id, :tid, :kid, :lp, :kst, :katalog, :nr,
                     :opis, :jm, :ilosc, :r, :m, :s, :ath)
            """), {
                "id": pid, "tid": tenant_id, "kid": kid, "lp": i,
                "kst": poz["kst_code"], "katalog": poz["katalog"],
                "nr": poz["pozycja_nr"], "opis": poz["opis"],
                "jm": poz["jednostka"], "ilosc": poz["ilosc"],
                "r": poz["r_jcena"], "m": poz["m_jcena"], "s": poz["s_jcena"],
                "ath": poz.get("ath_pozycja_xml"),
            })
            inserted += 1

    return {
        "imported": inserted,
        "kosztorys_id": kid,
        "source_file": file.filename,
    }


@router.get("/{kid}/export-pdf")
def export_pdf(kid: str, user: AuthUser) -> Response:
    """Eksportuj kosztorys do PDF (WeasyPrint)."""
    tenant_id = _require_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        hdr = _get_kosztorys_or_404(conn, kid, tenant_id)
        dzialy_rows = conn.execute(sa.text("""
            SELECT id::text, lp, nazwa FROM kosztorys_dzial
            WHERE kosztorys_id=:k AND tenant_id=:t ORDER BY lp
        """), {"k": kid, "t": tenant_id}).fetchall()
        poz_rows = conn.execute(sa.text("""
            SELECT lp, kst_code, opis, jednostka,
                   ilosc::float, r_jcena::float, m_jcena::float, s_jcena::float,
                   r_total::float, m_total::float, s_total::float,
                   ko_total::float, z_total::float, kz_total::float,
                   jcena_netto::float, wartosc_netto::float,
                   is_anomaly, dzial_id::text
            FROM kosztorys_pozycja
            WHERE kosztorys_id=:k AND tenant_id=:t ORDER BY lp
        """), {"k": kid, "t": tenant_id}).fetchall()

    header_dict = {
        "nazwa": hdr.nazwa, "inwestor": hdr.inwestor, "obiekt": hdr.obiekt,
        "lokalizacja": hdr.lokalizacja, "typ": hdr.typ, "status": hdr.status,
        "kwartalnr": hdr.kwartalnr, "kwartalrok": hdr.kwartalrok,
        "ko_r_pct": float(hdr.ko_r_pct), "ko_s_pct": float(hdr.ko_s_pct),
        "z_pct": float(hdr.z_pct), "kz_pct": float(hdr.kz_pct),
        "vat_pct": float(hdr.vat_pct),
        "tender_id": str(hdr.tender_id) if hdr.tender_id else None,
        "data_opracowania": str(hdr.data_opracowania) if hdr.data_opracowania else None,
    }
    pozycje_dicts = [dict(r._mapping) for r in poz_rows]
    dzialy_dicts  = [dict(r._mapping) for r in dzialy_rows]

    sums_dict = {
        "r": float(hdr.suma_r or 0), "m": float(hdr.suma_m or 0),
        "s": float(hdr.suma_s or 0), "ko": float(hdr.suma_ko or 0),
        "kz": float(hdr.suma_kz or 0), "z": float(hdr.suma_z or 0),
        "netto": float(hdr.suma_netto or 0), "vat": float(hdr.suma_vat or 0),
        "brutto": float(hdr.suma_brutto or 0),
    }
    intel_dict = {
        "benchmark_percentile": float(hdr.benchmark_percentile) if hdr.benchmark_percentile else None,
        "win_probability": float(hdr.win_probability) if hdr.win_probability else None,
        "anomaly_score": float(hdr.anomaly_score) if hdr.anomaly_score else None,
    }

    try:
        from ..intelligence.pdf_generator import generate_pdf
        pdf = generate_pdf(
            header=header_dict,
            pozycje=pozycje_dicts,
            dzialy=dzialy_dicts or None,
            sums=sums_dict,
            intel=intel_dict,
        )
    except Exception as e:
        raise HTTPException(500, f"Błąd generowania PDF: {e}")

    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="kosztorys_{kid[:8]}.pdf"'},
    )


@router.get("/{kid}/export-ath")
def export_ath(kid: str, user: AuthUser) -> Response:
    """Eksportuj kosztorys do formatu ATH XML (Norma PRO)."""
    tenant_id = _require_tenant(user)
    engine = get_engine()

    with engine.connect() as conn:
        hdr = _get_kosztorys_or_404(conn, kid, tenant_id)
        rows = conn.execute(sa.text("""
            SELECT kst_code, opis, jednostka, ilosc, r_jcena, m_jcena, s_jcena
            FROM kosztorys_pozycja
            WHERE kosztorys_id=:k AND tenant_id=:t
            ORDER BY lp
        """), {"k": kid, "t": tenant_id}).fetchall()

    pozycje_dicts = [
        {
            "kst_code": r.kst_code, "opis": r.opis,
            "jednostka": r.jednostka, "ilosc": float(r.ilosc or 1),
            "r_jcena": float(r.r_jcena or 0),
            "m_jcena": float(r.m_jcena or 0),
            "s_jcena": float(r.s_jcena or 0),
        }
        for r in rows
    ]

    from ..intelligence.ath_parser import generate_ath
    xml_bytes = generate_ath(pozycje_dicts, nazwa=hdr.nazwa)

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="kosztorys_{kid[:8]}.ath"'
        },
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _kosztorys_row(row: Any) -> dict:
    return {
        "id": str(row.id),
        "nazwa": row.nazwa,
        "status": row.status,
        "typ": row.typ,
        "tender_id": str(row.tender_id) if row.tender_id else None,
        "kwartalrok": row.kwartalrok,
        "kwartalnr": row.kwartalnr,
        "suma_netto": float(row.suma_netto) if row.suma_netto else 0.0,
        "suma_brutto": float(row.suma_brutto) if row.suma_brutto else 0.0,
        "win_probability": float(row.win_probability) if row.win_probability else None,
        "anomaly_score": float(row.anomaly_score) if row.anomaly_score else None,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# ─── Summary endpoint ─────────────────────────────────────────────────────────

@router.get("/{kid}/summary")
def get_kosztorys_summary(kid: str, user: AuthUser) -> dict:
    """Podsumowanie kosztorysu — nagłówek + sumy + liczba pozycji."""
    tenant_id = _require_tenant(user)
    with get_engine().connect() as conn:
        row = conn.execute(sa.text("""
            SELECT k.id, k.nazwa, k.inwestor, k.obiekt, k.lokalizacja, k.typ,
                   k.kwartalnr, k.kwartalrok, k.tender_id, k.status,
                   k.suma_netto, k.suma_brutto, k.suma_vat,
                   k.ko_r_pct, k.ko_s_pct, k.z_pct, k.kz_pct, k.vat_pct,
                   k.win_probability, k.anomaly_score,
                   k.created_at, k.updated_at,
                   (SELECT count(*) FROM kosztorys_pozycja WHERE kosztorys_id = k.id) AS poz_count
            FROM kosztorys k
            WHERE k.id = :kid AND k.tenant_id = :tid
        """), {"kid": kid, "tid": tenant_id}).mappings().first()
    if not row:
        raise HTTPException(404, "Kosztorys not found")
    return {
        "id": row.id,
        "nazwa": row.nazwa,
        "inwestor": row.inwestor,
        "obiekt": row.obiekt,
        "lokalizacja": row.lokalizacja,
        "typ": row.typ,
        "kwartalnr": row.kwartalnr,
        "kwartalrok": row.kwartalrok,
        "tender_id": row.tender_id,
        "status": row.status,
        "suma_netto": float(row.suma_netto) if row.suma_netto else 0.0,
        "suma_brutto": float(row.suma_brutto) if row.suma_brutto else 0.0,
        "suma_vat": float(row.suma_vat) if row.suma_vat else 0.0,
        "narzuty": {
            "ko_r_pct": float(row.ko_r_pct),
            "ko_s_pct": float(row.ko_s_pct),
            "z_pct": float(row.z_pct),
            "kz_pct": float(row.kz_pct),
            "vat_pct": float(row.vat_pct),
        },
        "win_probability": float(row.win_probability) if row.win_probability else None,
        "anomaly_score": float(row.anomaly_score) if row.anomaly_score else None,
        "pozycje_count": row.poz_count,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


# ─── Create from tender convenience ──────────────────────────────────────────

@router.post("/from-tender/{tender_id}", status_code=201)
def create_from_tender(tender_id: str, user: AuthUser) -> dict:
    """Utwórz kosztorys powiązany z przetargiem — pobiera dane z ZWIAD."""
    tenant_id = _require_tenant(user)
    # Validate UUID before hitting DB
    try:
        import uuid as _uuid_mod
        _uuid_mod.UUID(tender_id)
    except (ValueError, AttributeError):
        raise HTTPException(422, f"Nieprawidłowy UUID przetargu: {tender_id}")
    with get_engine().connect() as conn:
        # Pobierz dane z tenders (ZWIAD)
        tender = conn.execute(sa.text("""
            SELECT id, title, buyer, voivodeship
            FROM tender
            WHERE id = :tid AND tenant_id = :tenant_id
        """), {"tid": tender_id, "tenant_id": tenant_id}).mappings().first()

        if not tender:
            raise HTTPException(404, "Tender not found")

        import uuid
        kid = str(uuid.uuid4())
        conn.execute(sa.text("""
            INSERT INTO kosztorys
                (id, tenant_id, tender_id, nazwa, inwestor, lokalizacja,
                 typ, kwartalnr, kwartalrok,
                 ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct)
            VALUES
                (:id, :tid, :tender_id, :nazwa, :inwestor, :lokalizacja,
                 'ofertowy', :kw_nr, :kw_rok,
                 70.0, 30.0, 12.5, 7.1, 23.0)
        """), {
            "id": kid,
            "tid": tenant_id,
            "tender_id": tender_id,
            "nazwa": f"Kosztorys — {tender.title[:80]}" if tender.title else "Kosztorys ofertowy",
            "inwestor": tender.buyer,
            "lokalizacja": tender.voivodeship,
            "kw_nr": _current_quarter()[0],
            "kw_rok": _current_quarter()[1],
        })
        conn.commit()
    return {"id": kid, "status": "created", "tender_id": tender_id}


def _current_quarter() -> tuple[int, int]:
    """Return (quarter_number, year) for current date."""
    from datetime import date
    today = date.today()
    return (today.month - 1) // 3 + 1, today.year


# ─── Cost Estimation endpoints ───────────────────────────────────────────────

class CostEstimateRequest(BaseModel):
    method: str = Field(default="icb", pattern="^(swz|icb|user_rates|all)$")
    tender_id: str | None = None
    area_m2: float = Field(default=0.0, ge=0)
    cpv: str | None = None
    region: str | None = None
    swz_text: str | None = None
    kwartalnr: int | None = None
    kwartalrok: int | None = None
    notes: str | None = None


class UserRateCreate(BaseModel):
    symbol: str
    nazwa: str | None = None
    jednostka: str = "m²"
    typ_rms: str = Field(pattern="^[RMS]$")
    cena_netto: float = Field(gt=0)


@router.post("/estimate", status_code=201)
def create_estimate(req: CostEstimateRequest, user: AuthUser) -> dict:
    """Szacuje koszt przetargu jedną lub wszystkimi metodami i zapisuje wynik."""
    from ..analytics.cost_estimation import (
        estimate_all, estimate_from_icb, estimate_from_swz, estimate_from_user_rates,
    )
    import json as _json

    tenant_id = user.org_id or ""
    engine = get_engine()

    if req.method == "all":
        estimates = estimate_all(
            tenant_id=tenant_id,
            cpv=req.cpv,
            area_m2=req.area_m2,
            region=req.region,
            swz_text=req.swz_text,
            kwartalnr=req.kwartalnr,
            kwartalrok=req.kwartalrok,
            engine=engine,
        )
    elif req.method == "swz":
        if not req.swz_text:
            raise HTTPException(400, "swz_text wymagany dla metody 'swz'")
        estimates = [estimate_from_swz(req.swz_text, region=req.region).to_dict()]
    elif req.method == "icb":
        if req.area_m2 <= 0:
            raise HTTPException(400, "area_m2 > 0 wymagane dla metody 'icb'")
        estimates = [estimate_from_icb(
            cpv=req.cpv, area_m2=req.area_m2, region=req.region,
            kwartalnr=req.kwartalnr, kwartalrok=req.kwartalrok, engine=engine,
        ).to_dict()]
    elif req.method == "user_rates":
        if req.area_m2 <= 0:
            raise HTTPException(400, "area_m2 > 0 wymagane dla metody 'user_rates'")
        estimates = [estimate_from_user_rates(
            tenant_id=tenant_id, area_m2=req.area_m2,
            cpv=req.cpv, region=req.region, engine=engine,
        ).to_dict()]
    else:
        raise HTTPException(400, f"Nieznana metoda: {req.method}")

    # Zapisz każdy wynik do cost_estimate
    saved_ids: list[str] = []
    with engine.begin() as conn:
        for est in estimates:
            eid = str(uuid.uuid4())
            conn.execute(sa.text("""
                INSERT INTO cost_estimate
                    (id, tenant_id, tender_id, method, variant,
                     area_m2, cpv_prefix, region,
                     total_net_pln, confidence_low, confidence_high,
                     lines, params, notes)
                VALUES
                    (:id, :tid, :tender_id, :method, :variant,
                     :area_m2, :cpv, :region,
                     :total, :low, :high,
                     :lines::jsonb, :params::jsonb, :notes)
            """), {
                "id": eid,
                "tid": tenant_id,
                "tender_id": req.tender_id,
                "method": est["method"],
                "variant": est["variant"],
                "area_m2": req.area_m2,
                "cpv": req.cpv,
                "region": req.region,
                "total": est["total_net_pln"],
                "low": est["confidence_low"],
                "high": est["confidence_high"],
                "lines": _json.dumps(est["lines"], ensure_ascii=False),
                "params": _json.dumps(est["params"], ensure_ascii=False),
                "notes": est.get("notes", ""),
            })
            saved_ids.append(eid)

    return {"ids": saved_ids, "estimates": estimates, "count": len(estimates)}


@router.get("/estimate")
def list_estimates(user: AuthUser, tender_id: str | None = None) -> dict:
    """Zwraca zapisane szacowania kosztów dla tenanta (opcjonalnie filtr po przetargu)."""
    tenant_id = user.org_id
    engine = get_engine()

    with engine.connect() as conn:
        q = """
            SELECT id, method, variant, tender_id,
                   area_m2, cpv_prefix, region,
                   total_net_pln, confidence_low, confidence_high,
                   lines, params, notes, created_at
            FROM cost_estimate
            WHERE tenant_id = :tid
        """
        params: dict = {"tid": tenant_id}
        if tender_id:
            q += " AND tender_id = :tender_id"
            params["tender_id"] = tender_id
        q += " ORDER BY created_at DESC LIMIT 50"

        rows = conn.execute(sa.text(q), params).fetchall()

    items = []
    for r in rows:
        items.append({
            "id": str(r[0]),
            "method": r[1],
            "variant": r[2],
            "tender_id": str(r[3]) if r[3] else None,
            "area_m2": float(r[4]) if r[4] else None,
            "cpv_prefix": r[5],
            "region": r[6],
            "total_net_pln": float(r[7]) if r[7] else 0,
            "confidence_low": float(r[8]) if r[8] else 0,
            "confidence_high": float(r[9]) if r[9] else 0,
            "lines": r[10] if isinstance(r[10], list) else [],
            "params": r[11] if isinstance(r[11], dict) else {},
            "notes": r[12],
            "created_at": r[13].isoformat() if r[13] else None,
        })

    return {"items": items, "total": len(items)}


@router.delete("/estimate/{estimate_id}", status_code=204)
def delete_estimate(estimate_id: str, user: AuthUser) -> None:
    tenant_id = user.org_id
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(sa.text(
            "DELETE FROM cost_estimate WHERE id=:id AND tenant_id=:tid"
        ), {"id": estimate_id, "tid": tenant_id})
    if result.rowcount == 0:
        raise HTTPException(404, "Szacowanie nie znalezione")


# ─── User Rates (stawki własne) endpoints ────────────────────────────────────

@router.get("/user-rates")
def list_user_rates(user: AuthUser) -> dict:
    """Zwraca cennik własny tenanta."""
    tenant_id = user.org_id
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(sa.text("""
            SELECT id, symbol, nazwa, jednostka, typ_rms, cena_netto, updated_at
            FROM user_rates WHERE tenant_id=:tid ORDER BY typ_rms, symbol
        """), {"tid": tenant_id}).fetchall()

    return {
        "items": [
            {
                "id": str(r[0]),
                "symbol": r[1],
                "nazwa": r[2],
                "jednostka": r[3],
                "typ_rms": r[4].strip(),
                "cena_netto": float(r[5]),
                "updated_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ],
        "total": len(rows),
    }


@router.post("/user-rates", status_code=201)
def create_user_rate(rate: UserRateCreate, user: AuthUser) -> dict:
    """Dodaje lub aktualizuje pozycję cennika własnego."""
    tenant_id = user.org_id
    engine = get_engine()
    rid = str(uuid.uuid4())
    with engine.begin() as conn:
        conn.execute(sa.text("""
            INSERT INTO user_rates (id, tenant_id, symbol, nazwa, jednostka, typ_rms, cena_netto)
            VALUES (:id, :tid, :symbol, :nazwa, :jednostka, :typ_rms, :cena)
            ON CONFLICT (tenant_id, symbol, typ_rms)
            DO UPDATE SET nazwa=EXCLUDED.nazwa, jednostka=EXCLUDED.jednostka,
                          cena_netto=EXCLUDED.cena_netto, updated_at=now()
            RETURNING id
        """), {
            "id": rid,
            "tid": tenant_id,
            "symbol": rate.symbol,
            "nazwa": rate.nazwa or rate.symbol,
            "jednostka": rate.jednostka,
            "typ_rms": rate.typ_rms,
            "cena": rate.cena_netto,
        })
    return {"id": rid, "symbol": rate.symbol, "typ_rms": rate.typ_rms}


@router.delete("/user-rates/{rate_id}", status_code=204)
def delete_user_rate(rate_id: str, user: AuthUser) -> None:
    tenant_id = user.org_id
    engine = get_engine()
    with engine.begin() as conn:
        result = conn.execute(sa.text(
            "DELETE FROM user_rates WHERE id=:id AND tenant_id=:tid"
        ), {"id": rate_id, "tid": tenant_id})
    if result.rowcount == 0:
        raise HTTPException(404, "Stawka nie znaleziona")


# ─────────────────────── S70: Fork kosztorysu ───────────────────────────── #

@router.post("/{kosztorys_id}/fork", status_code=201)
def fork_kosztorys(kosztorys_id: str, user: AuthUser) -> dict:
    """S70: Utwórz nową wersję (fork) kosztorysu z version+1."""
    engine = get_engine()
    tenant_id = _require_tenant(user)
    import uuid as _uuid
    new_id = str(_uuid.uuid4())
    with engine.connect() as conn:
        src = _get_kosztorys_or_404(conn, kosztorys_id, tenant_id)
        cur_version = getattr(src, "version", 1) or 1
        conn.execute(sa.text("""
            INSERT INTO kosztorys
                (id, tenant_id, tender_id, nazwa, inwestor, obiekt, lokalizacja,
                 data_opracowania, status, typ, kwartalnr, kwartalrok,
                 ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                 suma_r, suma_m, suma_s, suma_ko, suma_z, suma_kz,
                 suma_netto, suma_vat, suma_brutto,
                 version, parent_version_id)
            SELECT
                :new_id, tenant_id, tender_id,
                nazwa || ' (v' || (:cur_ver + 1)::text || ')',
                inwestor, obiekt, lokalizacja,
                data_opracowania, 'draft', typ, kwartalnr, kwartalrok,
                ko_r_pct, ko_s_pct, z_pct, kz_pct, vat_pct,
                suma_r, suma_m, suma_s, suma_ko, suma_z, suma_kz,
                suma_netto, suma_vat, suma_brutto,
                :new_ver, :parent_id
            FROM kosztorys
            WHERE id = :src_id AND tenant_id = :tid
        """), {
            "new_id": new_id,
            "cur_ver": cur_version,
            "new_ver": cur_version + 1,
            "parent_id": kosztorys_id,
            "src_id": kosztorys_id,
            "tid": tenant_id,
        })
        conn.commit()
    return {"id": new_id, "parent_version_id": kosztorys_id, "version": cur_version + 1}


# ─────────────────── S72: Material risk per kosztorys ───────────────────── #

@router.get("/{kosztorys_id}/material-risk")
def get_kosztorys_material_risk(kosztorys_id: str, user: AuthUser) -> dict:
    """S72: Dla każdej pozycji kosztorysu — aktualny indeks cenowy GUS BDL."""
    engine = get_engine()
    tenant_id = _require_tenant(user)
    import httpx as _httpx

    with engine.connect() as conn:
        _get_kosztorys_or_404(conn, kosztorys_id, tenant_id)
        # Get distinct materials from kosztorys_pozycja
        rows = conn.execute(sa.text("""
            SELECT DISTINCT kp.symbol, kp.nazwa, kp.m_jcena
            FROM kosztorys_pozycja kp
            JOIN kosztorys_dzial kd ON kd.id = kp.dzial_id
            WHERE kd.kosztorys_id = :kid
              AND kp.m_jcena > 0
            LIMIT 20
        """), {"kid": kosztorys_id}).fetchall()

    results = []
    for row in rows:
        # Try to get GUS BDL price (use P3808 as construction materials index)
        gus_value = None
        yoy_change = None
        try:
            resp = _httpx.get(
                "https://bdl.stat.gov.pl/api/v1/data/by-variable/282893",
                params={"year": 2024, "unitLevel": 0, "format": "json"},
                headers={"X-ClientId": "yu-na-app"},
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                vals = []
                for item in data.get("results", [])[:1]:
                    for v in item.get("values", []):
                        if v.get("val") is not None:
                            vals.append(float(v["val"]))
                if vals:
                    gus_value = vals[0]
        except Exception:
            pass

        risk = "low"
        if gus_value and row.m_jcena:
            ratio = float(row.m_jcena) / gus_value if gus_value > 0 else 1.0
            if ratio < 0.7 or ratio > 1.5:
                risk = "high"
            elif ratio < 0.85 or ratio > 1.2:
                risk = "medium"

        results.append({
            "symbol": row.symbol,
            "material": row.nazwa,
            "current_price": float(row.m_jcena),
            "gus_index": gus_value,
            "yoy_change": yoy_change,
            "risk_level": risk,
        })

    return {"kosztorys_id": kosztorys_id, "items": results}
