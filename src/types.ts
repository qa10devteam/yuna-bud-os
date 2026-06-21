// Terra.OS Types - Single Source of Truth
export interface Tender {
  id: string;
  title: string;
  value: number;
  deadline: string;
  location: string;
  source: 'BIP' | 'BZP' | 'TED' | 'BK';
  status: 'new' | 'analyzed' | 'decision';
  redFlags: RedFlag[];
  estimatedCosts: CostBreakdown[];
}

export interface RedFlag {
  id: string;
  description: string;
  impact: number;
  page: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'technical' | 'financial' | 'legal' | 'safety';
}

export interface CostBreakdown {
  id: string;
  category: string;
  documentation: number;
  yourReal: number;
  unit: string;
}

export interface RiskAnalysis {
  tenderId: string;
  overallRisk: 'low' | 'medium' | 'high' | 'critical';
  riskScore: number;
  redFlags: RedFlag[];
  recommendations: string[];
}

export interface Decision {
  tenderId: string;
  recommendedPrice: number;
  confidence: number;
  action: 'accept' | 'decline' | 'negotiate';
  rationale: string[];
  risksMitigated: string[];
}

export type ModuleKey = 'zwiad' | 'kosztorys' | 'silnik' | 'decyzja';

export interface AppState {
  // Navigation
  currentModule: ModuleKey;
  selectedTender: string | null;
  isMenuOpen: boolean;
  
  // Data
  tenders: Tender[];
  selectedTenderData: Tender | null;
  
  // Actions
  setCurrentModule: (module: ModuleKey) => void;
  selectTender: (id: string) => void;
  toggleMenu: () => void;
}
