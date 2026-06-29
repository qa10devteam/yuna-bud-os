# Art. 50 AI Act — Obowiązki dostawcy systemu AI wysokiego ryzyka

*(Rozporządzenie (UE) 2024/1689, art. 50 — przejrzystość systemów AI)*

## Oświadczenie dostawcy

Terra.OS jest systemem wspomagania decyzji biznesowych sklasyfikowanym jako
**system AI niskiego ryzyka** (Aneks III nie ma zastosowania dla narzędzi
zarządzania projektami B2B). Mimo to, zgodnie z zasadą dobrowolnej przejrzystości,
dostawca systemu niniejszym oświadcza:

## 1. Identyfikacja systemu AI

- **Nazwa:** Terra.OS
- **Wersja:** M9 (Tier 3)
- **Przeznaczenie:** Wspomaganie decyzji przetargowych dla MŚP budowlanych
- **Klasyfikacja ryzyka (AI Act):** Niskie ryzyko (art. 50 — dobrowolne)

## 2. Przejrzystość interakcji

W miejscach, gdzie użytkownik wchodzi w interakcję z modelem językowym (LLM)
za pośrednictwem interfejsu chat (`POST /estimates/{id}/chat`), system:

- Wyraźnie oznacza, że odpowiedź pochodzi od systemu AI.
- Nie próbuje sprawiać wrażenia, że odpowiada człowiek.
- Wskazuje pole `explanation_md` jako jedyne pole autorstwa LLM w wyniku silnika.

## 3. Treści generowane przez AI

Jedynym polem w odpowiedziach API, którego treść generuje LLM bez deterministycznej
weryfikacji, jest `EngineResult.explanation_md`. Wszystkie wartości liczbowe
(koszty, współczynniki, prawdopodobieństwo wygranej) są obliczane deterministycznie.

## 4. Dane treningowe

System Terra.OS nie trenuje ani nie dostrajuje żadnych modeli na danych użytkownika.
Korekta kalibracyjna (`calibration_coeff`) jest liczbowym współczynnikiem,
a nie aktualizacją wag modelu.

## 5. Kontakt

Zgłoszenia dotyczące systemu AI: zarzadzanie@[domena-klienta].pl
Organ nadzorczy (PL): Urząd Ochrony Danych Osobowych (uodo.gov.pl)

---
*Wersja: 1.0 | Data: 2026-06-29 | Terra.OS M9*
