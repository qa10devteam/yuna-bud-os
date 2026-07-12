'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { Building2, Target, Upload, Radar, ChevronRight, ChevronLeft, X, Loader2 } from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

const CPV_OPTIONS = [
  { code: '45111', label: 'Roboty ziemne i drenaż',         sector: 'earthworks' },
  { code: '45233', label: 'Drogi, mosty, infrastruktura',   sector: 'roads' },
  { code: '45210', label: 'Kubatura — budynki i hale',      sector: 'cubature' },
  { code: '45400', label: 'Remonty i roboty wykończeniowe', sector: 'cubature' },
  { code: '45231', label: 'Sieci wod-kan i gazowe',         sector: 'utilities' },
  { code: '45310', label: 'Instalacje elektryczne',         sector: 'utilities' },
  { code: '45221', label: 'Mosty i konstrukcje specjalne',  sector: 'specialised' },
  { code: '45',    label: 'Ogólne roboty budowlane',        sector: 'generic' },
];

const CPV_CATEGORIES = CPV_OPTIONS;

const VOIVODESHIPS = [
  'dolnośląskie', 'kujawsko-pomorskie', 'lubelskie', 'lubuskie',
  'łódzkie', 'małopolskie', 'mazowieckie', 'opolskie',
  'podkarpackie', 'podlaskie', 'pomorskie', 'śląskie',
  'świętokrzyskie', 'warmińsko-mazurskie', 'wielkopolskie', 'zachodniopomorskie',
];

interface OnboardingWizardProps {
  onComplete: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { user, accessToken } = useStore();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: user?.name ?? '',
    nip: '',
    cpv: [] as string[],
    sector: '' as string,
    regions: [] as string[],
  });

  const steps = [
    { title: 'Profil firmy', icon: Building2, desc: 'Podstawowe dane organizacji' },
    { title: 'Obszar zainteresowań', icon: Target, desc: 'CPV i regiony geograficzne' },
    { title: 'Dane historyczne', icon: Upload, desc: 'Import wyników przetargów (opcjonalny)' },
    { title: 'Pierwsza synchronizacja', icon: Radar, desc: 'Pobierz przetargi z BZP' },
  ];

  async function handleNext() {
    if (step < steps.length - 1) {
      setStep(s => s + 1);
      return;
    }
    // Final step: scan
    setLoading(true);
    try {
      if (user?.org_id && accessToken) {
        await fetch(`/api/v2/organizations/${user.org_id}`, {
          method: 'PATCH',
          headers: { Authorization: `Bearer ${accessToken}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ cpv_codes: formData.cpv, regions: formData.regions, sector: formData.sector }),
        }).catch(() => {});
        await fetch('/api/v1/ingest/run', {
          method: 'POST',
          headers: { Authorization: `Bearer ${accessToken}` },
        }).catch(() => {});
      }
      showToast('success', 'Konfiguracja zakończona! Pierwsze przetargi wkrótce pojawią się w systemie.');
      onComplete();
    } catch {
      showToast('error', 'Błąd podczas konfiguracji');
    } finally {
      setLoading(false);
    }
  }

  function toggleCpv(code: string) {
    const option = CPV_OPTIONS.find(o => o.code === code);
    setFormData(d => ({
      ...d,
      cpv: d.cpv.includes(code) ? d.cpv.filter(c => c !== code) : [...d.cpv, code],
      sector: option?.sector ?? d.sector,
    }));
  }

  function toggleRegion(r: string) {
    setFormData(d => ({
      ...d,
      regions: d.regions.includes(r) ? d.regions.filter(x => x !== r) : [...d.regions, r],
    }));
  }

  return (
    <div className="fixed inset-0 z-50 bg-earth-950/90 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-earth-900 border border-earth-700/60 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-earth-800/60 flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-earth-100">Konfiguracja YU-NA</h2>
            <p className="text-xs text-earth-500 mt-0.5">Krok {step + 1} z {steps.length}</p>
          </div>
          <button onClick={onComplete} className="p-1.5 rounded-lg hover:bg-earth-800 text-earth-600 hover:text-earth-300 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Progress */}
        <div className="flex px-6 pt-4 gap-2">
          {steps.map((s, i) => (
            <div key={i} className={`flex-1 h-1 rounded-full transition-colors ${i <= step ? 'bg-accent-primary' : 'bg-earth-800'}`} />
          ))}
        </div>

        {/* Content */}
        <div className="p-6 min-h-[300px]">
          <AnimatePresence mode="wait">
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
            >
              {step === 0 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-earth-400 mb-1.5">Nazwa firmy</label>
                    <input
                      value={formData.name}
                      onChange={e => setFormData(d => ({ ...d, name: e.target.value }))}
                      placeholder="Kowalski Budownictwo Sp. z o.o."
                      className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-earth-400 mb-1.5">NIP</label>
                    <input
                      value={formData.nip}
                      onChange={e => setFormData(d => ({ ...d, nip: e.target.value }))}
                      placeholder="1234567890"
                      className="w-full bg-earth-800/60 border border-earth-700/60 rounded-xl px-4 py-2.5 text-sm text-earth-100 placeholder-earth-600 focus:outline-none focus:border-accent-primary/60 focus:ring-1 focus:ring-accent-primary/30"
                    />
                  </div>
                </div>
              )}

              {step === 1 && (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Kody CPV</p>
                    <div className="grid grid-cols-1 gap-1.5 max-h-40 overflow-y-auto">
                      {CPV_CATEGORIES.map(c => (
                        <label key={c.code} className="flex items-center gap-2.5 cursor-pointer group">
                          <input
                            type="checkbox"
                            checked={formData.cpv.includes(c.code)}
                            onChange={() => toggleCpv(c.code)}
                            className="w-3.5 h-3.5 accent-emerald-500"
                          />
                          <span className="text-xs text-earth-300 group-hover:text-earth-100">
                            <span className="font-mono text-earth-600 mr-1">{c.code}</span>{c.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-earth-400 uppercase tracking-wide mb-2">Województwa</p>
                    <div className="grid grid-cols-2 gap-1 max-h-36 overflow-y-auto">
                      {VOIVODESHIPS.map(v => (
                        <label key={v} className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={formData.regions.includes(v)}
                            onChange={() => toggleRegion(v)}
                            className="w-3.5 h-3.5 accent-emerald-500"
                          />
                          <span className="text-xs text-earth-300 capitalize">{v}</span>
                        </label>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {step === 2 && (
                <div className="text-center py-4">
                  <Upload className="w-12 h-12 text-earth-700 mx-auto mb-3" />
                  <h3 className="text-sm font-semibold text-earth-300 mb-1">Import danych historycznych</h3>
                  <p className="text-xs text-earth-600 mb-4">Wczytaj wyniki poprzednich przetargów aby AI mogło się nauczyć Twoich wzorców</p>
                  <button
                    onClick={() => setStep(3)}
                    className="px-4 py-2 bg-earth-800 text-earth-300 rounded-lg text-sm hover:bg-earth-700 transition-colors mr-3"
                  >
                    Pomiń teraz
                  </button>
                  <button className="px-4 py-2 bg-accent-primary/20 text-accent-primary rounded-lg text-sm hover:bg-accent-primary/30 transition-colors">
                    Importuj CSV
                  </button>
                </div>
              )}

              {step === 3 && (
                <div className="text-center py-4">
                  <Radar className="w-12 h-12 text-accent-primary mx-auto mb-3" />
                  <h3 className="text-sm font-semibold text-earth-100 mb-1">Gotowe do startu!</h3>
                  <p className="text-xs text-earth-500 mb-2">
                    Kliknij poniżej aby pobrać pierwsze przetargi z Biuletynu Zamówień Publicznych (BZP)
                  </p>
                  <p className="text-xs text-earth-700">Synchronizacja zajmuje ok. 30 sekund</p>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Footer */}
        <div className="px-6 pb-5 flex items-center justify-between">
          <button
            onClick={() => step > 0 ? setStep(s => s - 1) : onComplete()}
            className="flex items-center gap-1.5 px-4 py-2 text-sm text-earth-500 hover:text-earth-300 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            {step === 0 ? 'Pomiń' : 'Wstecz'}
          </button>
          <button
            onClick={handleNext}
            disabled={loading}
            className="flex items-center gap-1.5 px-5 py-2.5 bg-accent-primary text-earth-950 rounded-xl text-sm font-semibold hover:bg-emerald-400 transition-colors disabled:opacity-50"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
            {step === steps.length - 1 ? 'Skanuj przetargi' : 'Dalej'}
            {!loading && step < steps.length - 1 && <ChevronRight className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
