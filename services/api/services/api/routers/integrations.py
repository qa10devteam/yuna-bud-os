"""S113-S115 — Integration endpoints: Webhook fire, Slack test, Pipedrive."""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth.deps import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/api/v2/integrations', tags=['integrations'])

BLOCKED_HOSTS = {'127.0.0.1', 'localhost', '0.0.0.0', '::1'}


def _ssrf_check(url: str):
    h = urlparse(url).hostname or ''
    if h in BLOCKED_HOSTS or h.startswith(('10.', '192.168.', '172.')):
        raise HTTPException(400, 'SSRF blocked')


class WebhookFireBody(BaseModel):
    url: str
    payload: dict = {}


class SlackTestBody(BaseModel):
    message: str = 'YU-NA test'


class PipedriveSyncBody(BaseModel):
    offer_id: str
    title: str = ''


@router.post('/webhook/fire')
async def fire_webhook(body: WebhookFireBody, user: AuthUser):
    _ssrf_check(body.url)
    r = httpx.post(body.url, json=body.payload, timeout=10)
    return {'status': r.status_code}


@router.post('/slack/test')
async def slack_test(body: SlackTestBody, user: AuthUser):
    from ..integrations.slack import post_to_slack
    return post_to_slack(body.message)


@router.post('/pipedrive/sync')
async def pipedrive_sync(body: PipedriveSyncBody, user: AuthUser):
    from ..integrations.pipedrive import sync_offer_to_pipedrive
    return sync_offer_to_pipedrive(body.offer_id, body.title)
