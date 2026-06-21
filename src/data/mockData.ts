// Mock Data for Terra.OS
import { Tender } from '@/types';

export const mockData = {
  tenders: [
    {
      id: '1',
      title: 'Przetarg nieograniczony nr 234/2024',
      value: 850000,
      deadline: '2024-11-15',
      location: 'Śląsk, Katowice',
      source: 'BIP' as const,
      status: 'new' as const,
      redFlags: [
        {
          id: 'rf1',
          description: 'Brak odwodnienia w przedmiarze',
          impact: 12500,
          page: 's. 12',
          severity: 'high' as const,
          category: 'technical' as const
        },
        {
          id: 'rf2',
          description: 'Niekonkurencyjna cena transportu',
          impact: 8200,
          page: 's. 15',
          severity: 'medium' as const,
          category: 'financial' as const
        }
      ],
      estimatedCosts: [
        {
          id: 'ec1',
          category: 'Koparka 30t/h',
          documentation: 250.00,
          yourReal: 180.00,
          unit: 'zł/h'
        },
        {
          id: 'ec2',
          category: 'Wywrotka 20t',
          documentation: 45.00,
          yourReal: 35.00,
          unit: 'zł/h'
        },
        {
          id: 'ec3',
          category: 'Transport (km)',
          documentation: 12.00,
          yourReal: 9.50,
          unit: 'zł/km'
        }
      ]
    },
    {
      id: '2',
      title: 'Wykonanie nasypów gruntowych',
      value: 450000,
      deadline: '2024-11-20',
      location: 'Śląsk, Gliwice',
      source: 'BZP' as const,
      status: 'new' as const,
      redFlags: [],
      estimatedCosts: [
        {
          id: 'ec4',
          category: 'Walcarek 13t',
          documentation: 120.00,
          yourReal: 95.00,
          unit: 'zł/h'
        },
        {
          id: 'ec5',
          category: 'Grukt spękany',
          documentation: 85.00,
          yourReal: 70.00,
          unit: 'zł/m³'
        }
      ]
    },
    {
      id: '3',
      title: 'Prace ziemne na terenie fabryki',
      value: 1200000,
      deadline: '2024-11-25',
      location: 'Śląsk, Zabrze',
      source: 'TED' as const,
      status: 'new' as const,
      redFlags: [
        {
          id: 'rf3',
          description: 'Błąd w obmiarze nasypów',
          impact: 4100,
          page: 's. 22',
          severity: 'low' as const,
          category: 'technical' as const
        },
        {
          id: 'rf4',
          description: 'Brak uwzględnienia składowania gruntu',
          impact: 6000,
          page: 's. 28',
          severity: 'high' as const,
          category: 'financial' as const
        }
      ],
      estimatedCosts: [
        {
          id: 'ec6',
          category: 'Koparka 30t/h',
          documentation: 250.00,
          yourReal: 180.00,
          unit: 'zł/h'
        },
        {
          id: 'ec7',
          category: 'Owodnienie',
          documentation: 0.00,
          yourReal: 15.00,
          unit: 'zł/h'
        }
      ]
    },
    {
      id: '4',
      title: 'Roboty ziemne - droga gminna',
      value: 320000,
      deadline: '2024-12-01',
      location: 'Śląsk, Mysłowice',
      source: 'BIP' as const,
      status: 'new' as const,
      redFlags: [],
      estimatedCosts: [
        {
          id: 'ec8',
          category: 'Wywrotka 20t',
          documentation: 45.00,
          yourReal: 35.00,
          unit: 'zł/h'
        },
        {
          id: 'ec9',
          category: 'Walcarek 13t',
          documentation: 120.00,
          yourReal: 95.00,
          unit: 'zł/h'
        }
      ]
    },
    {
      id: '5',
      title: 'Układanie nawierzchni bitumicznych',
      value: 670000,
      deadline: '2024-12-05',
      location: 'Śląsk, Siemianowice',
      source: 'BZP' as const,
      status: 'new' as const,
      redFlags: [
        {
          id: 'rf5',
          description: 'Niekonkurencyjna cena transportu',
          impact: 5500,
          page: 's. 18',
          severity: 'medium' as const,
          category: 'financial' as const
        }
      ],
      estimatedCosts: [
        {
          id: 'ec10',
          category: 'Koparka 30t/h',
          documentation: 250.00,
          yourReal: 180.00,
          unit: 'zł/h'
        },
        {
          id: 'ec11',
          category: 'Transport (km)',
          documentation: 12.00,
          yourReal: 9.50,
          unit: 'zł/km'
        }
      ]
    }
  ] as Tender[]
};
