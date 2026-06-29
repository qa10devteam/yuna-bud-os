export interface Tender {
  id: string;
  externalId: string;
  source: 'BZP' | 'TED' | 'BK' | 'BIP';
  title: string;
  cpv: string[];
  voivodeship: string;
  publishDate: string;
  deadline: string;
  estimatedValue: number;
  matchScore: number;
  status: 'new' | 'analyzing' | 'ready' | 'accepted' | 'rejected' | 'archived';
  documents: TenderDocument[];
  summary?: TenderSummary;
  redFlags?: RedFlag[];
  discrepancies?: Discrepancy[];
}

export interface TenderDocument {
  id: string;
  type: 'SWZ' | 'projekt' | 'STWiOR' | 'przedmiar';
  fileName: string;
  fileSize: number;
  parsed: boolean;
  chunks: DocumentChunk[];
}

export interface DocumentChunk {
  id: string;
  tenderId: string;
  page?: number;
  position?: string;
  text: string;
  embedding: number[];
  type: 'text' | 'table' | 'clause' | 'price';
}

export interface TenderSummary {
  overview: string;
  scope: string;
  keyDates: string[];
  requirements: string[];
}

export interface RedFlag {
  id: string;
  tenderId: string;
  type: 'price' | 'quantity' | 'technical' | 'legal' | 'timeline';
  severity: 'low' | 'medium' | 'high' | 'critical';
  description: string;
  sourcePage: number;
  sourcePosition?: string;
  potentialCost?: number;
  recommendedAction: string;
}

export interface Discrepancy {
  id: string;
  tenderId: string;
  type: 'quantity' | 'description' | 'missing' | 'extra';
  description: string;
  beforemiarItem?: string;
  designCoverage: boolean;
  severity: 'low' | 'medium' | 'high';
  provenance: { page?: number; line?: number; position?: string };
}

export interface Estimate {
  id: string;
  tenderId: string;
  variant: 'A' | 'B';
  version: number;
  createdAt: string;
  updatedAt: string;
  lines: EstimateLine[];
  totals: EstimateTotals;
}

export interface EstimateLine {
  id: string;
  position: string;
  description: string;
  unit: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  source?: string;
}

export interface EstimateTotals {
  net: number;
  vat: number;
  gross: number;
  labor: number;
  equipment: number;
  materials: number;
  overhead: number;
  profit: number;
}

export interface RiskAnalysis {
  id: string;
  estimateId: string;
  timestamp: string;
  l1Feasibility: L1Feasibility;
  l2RiskDistribution: L2RiskDistribution;
  l3Explanation: string;
}

export interface L1Feasibility {
  verdict: 'feasible' | 'risky' | 'infeasible';
  violations: AxiomViolation[];
  derivedFacts: string[];
}

export interface AxiomViolation {
  id: string;
  axiomClass: 'A' | 'B' | 'C' | 'D';
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  provenance: { page?: number; line?: number; clause?: string };
}

export interface L2RiskDistribution {
  scenarios: RiskScenario[];
  dominantDrivers: string[];
  targetMarginProbability: number;
}

export interface RiskScenario {
  name: string;
  probability: number;
  outcome: number;
  margin: number;
}

export interface DecisionRecommendation {
  id: string;
  tenderId: string;
  offerPrice: number;
  recommendation: 'offer' | 'reject' | 'negotiate';
  confidence: number;
  reasoning: string;
  keyFactors: string[];
  timestamp: string;
}

export interface Equipment {
  id: string;
  name: string;
  type: 'excavator' | 'dump_truck' | 'roller' | 'other';
  capacity?: string;
  availability: boolean;
  location?: string;
}

export interface Employee {
  id: string;
  name: string;
  nameShort: string;
  competencies: string[];
  available: boolean;
  currentProject?: string;
}
