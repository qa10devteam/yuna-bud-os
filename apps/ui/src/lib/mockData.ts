import type {
  Tender,
  RedFlag,
  Discrepancy,
  Estimate,
  EstimateLine,
  EstimateTotals,
  RiskAnalysis,
  L1Feasibility,
  AxiomViolation,
  L2RiskDistribution,
  RiskScenario,
  DecisionRecommendation,
  Equipment,
  Employee,
} from '@/types';

// ============================================================================
// Terra.OS — Realistic Mock Data (GRUNT Blueprint)
// Polish earthworks contracts for firma p. Macieka (Dzierżoniów)
// ============================================================================

// ── Tenders ─────────────────────────────────────────────────────────────────

export const tenders: Tender[] = [
  {
    id: 'tender-1',
    externalId: 'BZP-2026-001',
    source: 'BZP',
    title: 'Budowa drogi gminnej nr 1234B — roboty ziemne i nawierzchnia',
    cpv: ['45111200-7', '45233200-8'],
    voivodeship: 'dolnośląskie',
    publishDate: '2026-06-15',
    deadline: '2026-07-15',
    estimatedValue: 2850000,
    matchScore: 92,
    status: 'ready',
    documents: [
      { id: 'doc-1', type: 'SWZ', fileName: 'SWZ_budowa_drogi.pdf', fileSize: 2400000, parsed: true, chunks: [] },
      { id: 'doc-2', type: 'przedmiar', fileName: 'przedmiar_robót_ziemnych.pdf', fileSize: 1800000, parsed: true, chunks: [] },
      { id: 'doc-3', type: 'projekt', fileName: 'projekt_budowlany.pdf', fileSize: 5200000, parsed: true, chunks: [] },
    ],
    summary: {
      overview: 'Budowa 2,3 km drogi gminnej w gminie Dzierżoniów. Zakres obejmuje roboty ziemne, odwodnienie, warstwy nawierzchni.',
      scope: 'Przygotowanie terenu, wykop dla rur kanalizacyjnych, nasyp drogowy 15 000 m³, nawierzchnia asfaltowa 2,3 km',
      keyDates: [
        'Termin składania ofert: 2026-07-15',
        'Otwarcie ofert: 2026-07-20',
        'Termin realizacji: 2026-09-01 do 2026-12-31',
      ],
      requirements: [
        'Doświadczenie: 2 kontrakty > 2 mln zł w ostatnich 5 latach',
        'Sprzęt: koparka > 30t, wywrotka > 20t, walcowarka',
        'BIP: oświadczenie o brak kar',
      ],
    },
    redFlags: [
      {
        id: 'rf-1',
        tenderId: 'tender-1',
        type: 'quantity',
        severity: 'high',
        description: 'Zaniżona ilość odvozu gruntu o 30% w stosunku do projektu',
        sourcePage: 12,
        sourcePosition: 'Poz. 4.2',
        potentialCost: 18500,
        recommendedAction: 'Zgłoś rozbieżność przed złożeniem oferty, żądaj korekty przedmiaru',
      },
      {
        id: 'rf-2',
        tenderId: 'tender-1',
        type: 'technical',
        severity: 'medium',
        description: 'Brak pozycji odwodnienia przy głębokości wykopu > 2m',
        sourcePage: 8,
        recommendedAction: 'Dodaj pozycję odwodnienia do kosztorysu',
      },
    ],
    discrepancies: [
      {
        id: 'disc-1',
        tenderId: 'tender-1',
        type: 'quantity',
        description: 'Przedmiar: 12 000 m³ wykopu ≠ Projekt: 15 000 m³',
        beforemiarItem: 'Poz. 4.1',
        designCoverage: false,
        severity: 'high',
        provenance: { page: 12, line: 45, position: 'Poz. 4.1 — Wykop ziemny' },
      },
    ],
  },
  {
    id: 'tender-2',
    externalId: 'BZP-2026-002',
    source: 'BZP',
    title: 'Przebudowa placu zabaw w parku miejskim — roboty ziemne i instalacje',
    cpv: ['45111200-7', '45321000-5'],
    voivodeship: 'dolnośląskie',
    publishDate: '2026-06-18',
    deadline: '2026-07-01',
    estimatedValue: 485000,
    matchScore: 78,
    status: 'analyzing',
    documents: [
      { id: 'doc-4', type: 'SWZ', fileName: 'SWZ_plac_zabaw.pdf', fileSize: 1200000, parsed: true, chunks: [] },
      { id: 'doc-5', type: 'przedmiar', fileName: 'przedmiar_plac_zabaw.pdf', fileSize: 800000, parsed: true, chunks: [] },
    ],
    summary: {
      overview: 'Przebudowa istniejącego placu zabaw — przygotowanie podłoża, nowe posadzki, instalacje wod-kan.',
      scope: 'Korekta terenu 500 m², posypka żwirowa 300 m², instalacja deszczowa, podłoże pod nawierzchnię elastyczną',
      keyDates: [
        'Termin ofert: 2026-07-01',
        'Realizacja: 2026-08-01 do 2026-09-30',
      ],
      requirements: [
        'Doświadczenie: 1 kontrakt > 300 tys. zł',
        'Termin realizacji: 60 dni roboczych',
      ],
    },
    redFlags: [
      {
        id: 'rf-3',
        tenderId: 'tender-2',
        type: 'price',
        severity: 'medium',
        description: 'Cena transportu gruntu niska o 25% vs. rynek',
        sourcePage: 15,
        potentialCost: 4200,
        recommendedAction: 'Skoryguj stawkę transportu o 25% w górę',
      },
    ],
    discrepancies: [],
  },
];

// ── Cost estimation lines ───────────────────────────────────────────────────

// Variant A — doc-based (simplified, per Rozp. MRiT 2021)
export const estimateLinesA: EstimateLine[] = [
  { id: 'line-a1', position: 'KNR 2-01 01-01', description: 'Wykop ziemny w gruncie I-III kategorii', unit: 'm³', quantity: 12000, unitPrice: 18.5, totalPrice: 222000, source: 'KNR' },
  { id: 'line-a2', position: 'KNR 2-01 01-02', description: 'Przewóz gruntu na odległość do 0,5 km', unit: 'm³', quantity: 12000, unitPrice: 8.2, totalPrice: 98400, source: 'KNR' },
  { id: 'line-a3', position: 'KNR 2-01 02-01', description: 'Nasyp drogowy z materiału własnego', unit: 'm³', quantity: 8000, unitPrice: 15.3, totalPrice: 122400, source: 'KNR' },
  { id: 'line-a4', position: 'KNR 2-01 05-01', description: 'Owodnienie wykopu', unit: 'm', quantity: 2300, unitPrice: 25.0, totalPrice: 57500, source: 'KNR' },
  { id: 'line-a5', position: 'KNR 2-02 01-01', description: 'Podłoże żwirowe gr. 20 cm', unit: 'm²', quantity: 4600, unitPrice: 45.0, totalPrice: 207000, source: 'KNR' },
  { id: 'line-a6', position: 'KNR 2-03 01-01', description: 'Nawierzchnia asfaltowa gr. 8 cm', unit: 'm²', quantity: 4600, unitPrice: 120.0, totalPrice: 552000, source: 'KNR' },
];

// Variant B — owner engine (real rates, crew efficiencies)
export const estimateLinesB: EstimateLine[] = [
  { id: 'line-b1', position: 'KAT-01', description: 'Wykop ziemny — koparka 30t + wywrotka 20t', unit: 'm³', quantity: 15000, unitPrice: 22.0, totalPrice: 330000, source: 'OWNER' },
  { id: 'line-b2', position: 'KAT-02', description: 'Transport gruntu 8 km — 2x wywrotka 20t', unit: 'm³', quantity: 15000, unitPrice: 12.5, totalPrice: 187500, source: 'OWNER' },
  { id: 'line-b3', position: 'KAT-03', description: 'Nasyp z gruntu własnego — zagęszczenie', unit: 'm³', quantity: 8000, unitPrice: 18.0, totalPrice: 144000, source: 'OWNER' },
  { id: 'line-b4', position: 'KAT-04', description: 'Owodnienie — pompy + rury', unit: 'm', quantity: 2300, unitPrice: 32.0, totalPrice: 73600, source: 'OWNER' },
  { id: 'line-b5', position: 'KAT-05', description: 'Podłoże żwirowe + zagęszczenie', unit: 'm²', quantity: 4600, unitPrice: 52.0, totalPrice: 239200, source: 'OWNER' },
  { id: 'line-b6', position: 'KAT-06', description: 'Nawierzchnia asfaltowa 8cm + podbudowa', unit: 'm²', quantity: 4600, unitPrice: 135.0, totalPrice: 621000, source: 'OWNER' },
];

// ── Full estimates ──────────────────────────────────────────────────────────

export const estimateA: Estimate = {
  id: 'est-a-1',
  tenderId: 'tender-1',
  variant: 'A',
  version: 1,
  createdAt: '2026-06-21T10:00:00Z',
  updatedAt: '2026-06-21T10:00:00Z',
  lines: estimateLinesA,
  totals: {
    net: 1259700,
    vat: 290731,
    gross: 1550431,
    labor: 350000,
    equipment: 450000,
    materials: 459700,
    overhead: 62985,
    profit: 137015,
  },
};

export const estimateB: Estimate = {
  id: 'est-b-1',
  tenderId: 'tender-1',
  variant: 'B',
  version: 1,
  createdAt: '2026-06-21T10:00:00Z',
  updatedAt: '2026-06-21T10:00:00Z',
  lines: estimateLinesB,
  totals: {
    net: 1695300,
    vat: 390919,
    gross: 2086219,
    labor: 480000,
    equipment: 620000,
    materials: 595300,
    overhead: 84765,
    profit: 137015,
  },
};

// ── Risk analysis (3-layer axiomatic-stochastic engine) ─────────────────────

export const riskAnalysis: RiskAnalysis = {
  id: 'risk-1',
  estimateId: 'est-a-1',
  timestamp: '2026-06-21T11:00:00Z',
  l1Feasibility: {
    verdict: 'risky',
    violations: [
      {
        id: 'av-1',
        axiomClass: 'C',
        description: 'Masa gruntu: wykop 12 000 m³ ≠ odwód + nasyp 8 000 m³ (brak 4 000 m³)',
        severity: 'critical',
        provenance: { page: 12, line: 45, clause: 'Poz. 4.1 vs 4.3' },
      },
      {
        id: 'av-2',
        axiomClass: 'C',
        description: 'Głębia wykopu > 2 m, brak pozycji odwodnienia w przedmiarze',
        severity: 'high',
        provenance: { page: 8, clause: 'Warunki geotechniczne' },
      },
      {
        id: 'av-3',
        axiomClass: 'A',
        description: 'Cena ofertowa < 70% szacowanej wartości — ryzyko abnormally low price',
        severity: 'medium',
        provenance: { clause: 'Art. 96 ust. 2 PZP' },
      },
    ],
    derivedFacts: [
      'Wymagane odwodnienie: TAK (głębia > 2m, wody gruntowe na głęb. 1.5m)',
      'Potrzebny przydział: koparka 30t + wywrotka 20t + walcowarka',
      'Czas realizacji szacowany: 90 dni roboczych',
    ],
  },
  l2RiskDistribution: {
    scenarios: [
      { name: 'Optymistyczny', probability: 0.15, outcome: 1800000, margin: 0.28 },
      { name: 'Realistyczny', probability: 0.45, outcome: 2100000, margin: 0.18 },
      { name: 'Pesymistyczny', probability: 0.30, outcome: 2450000, margin: 0.05 },
      { name: 'Krytyczny', probability: 0.10, outcome: 2800000, margin: -0.08 },
    ],
    dominantDrivers: [
      'Rozbieżność przedmiar-projekt (4 000 m³)',
      'Brak odwodnienia w przedmiarze',
      'Wzrost ceny paliwa +15%',
    ],
    targetMarginProbability: 0.60,
  },
  l3Explanation:
    'Na podstawie analizy dokumentacji przetargowej wykryto krytyczną rozbieżność między przedmiarem a projektem: przedmiar przewiduje 12 000 m³ wykopu, podczas gdy projekt zakłada 15 000 m³. Różnica 3 000 m³ generuje dodatkowy koszt ok. 66 000 zł (wykop + transport). Dodatkowo brakuje pozycji odwodnienia, co przy głębokości > 2m i wodach gruntowych na głębokości 1.5m jest nieodłączne — szacowany koszt 73 600 zł. Łączne ryzyko: ok. 140 000 zł (8.5% wartości przetargu). Rekomendacja: złożyć zapytanie o doprecyzowanie przedmiaru LUB skorygować ofertę o dodatkowe pozycje. Przy obecnych założeniach marża prawdopodobnie spadnie z 18% do 5% lub poniżej.',
};

// ── Decision recommendations ────────────────────────────────────────────────

export const decisions: Record<string, DecisionRecommendation> = {
  'tender-1': {
    id: 'dec-1',
    tenderId: 'tender-1',
    offerPrice: 2850000,
    recommendation: 'negotiate',
    confidence: 0.72,
    reasoning: 'Przetarg potencjalnie dochodowy, ale wymaga negocjacji przedmiaru lub skorygowania kosztorysu. Krytyczna rozbieżność przedmiar-projekt (3 000 m³) musi być rozwiązana przed złożeniem oferty.',
    keyFactors: [
      'Rozbieżność przedmiar-projekt: +3 000 m³ wykopu = +66 000 zł',
      'Brak odwodnienia w przedmiarze: +73 600 zł',
      'Ryzyko abnormally low price: TAK (oferta < 70% szacunkowej)',
      'Marża przy wariantach: A=18% → B=5% (przy korekcie)',
      'Dopasowanie firmy: 92% (sprzęt, referencje, CPV)',
    ],
    timestamp: '2026-06-21T12:00:00Z',
  },
  'tender-2': {
    id: 'dec-2',
    tenderId: 'tender-2',
    offerPrice: 485000,
    recommendation: 'offer',
    confidence: 0.85,
    reasoning: 'Przetarg prosty, dobrze dopasowany do firmy. Jedyna uwaga: cena transportu w przedmiarze jest niska, ale wpływ na całkowity koszt jest ograniczony.',
    keyFactors: [
      'Prosta dokumentacja (brak projektu budowlanego)',
      'Niska cena transportu w przedmiarze: skoryguj +25%',
      'Krótki termin realizacji (60 dni) — realistyczny',
      'Dopasowanie firmy: 78%',
    ],
    timestamp: '2026-06-21T12:00:00Z',
  },
};

// ── Equipment & employees (Module 3) ────────────────────────────────────────

export const equipment: Equipment[] = [
  { id: 'eq-1', name: 'Koparka CAT 320', type: 'excavator', capacity: '20t', availability: true, location: 'Dzierżoniów' },
  { id: 'eq-2', name: 'Koparka Liebherr 924', type: 'excavator', capacity: '24t', availability: false, location: 'Wałbrzych' },
  { id: 'eq-3', name: 'Wywrotka Scania P320', type: 'dump_truck', capacity: '25t', availability: true, location: 'Dzierżoniów' },
  { id: 'eq-4', name: 'Wywrotka Volvo FMX', type: 'dump_truck', capacity: '30t', availability: true, location: 'Dzierżoniów' },
  { id: 'eq-5', name: 'Walcowarka Bomag BW 213', type: 'roller', capacity: '13t', availability: true, location: 'Dzierżoniów' },
];

export const employees: Employee[] = [
  { id: 'emp-1', name: 'Maciek K.', nameShort: 'MK', competencies: ['operator_koparki', 'kierownik_budowy'], available: true },
  { id: 'emp-2', name: 'Jan W.', nameShort: 'JW', competencies: ['operator_wywrotki'], available: true },
  { id: 'emp-3', name: 'Piotr Z.', nameShort: 'PZ', competencies: ['operator_koparki', 'operator_wywrotki'], available: false, currentProject: 'tender-1' },
  { id: 'emp-4', name: 'Tomasz L.', nameShort: 'TL', competencies: ['operator_walcowarki'], available: true },
  { id: 'emp-5', name: 'Andrzej M.', nameShort: 'AM', competencies: ['pracownik_budowy'], available: true },
  { id: 'emp-6', name: 'Krzysztof N.', nameShort: 'KN', competencies: ['pracownik_budowy'], available: true },
  { id: 'emp-7', name: 'Robert S.', nameShort: 'RS', competencies: ['pracownik_budowy'], available: false, currentProject: 'tender-2' },
];
