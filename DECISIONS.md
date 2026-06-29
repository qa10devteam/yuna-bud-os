# DECISIONS.md — Kluczowe decyzje architektoniczne Terra.OS

Każde założenie i istotna decyzja projektowa jest tutaj udokumentowana.

---

## D001 — Integer arithmetic w Clingo (M4)
**Decyzja:** Wartości PLN mnożone ×100 (grosze), metry ×100 (cm) przed przekazaniem do Clingo.  
**Powód:** Clingo nie obsługuje floatów w ground. Błąd: `TypeError: unsupported operand`.  
**Wpływ:** Wszystkie aksjoaty operują na liczbach całkowitych. Wyniki dzielone przez 100 przy zwrocie.

## D002 — estimate.variant enum: 'doc' / 'owner' (M3)
**Decyzja:** Wariant kosztorysu to enum PostgreSQL z wartościami `doc` (z dokumentacji) i `owner` (własna kalkulacja).  
**Powód:** Czytelność; uniknięcie pomyłek A/B w kodzie.  
**UWAGA:** Alembic migrations — NIE używać `op.create_table` z SA Enum; używać `op.execute(DDL)`.

## D003 — Approval Gate: jedyna ścieżka do side-effects (M6+)
**Decyzja:** Każda akcja zewnętrzna (e-mail, dispatch, submit) musi przejść przez `approval_request` → `approve` → `audit_log`.  
**Powód:** Spec wymaga, żeby żaden external side-effect nie był możliwy bez ludzkiego zatwierdzenia.  
**Guard test:** `test_rfq_not_sent_before_approval` + `test_dispatch_returns_202_approval_id`.

## D004 — Monte Carlo seed=42, 2000 próbek (M5)
**Decyzja:** Deterministyczny seed dla powtarzalności testów.  
**Powód:** Testy muszą być deterministyczne. 2000 próbek to kompromis szybkość/precyzja.

## D005 — OR-Tools CP-SAT, seed=42, limit 10s (M7)
**Decyzja:** CP-SAT z fixed seed=42 i 10s time limit.  
**Powód:** Deterministyczność testów + szybkość w środowisku CI.

## D006 — httpx ASGITransport dla testów offline (wszystkie milestony)
**Decyzja:** `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.  
**Powód:** httpx 0.28+ nie akceptuje `app=app` bezpośrednio — wymagany explicit transport.

## D007 — DB_PASSWORD wyłącznie przez env var (wszystkie milestony)
**Decyzja:** Hasło DB nigdy w kodzie, logach ani w `pytest.ini`. Tylko `os.environ["DB_PASSWORD"]`.  
**Powód:** Bezpieczeństwo. Hermes redaktuje `***` w terminalu.

## D008 — Calibration coeff clip [0.5, 2.0] (M9)
**Decyzja:** Nowy współczynnik kalibracyjny jest przycinany do zakresu [0.5, 2.0].  
**Powód:** Ochrona przed outlierami (np. błędne dane kosztowe zamykającego kontraktu).  
**Weryfikacja:** `VERIFY` — zakres do ustalenia z klientem na podstawie historycznych danych.

## D009 — LangGraph: synchronous compile().invoke() w offline (M9)
**Decyzja:** W trybie TERRA_OFFLINE=1 pipeline LangGraph wykonuje się synchronicznie (`graph.invoke()`).  
**Powód:** Testy muszą być synchroniczne; brak potrzeby persystencji stanu między sesjami.  
**Produkcja:** Rozważyć LangGraph Cloud lub własny checkpointer PostgreSQL.

## D010 — explanation_md jedyne pole LLM (M4+)
**Decyzja:** `EngineResult.explanation_md` jest jedynym polem generowanym przez LLM.  
**Powód:** Spec/09 wymaga, żeby żadne wartości liczbowe nie były halucynowane przez LLM.  
**Compliance:** Udokumentowane w `docs/ART50_DISCLOSURE.md`.

## D011 — Backup: pg_dump --format=custom --compress=9 (M9)
**Decyzja:** Backup w formacie custom (binarny, indeksowany) z max kompresją.  
**Powód:** Szybszy restore (pg_restore -j N dla równoległości). Mniejszy rozmiar.  
**Harmonogram:** `VERIFY` — cron do skonfigurowania przez ops, nie przez aplikację.

## D012 — TIER=1/2/3 feature flags (M9)
**Decyzja:** Env var TIER kontroluje dostępność endpointów. Domyślnie TIER=3 (full).  
**Powód:** Spec wymaga feature-flags dla deployment na różnych poziomach licencji.  
**Guard:** `test_tier_flags` weryfikuje logikę is_enabled().
