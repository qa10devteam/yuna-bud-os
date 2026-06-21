---
title: "Mock Data Schema"
status: "Final"
---

# MOCK DATA SCHEMA

## 1. TENDERS
```typescript
interface Tender {
  id: string;
  title: string;
  value: number;
  source: 'BZP' | 'TED' | 'BK' | 'BIP';
  deadline: Date;
  matchScore: number;
  redFlags: RedFlag[];
  documents: Document[];
}
```

## 2. RED FLAGS
```typescript
interface RedFlag {
  id: string;
  type: 'volume' | 'price' | 'risk';
  description: string;
  impact: number;
  page: number;
}
```

## 3. COSTS
```typescript
interface Cost {
  id: string;
  item: string;
  documentCost: number;
  yourCost: number;
  difference: number;
}
```

## 4. RULES
- Mock data in `lib/mockData.ts`.
- 20+ tenders.
- Real Polish context.
- Consistent IDs.
