"""S117 — PWA Push Subscription endpoint."""
from __future__ import annotations

import logging
from typing import Any, Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text

from ..auth.deps import AuthUser
from terra_db.session import get_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/pwa', tags=['pwa'])


def get_db():
    engine = get_engine()
    with engine.connect() as conn:
        yield conn
        conn.commit()


DB = Annotated[Any, Depends(get_db)]


class PushSubscription(BaseModel):
    push_endpoint: str
    p256dh: str = ''
    auth: str = ''


@router.post('/subscribe')
def pwa_subscribe(body: PushSubscription, user: AuthUser, db: DB):
    # No unique constraint on push_endpoint — plain INSERT (device_token required NOT NULL)
    db.execute(
        text(
            'INSERT INTO mobile_device(id, tenant_id, device_token, push_endpoint, p256dh, auth_key, created_at) '
            'VALUES(gen_random_uuid(), :tid, :ep, :ep, :p, :a, now())'
        ),
        {
            'tid': str(user.org_id),
            'ep': body.push_endpoint,
            'p': body.p256dh,
            'a': body.auth,
        }
    )
    db.commit()
    return {'status': 'subscribed'}
