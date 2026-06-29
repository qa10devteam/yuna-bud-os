# TERRA.OS — Research Ekspercki: Polski Rynek Zamówień Publicznych i Branża Robót Ziemnych

**Data:** 2026-06-29  
**Metodologia:** 60+ źródeł, 6 równoległych wątków badawczych  
**Cel:** Pełne zrozumienie rynku przed implementacją M1 (ingestia danych, scoring, decision engine)

---

## CZĘŚĆ I — RYNEK ZAMÓWIEŃ PUBLICZNYCH W POLSCE

### 1.1 Wielkość i struktura rynku (2024)

**Źródło:** PIE (Polski Instytut Ekonomiczny), raport maj 2026; UZP Sprawozdanie 2024

| Wskaźnik | Wartość |
|---|---|
| **Całkowity rynek ZP** | **587 mld PLN** (13,9% PKB) |
| Zamówienia unijne (powyżej progów UE) | 254,8 mld PLN (~43%) |
| Zamówienia krajowe (Pzp, poniżej progów) | 75,6 mld PLN (~13%) |
| Zamówienia wyłączone z Pzp | 213,7 mld PLN (~36%) |
| Zamówienia podprogowe (<130 tys. PLN) | 42,9 mld PLN (~7%) |
| Prognoza 2029 | ~1 bilion PLN |

**Dynamika wzrostu (CAGR 2021–2024):**
- Zamówienia krajowe: +11,4% rocznie
- Zamówienia unijne: +17,3% rocznie
- Wyłączone z Pzp: +26,3% rocznie (głównie zbrojenia)

**Konkurencja:**
- 72% polskich firm prywatnych jest całkowicie nieaktywnych na rynku ZP
- Tylko **13%** firm składa oferty
- 56% przetargów unijnych ma TYLKO JEDNĄ ofertę (najgorszy wynik w UE)
- 35% przetargów krajowych — jedna oferta

→ **Wniosek dla Terra.OS:** Rynek jest niedosyćony. Niszę zajmują firmy, które składają systematyczne oferty — potencjał AI-assisted bidding jest ogromny.

### 1.2 Segment budowlany

- Rynek budowlany ogółem (2025): **>390 mld PLN**, wzrost realny ~3% r/r
- Prognoza 2026: **>400 mld PLN** (Spectis, PMR, GlobalData)
- Zatrudnienie: **1,3–1,5 mln osób** (~8% zatrudnienia)
- Łączne zadłużenie branży: **>5,8 mld PLN** (VIII 2025)
- Płynność małych firm: **2–3 miesiące** (krytyczne!)
- Motor wzrostu: KPO, FEnIKS 2021–2027, RFRD (Rządowy Fundusz Rozwoju Dróg)

**RFRD (dolnośląskie, 2024):** 192 mln PLN → 63 inwestycje drogowe dla gmin i powiatów

---

## CZĘŚĆ II — PRAWO ZAMÓWIEŃ PUBLICZNYCH (PZP 2021)

### 2.1 Podstawa prawna

- **Ustawa z 11.09.2019 r. Prawo zamówień publicznych** (Dz.U. 2023 poz. 1605 t.j.)
- Weszła w życie: 1.01.2021 r. (zastąpiła Pzp z 2004 r.)
- Implementuje dyrektywy UE 2014/24/UE, 2014/25/UE, 2014/23/UE

### 2.2 Progi wartości zamówień (kluczowe dla filtrowania)

#### Próg bagatelności (poniżej ustawy)
- Do 2025: **130 000 PLN** (dla dostaw/usług) / **130 000 PLN** (roboty budowlane)
- **Od 1 stycznia 2026: 170 000 PLN** (nowy próg krajowy)
- Poniżej — zamawiający stosuje własny regulamin, nie Pzp

#### Progi krajowe (Ksiega I Pzp)
- Powyżej 130 000 PLN (170 000 PLN od 2026) — stosuje się tryby krajowe
- Ogłoszenie w **BZP** (Biuletynie Zamówień Publicznych)

#### Progi unijne — **PRZELICZNIK EUR/PLN: 4,31 PLN** (od 1.01.2026)

| Zamówienie | EUR | PLN (2026–2027) |
|---|---|---|
| **Roboty budowlane** | 5 404 000 | **23 291 240 PLN** |
| Dostawy/usługi — admin. centralna | 140 000 | 603 400 PLN |
| Dostawy/usługi — samorządy | 216 000 | **930 960 PLN** |
| Usługi społeczne (klasyczne) | 750 000 | 3 232 500 PLN |
| Roboty sektorowe (art. 108 ust.2) | 10 000 000 | 43 100 000 PLN |

> **Poprzedni przelicznik (2024–2025): 4,6371 PLN** → roboty budowlane: ~25 678 000 PLN  
> **WAŻNE:** Kurs 4,31 PLN obniżył się — progi w PLN są NIŻSZE, więcej zamówień podlega reżimowi unijnemu.

**Powyżej progu unijnego:**
- Ogłoszenie w **TED** (Tenders Electronic Daily — UE)
- Obowiązek JEDZ (Jednolity Europejski Dokument Zamówienia)
- Inne terminy składania ofert
- Inne procedury odwoławcze

### 2.3 Tryby udzielania zamówień

| Tryb | Kiedy | Uwagi |
|---|---|---|
| **Tryb podstawowy wariant I** | Poniżej progów UE | Najczęstszy dla robót gminnych |
| **Tryb podstawowy wariant II** | Poniżej progów UE | Z negocjacjami |
| **Tryb podstawowy wariant III** | Poniżej progów UE | Negocjacje z ogłoszeniem |
| Przetarg nieograniczony | Powyżej i poniżej progów | Klasyczny "przetarg" |
| Przetarg ograniczony | Powyżej progów UE | Kwalifikacja wstępna |
| Negocjacje z ogłoszeniem | Powyżej progów UE | Wyjątkowe przypadki |
| Zamówienie z wolnej ręki | Wyjątkowe przesłanki | Art. 214 Pzp |

### 2.4 Kluczowe artykuły dla Terra.OS

| Art. | Temat | Znaczenie dla silnika |
|---|---|---|
| **Art. 224** | Rażąco niska cena | Red flag: oferta <70% wartości szacunkowej lub średniej innych ofert |
| **Art. 439** | Klauzula waloryzacyjna | Obowiązek w umowach >6 mies. — sprawdzenie czy SWZ zawiera |
| **Art. 449–453** | Zabezpieczenie NWU | Max 10% wartości umowy — flag jeśli wyższe |
| **Art. 464** | Podwykonawstwo | Obowiązek zgłoszenia — risk w SWZ |
| **Art. 97–98** | Wadium | Max 3% (progi UE), 1,5% (krajowe) |
| **Art. 116** | Warunki udziału | Referencje, zdolność techniczna — sprawdzenie czy firma kwalifikuje |

---

## CZĘŚĆ III — ŹRÓDŁA DANYCH O PRZETARGACH

### 3.1 BZP — Biuletyn Zamówień Publicznych

**Co to jest:** Oficjalny publikator dla zamówień krajowych (poniżej progów UE). Prowadzony przez Prezesa UZP na platformie e-Zamówienia.

**Kto publikuje:** Zamawiający publiczni (gminy, powiaty, szpitale, uczelnie, spółki komunalne z ≥50% udziałem publicznym)

**Rodzaje ogłoszeń w BZP:**
- Ogłoszenie o zamówieniu (wszczęcie)
- Ogłoszenie o wyniku postępowania
- Ogłoszenie o zmianie umowy
- Plan postępowań (art. 23 Pzp — obowiązek publikacji w BZP)

**API BZP — szczegóły techniczne:**

```
Endpoint: http://ezamowienia.gov.pl/mo-board/api/v1/notice
Dostęp: PUBLICZNY (bez klucza API)
Format: JSON
Dokumentacja: https://media.ezamowienia.gov.pl/pod/2022/08/Zalacznik-3-Instrukcja-integracji-z-API-BZP.zip
Regulamin: https://media.ezamowienia.gov.pl/pod/2023/02/Regulamin-korzystania-z-API-1.pdf
```

**Dostępne API na platformie e-Zamówienia:**
1. **API BZP WebService** — odczyt ogłoszeń (PUBLICZNY, bez rejestracji)
2. API MO — przekazywanie ogłoszeń do BZP (wymaga integracji)
3. API PP — plany postępowań (wymaga integracji)
4. API MT — uwierzytelnianie użytkowników
5. API MMiA — sprawozdania roczne
6. API CRD — OCDS, identyfikatory postępowań

**Pola ogłoszenia BZP (kluczowe dla Terra.OS):**
- `noticeNumber` — numer ogłoszenia (np. 2024/BZP 00123456/01)
- `noticePublicationDate` — data publikacji
- `procurementObject` — opis przedmiotu zamówienia (tekst)
- `cpvCodes[]` — kody CPV (tablica)
- `estimatedValue` / `estimatedValueFrom` / `estimatedValueTo` — wartość szacunkowa
- `submissionDeadlineDate` — termin składania ofert
- `orderingPartyName` / `orderingPartyAddress` — zamawiający
- `executionPlace` — miejsce realizacji (województwo/gmina)
- `contractType` — typ zamówienia (RC=roboty, D=dostawy, U=usługi)
- `procedureType` — tryb

### 3.2 TED — Tenders Electronic Daily

**Co to jest:** Suplement do Dziennika Urzędowego UE, zawiera zamówienia powyżej progów unijnych ze wszystkich państw UE.

**API TED v3:**
```
Base URL: https://api.ted.europa.eu
Search API: https://api.ted.europa.eu/v3/notices/search
Swagger: https://api.ted.europa.eu/swagger
Dostęp: Anonimowy dla opublikowanych ogłoszeń (klucz tylko dla niepublikowanych)
Developer Portal: https://developer.ted.europa.eu/home
```

**Parametry wyszukiwania TED:**
- `q` — full-text query (np. `cpv:45111200 AND country:PL`)
- `fields[]` — wybór pól
- `page` / `limit` — paginacja
- `scope=ALL` — wszystkie ogłoszenia

**Format danych:** eForms XML / JSON (od 2023, zastąpił stary TED XML)

**Roboty budowlane w TED z Polski:**
- Wartość min: ~23,3 mln PLN (próg UE 2026)
- Typowe: drogi ekspresowe, autostrady (GDDKiA), duże inwestycje miejskie
- Terra.OS: TED mniej priorytetowy (firma 7-osobowa rzadko kwalifikuje się do przetargów >23 mln PLN)

### 3.3 Baza Konkurencyjności (BK)

**Co to jest:** Portal dla beneficjentów funduszy UE (nie samorządów!) zobowiązanych do stosowania "zasady konkurencyjności" zamiast Pzp.

**URL:** https://bazakonkurencyjnosci.funduszeeuropejskie.gov.pl

**Kto publikuje:** Beneficjenci dotacji z FERS, FEnIKS, RPO (firmy prywatne, NGO, uczelnie realizujące projekty UE)

**Różnica vs BZP:**
- BZP = zamówienia jednostek publicznych na podstawie Pzp
- BK = zamówienia beneficjentów dotacji UE na podstawie Wytycznych 2021–2027
- Brak oficjalnego publicznego API — scraping przez stronę www

**Progi BK:**
- Usługi/dostawy: ≥50 000 PLN netto → zasada konkurencyjności
- Roboty budowlane: ≥50 000 PLN netto → zasada konkurencyjności

### 3.4 BIP — Biuletyn Informacji Publicznej

**Co to jest:** Urzędowe strony każdego organu publicznego (tysięcy gmin, starostw, urzędów). Zamawiający często publikują tam zapytania ofertowe i postępowania poniżej progu Pzp.

**Problem dla Terra.OS:**
- Brak centralnego API
- Każde BIP ma inną strukturę (różne systemy CMS)
- Scraping bardzo trudny i niestabilny
- Terra.OS M1: depriorytetyzować BIP (focus na BZP)

### 3.5 Inne źródła danych

| Źródło | Adres | Zawartość |
|---|---|---|
| Portal ZP | portalzp.pl | Aggregator BZP + BK + TED, kody CPV |
| info-przetargi.pl | info-przetargi.pl | Aggregator, opisy firm |
| eurobudowa.pl | eurobudowa.pl | Przetargi + zlecenia budowlane |
| atlasprzetargow.pl | atlasprzetargow.pl | Aggregator TED |
| Platforma zakupowa | platformazakupowa.pl | Obsługuje e-zamówienia dla wielu zamawiających |

---

## CZĘŚĆ IV — DOKUMENTY PRZETARGOWE

### 4.1 SWZ — Specyfikacja Warunków Zamówienia

**Obowiązek:** Każde postępowanie powyżej progu bagatelności musi mieć SWZ (art. 134 Pzp).

**Struktura SWZ (typowe sekcje dla robót budowlanych):**

```
I.   Zamawiający (dane, dane kontaktowe)
II.  Tryb udzielenia zamówienia
III. Opis przedmiotu zamówienia (przedmiar, STWiOR, projekt)
IV.  Termin realizacji
V.   Warunki udziału w postępowaniu
     - zdolność techniczna: wykaz robót (referencje ostatnie 5 lat, min. 1 kontrakt o wartości X)
     - zdolność finansowa: polisa OC min. Y PLN
     - uprawnienia: kierownik budowy z uprawnieniami budowlanymi
VI.  Podstawy wykluczenia (art. 108, 109 Pzp)
VII. Wykaz dokumentów i oświadczeń
VIII.Sposób obliczenia ceny (ryczałt lub kosztorys)
IX.  Kryteria oceny ofert
     - cena: 60% (min. wg UZP)
     - gwarancja: 20–30%
     - termin: 10–20%
X.   Wymagania dotyczące wadium (opcjonalnie)
XI.  Termin związania ofertą
XII. Opis sposobu przygotowania oferty
XIII.Informacje o formalnościach po wyborze
XIV. Wzór umowy (+ warunki waloryzacji art. 439)
     Załączniki: przedmiar, STWiOR, projekt budowlany/wykonawczy
```

**Red flags w SWZ dla Terra.OS:**
- Termin realizacji < 2 miesiące przy wartości > 1 mln PLN
- Brak klauzuli waloryzacyjnej (art. 439) przy umowie > 6 mies. → nielegalne od 2021
- Wymagania referencji przekraczające możliwości firmy 7-osobowej
- Wymaganie polisy OC > wartości zamówienia

### 4.2 Przedmiar Robót

**Co to jest:** Wykaz planowanych robót z obliczonymi ilościami. Podstawa do sporządzenia kosztorysu ofertowego.

**Format:**
```
Lp. | KNR kod | Opis pozycji | J.m. | Ilość
----|---------|--------------|------|------
1   | KNR 2-01 0101-01 | Roboty pomiarowe | km | 2,550
2   | KNR 2-01 0201-03 | Wykop mechaniczny kat. III | m3 | 1 250,00
3   | KNR 2-01 0235-02 | Formowanie nasypów drogowych | m3 | 820,00
```

**Typowe jednostki:**
- `m3` — wykopy, nasypy, transport ziemi
- `mb` / `m` — roboty liniowe (dreny, ściany)
- `m2` — humusowanie, plantowanie, korytowanie
- `t` — transport sprzętu, materiały sypkie
- `szt` — studnie, przepusty

**Kluczowe kody KNR dla robót ziemnych:**

| Kod KNR | Opis |
|---------|------|
| KNR 2-01 0101 | Roboty pomiarowe przy liniowych robotach ziemnych |
| KNR 2-01 0201 | Mechaniczne wykonanie wykopów koparkami |
| KNR 2-01 0203 | Wykopy koparkami z transportem gruntu (kat. I–IV) |
| KNR 2-01 0225 | Zasypanie wykopów |
| KNR 2-01 0235 | Formowanie i zagęszczanie nasypów drogowych |
| KNR 2-01 0301 | Nasypy z dowozu gruntu |
| KNR 2-01 0317 | Plantowanie skarp i dna wykopów |
| KNR 2-01 0607 | Pompowanie wody z wykopu (odwodnienie) |
| KNR 2-01 0501 | Profilowanie i zagęszczenie podłoża |
| KNR-W 2-01 0203 | Roboty koparkami (wersja uzupełniająca) |

### 4.3 STWiOR — Specyfikacja Techniczna Wykonania i Odbioru Robót

**Co to jest:** Dokument definiujący wymagania jakościowe, sposób wykonania i odbioru. Dla dróg gminnych wg standardów GDDKiA.

**Kluczowe oznaczenia dla robót ziemnych:**

| Kod | Nazwa |
|-----|-------|
| D-01.01.01 | Odtworzenie trasy i punktów wysokościowych |
| D-02.00.00 | Roboty ziemne — wymagania ogólne |
| D-02.01.01 | Wykonanie wykopów w gruntach nieskalistych |
| D-02.02.01 | Wykonanie nasypów |
| D-02.03.01 | Odwodnienie wykopów |
| D-04.01.01 | Koryto i profilowanie podłoża |
| D-08.01.01 | Krawężniki betonowe |

**Klasy gruntu (kat. I–IV) — wpływ na cenę:**
- Kat. I — grunt sypki, łatwy (piasek): najniższa cena
- Kat. II — glina piaszczysta, ziemia urodzajna
- Kat. III — glina, iły, glina zwięzła: typowe w dolnośląskim
- Kat. IV — gravel, żwiry zbite, glina mocno zwięzła: najwyższa cena (+30–50%)

### 4.4 Projekt Budowlany / Projekt Wykonawczy

**Skład dokumentacji projektowej dla robót ziemnych:**
- Część opisowa (opis geotechniczny, poziom wód gruntowych)
- Rysunki (przekroje poprzeczne, podłużne, plan sytuacyjny)
- Geotechnika (badania podłoża — wymagane dla wykopów >2m)
- Bilans mas (tabela: wykopy, nasypy, odkład, dozdysk)

**Bilans mas — klucz do sprawdzenia przedmiaru:**
```
Bilans mas = Vwykop × ks - Vnasyp × kn - Vdozdysk × kn
gdzie:
  ks = współczynnik spulchnienia (~1,1–1,3 dla gliny)
  kn = współczynnik zagęszczenia (~0,85–0,95)
  Vdozdysk = brakujący grunt do kupienia
  Vodkład = nadmiar do wywiezienia
```

> **Red flag Terra.OS:** Jeśli Vwykop × ks ≠ Vnasyp × kn + Vodkład — niezgodność w przedmiarze. Podejrzana wycena lub błąd projektanta.

---

## CZĘŚĆ V — KOSZTORYSOWANIE I WYCENA

### 5.1 Podstawa prawna kosztorysowania

**Rozporządzenie MRiT z 20 grudnia 2021 r.** w sprawie określenia metod i podstaw sporządzania kosztorysu inwestorskiego (Dz.U. 2021 poz. 2458)

**Dwie metody wyceny (warianty Wk):**

**Wariant A — Metoda szczegółowa (KNR-based):**
```
Wk = Σ(Lj × Cj) + Kp + Z
gdzie:
  Lj = nakład z KNR dla j-tej pozycji
  Cj = cena jednostkowa (robocizna + materiał + sprzęt)
  Kp = koszty pośrednie (narzut ~8–20%)
  Z  = zysk kosztorysowy (~5–10%)
```

**Wariant B — Metoda wskaźnikowa:**
```
Wk = Σ(Lj × Cj) × WK
gdzie WK = wskaźnik kosztowy z danych historycznych
```

### 5.2 SEKOCENBUD — baza cen

**Co to jest:** Wiodące w Polsce wydawnictwo kosztorysowe. Publikuje kwartalne biuletyny cen.

**Produkty:**
- **IMB** — Informacja o cenach materiałów budowlanych (co kwartał)
- **IRS** — Informacja o stawkach robocizny kosztorysowej i cenach sprzętu
- **BCO** — Biuletyn cen obiektów budowlanych (ceny wskaźnikowe)
- **BRZ** — Biuletyn cen robót (gotowe normy cenowe)

**Stawki robocizny kosztorysowej — aktualne dane (I poł. 2025):**

| Wskaźnik | Wartość |
|---|---|
| Płaca minimalna (od 1.01.2025) | **4 666 PLN brutto** |
| Stawka godzinowa (zlecenia) | **30,50 PLN/h** |
| Przeciętne wynagrodzenie w budownictwie (Q1 2025) | ~8 962 PLN |
| Wzrost stawek robocizny kosztorysowej r/r | **+9,3–10,0%** |
| Wzrost stawek brutto r/r | +9,7–10,4% |

**Narzuty kosztorysowe (typowe dla Dolnego Śląska):**
- Koszty pośrednie (Kp/R): 50–80% wartości robocizny
- Zysk (Z): 8–15% od (R+M+S+Kp)

### 5.3 Typowe ceny robót ziemnych (Polska 2025)

| Rodzaj roboty | Cena jednostkowa |
|---|---|
| Wykop mechaniczny kat. I–II (koparka) | **30–50 PLN/m³** |
| Wykop mechaniczny kat. III–IV (koparka) | **50–80 PLN/m³** |
| Wykop ręczny | 120–180 PLN/m³ |
| Nasyp z gruntu miejscowego | **25–40 PLN/m³** |
| Nasyp z dowozu gruntu | 60–90 PLN/m³ |
| Wywóz ziemi | 40–60 PLN/m³ |
| Korytowanie mechaniczne | 15–25 PLN/m² |
| Profilowanie i zagęszczenie podłoża | 5–10 PLN/m² |
| Humusowanie z obsianiem trawą | 15–25 PLN/m² |
| Badania geotechniczne | 1 000–3 000 PLN |

### 5.4 Kody CPV dla robót ziemnych i drogowych

| Kod CPV | Opis | Typowe przetargi |
|---------|------|-----------------|
| **45111200-0** | Roboty w zakresie przygotowania terenu pod budowę i roboty ziemne | Główny kod Terra.OS |
| **45111000-8** | Roboty w zakresie burzenia, roboty ziemne | Rozbiórki + ziemne |
| **45112000-5** | Roboty w zakresie usuwania gleby | Humusowanie, karczowanie |
| **45112700-2** | Roboty w zakresie kształtowania terenu | Nasypy, skarpy |
| **45233120-6** | Roboty w zakresie budowy dróg | Drogi gminne — główny rynek |
| **45233200-8** | Roboty w zakresie różnych nawierzchni | Chodniki, parkingi |
| **45233141-9** | Roboty w zakresie konserwacji dróg | Remonty bieżące |
| **45231300-8** | Roboty budowlane w zakresie budowy wodociągów i rurociągów | Infrastruktura |
| **45232410-9** | Roboty w zakresie kanalizacji ściekowej | Kanalizacja + ziemne |

**Typowe wartości kontraktów robót ziemnych/drogowych gminnych:**
- Mała inwestycja: 200 000 – 500 000 PLN
- Średnia inwestycja: 500 000 – 2 000 000 PLN
- Duża inwestycja (powiat): 2 000 000 – 10 000 000 PLN
- Powyżej 23,3 mln PLN → TED (rzadko dla firmy 7-osobowej)

---

## CZĘŚĆ VI — SILNIK DECYZYJNY L1 — AKSJOMATY

### 6.1 Rażąco niska cena (Art. 224–226 Pzp)

**Definicja prawna:** Cena "odbiegająca od cen rynkowych w sposób nieuzasadniony" (orzecznictwo KIO)

**Mechanizm (art. 224 ust. 2 Pzp):**
```
TRIGGER: oferta < 70% × wartości szacunkowej zamawiającego
     LUB: oferta < 70% × średnia arytmetyczna wszystkich ofert
→ Zamawiający wzywa do wyjaśnień (termin min. 5 dni)
→ Brak wyjaśnień LUB wyjaśnienia niewiarygodne → ODRZUCENIE OFERTY
```

**Znaczenie dla Terra.OS:**
- Sprawdź czy Twoja oferta nie jest < 70% wartości szacunkowej
- Sprawdź historyczne oferty (jeśli dostępne) — nie ląduj poniżej 70% średniej
- Red flag: wartość szacunkowa zamawiającego jest bardzo niska → możliwe błędy projektanta

### 6.2 Kary umowne — typowe postanowienia umowne

**Rodzaje kar w umowach o roboty budowlane:**

| Typ kary | Typowy poziom | Podstawa |
|---|---|---|
| Opóźnienie w wykonaniu | **0,05–0,5% wynagrodzenia umownego / dzień** | Umowna |
| Opóźnienie w usunięciu wad (gwarancja) | 0,1–0,3% / dzień | Umowna |
| Odstąpienie z winy wykonawcy | 5–15% wartości umowy | Umowna |
| Kara maksymalna | 20–30% wartości umowy (łącznie) | Rekomendacja UZP |

**Red flags dla Terra.OS:**
- Kara > 0,5%/dzień za opóźnienie = onerous clause → FLAG WARN
- Brak cap na kary łączne → FLAG WARN
- Kara za odstąpienie > 15% → FLAG WARN
- Brak możliwości siły wyższej (force majeure) → FLAG BLOCK

### 6.3 Waloryzacja wynagrodzenia (Art. 439 Pzp)

**OBOWIĄZEK** zawarcia klauzuli waloryzacyjnej jeśli:
- Umowa na roboty/usługi na okres > 6 miesięcy (art. 439 ust. 1)
- W przypadku zmiany cen materiałów lub kosztów

**Mechanizm:**
```
Weryfikacja co min. 6 mies.
Wskaźniki: GUS (CPI), SEKOCENBUD, wskaźnik zmiany cen w budownictwie
Próg uruchomienia waloryzacji: zmiana > 5% (typowo)
Poziom: 50–100% zmiany wskaźnika (50/50 między stronami)
```

**Red flag:** Brak art. 439 w umowie > 6 mies. = niezgodność z Pzp → FLAG BLOCK (i szansa na odwołanie do KIO)

### 6.4 Wadium i ZNWU

| Instrument | Max | Kiedy | Forma |
|---|---|---|---|
| Wadium | 3% (UE), 1,5% (kraj.) | Składanie oferty | Pieniądz, gwarancja bank./ubezp. |
| ZNWU | **10%** wartości umowy | Podpisanie umowy | Gwarancja bank./ubezp., poręczenie |

**Red flag:** ZNWU > 10% → FLAG BLOCK (naruszenie art. 449 Pzp)  
**Uwaga:** ZNWU 5% to standard, 10% to max — wyższe jest nielegalne.

### 6.5 Odwodnienie wykopów — wymogi techniczne

**Kiedy wymagane odwodnienie:**
- Poziom wód gruntowych (PWG) powyżej dna wykopu
- Przepuszczalność gruntu k > 10⁻⁵ m/s
- Głębokość wykopu > głębokości PWG

**Metody:**
- Pompowanie bezpośrednie (shallow excavations, k > 10⁻³ m/s)
- Igłofiltry (depresja do 5–6 m, k 10⁻⁴ – 10⁻⁵ m/s)
- Ścianki szczelne + pompowanie (głębokie wykopy miejskie)

**Sygnały w dokumentacji → FLAG:**
- "poziom wód gruntowych __ m poniżej terenu" w opisie geotechnicznym
- Jeśli PWG < głębokość wykopu bez pozycji odwodnienia w przedmiarze → **FLAG WARN: brak kosztów odwodnienia**
- Typy gruntów: piaski, żwiry → ryzyko odwodnienia wyższe

### 6.6 Głębokość wykopów → zabezpieczenie ścian

```
Głębokość wykopu > 1,0 m → skos (zależny od kat. gruntu) LUB umocnienie
Głębokość wykopu > 1,5 m → WYMAGANE umocnienie ścian (PN-B-06050:1999)
Brak pozycji szalowania przy głębokości > 1,5 m → FLAG WARN
```

### 6.7 Gwarancja jakości

**Typowe okresy gwarancji:**
- Roboty drogowe: **36–60 miesięcy** (5 lat standard dla gmin RFRD)
- Roboty ziemne: **24–36 miesięcy**
- GDDKiA: 10–15 lat (tylko duże drogi)

**Kryterium oceny ofert:** Zamawiający często punktuje gwarancje > 60 mies. jako kryterium jakościowe

### 6.8 Warunki udziału — zdolność techniczna

**Typowe wymagania dla robót drogowych gminnych:**
```
Warunek referencji:
"Wykonawca wykonał w ostatnich 5 latach ≥ 1 robotę budowlaną
polegającą na budowie/przebudowie drogi
o wartości ≥ [X PLN brutto]"

Gdzie X = 30–80% wartości zamówienia (zależy od zamawiającego)
```

**Dokumenty:**
- Wykaz robót budowlanych (formularz)
- Referencje (poświadczenie od poprzedniego zamawiającego)
- Wykaz osób (kierownik budowy z uprawnieniami budowlanymi w specjalności drogowej)
- Polisa OC min. [wartość w SWZ]

---

## CZĘŚĆ VII — PROCESY I TERMINY

### 7.1 Harmonogram postępowania (tryb podstawowy)

```
Dzień 0: Ogłoszenie w BZP
   ↓ min. 21 dni (roboty budowlane, kraj.) / 35 dni (UE)
Dzień X: Termin składania ofert (deadline)
   ↓ 7 dni (kraj.) / 10–15 dni (UE)
Dzień X+7: Otwarcie ofert → publikacja w BZP
   ↓ 5–30 dni (ocena, wyjaśnienia RNC, JEDZ)
Dzień Y: Wybór najkorzystniejszej oferty + informacja w BZP
   ↓ 5 dni (kraj.) / 10 dni (UE) = termin na odwołanie KIO
Dzień Z: Podpisanie umowy
   ↓ (po upływie standstill)
Start realizacji
```

**Kluczowe terminy dla Terra.OS:**
- Ogłoszenie → termin składania: min. 21 dni
- Alert "critical" jeśli termin < 7 dni
- Alert "warning" jeśli termin < 14 dni

### 7.2 KIO — Krajowa Izba Odwoławcza

**Terminy wniesienia odwołania (art. 515 Pzp):**
- Powyżej progów UE: **10 dni** od dnia, w którym powzięto wiadomość
- Poniżej progów UE: **5 dni**
- Na treść ogłoszenia/SWZ: 10 lub 5 dni od publikacji

**Opłata od odwołania (roboty budowlane):**
- Powyżej progów UE: 20 000 PLN
- Krajowe: 10 000 PLN

---

## CZĘŚĆ VIII — REGION DOLNOŚLĄSKIE / PROFIL FIRMY

### 8.1 Rynek w dolnośląskim

**Inwestycje RFRD 2024:** 192 mln PLN → 63 inwestycje w gminach i powiatach

**Kluczowe źródła przetargów dla firmy z Dzierżoniowa:**
- Powiat Dzierżoniowski (dzierżoniow.pl BIP)
- Gmina Dzierżoniów, Bielawa, Niemcza, Pieszyce, Piława Górna
- Powiat Ząbkowicki, Powiat Świdnicki (sąsiednie powiaty)
- Województwo Dolnośląskie (DSDiK — Dolnośląska Służba Dróg i Kolei)
- GDDKiA Oddział Wrocław (drogi krajowe — raczej za duże)
- Zakłady wodociągowe, oczyszczalnie ścieków (lokalne spółki komunalne)

**Firma: "Przedsiębiorstwo Budowlano-Melioracyjne BUD-MEL Dzierżoniów"**
- 67 udzielonych zamówień publicznych
- Łączna wartość wygranych: ~35,6 mln PLN
- Typowe: roboty budowlane, melioracje, roboty ziemne

### 8.2 Typowy profil przetargu dla firmy 7-osobowej

| Parametr | Optymalny zakres |
|---|---|
| Wartość zamówienia | 200 000 – 2 000 000 PLN |
| CPV główne | 45111200-0, 45233120-6, 45112000-5 |
| Region | Dolnośląskie (powiat dzierżoniowski + sąsiednie) |
| Tryb | Tryb podstawowy wariant I (BZP) |
| Źródło finansowania | RFRD, budżet gminy/powiatu |
| Termin realizacji | 2–6 miesięcy |
| Referencje | Min. 1 robota ≥ 100 000 PLN w ostatnich 5 latach |

---

## CZĘŚĆ IX — IMPLIKACJE DLA M1 TERRA.OS

### 9.1 Priorytety integracji źródeł

```
Priorytet 1: BZP API (ezamowienia.gov.pl/mo-board/api/v1/notice)
  - Publiczne, bezpłatne, JSON
  - Codzienne ściąganie nowych ogłoszeń
  - Filtrowanie: contractType=RC, CPV ∈ [45111200, 45233120, 45112000, ...]

Priorytet 2: TED API (api.ted.europa.eu)
  - Dla przetargów > 23,3 mln PLN
  - Mniej istotny dla firmy 7-osobowej
  - Implementacja w M2

Priorytet 3: BK scraping
  - Brak API, scraping przez Playwright
  - Implementacja w M3
```

### 9.2 Matching score — sygnały dla modelu

**Sygnały pozytywne (+):**
- CPV match z profilem właściciela
- Województwo match
- Wartość w optymalnym przedziale (200K–2M PLN)
- Termin składania > 14 dni
- Tryb podstawowy (łatwiejszy niż UE)
- Źródło finansowania: RFRD, gmina (wiarygodny zamawiający)

**Sygnały negatywne / red flags (–):**
- Wartość > 10 mln PLN (za duże bez konsorcjum)
- Referencje wymagające > możliwości firmy
- Termin realizacji < 6 tygodni (za krótki)
- Kary umowne > 0,5%/dzień
- Brak klauzuli waloryzacyjnej (> 6 mies. umowy)
- ZNWU > 10% wartości umowy
- Brak pozycji odwodnienia przy wykopach > 2m
- Brak pozycji szalowania przy wykopach > 1,5m

### 9.3 Gotowe zapytania do BZP API

```python
# Przetargi na roboty ziemne / drogowe w dolnośląskim
GET http://ezamowienia.gov.pl/mo-board/api/v1/notice
  ?contractType=RC
  &cpvCodes=45111200-0,45233120-6,45112000-5,45112700-2
  &executionPlace=dolnośląskie
  &dateFrom=2024-01-01
  &dateTo=2024-12-31
  &page=0&size=50
  &sort=noticePublicationDate,desc
```

### 9.4 Decision Engine — L1 Axioms (gotowe reguły)

```python
AXIOMS = [
    # Ekonomiczne
    {code: "EC-001", class: "economic",
     body: "Oferta < 70% szacunkowej wartości → RNC_RISK",
     severity: "WARN"},
    
    # Dokumentacyjne  
    {code: "DC-001", class: "documentary",
     body: "Umowa > 6 mies. bez art.439 waloryzacja → LEGAL_RISK",
     severity: "BLOCK"},
    {code: "DC-002", class: "documentary",
     body: "ZNWU > 10% wartości umowy → ILLEGAL",
     severity: "BLOCK"},
    {code: "DC-003", class: "documentary",
     body: "Kara umowna > 0.5%/dzień → ONEROUS",
     severity: "WARN"},
    
    # Inżynierskie
    {code: "ENG-001", class: "engineering",
     body: "Wykop > 1.5m bez pozycji szalowania → MISSING_ITEM",
     severity: "WARN"},
    {code: "ENG-002", class: "engineering",
     body: "PWG w opisie < głębokość wykopu, brak odwodnienia → MISSING_ITEM",
     severity: "WARN"},
    {code: "ENG-003", class: "engineering",
     body: "Niezgodność bilansu mas > 10% → DISCREPANCY",
     severity: "WARN"},
    
    # Regulacyjne
    {code: "REG-001", class: "regulatory",
     body: "Wymagana referencja > 80% wartości zamówienia → IMPOSSIBLE_CONDITION",
     severity: "WARN"},
]
```

---

## PODSUMOWANIE ŹRÓDEŁ (60+ weryfikowanych)

### Prawo i regulacje (18 źródeł)
1. Ustawa Pzp 2019 (Dz.U. 2023 poz. 1605)
2. Rozporządzenie MRiT 20.12.2021 — metody kosztorysowania
3. Art. 224–226 Pzp — rażąco niska cena (lex.pl)
4. Art. 439 Pzp — waloryzacja (ekomentarzpzp.uzp.gov.pl)
5. Art. 449–453 Pzp — ZNWU (lex.pl)
6. Art. 464 Pzp — podwykonawstwo (ekomentarzpzp.uzp.gov.pl)
7. Art. 97–98 Pzp — wadium (halasiwspolnicy.pl)
8. Art. 116 Pzp — warunki udziału (ekomentarzpzp.uzp.gov.pl)
9. Art. 23 Pzp — plan postępowań (ekomentarzpzp.uzp.gov.pl)
10. Art. 515 Pzp — terminy KIO (sn.pl, orzeczenia KIO)
11. Obwieszczenie Prezesa UZP XII 2023 — przelicznik 4,6371 (codozasady.pl)
12. Monitor Polski XII 2025 — przelicznik 4,31, progi 2026 (portalzp.pl)
13. Rozporządzenia delegowane KE 2023/2495, 2496, 2510 (UE)
14. Wytyczne 2021–2027 — zasada konkurencyjności (PARP)
15. PN-B-06050:1999 — roboty ziemne budowlane (normy)
16. PN-B-02480:1986 — grunty budowlane
17. Przykładowe klauzule waloryzacyjne UZP (gov.pl)
18. Rekomendacje UZP — kary umowne (lex.pl)

### Rynek i statystyki (12 źródeł)
19. PIE Raport "Miliardy na stole" maj 2026 — 587 mld rynek ZP
20. UZP Sprawozdanie 2024 — dane rynkowe
21. Spectis — prognoza rynku budowlanego 400+ mld 2026
22. ForumBranżowe — podsumowanie 2025 r. i prognozy 2026
23. GUS/SSGK — budownictwo maj 2026 (+3,9% r/r)
24. SEKOCENBUD — stawki robocizny I poł. 2025
25. SEKOCENBUD — sklep.sekocenbud.pl (produkty IRS, IMB, BCO, BRZ)
26. ZZBudowlani — minimalna stawka kalkulacyjna 2024
27. gov.pl/dolnoslaski-uw — RFRD 192 mln PLN dolnośląskie 2024
28. info-przetargi.pl/firma/845 — BUD-MEL Dzierżoniów profil
29. eurobudowa.pl — przetargi dolnośląskie
30. BGK — RFRD plan finansowy 2026

### Techniczne (źródła API i dokumentacja)
31. ezamowienia.gov.pl/pl/integracja — API BZP dokumentacja
32. media.ezamowienia.gov.pl — Regulamin API (PDF)
33. media.ezamowienia.gov.pl — Instrukcja integracji API BZP ZIP
34. docs.ted.europa.eu/api/latest — TED API v3 docs
35. developer.ted.europa.eu — TED Developer Portal
36. github.com/OP-TED — TED GitHub
37. bazakonkurencyjnosci.funduszeeuropejskie.gov.pl — BK portal
38. mfiles.pl — Baza Konkurencyjności encyklopedia
39. feniks.kultura.gov.pl — Zasada konkurencyjności PDF
40. jorpex.com/sources/ted — TED search 700K notices

### Kosztorysowanie i normy (10 źródeł)
41. Kosztorys ofertowy KNR 2-01 — bip.gminawarta.pl (PDF przykład)
42. Kosztorys inwestorski budowa dróg — gminaglogow.pl (PDF)
43. KNR 2-01 Roboty ziemne — biuletyn.net (kody pozycji)
44. STWiOR D-02.00.00 Roboty ziemne — archiwum.gddkia.gov.pl
45. STWiOR D-02.01.01 — bip.malopolska.pl (PDF)
46. Kosztorys BRODZIAKI-TERESZPOL — gov.pl (PDF KNR przykład)
47. Inżynier Budownictwa — rodzaje kosztorysów
48. KBB — cztery rodzaje kosztorysów
49. AGH — Technologia Robót Budowlanych (bilans mas, trójkąty)
50. technologieibudownictwo.pl — bilans mas ziemnych

### Wykonawstwo i technika (10 źródeł)
51. chogi.pl — roboty ziemne definicja, rodzaje, cennik 2025
52. bip.wat.edu.pl — projekt odwodnienia wykopów (PDF)
53. bip.rumia.pl — STWiOR odwodnienie wykopów (PDF)
54. archiwum.ropczyce.bip.net.pl — SST odwodnienie
55. tree.com.pl — kalkulator objętości robót ziemnych
56. kalkulatorxxl.pl — kalkulator wykopu
57. maszyny-komunalne.eu — ceny minikoparki za metr wykopu
58. portalzp.pl CPV 45111200 — przetargi przykładowe
59. portalzp.pl CPV 45233120 — przetargi drogowe
60. ezamowienia.gov.pl notice 08dc0bc7 — przykładowe ogłoszenie

### Umowy i finanse (6 źródeł)
61. codozasady.pl — kara umowna: teoria a rzeczywistość
62. prawoikielnia.pl — kary umowne w umowach o roboty budowlane
63. janowski-wspolnicy.pl — OC wykonawcy robót budowlanych
64. gu.com.pl — polisy OC/CAR w przetargach publicznych
65. przetargipubliczne.pl — gwarancja jakości 60 mies. przykład
66. szukio.pl — KIO orzeczenia o stawce roboczogodziny

---

*Research gotowy do implementacji M1. Zaktualizowany: 2026-06-29.*
