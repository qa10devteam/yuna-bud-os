"""S121-S124 — AI Assistant Chat: quick query, win-chance, kosztorys generation, SSE stream."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/chat', tags=['chat_ai'])

# Alias router for /api/v2/ai-chat paths
ai_chat_router = APIRouter(prefix='/api/v2/ai-chat', tags=['ai_chat'])


@ai_chat_router.get('/history')
def ai_chat_history(user: AuthUser, db: DB, limit: int = 50) -> dict:
    """GET /api/v2/ai-chat/history — return recent AI chat interactions for current user."""
    tid = str(user.org_id)
    try:
        rows = db.execute(
            text(
                'SELECT id, content, created_at FROM notifications '
                'WHERE tenant_id=:tid AND type=\'ai_chat\' ORDER BY created_at DESC LIMIT :limit'
            ),
            {'tid': tid, 'limit': limit}
        ).fetchall()
        items = [{'id': str(r.id), 'content': r.content, 'created_at': str(r.created_at)} for r in rows]
    except Exception:
        items = []
    return {'total': len(items), 'items': items}



def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]

KEYWORD_CPV = {
    'budowlan': '45',
    'drogowe': '45233',
    'it': '72',
    'informatyk': '72',
    'sprzątan': '90919',
    'ochrona': '79710',
    'transport': '60',
}
REGION_NUTS = {
    'śląsk': 'PL22',
    'mazow': 'PL91',
    'mazo': 'PL91',
    'łódzk': 'PL71',
    'dol': 'PL51',
    'wiel': 'PL41',
}


@router.get('/quick')
def chat_quick(q: str, user: AuthUser, db: DB):
    tid = str(user.org_id)
    filters = ['tenant_id=:tid']
    params: dict = {'tid': tid}
    ql = q.lower()
    for kw, cpv in KEYWORD_CPV.items():
        if kw in ql:
            filters.append('cpv_code LIKE :cpv')
            params['cpv'] = cpv + '%'
            break
    for kw, nuts in REGION_NUTS.items():
        if kw in ql:
            filters.append('nuts_code LIKE :nuts')
            params['nuts'] = nuts + '%'
            break
    m = re.search(r'>\s*(\d+)\s*k', ql)
    if m:
        filters.append('value_pln > :minv')
        params['minv'] = int(m.group(1)) * 1000
    where = ' AND '.join(filters)
    rows = db.execute(
        text(f'SELECT id,title,match_score,deadline_at,value_pln FROM tender WHERE {where} ORDER BY match_score DESC LIMIT 10'),
        params
    ).fetchall()
    return {'query': q, 'results': [dict(r._mapping) for r in rows]}


@router.get('/win-chance/{tender_id}')
def win_chance(tender_id: str, user: AuthUser, db: DB):
    try:
        from ..intelligence.win_prob import predict_win_prob
        prob = predict_win_prob(tender_id, str(user.org_id), db)
        return {'tender_id': tender_id, 'win_probability': prob, 'factors': ['match_score', 'cpv_history', 'region']}
    except Exception as e:
        return {'tender_id': tender_id, 'win_probability': 0.5, 'note': str(e)}


@router.post('/generate-kosztorys')
def generate_kosztorys(body: dict, user: AuthUser, db: DB):
    tender_id = body.get('tender_id')
    db.execute(
        text(
            'INSERT INTO kosztorys(id, tenant_id, tender_id, nazwa, status, created_at) '
            'VALUES(gen_random_uuid(), :org, :tid, :name, :st, now())'
        ),
        {'org': str(user.org_id), 'tid': tender_id, 'name': 'Draft AI', 'st': 'draft'}
    )
    db.commit()
    k = db.execute(
        text('SELECT id FROM kosztorys WHERE tender_id=:tid AND tenant_id=:org ORDER BY created_at DESC LIMIT 1'),
        {'tid': tender_id, 'org': str(user.org_id)}
    ).fetchone()
    return {'kosztorys_id': str(k.id) if k else None, 'status': 'created'}


@router.get('/stream')
async def chat_stream(q: str, user: AuthUser):
    async def generator():
        yield f'data: {json.dumps({"type": "start", "q": q})}\n\n'
        await asyncio.sleep(0.1)
        yield f'data: {json.dumps({"type": "thinking"})}\n\n'
        await asyncio.sleep(0.1)
        yield f'data: {json.dumps({"type": "result", "answer": f"Szukam przetargów dla: {q}"})}\n\n'
        yield f'data: {json.dumps({"type": "done"})}\n\n'
    return StreamingResponse(generator(), media_type='text/event-stream')
