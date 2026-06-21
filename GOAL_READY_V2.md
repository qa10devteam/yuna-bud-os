# 🚀 Terra.OS MVP — INIECJA DLA AGENTA

**CEL:** Stworzyć pełną web app "Terra.OS" — 4 moduły (ZWIAD→Kosztorys→Silnik→Decyzja), industrialny design dark/neon, gotową do prezentacji przed klientem Maciejem K.

---

## ⚠️ NA START — SPRWDŹ NARZĘDZIA

```bash
# Test terminal:
date
# Test write_file: napisz plik /tmp/test_write_ok i read_file go
# Test execute_code: print("OK")

# Jeśli jakiekolwiek zwraca exit 130 / interrupted → ZATRZYJ się i zgłoś. NIE kontynuuj.
```

## 📂 STRUKTURA PLIKÓW

```
/home/ubuntu/terra-os/          ← główne repo (jest już git init)
├── src/
│   ├── app/
│   │   ├── page.tsx            ← entry point + AnimatePresence
│   │   ├── layout.tsx          ← root layout z fontami
│   │   └── globals.css         ← Tailwind v4 + CSS variables
│   ├── components/
│   │   ├── OpeningView.tsx     ← ekran startowy (Łopata)
│   │   ├── Sidebar.tsx         ← nawigacja 4 modułów
│   │   ├── AppLayout.tsx       ← wrapper: sidebar + content
│   │   └── pages/
│   │       ├── DashboardPage.tsx
│   │       ├── ZwiadPage.tsx
│   │       ├── KosztorysPage.tsx
│   │       ├── SilnikPage.tsx
│   │       └── DecyzjaPage.tsx
│   ├── store/
│   │   └── useStore.ts         ← Zustand store
│   ├── types.ts                ← TypeScript types
│   └── data/
│       └── mock.ts             ← fake data
├── public/assets/              ← SVG assets
├── scripts/
│   ├── svg_converter.py
│   └── generate_assets.py
├── package.json
├── tsconfig.json
├── next.config.ts
├── tailwind.config.ts
└── .gitignore
```

## 🎨 DESIGN TOKENS

```css
--background: #0A0A0A
--surface: #1A1A1A
--border: #3D3D3C
--text: #F4F4F0
--accent-green: #00FF94
--accent-red: #FF3300
--accent-blue: #3B82F6
--accent-purple: #A855F7

Fonty: Space Grotesk (display), JetBrains Mono (mono/numbers)
```

## 📦 DEPENDENCIES

```json
{
  "dependencies": {
    "next": "14.2.0",
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "tailwindcss": "^4.0.0",
    "@tailwindcss/postcss": "^4.0.0",
    "motion": "^10.18.0",
    "zustand": "^4.5.0",
    "recharts": "^2.12.0",
    "lucide-react": "^0.390.0",
    "@phosphor-icons/react": "^2.1.0"
  }
}
```

---

## 🔨 FAZYPRACY — SEKWENCYJNIE

### Faza 0: Verify & Build (15 min)
1. Sprawdź narzędzia (date, write_file test, execute_code test)
2. `ls /home/ubuntu/terra-os/` — sprawdź co jest
3. `cat package.json` — sprawdź dependencies
4. `npm install && npm run build` — build musi przejść (exit 0)

### Faza 1: Core Types & Store (30 min)
**Stwórz:**
- `src/types.ts` — `Tender`, `Survey`, `Quote`, `Decision`, `ModuleKey`, `AppState`
- `src/store/useStore.ts` — Zustand store z: `currentModule`, `setCurrentModule()`, `tenders[]`, `addTender()`, `quotes[]`, `decisions[]`
- `src/data/mock.ts` — 3 fake tendery, 5 pozycji kosztorysowych, 3 rekomendacje

### Faza 2: Layout & Pages (45 min)
**Stwórz:**
- `src/app/layout.tsx` — `Space_Grotesk` + `JetBrains_Mono`, `globals.css` import
- `src/app/globals.css` — `@tailwind base/components/utilities`, CSS vars, `.card`, `.btn-primary`, `.badge-*`
- `src/app/page.tsx` — `useState showApp`, `AnimatePresence`, renderuje `OpeningView` lub `AppLayout`
- `src/components/AppLayout.tsx` — `<Sidebar />` + `<main>` z dynamiczną stroną
- `src/components/Sidebar.tsx` — logo + 4 przyciski (Map/Calculator/Flag/Brain) + user section + mobile toggle

### Faza 3: OpeningView (30 min)
**Stwórz:**
- `src/components/OpeningView.tsx` — animowany SVG/shape "Łopaty", tekst "Terra.OS" + "System Zarządzania Ziemią", tooltipy na 3 częściach, przycisk "Uruchom system" → `setShowApp(true)`

### Faza 4: Moduły (90 min)
**Stwórz 5 plików w `src/components/pages/`:**

1. **DashboardPage.tsx** — 4 karty modułów (nazwa, ikona, opis, status badge), sekcja "Ostatnie aktywności" (timeline), metryki (#tenderów, #aktów, #decyzji)
2. **ZwiadPage.tsx** — formularz (lokacja, pow. m², typ gruntu, dostępność, koszt), mock lista 3 tenderów, walidacja + zapis do store
3. **KosztorysPage.tsx** — tabela pozycji (nazwa, jednostka, ilość, cena, suma), podsumowanie (netto, VAT 23%, brutto), pie chart Recharts
4. **SilnikPage.tsx** — progress bar (animacja 3s), 3 rekomendacje (✅/⚠️/❌), przycisk "Przekazaj do Decyzji"
5. **DecyzjaPage.tsx** — podsumowanie lokalizacja/pow./koszt/rekomendacje, przyciski "Akceptuję" (zielony) + "Odrzucam" (czerwony), toast po akceptacji

### Faza 5: Polish & Assets (30 min)
1. `mkdir -p /home/ubuntu/terra-os/public/assets`
2. `python3 /home/ubuntu/terra-os/scripts/generate_assets.py` — generuje logo + 4 ikony SVG
3. Dodaj favicon + meta tags w `layout.tsx`
4. Dodaj toast notifications (custom component lub react-hot-toast)
5. Sprawdź responsive na mobile (hamburger, spacing)

### Faza 6: Final Build & Push (30 min)
1. `npm run build` — musi wyjść exit 0
2. `cd /home/ubuntu/terra-os && git add . && git commit -m "feat: Terra.OS MVP v2 — 4 moduły, layout, assets"`
3. `git push origin main` na `qa10devteam/terra-os`

---

## ✅ KRYTERIA SUKCESU

- [ ] `npm run build` → exit 0 (brak błędów TS/CSS/imports)
- [ ] `http://localhost:3000` → OpeningView z animacją
- [ ] Kliknięcie "Uruchom" → płynne przejście do AppLayout
- [ ] Sidebar → kliknięcie modułu zmienia widok + highlight
- [ ] Dashboard → 4 karty + metryki + timeline
- [ ] ZWIAD → formularz + mock dane + zapis do store
- [ ] Kosztorys → tabela + podsumowanie + wykres
- [ ] Silnik → progress bar + rekomendacje
- [ ] Decyzja → podsumowanie + przyciski + toast
- [ ] Brak błędów w konsoli (browser + terminal)
- [ ] `git log` → 1 commit z 15+ zmian
- [ ] `git push origin main` → sukces

---

## 🚫 Czego NIE robić

- NIE modyfikuj `/home/ubuntu/freecodecamp/` — tylko reference
- NIE używaj `any` w TypeScript — strict mode
- NIE dodawaj backendu — wszystko mock/local
- NIE pushuj dopóki build nie przechodzi
- NIE pomijaj weryfikacji narzędzi na start

---

## 📝 UWAGI DODATKOWE

- **freeCodeCamp** jest jako reference na `/home/ubuntu/freecodecamp` — nie jest częścią Terra.OS
- **Skill GPT-Image-2** jest gotowy (`gpt-image-2-prompting`) — do generowania assetów wizualnych
- **Skrypty Python** (`svg_converter.py`, `generate_assets.py`) są w `scripts/`
- Wszystkie dane są mock/fake — nie potrzebujesz API
- Deployment Vercel wymaga ręcznego `vercel login` — nie jest w scope MVP

---

**Plan V2.0 | QA10 | Terra.OS MVP**
