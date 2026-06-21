export interface RedFlag {
  id: number;
  desc: string;
  impact: number;
  page: string;
  severity: 'low' | 'medium' | 'high';
}

export interface Tender {
  id: number;
  title: string;
  value: number;
  deadline: string;
  source: string;
  redFlags: RedFlag[];
}

export interface CostItem {
  id: number;
  item: string;
  docCost: number;
  yourCost: number;
}

export const tenders: Tender[] = [
  {
    id: 1,
    title: 'Przetarg nieograniczony nr 234/2024',
    value: 850000,
    deadline: '2024-11-15',
    source: 'BIP',
    redFlags: [
      { id: 1, desc: 'Brak odwodnienia w przedmiarze', impact: 12500, page: 's. 12', severity: 'high' },
      { id: 2, desc: 'Niekonkurencyjna cena transportu', impact: 8200, page: 's. 15', severity: 'medium' },
    ],
  },
  {
    id: 2,
    title: 'Wykonanie nasypów gruntowych',
    value: 450000,
    deadline: '2024-11-20',
    source: 'BZP',
    redFlags: [],
  },
  {
    id: 3,
    title: 'Prace ziemne na terenie fabryki',
    value: 1200000,
    deadline: '2024-11-25',
    source: 'TED',
    redFlags: [
      { id: 1, desc: 'Błąd w obmiarze nasypów', impact: 4100, page: 's. 22', severity: 'low' },
      { id: 2, desc: 'Brak uwzględnienia składowania gruntu', impact: 6000, page: 's. 28', severity: 'high' },
    ],
  },
  {
    id: 4,
    title: 'Roboty ziemne - droga gminna',
    value: 320000,
    deadline: '2024-12-01',
    source: 'BIP',
    redFlags: [],
  },
  {
    id: 5,
    title: 'Układanie nawierzchni bitumicznych',
    value: 670000,
    deadline: '2024-12-05',
    source: 'BZP',
    redFlags: [
      { id: 1, desc: 'Niekonkurencyjna cena transportu', impact: 5500, page: 's. 18', severity: 'medium' },
    ],
  },
];

export const costItems: CostItem[] = [
  { id: 1, item: 'Koparka 30t/h', docCost: 250.00, yourCost: 180.00 },
  { id: 2, item: 'Wywrotka 20t', docCost: 45.00, yourCost: 35.00 },
  { id: 3, item: 'Walcarek 13t', docCost: 120.00, yourCost: 95.00 },
  { id: 4, item: 'Grukt spękany', docCost: 85.00, yourCost: 70.00 },
  { id: 5, item: 'Transport (km)', docCost: 12.00, yourCost: 9.50 },
  { id: 6, item: 'Owodnienie', docCost: 0.00, yourCost: 15.00 },
];
