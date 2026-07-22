'use client';

import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Building2, Target, Radar, ChevronRight, ChevronLeft,
  CheckCircle2, MapPin, Loader2, Hammer, Zap, TrendingUp, HardHat,
  Truck, Wrench, Bolt, Waves, AlertCircle,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

// ─────────────────────────────────────────────────────────────────────────────
// Dane
// ─────────────────────────────────────────────────────────────────────────────

const WORK_TYPES = [
  { code: '45233', icon: Truck,    label: 'Drogi i mosty',         hint: 'Inżynieria lądowa, autostrady, obwodnice' },
  { code: '45210', icon: Building2, label: 'Kubatura',              hint: 'Budynki, hale przemysłowe, biurowce' },
  { code: '45400', icon: Hammer,   label: 'Remonty i wykończenia', hint: 'Rewitalizacje, modernizacje wnętrz' },
  { code: '45111', icon: Wrench,   label: 'Roboty ziemne',         hint: 'Niwelacja terenu, drenaż, fundamenty' },
  { code: '45231', icon: Waves,    label: 'Sieci wod-kan i gaz',   hint: 'Wodociągi, kanalizacja, sieci gazowe' },
  { code: '45310', icon: Bolt,     label: 'Instalacje elektryczne',hint: 'Elektroenergetyka, teletechnika, OZE' },
  { code: '45221', icon: HardHat,  label: 'Obiekty specjalne',     hint: 'Mosty, tunele, konstrukcje stalowe' },
  { code: '45',    icon: Hammer,   label: 'Ogólne budownictwo',    hint: 'Wszystkie rodzaje robót budowlanych' },
];

const VOIVODESHIPS = [
  'dolnośląskie','kujawsko-pomorskie','lubelskie','lubuskie',
  'łódzkie','małopolskie','mazowieckie','opolskie',
  'podkarpackie','podlaskie','pomorskie','śląskie',
  'świętokrzyskie','warmińsko-mazurskie','wielkopolskie','zachodniopomorskie',
];

// Mapowanie województw na krótkie etykiety do pillek
const VOI_SHORT: Record<string, string> = {
  'dolnośląskie': 'dolnośląskie','kujawsko-pomorskie': 'kuj.-pom.','lubelskie': 'lubelskie',
  'lubuskie': 'lubuskie','łódzkie': 'łódzkie','małopolskie': 'małopolskie',
  'mazowieckie': 'mazowieckie','opolskie': 'opolskie','podkarpackie': 'podkarpackie',
  'podlaskie': 'podlaskie','pomorskie': 'pomorskie','śląskie': 'śląskie',
  'świętokrzyskie': 'świętokrzyskie','warmińsko-mazurskie': 'warm.-maz.',
  'wielkopolskie': 'wielkopolskie','zachodniopomorskie': 'zach.-pom.',
};

// ─────────────────────────────────────────────────────────────────────────────
// Definicje kroków
// ─────────────────────────────────────────────────────────────────────────────

const STEPS = [
  {
    id: 'firma',
    icon: Building2,
    title: 'Twoja firma',
    tagline: 'Na dobry początek — powiemy systemowi, z kim ma do czynienia.',
    value: 'Przetargi dopasowane do Twojej firmy, nie do wszystkich.',
  },
  {
    id: 'zakres',
    icon: Target,
    title: 'Co robicie?',
    tagline: 'Zaznacz typy robót, które realizujesz. Im dokładniej, tym trafniejsze wyniki.',
    value: 'AI będzie filtrować tylko to, co naprawdę wam pasuje.',
  },
  {
    id: 'teren',
    icon: MapPin,
    title: 'Gdzie działacie?',
    tagline: 'Wybierz województwa, na których chcesz wygrywać przetargi.',
    value: 'Żadnych przetargów z drugiego końca Polski — jeśli nie chcesz.',
  },
  {
    id: 'start',
    icon: Radar,
    title: 'Start!',
    tagline: 'Wszystko gotowe. Uruchamiamy pierwszy zwiad przetargowy.',
    value: 'Za chwilę zobaczysz przetargi dopasowane do Twojego profilu.',
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

function nipValidate(nip: string) {
  const n = nip.replace(/[\s\-]/g, '');
  if (!/^\d{10}$/.test(n)) return false;
  const w = [6, 5, 7, 2, 3, 4, 5, 6, 7];
  const sum = w.reduce((acc, wi, i) => acc + wi * parseInt(n[i]), 0);
  return (sum % 11) === parseInt(n[9]);
}

// ─────────────────────────────────────────────────────────────────────────────
// Props
// ─────────────────────────────────────────────────────────────────────────────

interface OnboardingWizardProps {
  onComplete: () => void;
}

// ─────────────────────────────────────────────────────────────────────────────
// Komponent
// ─────────────────────────────────────────────────────────────────────────────

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const { user, accessToken, setAuth, refreshToken } = useStore();
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [direction, setDirection] = useState<1 | -1>(1);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [formData, setFormData] = useState({
    name: user?.name ?? '',
    nip: '',
    cpv: [] as string[],
    regions: [] as string[],
  });

  const currentStep = STEPS[step];
  const StepIcon = currentStep.icon;

  // ── Walidacja per krok ────────────────────────────────────────────────────
  function validate(): boolean {
    const e: Record<string, string> = {};
    if (step === 0) {
      if (!formData.name.trim()) e.name = 'Podaj nazwę firmy';
      if (formData.nip && !nipValidate(formData.nip)) e.nip = 'Nieprawidłowy NIP';
    }
    if (step === 1 && formData.cpv.length === 0) {
      e.cpv = 'Zaznacz przynajmniej jeden typ robót';
    }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  // ── Nawigacja ─────────────────────────────────────────────────────────────
  function goNext() {
    if (!validate()) return;
    if (step < STEPS.length - 1) {
      setDirection(1);
      setStep(s => s + 1);
    }
  }

  function goPrev() {
    setDirection(-1);
    setStep(s => s - 1);
  }

  // ── Submit finalny ────────────────────────────────────────────────────────
  async function handleStart() {
    setLoading(true);
    try {
      if (!accessToken || !user) throw new Error('Brak sesji');

      const headers = {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      };

      let orgId = user.org_id;

      // Jeśli user nie ma org — utwórz przez onboarding/start
      if (!orgId) {
        const res = await fetch('/api/v2/onboarding/start', {
          method: 'POST',
          headers,
          body: JSON.stringify({
            org_name: formData.name.trim() || 'Moja Firma',
            email: user.email,
            cpv_codes: formData.cpv,
            regions: formData.regions,
          }),
        });
        const data = await res.json();
        if (data.org_id) {
          orgId = data.org_id;
          // Zaktualizuj store żeby user.org_id był wypełniony
          setAuth({ ...user, org_id: orgId }, accessToken, refreshToken ?? '');
        }
      } else {
        // Org już istnieje — zaktualizuj CPV i regiony
        await fetch(`/api/v2/organizations/${orgId}`, {
          method: 'PATCH',
          headers,
          body: JSON.stringify({
            cpv_codes: formData.cpv,
            regions: formData.regions,
          }),
        }).catch(() => {});
      }

      // Uruchom ingest jeśli mamy org
      if (orgId) {
        await fetch('/api/v1/ingest/run', {
          method: 'POST',
          headers,
        }).catch(() => {});
      }

      showToast('success', 'Profil zapisany. Pierwsze przetargi pojawiają się za chwilę.');
      onComplete();
    } catch {
      showToast('error', 'Coś poszło nie tak. Spróbuj ponownie.');
    } finally {
      setLoading(false);
    }
  }

  // ── Toggles ───────────────────────────────────────────────────────────────
  function toggleCpv(code: string) {
    setFormData(d => ({
      ...d,
      cpv: d.cpv.includes(code) ? d.cpv.filter(c => c !== code) : [...d.cpv, code],
    }));
    setErrors(e => ({ ...e, cpv: '' }));
  }

  function toggleRegion(r: string) {
    setFormData(d => ({
      ...d,
      regions: d.regions.includes(r) ? d.regions.filter(x => x !== r) : [...d.regions, r],
    }));
  }

  // ─────────────────────────────────────────────────────────────────────────
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-950/95 backdrop-blur-md">
      <div className="w-full max-w-xl">

        {/* ── Karta główna ── */}
        <motion.div
          initial={{ opacity: 0, scale: 0.97, y: 16 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="bg-ink-900 border border-ink-700/50 rounded-2xl shadow-2xl overflow-hidden"
        >

          {/* ── Pasek kroków ── */}
          <div className="flex border-b border-ink-800/70">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const done = i < step;
              const active = i === step;
              return (
                <div
                  key={s.id}
                  className={`flex-1 flex flex-col items-center gap-1 py-3 px-2 transition-colors border-b-2 ${
                    active
                      ? 'border-em bg-em/5'
                      : done
                        ? 'border-em/30 bg-transparent'
                        : 'border-transparent'
                  }`}
                >
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                    done
                      ? 'bg-em/20 text-em'
                      : active
                        ? 'bg-em text-ink-950'
                        : 'bg-ink-800 text-slate-600'
                  }`}>
                    {done
                      ? <CheckCircle2 className="w-3.5 h-3.5" />
                      : <Icon className="w-3.5 h-3.5" />
                    }
                  </div>
                  <span className={`text-[10px] font-medium hidden sm:block ${
                    active ? 'text-slate-200' : done ? 'text-slate-500' : 'text-slate-700'
                  }`}>
                    {s.title}
                  </span>
                </div>
              );
            })}
          </div>

          {/* ── Nagłówek kroku ── */}
          <AnimatePresence mode="wait">
            <motion.div
              key={`header-${step}`}
              initial={{ opacity: 0, y: direction > 0 ? 8 : -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: direction > 0 ? -8 : 8 }}
              transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
              className="px-6 pt-5 pb-4"
            >
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-em/10 border border-em/20 flex items-center justify-center shrink-0 mt-0.5">
                  <StepIcon className="w-5 h-5 text-em" />
                </div>
                <div className="min-w-0">
                  <h2 className="text-base font-bold text-slate-100 leading-tight">{currentStep.title}</h2>
                  <p className="text-sm text-slate-500 mt-0.5 leading-relaxed">{currentStep.tagline}</p>
                </div>
              </div>

              {/* Obietnica wartości */}
              <div className="mt-3 flex items-center gap-2 bg-ink-800/40 border border-ink-700/40 rounded-xl px-3 py-2">
                <Zap className="w-3.5 h-3.5 text-warn shrink-0" />
                <span className="text-xs text-slate-400">{currentStep.value}</span>
              </div>
            </motion.div>
          </AnimatePresence>

          {/* ── Zawartość kroku ── */}
          <div className="px-6 pb-2 min-h-[220px]">
            <AnimatePresence mode="wait">
              <motion.div
                key={`content-${step}`}
                initial={{ opacity: 0, x: direction > 0 ? 24 : -24 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: direction > 0 ? -24 : 24 }}
                transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              >

                {/* ── Krok 0: Firma ── */}
                {step === 0 && (
                  <div className="space-y-4">
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
                        Nazwa firmy
                      </label>
                      <input
                        value={formData.name}
                        onChange={e => {
                          setFormData(d => ({ ...d, name: e.target.value }));
                          setErrors(er => ({ ...er, name: '' }));
                        }}
                        placeholder="np. Kowalski Budownictwo Sp. z o.o."
                        autoFocus
                        className={`w-full bg-ink-800/60 border rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-ink-600 focus:outline-none focus:ring-1 transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                          errors.name
                            ? 'border-red-500/60 focus:border-red-500/60 focus:ring-red-500/20'
                            : 'border-ink-700/60 focus:border-em/60 focus:ring-em/20'
                        }`}
                      />
                      {errors.name && (
                        <p className="mt-1 flex items-center gap-1 text-xs text-nogo">
                          <AlertCircle className="w-3 h-3" />{errors.name}
                        </p>
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase tracking-wide">
                        NIP <span className="font-normal text-slate-600 normal-case">(opcjonalny, do weryfikacji w GUS)</span>
                      </label>
                      <input
                        value={formData.nip}
                        onChange={e => {
                          setFormData(d => ({ ...d, nip: e.target.value }));
                          setErrors(er => ({ ...er, nip: '' }));
                        }}
                        placeholder="np. 123-456-78-90"
                        className={`w-full bg-ink-800/60 border rounded-xl px-4 py-2.5 text-sm font-mono text-slate-100 placeholder-ink-600 focus:outline-none focus:ring-1 transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                          errors.nip
                            ? 'border-red-500/60 focus:border-red-500/60 focus:ring-red-500/20'
                            : 'border-ink-700/60 focus:border-em/60 focus:ring-em/20'
                        }`}
                      />
                      {errors.nip && (
                        <p className="mt-1 flex items-center gap-1 text-xs text-nogo">
                          <AlertCircle className="w-3 h-3" />{errors.nip}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* ── Krok 1: Zakres robót ── */}
                {step === 1 && (
                  <div>
                    <div className="grid grid-cols-2 gap-2">
                      {WORK_TYPES.map(wt => {
                        const Icon = wt.icon;
                        const selected = formData.cpv.includes(wt.code);
                        return (
                          <button
                            key={wt.code}
                            type="button"
                            onClick={() => toggleCpv(wt.code)}
                            className={`relative flex flex-col items-start gap-1 p-3 rounded-xl border text-left transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                              selected
                                ? 'border-em/60 bg-em/10 text-slate-100'
                                : 'border-ink-700/40 bg-ink-800/30 text-slate-400 hover:border-ink-600 hover:text-slate-300'
                            }`}
                          >
                            {selected && (
                              <CheckCircle2 className="absolute top-2 right-2 w-3.5 h-3.5 text-em" />
                            )}
                            <Icon className={`w-4 h-4 ${selected ? 'text-em' : 'text-slate-600'}`} />
                            <span className="text-xs font-semibold leading-tight">{wt.label}</span>
                            <span className="text-[10px] text-slate-600 leading-tight">{wt.hint}</span>
                          </button>
                        );
                      })}
                    </div>
                    {errors.cpv && (
                      <p className="mt-2 flex items-center gap-1 text-xs text-nogo">
                        <AlertCircle className="w-3 h-3" />{errors.cpv}
                      </p>
                    )}
                  </div>
                )}

                {/* ── Krok 2: Teren ── */}
                {step === 2 && (
                  <div>
                    <div className="flex flex-wrap gap-1.5">
                      {VOIVODESHIPS.map(v => {
                        const selected = formData.regions.includes(v);
                        return (
                          <button
                            key={v}
                            type="button"
                            onClick={() => toggleRegion(v)}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
                              selected
                                ? 'border-em/60 bg-em/15 text-em'
                                : 'border-ink-700/40 bg-ink-800/40 text-slate-500 hover:border-ink-600 hover:text-slate-300'
                            }`}
                          >
                            {VOI_SHORT[v]}
                          </button>
                        );
                      })}
                    </div>
                    <p className="mt-3 text-xs text-slate-600">
                      {formData.regions.length === 0
                        ? 'Nie wybrano regionu — system pokaże przetargi z całej Polski.'
                        : `Wybrano ${formData.regions.length} ${formData.regions.length === 1 ? 'województwo' : formData.regions.length < 5 ? 'województwa' : 'województw'}.`
                      }
                    </p>
                  </div>
                )}

                {/* ── Krok 3: Start ── */}
                {step === 3 && (
                  <div className="space-y-3">
                    {/* Podsumowanie */}
                    <div className="space-y-2">
                      <SummaryRow icon={Building2} label="Firma" value={formData.name || 'Nie podano'} />
                      <SummaryRow
                        icon={Target}
                        label="Typy robót"
                        value={
                          formData.cpv.length === 0
                            ? 'Nie wybrano'
                            : WORK_TYPES.filter(w => formData.cpv.includes(w.code)).map(w => w.label).join(', ')
                        }
                      />
                      <SummaryRow
                        icon={MapPin}
                        label="Teren"
                        value={
                          formData.regions.length === 0
                            ? 'Cała Polska'
                            : `${formData.regions.length} województw`
                        }
                      />
                    </div>

                    {/* Info o czasie */}
                    <div className="flex items-center gap-2 bg-ink-800/40 border border-ink-700/30 rounded-xl px-3 py-2.5">
                      <Radar className="w-4 h-4 text-em shrink-0" />
                      <div>
                        <p className="text-xs font-semibold text-slate-200">Pierwszy zwiad zajmuje ~30 sekund</p>
                        <p className="text-[11px] text-slate-600">Pobieramy przetargi z BZP, TED i portali BIP</p>
                      </div>
                    </div>
                  </div>
                )}

              </motion.div>
            </AnimatePresence>
          </div>

          {/* ── Przyciski nawigacji ── */}
          <div className="px-6 py-4 border-t border-ink-800/60 flex items-center justify-between">
            {step > 0 ? (
              <button type="button"
                onClick={goPrev}
                className="flex items-center gap-1.5 px-3 py-2 text-sm text-slate-500 hover:text-slate-300 transition-colors rounded-lg hover:bg-ink-800/50"
              >
                <ChevronLeft className="w-4 h-4" />
                Wstecz
              </button>
            ) : (
              <button type="button"
                onClick={onComplete}
                className="px-3 py-2 text-sm text-slate-700 hover:text-slate-500 transition-colors"
              >
                Pomiń konfigurację
              </button>
            )}

            {step < STEPS.length - 1 ? (
              <button type="button"
                onClick={goNext}
                className="flex items-center gap-2 px-5 py-2.5 bg-em text-ink-950 rounded-xl text-sm font-bold hover:bg-em active:scale-[0.98] transition-[color,background-color,border-color,opacity,transform,box-shadow]"
              >
                Dalej
                <ChevronRight className="w-4 h-4" />
              </button>
            ) : (
              <button type="button"
                onClick={handleStart}
                disabled={loading}
                className="flex items-center gap-2 px-5 py-2.5 bg-em text-ink-950 rounded-xl text-sm font-bold hover:bg-em active:scale-[0.98] transition-[color,background-color,border-color,opacity,transform,box-shadow] disabled:opacity-60 disabled:pointer-events-none"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Skanujemy...
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4" />
                    Zacznij zwiad
                  </>
                )}
              </button>
            )}
          </div>

        </motion.div>

        {/* ── Przypis ── */}
        <p className="text-center text-[11px] text-slate-700 mt-3">
          Dane konfiguracyjne mozna zmienić w dowolnym momencie w Ustawieniach.
        </p>

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Subkomponent: wiersz podsumowania
// ─────────────────────────────────────────────────────────────────────────────

function SummaryRow({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3 bg-ink-800/30 rounded-xl px-3 py-2.5 border border-ink-700/30">
      <Icon className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-wide text-slate-600 font-semibold">{label}</p>
        <p className="text-xs text-slate-200 mt-0.5 leading-snug truncate">{value}</p>
      </div>
    </div>
  );
}
