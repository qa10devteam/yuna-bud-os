# Data Processing Agreement — Terra.OS

*Wersja: 1.0 | Data: 2026-07-10 | Status: Szablon*

---

## 1. Strony Umowy

**Administrator danych (Controller):**  
Klient Terra.OS — podmiot korzystający z platformy (dalej: „Administrator").

**Podmiot przetwarzający (Processor):**  
Nous Research / Terra.OS SaaS (dalej: „Procesor").

Strony zawierają niniejszą Umowę o Powierzeniu Przetwarzania Danych Osobowych (DPA) na podstawie art. 28 Rozporządzenia (UE) 2016/679 (RODO).

---

## 2. Przedmiot i cel przetwarzania

Procesor przetwarza dane osobowe w imieniu Administratora wyłącznie w celu świadczenia usług platformy Terra.OS, w tym:
- zarządzania przetargami publicznymi i ofertami,
- analityki biznesowej i raportowania,
- powiadomień i alertów przetargowych,
- integracji z zewnętrznymi systemami CRM/ERP.

Przetwarzanie odbywa się wyłącznie na udokumentowane polecenie Administratora.

---

## 3. Kategorie danych osobowych

Przetwarzane kategorie danych:
- **Dane identyfikacyjne:** imię, nazwisko, adres e-mail, numer telefonu pracowników.
- **Dane organizacyjne:** nazwa firmy, NIP, REGON, adres siedziby.
- **Dane transakcyjne:** oferty, przetargi, decyzje, kosztorysy.
- **Dane techniczne:** adresy IP, logi dostępu, tokeny sesji.
- **Dane kontrahentów:** informacje o nabywcach (zamawiających) z publicznych rejestrów.

Brak przetwarzania danych szczególnych kategorii (art. 9 RODO) o ile Administrator nie wprowadzi ich samodzielnie.

---

## 4. Art. 15 RODO — Prawo dostępu

Administrator zapewnia osobom, których dane dotyczą, dostęp do ich danych.

Procesor wspiera realizację tego prawa poprzez:
- Endpoint `GET /api/v2/gdpr/audit-trail` — zwraca historię przetwarzania dla użytkownika.
- Endpoint `GET /api/v2/gdpr/export` — eksport wszystkich danych użytkownika (Art. 20).
- Czas odpowiedzi: Procesor dostarcza niezbędne informacje Administratorowi w ciągu **72 godzin** od otrzymania wniosku.

---

## 5. Art. 17 RODO — Prawo do usunięcia ('Prawo do bycia zapomnianym')

Na żądanie osoby fizycznej lub Administratora, Procesor:
1. Anonimizuje dane użytkownika w systemie (imię → `[USUNIĘTY]`, e-mail → `deleted_<hash>@terra.invalid`).
2. Usuwa tokeny sesji i klucze API.
3. Archiwizuje rekord z flagą `deleted=true` dla celów audytowych (retencja 90 dni, następnie trwałe usunięcie).
4. Endpoint: `DELETE /api/v2/gdpr/account`.

Wyjątki: dane niezbędne do realizacji obowiązków prawnych (faktury, audyt) przechowywane są przez ustawowy okres.

---

## 6. Art. 20 RODO — Prawo do przenoszenia danych

Osoby fizyczne mogą pobrać swoje dane w formacie JSON:
- Endpoint: `GET /api/v2/gdpr/export`
- Format: `application/json`, plik `my_data.json`
- Zakres: zakładki przetargów, alerty, decyzje, zgody.

Administrator może automatycznie przekazać eksport do innego systemu.

---

## 7. Środki techniczne i organizacyjne

Procesor stosuje następujące środki bezpieczeństwa:

| Obszar | Środek |
|--------|--------|
| Szyfrowanie w tranzycie | TLS 1.2+ (HTTPS) |
| Szyfrowanie danych | AES-256 dla backupów |
| Kontrola dostępu | RBAC (admin/manager/viewer), JWT + API keys |
| Izolacja danych | Row-Level Security (RLS) per tenant |
| Audyt | Pełne logi dostępu w `usage_events` |
| Backupy | Codzienne pg_dump, retencja 30 dni |
| Monitoring | Health checks, alerty ingest_lag |
| Testy DR | Miesięczne próby odtworzeniowe (`dr_drill.sh`) |

---

## 8. Podwykonawcy przetwarzania (Subprocessors)

| Podwykonawca | Cel | Lokalizacja |
|--------------|-----|-------------|
| Amazon Web Services (AWS) | Infrastruktura chmurowa, S3 backupy | EU (Frankfurt) |
| OpenAI (opcjonalne) | Analiza AI/ML przetargów | USA (SCCs) |
| Slack (opcjonalne) | Powiadomienia alertów | USA (SCCs) |
| Pipedrive (opcjonalne) | CRM integracja | EU |

Administrator zostanie powiadomiony o każdej zmianie podwykonawców z wyprzedzeniem **30 dni**.

---

## 9. Naruszenia danych osobowych

W przypadku wykrycia naruszenia Procesor:
1. Powiadomi Administratora w ciągu **24 godzin** od wykrycia.
2. Dostarczy opis incydentu, kategorię danych, liczbę osób.
3. Wdroży środki zaradcze i udokumentuje działania.

---

## 10. Postanowienia końcowe

- Umowa obowiązuje przez cały okres korzystania z platformy Terra.OS.
- Po zakończeniu umowy Procesor usuwa lub zwraca dane w ciągu **30 dni**.
- Właściwość prawa: prawo polskie, sąd właściwy dla siedziby Procesora.

---

*Dokument wygenerowany automatycznie przez system Terra.OS. Wymaga podpisu obu stron przed wejściem w życie.*
