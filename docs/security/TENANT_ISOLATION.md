# Tenant Isolation Audit — TERRA-OS

**Data wykonania:** 2026-07-10  
**Skrypt:** `services/scripts/tenant_isolation_audit.py`  
**Sprint:** S104 (BPMN Faza 3)

## Wyniki

| Tabela | NULL tenant_id | Status |
|--------|---------------|--------|
| agent_run | 0 | ✅ OK |
| alert_failed | 0 | ✅ OK |
| approval_request | 0 | ✅ OK |
| audit_log | 0 | ✅ OK |
| automation_event_log | 0 | ✅ OK |
| automation_webhook | 0 | ✅ OK |
| availability | 0 | ✅ OK |
| axiom | 0 | ✅ OK |
| bid_intelligence | 0 | ✅ OK |
| buyer_crm | 0 | ✅ OK |
| calendar_event | 0 | ✅ OK |
| calibration_coeff | 0 | ✅ OK |
| competency | 0 | ✅ OK |
| competitor_watch | 0 | ✅ OK |
| contract | 0 | ✅ OK |
| cost_estimate | 0 | ✅ OK |
| daily_plan | 0 | ✅ OK |
| discrepancy | 0 | ✅ OK |
| dispatch | 0 | ✅ OK |
| document_chunk | 0 | ✅ OK |
| employee | 0 | ✅ OK |
| estimate | 0 | ✅ OK |
| estimate_line | 0 | ✅ OK |
| field_status | 0 | ✅ OK |
| ingest_task | 0 | ✅ OK |
| kosztorys | 0 | ✅ OK |
| kosztorys_dzial | 0 | ✅ OK |
| kosztorys_pozycja | 0 | ✅ OK |
| kosztorys_skladnik | 0 | ✅ OK |
| market_results | 0 | ✅ OK |
| material_alert | 0 | ✅ OK |
| mobile_device | 0 | ✅ OK |
| offer_result | 0 | ✅ OK |
| offers | 0 | ✅ OK |
| **organizations** | **2** | ⚠️ ISSUE |
| owner_profile | 0 | ✅ OK |
| przedmiar_item | 0 | ✅ OK |
| rate_card | 0 | ✅ OK |
| resource_equipment | 0 | ✅ OK |
| rfq | 0 | ✅ OK |
| rfq_message | 0 | ✅ OK |
| risk_run | 0 | ✅ OK |
| scoring_config | 0 | ✅ OK |
| tender | 0 | ✅ OK |
| tender_alert | 0 | ✅ OK |
| tender_bookmark | 0 | ✅ OK |
| tender_document | 0 | ✅ OK |
| tender_duplicate | 0 | ✅ OK |
| user_rates | 0 | ✅ OK |
| workflow_definition | 0 | ✅ OK |

## Podsumowanie

- **Sprawdzono tabel:** 52
- **Tabel z problemem (NULL tenant_id):** 1
- **Tabela z problemem:** `organizations` — 2 rekordy bez tenant_id

## Zalecenie

Tabela `organizations` posiada 2 rekordy z `tenant_id IS NULL`. Są to prawdopodobnie organizacje systemowe/testowe. Należy:
1. Sprawdzić te rekordy: `SELECT id, name FROM organizations WHERE tenant_id IS NULL`
2. Przypisać tenant lub oznaczyć jako systemowe
3. Rozważyć dodanie NOT NULL constraint na `organizations.tenant_id` po czyszczeniu

## Środki techniczne zapobiegające

- RLS (Row Level Security) jest włączone na tabelach wrażliwych
- Kolumna `tenant_id` posiada NOT NULL constraint na większości tabel
- Polityki RLS: `tenant_isolation` aktywna na `tender`, `organizations`, `mobile_device` i innych
