'use client';

import { create } from 'zustand';
import type {
  Tender,
  Estimate,
  RiskAnalysis,
  DecisionRecommendation,
  Equipment,
  Employee,
} from '@/types';

// ── Module names used in navigation ────────────────────────────────────────

export type ModuleName = 'dashboard' | 'zwiad' | 'kosztorys' | 'silnik' | 'decyzja' | 'logistyka';

interface AppState {
  // ── Navigation ──────────────────────────────────────────────────────────
  currentModule: ModuleName;
  setCurrentModule: (module: ModuleName) => void;

  // ── Tender state ────────────────────────────────────────────────────────
  tenders: Tender[];
  selectedTender: Tender | null;
  setSelectedTender: (tender: Tender | null) => void;

  // ── Estimates ───────────────────────────────────────────────────────────
  estimates: Record<string, Estimate>;
  setEstimate: (tenderId: string, estimate: Estimate) => void;

  // ── Risk analysis ───────────────────────────────────────────────────────
  riskAnalysis: Record<string, RiskAnalysis>;
  setRiskAnalysis: (tenderId: string, analysis: RiskAnalysis) => void;

  // ── Decisions ───────────────────────────────────────────────────────────
  decisions: Record<string, DecisionRecommendation>;
  setDecision: (tenderId: string, decision: DecisionRecommendation) => void;

  // ── Resources (Module 3) ────────────────────────────────────────────────
  equipment: Equipment[];
  employees: Employee[];
  setEquipment: (equipment: Equipment[]) => void;
  setEmployees: (employees: Employee[]) => void;

  // ── UI state ────────────────────────────────────────────────────────────
  isMenuOpen: boolean;
  toggleMenu: () => void;

  // ── Loading states ──────────────────────────────────────────────────────
  isLoading: boolean;
  setIsLoading: (loading: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  // ── Navigation ──────────────────────────────────────────────────────────
  currentModule: 'dashboard',
  setCurrentModule: (module) => set({ currentModule: module }),

  // ── Tender state ────────────────────────────────────────────────────────
  tenders: [],
  selectedTender: null,
  setSelectedTender: (tender) => set({ selectedTender: tender }),

  // ── Estimates ───────────────────────────────────────────────────────────
  estimates: {},
  setEstimate: (tenderId, estimate) =>
    set((state) => ({ estimates: { ...state.estimates, [tenderId]: estimate } })),

  // ── Risk analysis ───────────────────────────────────────────────────────
  riskAnalysis: {},
  setRiskAnalysis: (tenderId, analysis) =>
    set((state) => ({ riskAnalysis: { ...state.riskAnalysis, [tenderId]: analysis } })),

  // ── Decisions ───────────────────────────────────────────────────────────
  decisions: {},
  setDecision: (tenderId, decision) =>
    set((state) => ({ decisions: { ...state.decisions, [tenderId]: decision } })),

  // ── Resources (Module 3) ────────────────────────────────────────────────
  equipment: [],
  employees: [],
  setEquipment: (equipment) => set({ equipment }),
  setEmployees: (employees) => set({ employees }),

  // ── UI state ────────────────────────────────────────────────────────────
  isMenuOpen: false,
  toggleMenu: () => set((state) => ({ isMenuOpen: !state.isMenuOpen })),

  // ── Loading states ──────────────────────────────────────────────────────
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
}));
