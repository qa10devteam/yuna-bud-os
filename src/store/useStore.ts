'use client';

import { create } from 'zustand';
import { AppState, Tender, ModuleKey } from '@/types';
import { mockData } from '@/data/mockData';

export const useStore = create<AppState>((set) => ({
  // Navigation
  currentModule: 'zwiad',
  selectedTender: null,
  isMenuOpen: false,
  
  // Data
  tenders: mockData.tenders,
  selectedTenderData: null,
  
  // Actions
  setCurrentModule: (module: ModuleKey) => 
    set({ currentModule: module, isMenuOpen: false }),
  
  selectTender: (id: string) => 
    set((state) => {
      const tender = state.tenders.find(t => t.id === id) || null;
      return { 
        selectedTender: id,
        selectedTenderData: tender
      };
    }),
  
  toggleMenu: () => 
    set((state) => ({ isMenuOpen: !state.isMenuOpen })),
}));

// Custom hooks for specific slices of state
export const useNavigation = () => {
  const currentModule = useStore((state) => state.currentModule);
  const setCurrentModule = useStore((state) => state.setCurrentModule);
  return { currentModule, setCurrentModule };
};

export const useTenders = () => {
  const tenders = useStore((state) => state.tenders);
  const selectTender = useStore((state) => state.selectTender);
  return { tenders, selectTender };
};

export const useMenu = () => {
  const isMenuOpen = useStore((state) => state.isMenuOpen);
  const toggleMenu = useStore((state) => state.toggleMenu);
  return { isMenuOpen, toggleMenu };
};
