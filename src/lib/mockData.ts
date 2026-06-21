export interface RedFlag {
  id: string;
  type: 'volume' | 'price' | 'risk';
  description: string;
  impact: number;
  page: number;
}

export interface Tender {
  id: string;
  title: string;
  value: number;
  source: 'BZP' | 'TED' | 'BK' | 'BIP';
  deadline: string;
  matchScore: number;
  redFlags: RedFlag[];
  location: string;
  cpv: string;
}

export interface CostItem {
  id: string;
  item: string;
  docCost: number;
  yourCost: number;
}

export interface Team {
  id: string;
  name: string;
  skills: string[];
  availability: number;
}

export const tenders: Tender[] = [
  {
    id: 't1',
    title: 'Przebudowa dróg gminnych w Dzierżoniowie',
    value: 4500000,
    source: 'BIP',
    deadline: '2024-07-15',
    matchScore: 92,
    redFlags: [
      { id: 'rf1', type: 'volume', description: 'Niewystarczająca objętość wydobycia gruntu w przedmiarze', impact: 12000, page: 12 },
      { id: 'rf2', type: 'risk', description: 'Brak uwzględnienia odwodnienia wykopów', impact: 8500, page: 15 }
    ],
    location: 'Dzierżoniów',
    cpv: '45233000-7'
  },
  {
    id: 't2',
    title: 'Budowa zbiornika retencyjnego w Dolnym Śląsku',
    value: 12000000,
    source: 'TED',
    deadline: '2024-07-20',
    matchScore: 85,
    redFlags: [
      { id: 'rf3', type: 'price', description: 'Niekonkurencyjna cena jednostkowa za wywóz gruntu', impact: 45000, page: 22 },
      { id: 'rf4', type: 'risk', description: 'Nieprawidłowe oznaczenie strefy ochronnej', impact: 15000, page: 8 }
    ],
    location: 'Świdnica',
    cpv: '45110000-8'
  },
  {
    id: 't3',
    title: 'Rekultywacja terena poeksploatacyjnego w Okrzeszynie',
    value: 2800000,
    source: 'BZP',
    deadline: '2024-07-10',
    matchScore: 78,
    redFlags: [
      { id: 'rf5', type: 'volume', description: 'Błąd w obmiarze nasypów', impact: 6000, page: 30 }
    ],
    location: 'Okrzeszyn',
    cpv: '45000000-0'
  },
  {
    id: 't4',
    title: 'Wykonanie odwodnienia terenu fabrycznego w Legnicy',
    value: 1500000,
    source: 'BIP',
    deadline: '2024-07-05',
    matchScore: 95,
    redFlags: [],
    location: 'Legnica',
    cpv: '42900000-4'
  },
  {
    id: 't5',
    title: 'Przeróbka kamienia walecznego w rejonie Wałbrzycha',
    value: 900000,
    source: 'BK',
    deadline: '2024-07-12',
    matchScore: 60,
    redFlags: [
      { id: 'rf6', type: 'price', description: 'Zaniżona cena za transport', impact: 3000, page: 5 }
    ],
    location: 'Wałbrzych',
    cpv: '12100000-0'
  }
];

export const costItems: CostItem[] = [
  { id: 'c1', item: 'Wykopy ziemne powszechne', docCost: 15.50, yourCost: 18.20 },
  { id: 'c2', item: 'Nasypy z gruntów naturalnych', docCost: 22.00, yourCost: 20.50 },
  { id: 'c3', item: 'Odwodnienie wykopów', docCost: 0.00, yourCost: 12.50 },
  { id: 'c4', item: 'Transport gruntu 15km', docCost: 45.00, yourCost: 42.00 },
  { id: 'c5', item: 'Składowanie gruntu', docCost: 12.00, yourCost: 10.50 },
];

export const teams: Team[] = [
  { id: 'tm1', name: 'Ekipa Alpha', skills: ['Ziemia', 'Transport'], availability: 85 },
  { id: 'tm2', name: 'Ekipa Beta', skills: ['Ziemia', 'Asfalt'], availability: 40 },
  { id: 'tm3', name: 'Ekipa Gamma', skills: ['Inżynieryjne'], availability: 100 },
];
