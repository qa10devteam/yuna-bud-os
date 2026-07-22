# YU-NA BudOS — Architektura Frontendu

> Źródło prawdy dla wszystkich agentów i sprintów. Aktualizuj przy każdej zmianie struktury.
> Stack: Next.js 15 App Router · TypeScript · Tailwind · Framer Motion (motion/react) · Zustand · Canvas 2D

---

## 1. Routing — dwie strefy

### Strefa publiczna — `src/app/(marketing)/`
| Route | Plik | Status |
|---|---|---|
| `/` | `page.tsx` (1250+ ln) | ✅ Trendsetter landing — DM Serif, floating nav, bento |
| `/login` | `login/page.tsx` | ✅ LoginForm.tsx |
| `/signup` | `signup/page.tsx` | ✅ |
| `/budos` | `budos/page.tsx` | ✅ |
| Layout | `layout.tsx` | ✅ marketing layout |

### Strefa aplikacji — `src/app/app/`
| Route | Plik | Komponent Page | Status |
|---|---|---|---|
| `/app` | `page.tsx` (264 ln) | **inline** dashboard | ✅ Faza 1 done |
| `/app/zwiad` | `zwiad/page.tsx` | `ZwiadPage.tsx` (620 ln) | ✅ real |
| `/app/budos` | `budos/page.tsx` | ? | ❓ sprawdzić |
| Layout | `layout.tsx` | **AppShell** — Sidebar (240px) + TopBar + main | ✅ Faza 1 done |

### Standalone app routes (NIE pod /app/layout — własny routing!)
> ⚠️ Te strony używają `PageShell.tsx` i mają własny sidebar przez moduły useStore. Renderowane przez główny `/app/page.tsx` jako SPA switch.

| Route URL | Page file | Komponent | Linie | Stan |
|---|---|---|---|---|
| `/zwiad` | `zwiad/page.tsx` | `ZwiadPage.tsx` | 620 | ✅ real — lista przetargów BZP/TED, filtry, TenderCard |
| `/silnik` | `silnik/page.tsx` | `SilnikPage.tsx` | 941 | ✅ real — AHP weights, Friedman, scoring |
| `/pipeline` | `pipeline/page.tsx` | `PipelinePage.tsx` | 715 | ✅ real — Kanban lejek przetargów |
| `/kosztorys` | `kosztorys/page.tsx` | `KosztorysPage.tsx` | 1789 | ✅ real — tabela KNR, materiały, marża |
| `/decyzja` | `decyzja/page.tsx` | `DecyzjaPage.tsx` | 882 | ✅ real — rekomendacja AI, risk gauge |
| `/oferta` | `oferta/page.tsx` | `OfertaPage.tsx` | 1591 | ✅ real — kreator oferty PDF |
| `/contracts` | `contracts/page.tsx` | `ContractsPage.tsx` | 227 | ⚠️ stub — mała, wymaga rozbudowy |
| `/bid-intelligence` | `bid-intelligence/page.tsx` | `BidIntelligencePage.tsx` | 142 | ⚠️ stub — bardzo mała |
| `/analytics` | `analytics/page.tsx` | `AnalyticsPage.tsx` | 646 | ✅ real — AHP, Friedman, Ryzyko |
| `/settings` | `settings/page.tsx` | `SettingsPage.tsx` | 1645 | ✅ real — org, konto, billing |
| `/buyer-crm` | `buyer-crm/page.tsx` | `BuyerCRMPage.tsx` | 1212 | ✅ real — CRM zamawiających |
| `/resources` | `resources/page.tsx` | `ResourcesPage.tsx` | 234 | ⚠️ stub — placeholder hits |
| `/logistyka` | `logistyka/page.tsx` | `LogistykaPage.tsx` | 1353 | ✅ real — sprzęt, harmonogram |
| `/team` | `team/page.tsx` | `TeamPage.tsx` | 136 | ⚠️ stub — bardzo mała |
| `/market-intel` | `market-intel/page.tsx` | `MarketIntelPage.tsx` | 404 | ✅ real — trendy CPV |
| `/icb` | `icb/page.tsx` | `ICBPage.tsx` | 1729 | ✅ real — baza cen InterCenBud |
| `/competitors` | `competitors/page.tsx` | `CompetitorPage.tsx` | 511 | ✅ real |
| `/dashboard` | `dashboard/page.tsx` | `DashboardPage.tsx` | 962 | ✅ real (stary dashboard?) |
| `/documents` | `documents/page.tsx` | `DocumentsPage.tsx` | ? | ❓ |
| `/reports` | `reports/page.tsx` | `ReportsPage.tsx` | ? | ❓ |
| `/notifications` | `notifications/page.tsx` | `NotificationsPage.tsx` | ? | ❓ |
| `/automations` | `automations/page.tsx` | `AutomationPage.tsx` | ? | ❓ |
| `/export` | `export/page.tsx` | `ExportPage.tsx` | ? | ❓ |
| `/import` | `import/page.tsx` | `ImportPage.tsx` | ? | ❓ |
| `/pogoda` | `pogoda/page.tsx` | `PogodaPage.tsx` | ? | ❓ |
| `/rfq` | `rfq/page.tsx` | `RfqPage.tsx` | ? | ❓ |
| `/webhooks` | `webhooks/page.tsx` | `WebhooksPage.tsx` | ? | ❓ |
| `/system` | `system/page.tsx` | `SystemPage.tsx` | ? | ❓ |
| `/proactive` | `proactive/page.tsx` | `ProactivePage.tsx` | ? | ❓ |
| `/axiom` | `axiom/page.tsx` | `AxiomEnginePage.tsx` | ? | ❓ |
| `/bookmarks` | `bookmarks/page.tsx` | `BookmarksBoardPage.tsx` | ? | ❓ |
| `/billing` | `billing/page.tsx` | inline | ? | ✅ billing page |

---

## 2. Komponenty UI — `src/components/ui/`

| Komponent | Opis |
|---|---|
| `Badge.tsx` | GO/UWAGA/NO-GO + inne warianty |
| `Button.tsx` | Primary/secondary/ghost |
| `DataTable.tsx` | Tabela z sortowaniem |
| `Drawer.tsx` | Slide-in panel |
| `EmptyState.tsx` | Branded empty states |
| `GlassCard.tsx` | Glassmorphism card |
| `Input.tsx` | Form input |
| `MetricCard.tsx` | KPI karta z trendem |
| `Modal.tsx` | Modal/dialog |
| `ProgressBar.tsx` | Progress bar |
| `Select.tsx` | Select dropdown |
| `SkeletonLoader.tsx` | Skeleton placeholders |
| `StatusBadge.tsx` | Status indicator |
| `Tabs.tsx` | Tab navigation |
| `TenderCard.tsx` | Karta przetargu |
| `Tooltip.tsx` | Tooltip |

---

## 3. Komponenty Globalne — `src/components/`

| Komponent | Opis | Stan |
|---|---|---|
| `Sidebar.tsx` | Sidebar z grupami modułów (collapse/expand) | ✅ Faza 1 upgraded |
| `TopBar.tsx` | Breadcrumb + Search + Avatar dropdown | ✅ Faza 1 new |
| `PageShell.tsx` | Wrapper dla standalone route pages | ✅ |
| `TenderDetail.tsx` | Szczegół przetargu (drawer/modal) | ✅ |
| `TenderFTSSearch.tsx` | Full-text search przetargów | ✅ |
| `TenderMap.tsx` | Mapa Polski z przetargami (Leaflet) | ✅ |
| `ICBPriceExplorer.tsx` | Explorer bazy cen ICB | ✅ |
| `MarketIntelligenceDashboard.tsx` | Dashboard rynku | ✅ |
| `LoginForm.tsx` | Formularz logowania/rejestracji | ✅ |
| `ChatWidget.tsx` | Asystent AI (floating) | ✅ |
| `CommandMenu.tsx` | Cmd+K command palette | ✅ |
| `NotificationsBell.tsx` | Dzwonek powiadomień | ✅ |
| `OnboardingWizard.tsx` | 3-krokowy onboarding | ✅ |
| `PlanBadge.tsx` | Fundament/Silnik/Mózg badge | ✅ |
| `PolandHeatmap.tsx` | Heatmapa województw | ✅ |
| `Toast.tsx` | Toast notifications | ✅ |
| `DemoTour.tsx` | Tour dla nowych użytkowników | ✅ |
| `OpeningView.tsx` | Opening view / splash | ✅ |
| `DocumentViewer.tsx` | PDF/doc viewer | ✅ |

---

## 4. Charts — `src/components/charts/`

| Komponent | Opis |
|---|---|
| `RiskChart.tsx` | Risk visualization |
| `SensitivityWaterfall.tsx` | Waterfall chart wrażliwości |
| `WinProbGauge.tsx` | Gauge prawdopodobieństwa wygranej |

---

## 5. Store — `src/store/useStore.ts`

Zustand persist (`terra-auth`):
```ts
AuthUser { id, name, email, org_id, role, plan? }
accessToken, refreshToken
currentModule  // SPA routing state
tenders[], selectedTender
isMenuOpen, toggleMenu
```

---

## 6. API — `src/lib/`

| Plik | Opis |
|---|---|
| `api-v2.ts` | 60 exports — główne API hooks (useAuthFetch + wszystkie endpointy) |
| `api.ts` | Starsza warstwa |
| `api-client.ts` | Bare client |
| `tokens.ts` | Design token export (T.xxx) |
| `constants.ts` | Stałe |
| `utils.ts` | Utilities |

---

## 7. Design Tokens — `src/lib/tokens.ts` + `globals.css`

```
bg:      #050508 (ink-950)
surface: rgba(255,255,255,0.03)
border:  rgba(255,255,255,0.07)
accent:  #10b981 (emerald)
go:      #10b981
warn:    #eab308
nogo:    #ef4444
text-1:  #e8edf5
text-2:  #64748b
text-3:  #334155
font-d:  DM Serif Display (headlines)
font-s:  Space Grotesk (body)
```

---

## 8. Plan 4-fazowy — postęp

### FAZA 1 — Foundation ✅ (w toku)
- [x] `/app` dashboard — KPI inline, chart z dniami, polskie znaki
- [x] `TopBar.tsx` — breadcrumb + FTS search + avatar dropdown
- [x] `Sidebar.tsx` — SVG signet, active state rgba, plan badge, group separatory
- [x] `app/layout.tsx` — AppShell z TopBar
- [ ] Screenshoty finalne + weryfikacja wizualna
- [ ] Branding audit całej aplikacji (budos → YU-NA BudOS)

### FAZA 2 — Moduły główne (następna)
- [ ] ZwiadPage — list/kanban toggle, inline filtry CPV
- [ ] SilnikPage — AHP radar chart, breakdown p10/p50/p90
- [ ] PipelinePage — kanban polish, kolumny labels
- [ ] Empty states brandowane

### FAZA 3 — Data screens
- [ ] KosztorysPage — tabela pozycji z live marżą
- [ ] DecyzjaPage — GO/NO-GO verdict card duże, risk gauge
- [ ] BidIntelligencePage — rozbudowa (aktualnie 142 ln stub)
- [ ] ContractsPage — rozbudowa (aktualnie 227 ln stub)

### FAZA 4 — Polish
- [ ] ResourcesPage, TeamPage — rozbudowa
- [ ] Onboarding flow polish
- [ ] Settings — billing plan display
- [ ] Mobile 768px
- [ ] Micro-interactions, skeleton loaders

---

## 9. Dual Sidebar Problem ⚠️

**UWAGA:** Jest duplikacja sidebara:
- `src/components/Sidebar.tsx` — stary Sidebar z module-switch przez Zustand `currentModule`
- `src/app/app/layout.tsx` → AppShell — nowy sidebar z `<Link href>` Next.js routing

Aktualnie `/app/*` routes używają `AppShell` (layout.tsx). Standalone routes (`/zwiad`, `/silnik` itp.) używają `PageShell` z innym layoutem.

**Do ujednolicenia w Fazie 2** — wszystkie moduły powinny być pod `/app/*` z jednym AppShell.
