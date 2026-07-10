# Terra-OS Workflow JSON Schema

## Overview

Terra-OS BPMN-like workflows are stored as JSONB in `workflow_definition` table.
Each workflow defines triggers, conditions, and actions.

## Schema

```json
{
  "id": "uuid (auto)",
  "name": "string",
  "description": "string",
  "version": "1.0",
  "trigger": {
    "type": "TENDER_CREATED | SCORE_UPDATED | DEADLINE_7D | DEADLINE_3D | DECISION_MADE | MANUAL",
    "filters": {
      "min_score": 0.7,
      "cpv_codes": ["45000000"],
      "regions": ["PL21"]
    }
  },
  "conditions": [
    {
      "field": "match_score | value_pln | cpv_code | deadline_at | title",
      "operator": "eq | gt | lt | contains | in_list",
      "value": "any"
    }
  ],
  "condition_logic": "AND | OR",
  "actions": [
    {
      "type": "EMAIL | WEBHOOK | BOOKMARK | DECISION | NOTIFICATION",
      "params": {
        "to": "email address (EMAIL)",
        "subject": "string (EMAIL)",
        "body": "string (EMAIL)",
        "url": "https://... (WEBHOOK)",
        "method": "POST (WEBHOOK)",
        "payload": {} ,
        "message": "string (NOTIFICATION)",
        "decision": "bid|pass (DECISION)"
      },
      "order": 1
    }
  ],
  "is_active": true,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

## Trigger Types

| Type | Description |
|------|-------------|
| `TENDER_CREATED` | Fires when a new tender is ingested |
| `SCORE_UPDATED` | Fires when match_score changes |
| `DEADLINE_7D` | Fires 7 days before deadline |
| `DEADLINE_3D` | Fires 3 days before deadline |
| `DEADLINE_1D` | Fires 1 day before deadline |
| `DECISION_MADE` | Fires when bid/pass decision is recorded |
| `MANUAL` | Triggered manually via API |

## Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `eq` | Equals | `{"field":"cpv_code","operator":"eq","value":"45000000"}` |
| `gt` | Greater than | `{"field":"match_score","operator":"gt","value":0.7}` |
| `lt` | Less than | `{"field":"value_pln","operator":"lt","value":1000000}` |
| `contains` | String contains | `{"field":"title","operator":"contains","value":"budowlan"}` |
| `in_list` | Value in list | `{"field":"region","operator":"in_list","value":["PL21","PL22"]}` |

## Action Types

| Type | Description |
|------|-------------|
| `EMAIL` | Send email notification |
| `WEBHOOK` | HTTP POST to external URL |
| `BOOKMARK` | Auto-bookmark tender |
| `DECISION` | Set bid/pass decision |
| `NOTIFICATION` | Create in-app notification |
