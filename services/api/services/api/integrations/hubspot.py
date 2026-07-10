"""S112 — HubSpot integration."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def sync_offer_to_hubspot(offer_id: str, env: dict = os.environ) -> dict:  # type: ignore[assignment]
    """Sync an offer/deal to HubSpot CRM.

    Returns {'status': 'skipped'} if HUBSPOT_API_KEY is not configured.
    """
    api_key = env.get("HUBSPOT_API_KEY")
    if not api_key:
        logger.info("HUBSPOT_API_KEY missing — skipping HubSpot sync for offer=%s", offer_id)
        return {"status": "skipped"}

    try:
        import httpx  # type: ignore
        resp = httpx.post(
            "https://api.hubapi.com/crm/v3/objects/deals",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"properties": {"dealname": offer_id, "pipeline": "default", "dealstage": "appointmentscheduled"}},
            timeout=10,
        )
        resp.raise_for_status()
        deal_id = resp.json().get("id", "unknown")
        logger.info("HubSpot deal created: offer=%s deal_id=%s", offer_id, deal_id)
        return {"status": "synced", "deal_id": deal_id}
    except Exception as e:
        logger.warning("HubSpot sync failed for offer=%s: %s", offer_id, e)
        return {"status": "error", "detail": str(e)}
