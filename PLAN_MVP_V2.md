# Terra.OS — Plan MVP (V2.0)
**System Zarządzania Ziemią dla Firmy Robót Ziemnych**  
**Status:** Faza 0 (Rebuild) | **Termin:** 5 dni roboczych | **Repo:** `qa10devteam/terra-os`

---

## 🎯 CEL MVP

Stworzyć interaktywną symulację SaaS "Terra.OS" — web app z 4 modułami (ZWIAD → Kosztorys → Silnik → Decyzja), industrialnym designem, animacjami, mock danymi i gotową do prezentacji przed klientem Maciejem K.

**Stack:** Next.js 14 (App Router) + Tailwind v4 + TypeScript + Zustand + Framer Motion + Recharts  
**Design:** Industrial Dark (`#0A0A0A`, `#1A1A1A`) + neon (`#00FF94`, `#FF3300`)  
**Metafora:** Łopata — Trzonek (ZWIAD), Kij (Kosztorys), Łyżka (Decyzja)

---

## 📋 ARCHITEKTURA ZADAŃ

### Faza 0: Przygotowanie Środowiska (Day 1 — rano)
**Cel:** Upewnić się, że build działa i repo jest w porządku.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 0.1 | **Weryfikacja narzędzi** — terminal, write_file, execute_code | P0 | Wszystkie 3 działają bez exit 130 | ❌ |
| 0.2 | **Check struktury repo** — `ls terra-os/` i `ls terra-os/src/` | P0 | Lista istniejących plików i pustych katalogów | ❌ |
| 0.3 | **Sprawdź konfigurację** — package.json, tsconfig, tailwind, next.config | P1 | Wszystkie pliki konfiguracyjne poprawne | ❌ |
| 0.4 | **Sprawdź freeCodeCamp** — `/home/ubuntu/freecodecamp` istnieje | P2 | Potwierdzenie klonowania | ✅ |
| 0.5 | **Test buildu** — `npm install && npm run build` | P0 | Build bez błędów lub lista do naprawy | ❌ |

**Kryterium sukcesu:** `npm run build` kończy się exit 0.

---

### Faza 1: Core — Struktura Aplikacji (Day 1 — popołudnie)
**Cel:** Stworzyć szkielet aplikacji z nawigacją i layoutem.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 1.1 | **src/types.ts** — definicje typów: `Tender`, `Survey`, `Quote`, `Decision`, `AppState` | P0 | Single Source of Truth dla danych | ❌ |
| 1.2 | **src/store/useStore.ts** — Zustand store z actionami: `setCurrentModule`, `addTender`, `updateQuote`, `generateDecision` | P0 | Global state management | ❌ |
| 1.3 | **src/app/layout.tsx** — root layout z fontami (Space Grotesk + JetBrains Mono) i globals.css | P0 | Layout renderuje się z fontami | ❌ |
| 1.4 | **src/app/globals.css** — Tailwind v4 + CSS variables + komponenty: `.card`, `.btn-primary`, `.badge-*` | P0 | Wszystkie utility classes gotowe | ❌ |
| 1.5 | **src/app/page.tsx** — entry point z `useState` + `AnimatePresence` (OpeningView → AppLayout) | P0 | Strona główna renderuje się | ❌ |

**Kryterium sukcesu:** `http://localhost:3000` renderuje otwierający widok "Łopaty".

---

### Faza 2: Open View — Ekran Startowy (Day 2 — rano)
**Cel:** Stworzyć efektowny ekran startowy z metaforą Łopaty.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 2.1 | **src/components/OpeningView.tsx** — animowana Łopata (SVG/CSS shapes) z tekstem "Terra.OS" + "System Zarządzania Ziemią" | P0 | Animacja wejścia 3s + przycisk "Uruchom system" | ❌ |
| 2.2 | **src/components/OpeningView.tsx** — sekcja "Jak działa" — tooltipy na 3 częściach łopaty: Trzonek=ZWIAD, Kij=Kosztorys, Łyżka=Decyzja | P1 | Interaktywne tooltipy na hover | ❌ |
| 2.3 | **src/components/OpeningView.tsx** — animacja przejścia: fade-out łopaty + fade-in AppLayout | P1 | Płynne przejście ≤0.5s | ❌ |

**Kryterium sukcesu:** Kliknięcie "Uruchom system" płynnie przechodzi do dashboardu.

---

### Faza 3: Layout + Nawigacja (Day 2 — południe)
**Cel:** Sidebar z 4 modułami + responsive mobile menu.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 3.1 | **src/components/Sidebar.tsx** — logo Terra.OS (SVG) + 4 przyciski modułów z ikonami (Map, Calculator, Flag, Brain) | P0 | Sidebar pokazuje się na desktopie | ❌ |
| 3.2 | **src/components/Sidebar.tsx** — stan aktywnego modułu (highlight `#00FF94`) + hover effects | P0 | Kliknięcie zmienia kolor na active | ❌ |
| 3.3 | **src/components/Sidebar.tsx** — sekcja user (Avatar "MK" + imię + firma) + przyciski Settings/Profile | P1 | User section widoczny na dole sidebaru | ❌ |
| 3.4 | **src/components/Sidebar.tsx** — mobile responsive: hamburger menu + overlay na mobile | P1 | Menu zwija/rozwija się na mobile | ❌ |
| 3.5 | **src/components/AppLayout.tsx** — wrapper: Sidebar + main content area + top bar (breadcrumb + time) | P0 | Layout renderuje się poprawnie | ❌ |

**Kryterium sukcesu:** Kliknięcie modułu w sidebarze aktualizuje URL i pokazuje odpowiedni content.

---

### Faza 4: Moduł Dashboard (Day 3 — rano)
**Cel:** Widok overview z 4 modułami i metrykami.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 4.1 | **src/components/pages/DashboardPage.tsx** — header z tytułem "Dashboard" + subheader "Overview Systemu" | P0 | Header renderuje się | ❌ |
| 4.2 | **src/components/pages/DashboardPage.tsx** — 4 karty modułów (ZWIAD/Kosztorys/Silnik/Decyzja) z ikonami, nazwami, opisami, statusem | P0 | Karty widoczne z badge: "Aktywny"/"Oczekujący" | ❌ |
| 4.3 | **src/components/pages/DashboardPage.tsx** — sekcja "Ostatnie aktywności" — timeline z 3-5 mock eventami | P1 | Timeline z datami i opisami | ❌ |
| 4.4 | **src/components/pages/DashboardPage.tsx** — sekcja "Kluczowe metryki" — 3 liczby: #tenderów, #aktów, #decyzji | P1 | Metryki z animacją liczenia | ❌ |

**Kryterium sukcesu:** Dashboard pokazuje 4 moduły i 3 metryki.

---

### Faza 5: Moduł ZWIAD — Trzonek (Day 3 — popołudnie)
**Cel:** Formularz survey terenowego z danymi gruntów.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 5.1 | **src/components/pages/ZwiadPage.tsx** — header "ZWIAD — Trzonek" + opis "Dane terenowe" | P0 | Header renderuje się | ❌ |
| 5.2 | **src/components/pages/ZwiadPage.tsx** — formularz z polami: lokalizacja, powierzchnia (m²), typ gruntu, dostępność, kosztorys wstępny | P0 | Formularz z 6 polami input | ❌ |
| 5.3 | **src/components/pages/ZwiadPage.tsx** — mock dane: 3 przykładowe tendery z mapy (placeholder) | P1 | Mock data renderuje się jako lista | ❌ |
| 5.4 | **src/components/pages/ZwiadPage.tsx** — walidacja pól + przycisk "Zapisz dane" → zapis do Zustand store | P1 | Dane trafiają do store | ❌ |

**Kryterium sukcesu:** Wypełnienie formularza + kliknięcie "Zapisz" aktualizuje store i pokazuje toast "Zapisano".

---

### Faza 6: Moduł Kosztorys — Kij (Day 4 — rano)
**Cel:** Kalkulator kosztorysowy z tabelą pozycji.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 6.1 | **src/components/pages/KosztorysPage.tsx** — header "KOSZTORYS — Kij" + opis "Struktura kosztów" | P0 | Header renderuje się | ❌ |
| 6.2 | **src/components/pages/KosztorysPage.tsx** — tabela pozycji: nazwa, jednostka, ilość, cena jedn., suma | P0 | Tabela z 5 mock pozycjami | ❌ |
| 6.3 | **src/components/pages/KosztorysPage.tsx** — sekcja podsumowania: suma brutto, VAT 23%, netto | P0 | Podsumowanie z obliczeniami | ❌ |
| 6.4 | **src/components/pages/KosztorysPage.tsx** — wykres Recharts: rozkład kosztów (pie chart) | P1 | Wykres renderuje się | ❌ |

**Kryterium sukcesu:** Tabela pokazuje 5 pozycji z obliczoną sumą brutto.

---

### Faza 7: Moduł Silnik — Przetwarzanie (Day 4 — popołudnie)
**Cel:** Symulacja "przetwarzania" danych z ZWIAD i Kosztorys.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 7.1 | **src/components/pages/SilnikPage.tsx** — header "SILNIK — Przetwarzanie" + opis "Analiza i generowanie" | P0 | Header renderuje się | ❌ |
| 7.2 | **src/components/pages/SilnikPage.tsx** — progress bar z animacją "Przetwarzanie danych terenowych..." | P0 | Progress bar animuje się 3s | ❌ |
| 7.3 | **src/components/pages/SilnikPage.tsx** — wynik: lista 3 rekomendacji z ikonami ✅/⚠️/❌ | P1 | Rekomendacje renderują się po "przetworzeniu" | ❌ |
| 7.4 | **src/components/pages/SilnikPage.tsx** — przycisk "Przekazaj do Decyzji" → nawigacja do DecyzjaPage | P1 | Kliknięcie przechodzi do modułu Decyzja | ❌ |

**Kryterium sukcesu:** Progress bar animuje się i pokazuje 3 rekomendacje.

---

### Faza 8: Moduł Decyzja — Łyżka (Day 5 — rano)
**Cel:** Podsumowanie decyzji z akceptacją klienta.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 8.1 | **src/components/pages/DecyzjaPage.tsx** — header "DECYZJA — Łyżka" + opis "Decyzja końcowa" | P0 | Header renderuje się | ❌ |
| 8.2 | **src/components/pages/DecyzjaPage.tsx** — sekcja z podsumowaniem: lokalizacja, pow., koszt brutto, rekomendacje | P0 | Podsumowanie renderuje się | ❌ |
| 8.3 | **src/components/pages/DecyzjaPage.tsx** — 2 przyciski: "Akceptuję" (zielony) i "Odrzucam" (czerwony) | P1 | Przyciski klikalne z feedbackiem | ❌ |
| 8.4 | **src/components/pages/DecyzjaPage.tsx** — toast po akceptacji: "Decyzja zaakceptowana — akt gotowy do podpisu" | P1 | Toast pojawia się na 3s | ❌ |

**Kryterium sukcesu:** Kliknięcie "Akceptuję" pokazuje toast z potwierdzeniem.

---

### Faza 9: Polish + Assets (Day 5 — południe)
**Cel:** Drobne poprawki, assety, ikony, finalne szlify.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 9.1 | **public/assets/** — generacja logo SVG + ikony modułów przez `scripts/generate_assets.py` | P1 | 5 plików SVG w public/assets/ | ❌ |
| 9.2 | **src/components/** — dodanie favicon i meta tags | P2 | Favicon renderuje się w tabie | ❌ |
| 9.3 | **src/components/** — dodanie toast notifications system (react-hot-toast lub custom) | P1 | Toasty pojawiają się na akcje | ❌ |
| 9.4 | **Stylistyczne** — sprawdź kontrast, spacing, font sizes na desktop+iPhone | P1 | Wszystkie komponenty spójne | ❌ |

**Kryterium sukcesu:** Brak błędów konsoli, wszystkie strony renderują się bez warningów.

---

### Faza 10: Test + Deploy + Push (Day 5 — wieczór)
**Cel:** Finalne testy, build, commit, push, deploy.

| # | Zadanie | Priorytet | Deliverable | Status |
|---|---------|-----------|-------------|--------|
| 10.1 | **Test lokalny** — `npm run dev` i ręczne przejście przez wszystkie 4 moduły | P0 | Brak błędów, smooth transitions | ❌ |
| 10.2 | **Build** — `npm run build` i `npm start` | P0 | Production build działa | ❌ |
| 10.3 | **Git** — `git add . && git commit -m "feat: Terra.OS MVP v2 — 4 moduły, layout, assets"` | P0 | Commit z 10+ zmienionych plików | ❌ |
| 10.4 | **Push** — `git push origin main` na `qa10devteam/terra-os` | P0 | Push bez błędów | ❌ |
| 10.5 | **Deploy** — `vercel deploy --prod` (wymaga loginu) lub manualne | P1 | App widoczna online | ❌ |

**Kryterium sukcesu:** `git log` pokazuje commit z 10+ zmianami, repo online z pełnym kodem.

---

## 🔑 ZALEŻNOŚCI MIĘDZY ZADANIAM

```
Faza 0 (tools) → Faza 1 (core) → Faza 2 (opening) → Faza 3 (layout)
                                                              ↓
Faza 4 (dashboard) ← Faza 5 (zwiad) ← Faza 6 (kosztorys) ← Faza 7 (silnik)
                                                              ↓
Faza 8 (decyzja) ← Faza 9 (polish) ← Faza 10 (deploy)
```

**Kluczowe zależności:**
- Faza 1 (store/types) → **wszystkie moduły** (muszą korzystać z store)
- Faza 3 (layout/sidebar) → **wszystkie strony** (layout otacza content)
- Faza 5 (ZWIAD) → Faza 6 (Kosztorys) → Faza 7 (Silnik) → Faza 8 (Decyzja) (pipeline danych)

---

## 🎨 KRYTERIA JAKOŚCI

| Obszar | Standard |
|--------|----------|
| **Kod** | TypeScript strict mode, no `any`, ESLINT clean |
| **Design** | Spójny dark theme, neon accents, industrial feel |
| **Performance** | Lighthouse ≥ 90 (perf/acc/best-practices/seo) |
| **UX** | Smooth transitions (Framer Motion), zero layout shifts |
| **Accessibility** | ARIA labels, keyboard navigation, contrast ≥ 4.5:1 |
| **Mobile** | Responsive na 320px+ (iPhone SE+) |

---

## 🚀 TO DO LIST — SKOROWANIE DLA AGENTA

### Priority P0 — MUST DO (Blocker):
1. ✅ Zainicjować repo `terra-os` (jest już)
2. ✅ Skonfigurować Next.js 14 + Tailwind v4 + TS + Zustand + Motion + Recharts
3. ✅ Stworzyć `src/types.ts` + `src/store/useStore.ts`
4. ✅ Stworzyć layout + sidebar + 4 moduły
5. ✅ Stworzyć OpeningView z metaforą Łopaty
6. ✅ Build + Push

### Priority P1 — SHOULD DO:
- Polish UI (toast, animations, spacing)
- Assets (SVG logo + module icons)
- Mobile responsive polish

### Priority P2 — NICE TO HAVE:
- Favicon + meta tags
- Verge deploy

---

## 📝 UWAGI DLA AGENTA (NOWY WĄTEK)

**Przy startu nowego wątku z tym planem:**

1. **Zawsze weryfikuj narzędzia na start** — terminal, write_file, execute_code. Jeśli exit 130, nie kontynuuj — zgłoś.
2. **Pracuj sekwencyjnie** — Faza 0 → 1 → 2 → ... → 10. Nie skacz po fazach.
3. **Po każdej fazie** — zweryfikuj pliki (read_file) i zbuduj (`npm run build`).
4. **Nie pushuj dopóki build nie przechodzi** — exit 0 na `npm run build` jest mandatory.
5. **Dane mock** — wszystkie dane są lokalne, fake. Nie potrzebujesz backendu.
6. **Assety** — jeśli GPT-Image-2 nie działa, użyj SVG inline w komponentach.
7. **freeCodeCamp** — służy jako reference do nauki React, nie jest częścią Terra.OS.

**Ścieżki kluczowe:**
- `/home/ubuntu/terra-os/` — główny projekt
- `/home/ubuntu/terra-os/src/` — kod źródłowy
- `/home/ubuntu/terra-os/public/` — static assets
- `/home/ubuntu/terra-os/scripts/` — Python utilities
- `/home/ubuntu/freecodecamp/` — reference (nie modyfikuj)

**Repo docelowe:** `git@github.com:qa10devteam/terra-os.git`

---

*Plan V2.0 — Ostatnia aktualizacja: 2025-01-XX*  
*Autor: AI Agent + Mateusz Jakimów (QA10)*
