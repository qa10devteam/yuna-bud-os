"""S118-S120 — Monthly reporting + benchmark endpoints."""
from __future__ import annotations

import io
import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/reports', tags=['reports'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


@router.get('/monthly')
def monthly_report(user: AuthUser, db: DB, year: int = 2026, month: int = 7):
    tid = str(user.org_id)
    new_tenders = db.execute(
        text('SELECT count(*) FROM tender WHERE tenant_id=:t AND EXTRACT(YEAR FROM created_at)=:y AND EXTRACT(MONTH FROM created_at)=:m'),
        {'t': tid, 'y': year, 'm': month}
    ).scalar() or 0
    won = db.execute(
        text("SELECT count(*) FROM offer_result WHERE tenant_id=:t AND status='won' AND EXTRACT(MONTH FROM decided_at)=:m AND EXTRACT(YEAR FROM decided_at)=:y"),
        {'t': tid, 'y': year, 'm': month}
    ).scalar() or 0
    total_or = db.execute(
        text('SELECT count(*) FROM offer_result WHERE tenant_id=:t'),
        {'t': tid}
    ).scalar() or 1
    pipeline_val = db.execute(
        text('SELECT COALESCE(sum(value_pln),0) FROM tender WHERE tenant_id=:t AND match_score>=0.5'),
        {'t': tid}
    ).scalar() or 0
    return {
        'year': year,
        'month': month,
        'new_tenders': new_tenders,
        'win_rate': round(won / total_or * 100, 1),
        'pipeline_value_pln': float(pipeline_val),
    }


@router.get('/monthly/pdf')
def monthly_report_pdf(user: AuthUser, db: DB, year: int = 2026, month: int = 7):
    try:
        from reportlab.pdfgen import canvas as rl_canvas
        buf = io.BytesIO()
        c = rl_canvas.Canvas(buf)
        c.drawString(100, 750, f'YU-NA Monthly Report {year}-{month:02d}')
        c.drawString(100, 720, f'Generated for tenant: {user.org_id}')
        c.save()
        buf.seek(0)
        return Response(
            content=buf.read(),
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="report_{year}_{month:02d}.pdf"'},
        )
    except ImportError:
        html = f'<h1>YU-NA Monthly Report {year}-{month:02d}</h1><p>Tenant: {user.org_id}</p>'
        return Response(content=html, media_type='text/html')


@router.get('/benchmark')
def report_benchmark(user: AuthUser, db: DB):
    tid = str(user.org_id)
    rows = db.execute(
        text('SELECT tenant_id, count(*) cnt, ROUND(avg(match_score)::numeric,3) avg_score FROM tender GROUP BY tenant_id ORDER BY cnt DESC')
    ).fetchall()
    my_rank = next((i + 1 for i, r in enumerate(rows) if str(r.tenant_id) == tid), None)
    my = next((r for r in rows if str(r.tenant_id) == tid), None)
    return {
        'your_rank': my_rank,
        'total_tenants': len(rows),
        'your_tenders': my.cnt if my else 0,
        'your_avg_score': float(my.avg_score) if my else 0,
    }
