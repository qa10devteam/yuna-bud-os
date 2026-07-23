# YU-NA / BudOS Frontend — 4 Fazy Roadmap
*800 sprintów (4×200) · iteracyjne dopieszczanie · commit po każdej grupie*

---

## KONTEKST I ZASADY NIEZMIENNE

```
Strony w scope:
  /            → (marketing)/page.tsx         — YU-NA LIGHT theme
  /budos       → (marketing)/budos/page.tsx   — BudOS DARK theme  
  /app         → app/app/page.tsx             — YU-NA Hub LIGHT theme
  /app/*       → NIE DOTYKAĆ (BudOS shell)

Loga:
  YU-NA  → /brand/01-logo-concept.png
  BudOS  → /brand/B01-app-icon-budos.png

Screenshoty live:
  /brand/live-zwiad.png
  /brand/live-kosztorys.png
  /brand/live-silnik.png
  /brand/live-dashboard.png

Token system:
  Każda strona ma const T = { ... } na górze pliku — zero inline hex poza T.
  YU-NA T.bg0 = #f7f9fc (light). BudOS bg = #07070d (dark).

Hallmark doctrine (NIGDY nie łamać):
  N5 Sparse nav pill (nie topbar)
  58/42 hero bias LEFT
  Bez icon-above cards
  Bez blur orbs
  Bez invented metrics (zero % bez danych z API lub — )
  Ft5 Statement footer

Dev server: localhost:3001
Backend:    localhost:8000
Branch:     main
```

---

## FAZA 1 — FUNDAMENT (Sprint 1–200)
*Cel: każda strona ma prawidłową strukturę, token system, branding, i zero Hallmark violations.*

### § 1A — YU-NA Landing `/` — Struktura i tokeny (Sprint 1–30)

```
[ S01 ] Audit token T w (marketing)/page.tsx — każda wartość musi być w T.*
          Szukaj: grep "oklch\|#[0-9a-f]\{3,6\}" page.tsx → 0 wyników poza T definicją
[ S02 ] T.serif = DM Serif Display — upewnij się że jest importowany w layout.tsx
          Sprawdź: src/app/(marketing)/layout.tsx lub src/app/layout.tsx → font-dm-serif
[ S03 ] Nav pill — weryfikacja N5: pill nie topbar, max 3 linki, "Zaloguj" + "Zacznij" CTA
          Plik: (marketing)/page.tsx ~L240 NavRow
[ S04 ] Nav: YU-NA logo 01-logo-concept.png, alt="YU-NA", width=26 height=26
[ S05 ] Nav: Zaloguj → /login, Zacznij → /signup — sprawdź href
[ S06 ] Nav: sticky top-0, z-50, background rgba(255,255,255,0.88) blur(24px) — weryfikacja
[ S07 ] Hero left (58%): headline DM Serif Display, min-fontSize 48px desktop / 36px mobile
[ S08 ] Hero left: subline Space Grotesk 16px T.muted — max 2 linie
[ S09 ] Hero left: CTA pair — primary filled (T.accent) + ghost (outline T.edge0)
[ S10 ] Hero left: social proof strip — "Bez karty kredytowej · 14 dni za darmo"
[ S11 ] Hero right (42%): DataPanel — biały kard, border T.edge0, borderRadius 20, shadow
[ S12 ] DataPanel header: "LIVE" badge + "Aktywne przetargi" label + sync indicator "15 min"
[ S13 ] DataPanel body: 3 metryki z JetBrains Mono — 1 626 / 1.4 mln / 9 913
[ S14 ] DataPanel labels: "przetargów w BZP" / "wartość w tym tygodniu" / "historycznych" 
[ S15 ] DataPanel tenders list: 3 wiersze z ScoreBadge + title + PLN value + status
[ S16 ] ScoreBadge: ≥80 green, 65–79 amber, <65 edge0/muted — zero T.faint na jasnym tle
[ S17 ] TENDERS mock data — frozen values (nie losowe): 87/74/51 scores, tytuły prawdziwe
[ S18 ] Stat strip pod hero: 3 pillary oddzielone dividerami — "1 626 przetargów" itp.
[ S19 ] Stat strip: wartości JetBrains Mono, labels Space Grotesk uppercase 10px 0.1em
[ S20 ] Sekcja "Jeden ekosystem. Trzy produkty." — H2 DM Serif Display 38px
[ S21 ] Bento grid: Bud.OS karta duża (span 2 cols lg), Infra.OS + Dev.OS małe
[ S22 ] Bud.OS karta: name "Bud.OS" widoczny (NIE chowany), opis 2 zdania, CTA
[ S23 ] Bud.OS karta: browser chrome mock z live-zwiad.png wewnątrz
          <div chrome> → <Image src="/brand/live-zwiad.png" ... />
[ S24 ] Infra.OS karta: icon (Hexagon lucide), name, opis 1 zdanie, "Wkrótce" badge
[ S25 ] Dev.OS karta: icon (Code2 lucide), name, opis 1 zdanie, "Wkrótce" badge
[ S26 ] "Od danych do decyzji" sekcja: 3 kroki — nie ikony nad kartami, inline numeracja
[ S27 ] Krok 1/2/3: JetBrains Mono numery "01" / "02" / "03", nagłówek, opis
[ S28 ] CTA sekcja: "Gotowy na przewagę?" — H2 DM Serif, subline, 2 buttony
[ S29 ] Footer Ft5: © YU-NA Intelligence 2026, 3 linki (Regulamin/Prywatność/RODO), brand mark
[ S30 ] TS check: npx tsc --noEmit → exit 0 → git commit "feat(landing/f1): structure audit"
```

### § 1B — BudOS Landing `/budos` — Token audit + hero (Sprint 31–70)

```
[ S31 ] Audit token system w budos/page.tsx — stwórz const T dark jeśli brak
          T.bg0 = '#07070d', T.bg1 = '#0d0d16', T.accent = '#10b981' itp.
[ S32 ] Wszystkie kolory przez T.* — zero inline hex
[ S33 ] Body background: (marketing)/layout.tsx już ma transparent — budos bg0 ustawiony
          na root div background: T.bg0 → sprawdź czy nie ma ciemnego artefaktu
[ S34 ] Nav BudOS: pill N5, tło rgba(7,7,13,0.85) blur(24px), border T.edge0
[ S35 ] Nav BudOS: logo B01-app-icon-budos.png 26×26, "BudOS" text, Zaloguj + Zacznij
[ S36 ] Hero BudOS: H1 DM Serif Display, kolor T.ink (jasny na ciemnym), 52px desktop
[ S37 ] Hero: headline "Twoja przewaga w przetargach." — weryfikacja tekstu i size
[ S38 ] Hero: subline ≤2 linie, T.muted jasny-grey, 16px Space Grotesk
[ S39 ] Hero: CTA primary T.accent (green) filled + ghost border T.edge0
[ S40 ] Hero right 42%: live-dashboard.png w browser chrome mock
          div chrome: T.bg1 background, T.edge0 border, dots indicator (3 kółka)
[ S41 ] Chrome mock: padding 12px top (chrome bar), borderRadius 12, overflow hidden
[ S42 ] live-dashboard.png: Image fill objectFit="cover", priority, alt="BudOS Dashboard"
[ S43 ] Sekcja modułów: "Zwiad / Silnik / Kosztorys" — 3 karty T.bg1 border T.edge0
[ S44 ] Karta Zwiad: Satellite icon T.accent, "Zwiad Przetargowy" H3, opis, feature list
[ S45 ] Karta Zwiad: screenshot live-zwiad.png w karcie (small mockup 200px high)
[ S46 ] Karta Silnik: Brain icon, "Silnik Decyzyjny AI", GO/NO-GO badge demo
[ S47 ] Karta Silnik: live-silnik.png screenshot w karcie
[ S48 ] Karta Kosztorys: Calculator icon, "Kosztorys AI", opis, live-kosztorys.png
[ S49 ] FAQ sekcja (istniejąca) — weryfikacja Accordion działania, T.bg1/T.bg2 kolory
[ S50 ] FAQ: ChevronDown animation — rotate 180° on open
[ S51 ] Footer BudOS Ft5: copyright, linki, logo mark BudOS
[ S52 ] Pricing sekcja (jeśli istnieje) — sprawdź czy jest, jeśli tak — audit cen
[ S53 ] Testimonials / social proof — jeśli placeholder → usuń lub zamień na `—`
[ S54 ] "Jak to działa" sekcja: 3 kroki inline numerowane (bez icon-above)
[ S55 ] CTA section bottom: "Zacznij za darmo" button T.accent, subline no-card/14days
[ S56 ] motion.div w budos: sprawdź czy Framer Motion działa (brak Cloudflare tunnel)
[ S57 ] Jeśli motion nie działa → CSS keyframes fallback (jak w globals.css)
[ S58 ] scroll-triggered reveals: useInView z motion/react zamiast useScroll
[ S59 ] TS check budos/page.tsx → exit 0
[ S60 ] commit "feat(budos/f1): token audit + hero structure + module cards"
```

### § 1C — YU-NA Hub `/app` — Struktura i baseline (Sprint 71–120)

```
[ S71 ] Audit app/app/page.tsx — token system: Tailwind classes OK lub inline T?
[ S72 ] Hub background: '#f8f9fb' dot grid — weryfikacja wyglądu (nie ciemny)
[ S73 ] Nav hub: sticky, white/90 backdrop, YU-NA logo, user avatar initials, logout
[ S74 ] Nav hub: aktywny user firstName w "Witaj, {firstName}" — real ze store
[ S75 ] Welcome row: "Witaj, {firstName}. Oto Twój hub." — H1 Tailwind text-2xl font-semibold
[ S76 ] Welcome row: data dzisiejsza po prawej — new Date().toLocaleDateString('pl-PL')
[ S77 ] Bud.OS hero card: karta pełna szerokość, dark bg (#07070d lub T.accent sub)
[ S78 ] Bud.OS hero card: logo B01-app-icon-budos.png, nazwa "Bud.OS", opis 1 zdanie
[ S79 ] Bud.OS hero card: screenshot live-dashboard.png prawa strona (40% width)
[ S80 ] Bud.OS hero card: "Otwórz Bud.OS" → href="/app/zwiad" button T.accent
[ S81 ] Bud.OS hero card: 3 metryki z API lub — (NIE invented values)
          GET /api/tenders?limit=1 → count field lub — jeśli error
[ S82 ] Metryki: "Aktywne przetargi" z backend, "Twoje przetargi" z backend, "Alerty" z backend
[ S83 ] Fetch metryki pattern: useEffect → fetch('/api/...') → useState({loaded: false, val: '—'})
[ S84 ] Loading state: skeleton shimmer dla liczb (bg-zinc-100 animate-pulse)
[ S85 ] Infra.OS karta: icon Hexagon, "Infra.OS", "Wkrótce" badge amber, opis
[ S86 ] Dev.OS karta: icon Code2, "Dev.OS", "Wkrótce" badge amber, opis
[ S87 ] Grid: 3 karty (Bud.OS full-width top, Infra+Dev row below) lub 2+2 layout
[ S88 ] Quick actions row: "Nowy przetarg", "Moje zakładki", "Raporty" — linki z ikonami
[ S89 ] Quick actions: aktywne href → /app/zwiad, /app/bookmarks, /app/reports
[ S90 ] Recent activity section: ostatnie 3 przetargi z /api/tenders?limit=3&sort=recent
[ S91 ] Recent activity: jeśli 0 wyników → empty state "Zacznij od Zwiad Przetargowy →"
[ S92 ] Auth gate: if (!hydrated || !isAuth) → spinner zamiast null (UX)
[ S93 ] Logout button: clearAuth() + router.replace('/login') — weryfikacja
[ S94 ] Mobile responsiveness nav: hamburger lub kompaktowy pill na <640px
[ S95 ] Hub: brak BudOS ciemnego sidebar — weryfikacja pathname === '/app' exact match
          app/layout.tsx: pathname === '/app' → no shell (już zaimplementowane)
[ S96 ] Hallmark check hub: brak invented metrics ✓, widoczne nazwy produktów ✓
[ S97 ] TS check app/page.tsx → exit 0
[ S98 ] commit "feat(hub/f1): welcome row + metrics from API + product cards"
```

### § 1D — Cross-cutting: fonts, globals, layout (Sprint 121–150)

```
[ S121 ] layout.tsx root: DM Serif Display import i definicja jako --font-dm-serif
[ S122 ] layout.tsx root: Space Grotesk + JetBrains Mono — sprawdź czy oba są
[ S123 ] globals.css: nie ma konfliktu color-scheme: dark dla marketing group
[ S124 ] (marketing)/layout.tsx: body transparent + color-scheme: light explicit
[ S125 ] Sprawdź font-dm-serif jest używany w heading elementach (font-family: T.serif)
[ S126 ] next.config.mjs: images.domains lub remotePatterns poprawne dla /brand/*
[ S127 ] next.config.mjs: unoptimized: false — lokalne /brand/ są static, NIE remote
[ S128 ] public/brand/ — weryfikacja że wszystkie live-*.png istnieją i nie są 0 bytes
          ls -la /public/brand/live-*.png
[ S129 ] Favicon: /brand/10-favicon.png → link rel=icon w layout.tsx <head>
[ S130 ] OG meta: layout.tsx lub page.tsx generateMetadata → title, description, og:image
[ S131 ] Landing og:image → /brand/05-og-social.png
[ S132 ] BudOS og:image → /brand/B04-og-dark.png
[ S133 ] Hub og:image → /brand/04-dashboard-mockup.png
[ S134 ] Responsive breakpoints: sm(640) md(768) lg(1024) xl(1280) — sprawdź czy hero 58/42 łamie się na mobile
[ S135 ] Mobile hero: poniżej md → stack (left 100% top, right 100% bottom), nie side-by-side
[ S136 ] Mobile nav pill: compact — tylko logo + CTA "Zacznij", Zaloguj schowany
[ S137 ] Mobile fonts: H1 clamp(32px, 5vw, 56px) — nie fix 48px bo overflow na małych
[ S138 ] Viewport meta: <meta name="viewport" content="width=device-width, initial-scale=1">
[ S139 ] Sprawdź all pages brak overflow-x na mobile (body overflow-x: hidden w globals)
[ S140 ] TS check --noEmit dla całego projektu → exit 0
[ S141 ] commit "feat(globals/f1): fonts, OG meta, responsive foundations"
```

### § 1E — Hallmark final sweep Faza 1 (Sprint 151–200)

```
[ S151 ] Landing: brak blur-orb (radial-gradient dekoracyjny) w hero background
[ S152 ] Landing: brak generic "Trusted by X companies" bez danych
[ S153 ] Landing: brak "Revolutionary", "Seamless", "Powerful" w copy
[ S154 ] Landing: hero headline ≤ 8 słów — "Przetargi budowlane. Opanowane." ✓
[ S155 ] Landing: sekcja produktów — nazwy widoczne (Bud.OS, Infra.OS, Dev.OS), nie blur
[ S156 ] BudOS: brak "99.9% uptime" lub innych invented SLA metrics
[ S157 ] BudOS: brak placeholderów "Lorem ipsum" lub "Coming soon" na primarych treściach
[ S158 ] Hub: metryki real lub —, nigdy % bez źródła
[ S159 ] Hub: brak "See all" lub "View more" bez docelowego href
[ S160 ] Hub: każdy CTA button ma href lub onClick — brak dead buttons
[ S161 ] Landing: Ft5 footer — company mark "YU-NA Intelligence", rok 2026, ≥3 linki legal
[ S162 ] BudOS: Ft5 footer analogiczny — "BudOS by YU-NA Intelligence"
[ S163 ] Hub: footer nie potrzebny (app shell), ale upewnij się brak floating orphan text
[ S164 ] Accessibility: wszystkie Image mają alt (nie pusty)
[ S165 ] Accessibility: Link mają widoczne focus ring (focus-visible:ring-2)
[ S166 ] Accessibility: kontrast headline na tle ≥ 4.5:1 (sprawdź: #0c1524 na #f7f9fc)
[ S167 ] Accessibility: kontrast BudOS headline na dark bg ≥ 4.5:1
[ S168 ] Accessibility: przyciski mają aria-label gdy ikona-only
[ S169 ] Loading: żadna strona nie ma białego flash przy pierwszym load (body bg transparent OK)
[ S170 ] SEO: każda strona ma <title> unikalny
[ S171 ] SEO: meta description ≤ 160 znaków, zawiera główne keyword
[ S172 ] Canonical URL: sprawdź brak duplicate content /en/ lub /pl/ variants
[ S173 ] Console errors: otwórz każdą stronę, sprawdź devtools → 0 JS errors
[ S174 ] Landing: upewnij się że (marketing)/layout.tsx body transparent działa
          console: document.body.style.backgroundColor = '' (transparent, nie #050508)
[ S175 ] Visual check landing: Playwright screenshot pełna strona → jasne tło ✓
[ S176 ] Visual check budos: Playwright screenshot → ciemne tło #07070d ✓
[ S177 ] Visual check hub: Playwright screenshot → light bg #f8f9fb ✓
[ S178 ] Commit: "feat(hallmark/f1): sweep — a11y, SEO, zero invented metrics"
[ S179 ] Git tag: v1.0-faza1-done
[ S180 ] Push origin main
[ S181–200 ] Buffer — naprawianie błędów znalezionych w sweep
```

---

## FAZA 2 — TREŚĆ I DANE (Sprint 201–400)
*Cel: real screenshots w każdym miejscu, live data z API, copy dopracowane do B2B precision.*

### § 2A — Hero mockupy live (Sprint 201–240)

```
[ S201 ] Landing hero right — DataPanel: połącz z /api/tenders (GET, bearer token jeśli potrzebny)
          Response: { total: number, thisWeek: number, total_value: number }
          Fallback: { total: 1626, thisWeek: 9913, total_value: 1400000 } (hardcoded OK dla MVP)
[ S202 ] DataPanel: refactor TENDERS mock → fetch /api/tenders?limit=3&sort=score&go=true
          Jeśli API error → pokaż mock TENDERS (frozen values)
[ S203 ] DataPanel LIVE indicator: blinking dot animation
          CSS: @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
[ S204 ] DataPanel: "sync co 15 min" → dynamiczna godzina ostatniej synchronizacji
          Format: "sync 14:32" z getHours():getMinutes()
[ S205 ] Landing hero: dodaj "04-dashboard-mockup.png" jako tło hero left (bardzo lekki, opacity 0.04)
          background-image + bg-blend-mode = cichy "data feel" bez literal screenshot
[ S206 ] Browser chrome mock w Bud.OS karcie: 3 kółka (red #ef4444, yellow #f59e0b, green #10b981)
          div 8px×8px rounded-full, gap 6px, padding 8px 12px
[ S207 ] Bud.OS karta w landing: live-zwiad.png → Image fill, objectFit cover
          Sprawdź że plik istnieje: ls /home/ubuntu/terra-os/apps/ui/public/brand/live-zwiad.png
[ S208 ] BudOS landing hero: live-dashboard.png w chrome mock — priority load
[ S209 ] Karta Silnik: live-silnik.png, karta Kosztorys: live-kosztorys.png — verify paths
[ S210 ] Playwright screenshot po każdej zmianie: sprawdź czy screenshot się wyświetla
          python3 -c "from playwright.sync_api import sync_playwright; ..."
[ S211 ] Wszystkie Image next.js: sprawdź sizes prop dla responsywności
          sizes="(max-width: 768px) 100vw, 50vw"
[ S212 ] Lazy loading: Image priority tylko dla hero (above the fold), reszta lazy (domyślne)
[ S213 ] Hub Bud.OS card: live-dashboard.png — Image fill right side 40% width
          wrapper: position relative, height 180px, overflow hidden
[ S214 ] Hub karta: live-dashboard.png z overlay gradient (right fade: transparent → bg-card)
          gradient: linear-gradient(to right, T.bg-card 20%, transparent)
[ S215 ] commit "feat(screenshots/f2): live mockups in all hero + card positions"
```

### § 2B — API data integration (Sprint 241–280)

```
[ S241 ] Hub: fetch /api/tenders/stats → { active: number, thisWeek: number, myTenders: number }
          API endpoint: backend port 8000 — sprawdź czy istnieje
[ S242 ] Jeśli /api/tenders/stats nie istnieje → fetch /api/tenders?limit=1 i extract total z headers
[ S243 ] Hub metryki pattern:
          const [stats, setStats] = useState<{active:'—', week:'—', mine:'—'}>
          useEffect: fetch → setStats lub setStats({active:'—',...}) on error
[ S244 ] Hub: metryki render z JetBrains Mono, fallback '—' widoczne (nie spinner na zawsze)
[ S245 ] Timeout 3s dla fetch — AbortController pattern
[ S246 ] Hub: recent tenders list → /api/tenders?limit=3&sort=-created_at
          Render: 3 wiersze z title + value + statusBadge (GO/WAIT/NO-GO)
[ S247 ] Hub recent: empty state jeśli brak danych — "Zacznij od Zwiad →" link /app/zwiad
[ S248 ] Hub recent: skeleton loading 3 rows (animate-pulse bg-zinc-100 h-12 rounded-lg)
[ S249 ] DataPanel w landing: /api/tenders?limit=3&sort=-score (top przetargi)
          Render: mock frozen jeśli unauthenticated (landing = public)
[ S250 ] Landing jest PUBLIC — NIE fetch secured endpoints. Frozen mock data jest OK i preferred.
[ S251 ] Stat strip landing: frozen values "1 626 · 1.4 mln · 9 913" — nie fetch (public page)
[ S252 ] BudOS /budos jest PUBLIC — frozen mock OK. Brak fetch.
[ S253 ] commit "feat(api/f2): hub live data + fallback pattern"
```

### § 2C — Copy dopracowanie (Sprint 281–320)

```
[ S281 ] Landing headline: "Przetargi budowlane. Opanowane." — weryfikacja, nic nie zmieniac
[ S282 ] Landing subline: "Analizuje BZP i TED, ocenia szanse i generuje kosztorysy.
          Decyzja GO/NO-GO w minuty — nie dni." — max 2 linie, weryfikacja treści
[ S283 ] Landing: CTA primary "Zacznij za darmo" — NIE "Demo", NIE "Sprawdź"
[ S284 ] Landing: CTA ghost "Poznaj Bud.OS" → href="/budos"
[ S285 ] Landing sekcja produktów intro: "100% danych zamiast domysłów na każdym etapie."
[ S286 ] Bud.OS karta opis: "Monitor BZP i TED, AI engine GO/NO-GO, kosztorys ICB — jeden system."
[ S287 ] Infra.OS opis: "Infrastruktura danych dla firm inżynieryjnych. Zarządzanie zasobami, BIM-ready."
[ S288 ] Dev.OS opis: "SDK i webhooks do integracji z własnymi systemami ERP / CRM."
[ S289 ] "Od danych do decyzji" kroki:
          01 → "Monitoring" — BZP i TED skanowane co 15 minut, 100% coverage
          02 → "Analiza" — AI czyta SWZ, ocenia ryzyko, wydaje werdykt GO/NO-GO
          03 → "Decyzja" — Kosztorys w minuty. Oferta złożona. Przetarg wygrany.
[ S290 ] CTA sekcja: "Gotowy na przewagę?" + subline "Dołącz do firm które wygrywają więcej."
          NIE "Join thousands of companies" (invented)
[ S291 ] BudOS headline: "Twoja przewaga w przetargach." — weryfikacja
[ S292 ] BudOS subline: "Zwiad przetargowy, analiza AI i kosztorys w jednym narzędziu."
[ S293 ] BudOS pillar Zwiad: "Monitoring BZP i TED w czasie rzeczywistym. AI dopasowuje
          ogłoszenia do Twojego profilu." — weryfikacja
[ S294 ] BudOS pillar Silnik: "Pełna analiza SWZ w 30 sekund. GO/NO-GO z uzasadnieniem
          i listą ryzyk." — weryfikacja
[ S295 ] BudOS pillar Kosztorys: "Automatyczna wycena z dokumentacji SWZ.
          Format ATH/PDF, baza materiałów." — weryfikacja
[ S296 ] BudOS FAQ: min 4 pytania. Sugerowane:
          "Czy BudOS działa z TED (UE)?" → Tak, BZP + TED Official Journal
          "Jak szybko AI ocenia przetarg?" → 30-60 sekund po wczytaniu SWZ
          "Czy mogę eksportować kosztorys do ATH?" → Tak, format ATH i PDF
          "Co to jest GO/NO-GO?" → Decyzja AI: czy warto złożyć ofertę
[ S297 ] Hub welcome: "Witaj, {firstName}. Twój pulpit." — NIE "Hey!", NIE emoji
[ S298 ] Hub Bud.OS card: "Bud.OS Intelligence — Twoje narzędzie przetargowe"
[ S299 ] Hub empty state (brak przetargów): "Zacznij od zwiadowania rynku →" CTA
[ S300 ] commit "fix(copy/f2): B2B precision copy na wszystkich 3 stronach"
```

### § 2D — Responsywność (Sprint 321–370)

```
[ S321 ] Landing hero: poniżej 768px → flexDirection column, left 100%, right 100%
[ S322 ] Landing hero right (DataPanel): na mobile max-height 280px, scroll inside
[ S323 ] Landing nav pill: na mobile max-width 100% minus 2×16px margin
[ S324 ] Landing produkty bento: na mobile → 1 kolumna (Bud.OS full, Infra, Dev osobno)
[ S325 ] Landing krokit "Od danych do decyzji": na mobile → vertical stack zamiast row
[ S326 ] Landing stat strip: na mobile → 2 kolumny (1626 / 1.4mln w row 1, 9913 w row 2)
[ S327 ] BudOS hero: poniżej 768px → stack, chrome mock poniżej headline
[ S328 ] BudOS chrome mock: na mobile height 200px, full width
[ S329 ] BudOS module cards: na mobile → 1 kolumna
[ S330 ] BudOS FAQ: na mobile accordion działa dotykiem (tapTarget min 44px)
[ S331 ] Hub: 3 product karty na mobile → 1 kolumna, Bud.OS first
[ S332 ] Hub quick actions: na mobile → 2 kolumny (3→2 wrap)
[ S333 ] Hub recent list: na mobile → card per tender zamiast table row
[ S334 ] Sprawdź viewport 375px, 414px, 768px, 1024px, 1280px dla każdej strony
[ S335 ] Playwright mobile screenshots: viewport {width:390, height:844}
[ S336 ] commit "feat(responsive/f2): mobile-first corrections na wszystkich 3 stronach"
```

### § 2E — Polish detale Faza 2 (Sprint 371–400)

```
[ S371 ] Landing: ScoreBadge color: 87=green T.accent, 74=amber, 51=edge0+muted — weryfikacja
[ S372 ] Landing: status badge "GO" = T.accentSub bg + T.accent text, "WAIT" = edge0 + muted
[ S373 ] DataPanel tender row: hover state → T.bg2 background transition 150ms
[ S374 ] Nav pill: aktywny link (pathname match) → T.ink bold, reszta T.muted
[ S375 ] Nav pill: smooth shadow-sm pojawiający się po scroll > 10px
          useEffect + addEventListener scroll → setShadow(window.scrollY > 10)
[ S376 ] BudOS karta feature list: checkmark icons T.accent, text T.muted 14px
[ S377 ] BudOS FAQ: płynne expand/collapse z max-height transition (nie jump)
[ S378 ] Hub Bud.OS card: gradient overlay żeby tekst na screenshocie był czytelny
[ S379 ] Hub: loading skeleton → wymień animate-pulse na shimmer gradient animation
[ S380 ] Hub: produkty "Wkrótce" badge — amber-100 bg, amber-700 text, nie neon
[ S381 ] Landing footer: wyśrodkowany, text T.muted 13px, linki T.faint → hover T.muted
[ S382 ] BudOS footer: analogiczny na dark bg — text T.muted (dark-variant), border T.edge0
[ S383 ] Scrollbar: globals.css ma custom scrollbar — weryfikacja że marketing pages nie nadpisują
[ S384 ] Print media: @media print → hide nav, hide CTA, expand content — opcjonalne
[ S385 ] TS check pełny projekt → exit 0
[ S386 ] Playwright full-page screenshots (1280px): landing, budos, hub — zapisz do /tmp/
[ S387 ] visual diff: porównaj z poprzednim commitem (opcjonalne)
[ S388 ] git tag v2.0-faza2-done
[ S389 ] git push origin main
[ S390–400 ] Buffer fixes
```

---

## FAZA 3 — MOTION I GŁĘBIA (Sprint 401–600)
*Cel: MOTION:5 (restrained) — scroll reveals, micro-interactions, depth bez performativity.*

### § 3A — Scroll reveals (Sprint 401–440)

```
[ S401 ] Zasada: MOTION:5 = subtelne, functional, reduced-motion aware
          Każda animacja musi mieć reduce = useReducedMotion() → skip
[ S402 ] Wzorzec scroll reveal dla wszystkich sekcji:
          motion.div initial={{opacity:0, y:24}} whileInView={{opacity:1,y:0}}
          transition={{duration:0.45, ease:[0.16,1,0.3,1]}} viewport={{once:true,amount:0.2}}
[ S403 ] Landing sekcja produktów: reveal przy wejściu w viewport
[ S404 ] Landing krokit: każdy krok reveal z delay 0.1s stagger
[ S405 ] Landing CTA sekcja: reveal z y:16 (nie 24 — mniej dramatyczne)
[ S406 ] Landing stat strip: counter animation dla liczb (1626 count up od 0 w 0.8s)
          Warunek: tylko jeśli !reduce
[ S407 ] BudOS pillary: stagger reveal 0.1s między kartami
[ S408 ] BudOS hero chrome mock: parallax lekki → useScroll + useTransform y: [0,100] → [0, -15]
          Tylko na desktop (md+), reduce=skip
[ S409 ] BudOS FAQ: accordion max-height animacja (AnimatePresence + motion.div)
[ S410 ] Hub product cards: reveal z stagger przy mount (nie scroll — są above fold)
[ S411 ] Hub recent list: fade-in stagger 0.08s per row
[ S412 ] Hub metryki loading → reveal animacja gdy dane załadowane (opacity 0→1, y 8→0)
[ S413 ] Nav pill drop-shadow: motion.div animate shadow opacity na scroll
[ S414 ] Commit "feat(motion/f3): scroll reveals + stagger + counter animation"
```

### § 3B — Micro-interactions (Sprint 441–480)

```
[ S441 ] Primary button (PrimaryButton): hover scale 1.02 + shadow intensify — motion.a
[ S442 ] Ghost button: hover bg T.accentSub fill-in transition 200ms
[ S443 ] Nav links: underline grow from center (pseudo ::after scaleX)
[ S444 ] DataPanel tender rows: hover translateX(4px) + bg T.bg2 → 150ms ease
[ S445 ] ScoreBadge: hover scale(1.08) z transition
[ S446 ] Bud.OS karta landing: hover → screenshot scale 1.02 (zoom effect, overflow hidden)
[ S447 ] Infra.OS / Dev.OS karty: hover → border-color T.accent transition 200ms
[ S448 ] BudOS pillar karty: hover → glow T.accentBrd shadow (nie blur orb — element shadow)
          box-shadow: 0 0 24px T.accentBrd — na hover, 0s → transition
[ S449 ] FAQ accordion: ChevronDown rotate 180deg transition 200ms
[ S450 ] Hub product cards: hover → slight elevation shadow + border T.accent
[ S451 ] Hub quick actions: hover → bg fill + icon translate(2,0)
[ S452 ] Hub Bud.OS card: hover → screenshot scale 1.01 (subtle, overflow hidden)
[ S453 ] "GO" badge: subtle pulse animation 2s infinite na hub recent list
          @keyframes pulse-go { 0%,100%{box-shadow:0 0 0 0 T.accentBrd} 50%{box-shadow:0 0 0 4px transparent} }
[ S454 ] LIVE dot w DataPanel: blink animation (opacity 1→0.3→1, 1.5s infinite)
[ S455 ] commit "feat(interactions/f3): micro-interactions na wszystkich elementach"
```

### § 3C — Typografia i spacing precision (Sprint 481–530)

```
[ S481 ] Type scale audit — wszystkie strony:
          Display: DM Serif Display 56/48/40px (xl/lg/md)
          H2: DM Serif 38/32px
          H3: Space Grotesk 700 22/18px
          Body: Space Grotesk 400 16/15px
          Small: Space Grotesk 500 13/12px
          Mono: JetBrains Mono 500 — WYŁĄCZNIE dla liczb i kodu
[ S482 ] Landing H1 clamp: font-size: clamp(36px, 4.5vw, 56px)
[ S483 ] BudOS H1 clamp: analogiczne clamp
[ S484 ] Hub H1: 24px semi — nie DM Serif (app, nie marketing)
[ S485 ] Line-height: headings 1.1-1.15, body 1.6-1.65
[ S486 ] Letter-spacing: headings -0.02em, body 0, mono 0, labels +0.08em uppercase
[ S487 ] Spacing system: 4/8/12/16/24/32/48/64/96px — nie losowe wartości
[ S488 ] Section padding: py-16 (64px) desktop, py-10 (40px) mobile
[ S489 ] Card padding: 24px desktop, 16px mobile
[ S490 ] Nav height: 60px fixed — weryfikacja na wszystkich stronach
[ S491 ] Hero padding-top: 60px (nav height) + 48px content top = 108px total padding-top
[ S492 ] Max-width: 1200px (marketing) / 1024px (hub) — nie 100% fluid
[ S493 ] Gutter: px-6 (24px) mobile, px-8 (32px) desktop — konsystentne
[ S494 ] Sprawdź: brak "dangling" text (ostatnia linia 1 słowo w headline) — adjust clamp
[ S495 ] commit "feat(typography/f3): type scale + spacing precision"
```

### § 3D — Visual depth (Sprint 531–570)

```
[ S531 ] Landing DataPanel: box-shadow wielowarstwowy:
          0 1px 2px rgba(0,0,0,0.04), 0 4px 16px rgba(0,0,0,0.06), 0 16px 48px rgba(0,0,0,0.08)
[ S532 ] Landing bento karty: shadow-sm na default, shadow-md na hover
[ S533 ] BudOS chrome mock: inset shadow góra (border-bottom w chrome bar T.edge0)
[ S534 ] BudOS karty: dark elevated — T.bg1 z T.bg2 hover, border T.edge0
[ S535 ] Hub Bud.OS card: gradient bg — linear-gradient(135deg, #0d0d16 0%, #07070d 100%)
[ S536 ] Hub product grid: subtle grid lines między kartami (divider T.edge0)
[ S537 ] Landing: między sekcjami — subtle hairline divider (1px T.edge0 opacity 0.5)
[ S538 ] Stat strip: tło T.bg1 (white card) z shadow-sm — odróżnienie od hero
[ S539 ] BudOS: hero bg — bardzo delikatny radial gradient (T.bg0 center → T.bg1 edges)
          NIE orb, NIE bloom — tylko subtil vignette
[ S540 ] Sprawdź: żaden element nie ma raw drop-shadow filter (performance) → box-shadow zamiast filter
[ S541 ] commit "feat(depth/f3): multi-layer shadows + depth system"
```

### § 3E — Faza 3 finalizacja (Sprint 571–600)

```
[ S571 ] Performance check: Playwright trace → brak LCP > 2.5s
[ S572 ] Sprawdź bundle size: next build --profile → main chunk ≤ 150kb gzip
[ S573 ] next/image: wszystkie karty z produktami mają sizes prop
[ S574 ] Lazy components: jeśli FAQ jest duże → dynamic import
[ S575 ] Sprawdź: brak unused imports (ESLint no-unused-vars)
[ S576 ] Sprawdź: wszystkie motion.* mają reduce check
[ S577 ] TS check pełny → exit 0
[ S578 ] Playwright full suite: landing, budos, hub → screenshots zapisane
[ S579 ] git tag v3.0-faza3-done
[ S580 ] git push origin main
[ S581–600 ] Buffer
```

---

## FAZA 4 — KONWERSJA I PRODUKCJA (Sprint 601–800)
*Cel: CRO-ready, a11y WCAG AA, Vercel deploy produkcyjny, zero runtime errors.*

### § 4A — CRO (Conversion Rate Optimization) (Sprint 601–640)

```
[ S601 ] Above-fold check: CTA "Zacznij za darmo" musi być visible bez scrollowania (1280px)
[ S602 ] CTA button hierarchy: PRIMARY (filled T.accent) > GHOST (outline) — nigdy 2× primary
[ S603 ] Social proof strip: "Bez karty kredytowej · 14 dni za darmo · Anuluj kiedy chcesz"
          Mały text pod CTA — 12px T.muted
[ S604 ] Urgency / benefit proximate: pod headline dodaj "→ 327 firm korzysta z Bud.OS"
          (lub usuń jeśli brak real data — zero invented)
[ S605 ] Landing: dodaj sekcję "Dla kogo?" (target personas)
          "Właściciel firmy budowlanej · Dyrektor przetargów · Kosztorysant"
          3 ikony, 1 zdanie każde — nie karty, inline pills
[ S606 ] BudOS: pricing sekcja — jeśli brak, dodaj minimalistyczną
          Starter / Professional / Enterprise — 3 tiers, T.accent highlight na middle
[ S607 ] BudOS pricing: ceny Starter = 299 PLN/mies, Pro = 799 PLN/mies, Enterprise = kontakt
          Tylko jeśli są to aktualne ceny — jeśli nie wiadomo → "od 299 PLN/mies"
[ S608 ] BudOS pricing CTA: "Zacznij za darmo" dla Starter, "Skontaktuj się" dla Enterprise
[ S609 ] Anchoring: Professional tier highlighted (border T.accent, "Najpopularniejszy" badge)
[ S610 ] Hub: pusty stan = onboarding CTA — "Skonfiguruj profil firmy →" link /app/settings
[ S611 ] Hub: onboarding progress bar (jeśli user nie skonfigurował) — "Setup 2/4"
[ S612 ] commit "feat(cro/f4): conversion architecture na landing + budos + hub"
```

### § 4B — Accessibility WCAG AA (Sprint 641–680)

```
[ S641 ] Kontrast: wszystkie body text ≥ 4.5:1 (AA), large text ≥ 3:1
          Tool: npx wcag-contrast-checker lub manual check
[ S642 ] T.muted (#5a6d84) na T.bg0 (#f7f9fc): ratio check
          → 5.a6d84 vs f7f9fc → oblicz: jeśli <4.5 → darken to #4a5d72
[ S643 ] T.faint (#8fa0b4) na T.bg0: likely <4.5 → używać TYLKO dla dekoracji, nie tekstu
[ S644 ] BudOS T.muted na dark bg — sprawdź contrast
[ S645 ] Focus rings: wszystkie interaktywne elementy — focus-visible:outline-2 focus-visible:outline-offset-2
[ S646 ] Focus ring color: T.accent na light pages, T.accentDim na dark pages
[ S647 ] Skip-to-content link: <a href="#main" className="sr-only focus:not-sr-only"> — layout.tsx
[ S648 ] Headings hierarchy: H1 → H2 → H3 — brak skipów (nie H1 → H3)
[ S649 ] aria-label na nav: <nav aria-label="Nawigacja główna">
[ S650 ] aria-label na footer: <footer aria-label="Stopka">
[ S651 ] aria-expanded na FAQ accordion: dynamiczne true/false
[ S652 ] role="region" aria-label dla każdej main sekcji landing
[ S653 ] Keyboard navigation: Tab przez wszystkie elementy w logicznej kolejności
[ S654 ] DataPanel tender titles: title= prop na truncated text (tooltip)
[ S655 ] Image alt texts: descriptive (nie "screenshot", nie "image")
          live-zwiad.png → alt="Panel zwiadowania przetargów - lista aktywnych ogłoszeń"
[ S656 ] Playwright accessibility scan: page.accessibility.snapshot() → sprawdź violations
[ S657 ] commit "feat(a11y/f4): WCAG AA compliance — kontrast, focus, aria"
```

### § 4C — Performance (Sprint 681–720)

```
[ S681 ] next build --no-lint → sprawdź warnings (nie errors)
[ S682 ] Bundle analyzer: ANALYZE=true next build → sprawdź chunk breakdown
[ S683 ] Largest chunks: jeśli motion/react > 30kb → tree-shake niepotrzebne exports
[ S684 ] Image optimization: wszystkie brand/*.png — sprawdź rozmiar
          ls -la /public/brand/*.png | awk '{print $5, $9}' | sort -rn | head
[ S685 ] Jeśli live-*.png > 500kb → zoptymalizuj: npx sharp-cli compress
[ S686 ] next/image: automatyczna optymalizacja dla static (nie unoptimized) — verify
[ S687 ] Font loading: display=swap dla DM Serif, Space Grotesk, JetBrains
[ S688 ] FOUC prevention: krytyczny CSS inline dla above-fold tokens
[ S689 ] Preload hero screenshot: <link rel="preload" as="image" href="/brand/live-dashboard.png">
          W odpowiedniej page.tsx generateMetadata lub layout head
[ S690 ] Sprawdź: brak layout shifts (CLS) — statyczne Image width/height zdefiniowane
[ S691 ] DataPanel: brak useEffect na mount bez cleanup (memory leak)
[ S692 ] Hub fetch: brak race condition (AbortController cleanup w useEffect return)
[ S693 ] Memoization: ciężkie komponenty z React.memo jeśli potrzeba
[ S694 ] commit "feat(perf/f4): bundle, image, font optimizations"
```

### § 4D — Produkcja: Vercel deploy (Sprint 721–760)

```
[ S721 ] Vercel project: prj_AUy2fwxTn9cbBbFwfVhlo09NhZ3G (terra-os), team qa10devteams-projects
[ S722 ] NEXT_PUBLIC_API_URL: sprawdź czy ustawione w Vercel jako https://api.yu-na.io
[ S723 ] next build lokalnie: cd /home/ubuntu/terra-os/apps/ui && npm run build → exit 0
[ S724 ] Wszystkie błędy build time naprawić przed deploy
[ S725 ] git push origin main → auto-deploy trigger (GitHub webhook → Vercel)
[ S726 ] Sprawdź Vercel deploy status: curl https://api.vercel.com/v13/deployments?teamId=team_Aq6uSv03E0lkJLes8860KfdN
          Lub: https://vercel.com/qa10devteams-projects/terra-os
[ S727 ] Po deploy: sprawdź https://yu-na.io → landing light theme ✓
[ S728 ] Sprawdź https://yu-na.io/budos → BudOS dark ✓
[ S729 ] Sprawdź https://yu-na.io/app → redirect /login (unauthenticated) ✓
[ S730 ] Sprawdź api.yu-na.io/health → {"status":"ok"} (Caddy → port 8000)
[ S731 ] OG preview: https://www.opengraph.xyz/?url=https://yu-na.io → sprawdź og:image
[ S732 ] Google PageSpeed: https://pagespeed.web.dev/ → yu-na.io → cel ≥ 85 Performance
[ S733 ] Console errors na produkcji: żadne 404 dla /brand/* images
[ S734 ] CORS: api.yu-na.io odpowiada na Origin: https://yu-na.io poprawnie
[ S735 ] commit "chore(deploy/f4): production verification + fixes"
```

### § 4E — Final Polish i bufor (Sprint 761–800)

```
[ S761 ] Landing: przeklikaj wszystkie linki — brak 404, brak broken hrefs
[ S762 ] BudOS: przeklikaj wszystkie linki
[ S763 ] Hub: przeklikaj quick actions — wszystkie prowadzą do istniejących stron
[ S764 ] Mobile manual test na iPhone viewport (390px) — Playwright
[ S765 ] Dark mode OS: sprawdź czy light pages nie łapią system dark mode
          (marketing)/layout.tsx: <meta name="color-scheme" content="light"> 
[ S766 ] BudOS: color-scheme: dark meta
[ S767 ] Print CSS: @media print na landing — ukryj nav, CTA, zachowaj content
[ S768 ] 404 page: not-found.tsx — sprawdź że istnieje i wygląda OK
[ S769 ] error.tsx: sprawdź że istnieje — "Coś poszło nie tak" z linkiem powrotu
[ S770 ] Loading states: żadna strona nie "mignie" białym flashem na reload
[ S771 ] Final TS check: npx tsc --noEmit → exit 0
[ S772 ] Final ESLint: npm run lint → 0 errors
[ S773 ] Playwright final suite: screenshots wszystkich stron desktop+mobile
[ S774 ] git tag v4.0-faza4-done
[ S775 ] git push origin main
[ S776 ] Ostateczny push produkcyjny → https://yu-na.io live ✅
[ S777–800 ] Buffer — hotfixy po deploy
```

---

## EXECUTION ORDER

```
FAZA 1: S01–S200    — Fundament, token system, branding, Hallmark sweep
FAZA 2: S201–S400   — Treść, screenshoty, copy, responsywność
FAZA 3: S401–S600   — Motion, micro-interactions, typografia, głębia
FAZA 4: S601–S800   — CRO, a11y, performance, Vercel production

Commit cadence: co § group (co ~20-30 sprintów)
Tag cadence:    v1.0/v2.0/v3.0/v4.0 po każdej fazie

Deploy:
  Dev:  localhost:3001 (przez cały czas)
  Prod: git push → Vercel auto-deploy (staging at commit hash)
  Final prod: po Fazie 4 weryfikacji
```

---

## WYKLUCZENIA (NIE DOTYKAĆ)

```
/app/zwiad       → BudOS app — NIE
/app/silnik      → BudOS app — NIE
/app/kosztorys   → BudOS app — NIE
/app/decyzja     → BudOS app — NIE
/app/layout.tsx  → BudOS sidebar shell — NIE (tylko pathname=/app exact bypass)
globals.css      → dark BudOS tokens — NIE zmieniać, tylko dodawać w (marketing)/layout.tsx
```
