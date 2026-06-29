# Informacja o stosowaniu AI w systemie Terra.OS

*(Dokument AI-Literacy zgodny z art. 13 rozporządzenia UE 2024/1689 — AI Act)*

## Czym jest Terra.OS?

Terra.OS to system wspomagania decyzji dla firm budowlanych i przetargowych.
System automatyzuje analizę dokumentacji przetargowej, kosztorysowanie
i planowanie logistyki. **System jest narzędziem wspomagającym — nie zastępuje
decyzji człowieka.**

## Jakie modele AI są używane?

| Moduł | Funkcja | Model AI |
|-------|---------|----------|
| Zwiad (M1) | Pobieranie i filtrowanie przetargów BZP | Heurystyki + dopasowanie CPV |
| Analiza (M2) | OCR, ekstrakcja przedmiaru, streszczenie | LLM (offline: StubClient) |
| Silnik (M4/M5) | Decyzja go/no-go, ocena ryzyka | Clingo (symboliczny) + Monte Carlo |
| Kosztorys (M3) | Generowanie kosztorysu | Deterministyczny kalkulator |
| Chat-brain (M6) | Edycja parametrów w języku naturalnym | LLM (offline: StubClient) |
| Logistyka (M7) | Planowanie ekip i sprzętu | OR-Tools CP-SAT |

## Co system robi automatycznie?

- Pobiera i filtruje ogłoszenia przetargowe (bez interakcji użytkownika).
- Analizuje dokumenty i generuje kosztorysy wstępne.
- Proponuje przydziały pracowników i sprzętu.
- Generuje szkice wiadomości do wykonawców.

## Co system NIGDY nie robi bez zatwierdzenia?

Następujące działania zawsze wymagają jawnego zatwierdzenia przez użytkownika
(przez mechanizm **Approval Gate**):

- Wysyłka zapytań ofertowych (RFQ) do kontrahentów.
- Złożenie oferty lub formularza przetargowego.
- Rozsyłanie planów dziennych do ekip.
- Każda inna komunikacja zewnętrzna.

Każde zatwierdzone działanie jest rejestrowane w logu audytowym (`audit_log`)
z datą, aktorem i treścią.

## Ograniczenia systemu

- Kosztorysy są wstępne — mogą nie uwzględniać lokalnych warunków rynkowych.
- Analiza przedmiaru opiera się na OCR — błędy skanowania mogą wpływać na wynik.
- Decyzja go/no-go jest rekomendacją, nie gwarancją rentowności.
- Dane kalibracyjne aktualizują się po każdym zamkniętym kontrakcie — nowy
  system ma mniejszą precyzję do momentu zebrania historii.

## Prawa użytkownika

Masz prawo do: wglądu w logi decyzyjne (`GET /audit`), żądania wyjaśnienia
konkretnej decyzji, zaskarżenia rekomendacji systemu i podjęcia decyzji
bez uwzględnienia rekomendacji AI.

---
*Wersja: 1.0 | Data: 2026-06-29 | Terra.OS M9*
