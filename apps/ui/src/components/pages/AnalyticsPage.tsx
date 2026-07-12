'use client';

import { useState } from 'react';
import { motion } from 'motion/react';
import {
  Brain, Target, TrendingUp, BarChart3, AlertTriangle,
  ChevronRight, Info, CheckCircle2, XCircle, HelpCircle,
  Zap, Calculator, Scale,
} from 'lucide-react';
import { useStore } from '@/store/useStore';
import MarketIntelligenceDashboard from '@/components/MarketIntelligenceDashboard';
import ICBPriceExplorer from '@/components/ICBPriceExplorer';
import TenderFTSSearch from '@/components/TenderFTSSearch';

// ── Types ──────────────────────────────────────────────────────────────────────
interface AHPCriterion {
  id: string;
  label: string;
  weight: number;
}

interface BiddingResult {
  optimal_markup_pct: number;
  win_probability_pct: number;
  expected_profit: number;
  bid_price: number;
  chart_data: Array<{ markup_pct: number; expected_profit: number; win_probability: number }>;
}

interface AHPResult {
  total: number;
  recommendation: 'GO' | 'NO-GO' | 'CONSIDER';
  recommendation_pl: string;
  color: string;
  breakdown: Array<{ criterion_id: string; criterion: string; score: number; weight: number; contribution: number }>;
}

interface RiskResult {
  red_flags: Array<{ message: string; severity: string; excerpt?: string }>;
  deadlines: Array<{ description: string; value: string }>;
  penalties: Array<{ description: string; percent: number }>;
  valorization: boolean;
  ai_enhanced: boolean;
}

interface WinData {
  win_rate: number;
  total_bids: number;
  wins: number;
  trend: Array<{ month: string; rate: number }>;
}

// ── Default criteria ───────────────────────────────────────────────────────────
const DEFAULT_CRITERIA: AHPCriterion[] = [
  { id: 'technical_fit',   label: 'Fit techniczny',      weight: 0.25 },
  { id: 'expected_margin', label: 'Marża oczekiwana',    weight: 0.20 },
  { id: 'team_load',       label: 'Obciążenie zespołu',  weight: 0.15 },
  { id: 'penalty_risk',    label: 'Ryzyko kar',          weight: 0.15 },
  { id: 'strategic_value', label: 'Wartość strategiczna',weight: 0.10 },
  { id: 'cashflow_impact', label: 'Cash flow impact',    weight: 0.10 },
  { id: 'buyer_history',   label: 'Historia z zamaw.',   weight: 0.05 },
];

// ── Formatters ─────────────────────────────────────────────────────────────────
function fmtPLN(v: number) {
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + ' mln zł';
  if (v >= 1_000) return (v / 1_000).toFixed(0) + ' tys. zł';
  return v.toFixed(0) + ' zł';
}

// ── Tabs ───────────────────────────────────────────────────────────────────────
const TABS = [
  { id: 'ahp',      label: 'GO/NO-GO AHP',    icon: Scale },
  { id: 'bidding',  label: 'Optymalna oferta', icon: Target },
  { id: 'risk',     label: 'Ryzyko SWZ',       icon: AlertTriangle },
  { id: 'dashboard',label: 'Dashboard',         icon: BarChart3 },
  { id: 'win',      label: 'Win Rate',          icon: TrendingUp },
] as const;
type Tab = typeof TABS[number]['id'];

// ── ScoreSlider ────────────────────────────────────────────────────────────────
function ScoreSlider({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-earth-400 w-36 shrink-0">{label}</span>
      <input
        type="range" min={0} max={10} step={0.5} value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="flex-1 accent-accent-primary h-1.5"
      />
      <span className={`text-xs font-bold w-8 text-right ${
        value >= 7 ? 'text-accent-primary' : value >= 4 ? 'text-accent-warning' : 'text-accent-danger'
      }`}>{value.toFixed(1)}</span>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function AnalyticsPage() {
  const token = useStore(s => s.accessToken);
  const [tab, setTab] = useState<Tab>('ahp');
  const [loading, setLoading] = useState(false);

  // AHP state
  const [ahpScores, setAhpScores] = useState<Record<string, number>>(
    Object.fromEntries(DEFAULT_CRITERIA.map(c => [c.id, 6]))
  );
  const [ahpResult, setAhpResult] = useState<AHPResult | null>(null);

  // Bidding state
  const [costEst, setCostEst] = useState(2_000_000);
  const [nComp, setNComp] = useState(5);
  const [biddingResult, setBiddingResult] = useState<BiddingResult | null>(null);

  // Risk state
  const [swzText, setSwzText] = useState('');
  const [riskResult, setRiskResult] = useState<RiskResult | null>(null);

  // Dashboard state
  const [dashData, setDashData] = useState<Record<string, unknown> | null>(null);

  // Win state
  const [winData, setWinData] = useState<WinData | null>(null);

  // ── Handlers ────────────────────────────────────────────────────────────────

  async function runAHP() {
    setLoading(true);
    try {
      const res = await fetch('/api/v2/analytics/ahp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ scores: ahpScores }),
      });
      const d = await res.json();
      // Normalize: add recommendation_pl if missing
      if (!d.recommendation_pl) {
        d.recommendation_pl = d.recommendation === 'GO' ? 'Złóż ofertę'
          : d.recommendation === 'CONSIDER' ? 'Rozważ'
          : 'Nie składaj oferty';
      }
      setAhpResult(d);
    } finally {
      setLoading(false);
    }
  }

  async function runBidding() {
    setLoading(true);
    try {
      const res = await fetch('/api/v2/analytics/bidding', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ cost_estimate: costEst, n_competitors: nComp }),
      });
      const d = await res.json();
      // Normalize field names
      const norm: BiddingResult = {
        optimal_markup_pct: d.optimal_markup_pct ?? (d.optimal_markup ?? 0) * 100,
        win_probability_pct: d.win_probability_pct ?? (d.win_probability ?? 0) * 100,
        expected_profit: d.expected_profit ?? 0,
        bid_price: d.bid_price ?? costEst * (1 + (d.optimal_markup ?? 0)),
        chart_data: d.chart_data ?? [],
      };
      setBiddingResult(norm);
    } finally {
      setLoading(false);
    }
  }

  async function runRisk() {
    if (!swzText.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/v2/analytics/risk-extract', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ text: swzText, use_ai: false }),
      });
      const d = await res.json();
      setRiskResult(d);
    } finally {
      setLoading(false);
    }
  }

  async function loadDashboard() {
    setLoading(true);
    try {
      const res = await fetch('/api/v2/analytics/dashboard', {
        headers: { Authorization: `Bearer ${token}` },
      });
      const d = await res.json();
      setDashData(d);
    } finally {
      setLoading(false);
    }
  }

  async function loadWin() {
    setLoading(true);
    try {
      const d = await fetch('/api/v2/analytics/win-probability', {
        headers: { Authorization: `Bearer ${token}` },
      }).then(r => r.json());
      setWinData(d);
    } finally {
      setLoading(false);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="flex flex-col h-full bg-earth-950"
    >
      {/* Header */}
      <div className="px-6 pt-5 pb-4 border-b border-earth-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent-primary/15 flex items-center justify-center">
            <Brain className="w-4 h-4 text-accent-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-earth-100">Silnik Analityczny</h1>
            <p className="text-xs text-earth-500">GO/NO-GO · Optymalna oferta · Analiza ryzyka SWZ</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mt-4">
          {TABS.map(t => {
            const Icon = t.icon;
            return (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); if (t.id === 'dashboard') loadDashboard(); if (t.id === 'win') loadWin(); }}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  tab === t.id
                    ? 'bg-accent-primary/15 text-accent-primary'
                    : 'text-earth-500 hover:text-earth-300 hover:bg-earth-800/50'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">

        {/* ── AHP Tab ── */}
        {tab === 'ahp' && (
          <div className="max-w-2xl space-y-5">
            <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Scale className="w-4 h-4 text-accent-primary" />
                <span className="text-sm font-semibold text-earth-200">Ocena kryteriów AHP</span>
                <span className="text-xs text-earth-500 ml-auto">Skala 0–10</span>
              </div>
              <div className="space-y-3">
                {DEFAULT_CRITERIA.map(c => (
                  <div key={c.id} className="space-y-1">
                    <ScoreSlider
                      label={`${c.label} (${(c.weight * 100).toFixed(0)}%)`}
                      value={ahpScores[c.id] ?? 6}
                      onChange={v => setAhpScores(prev => ({ ...prev, [c.id]: v }))}
                    />
                  </div>
                ))}
              </div>
              <button
                onClick={runAHP}
                disabled={loading}
                className="mt-5 w-full py-2 rounded-lg bg-accent-primary text-white text-sm font-semibold hover:bg-accent-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Obliczam…' : 'Oblicz rekomendację GO/NO-GO'}
              </button>
            </div>

            {ahpResult && (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                className={`bg-earth-900/60 border rounded-xl p-5 ${
                  ahpResult.recommendation === 'GO'
                    ? 'border-emerald-500/40'
                    : ahpResult.recommendation === 'CONSIDER'
                    ? 'border-yellow-500/40'
                    : 'border-red-500/40'
                }`}
              >
                <div className="flex items-center gap-3 mb-4">
                  {ahpResult.recommendation === 'GO' ? (
                    <CheckCircle2 className="w-8 h-8 text-emerald-400" />
                  ) : ahpResult.recommendation === 'CONSIDER' ? (
                    <HelpCircle className="w-8 h-8 text-yellow-400" />
                  ) : (
                    <XCircle className="w-8 h-8 text-red-400" />
                  )}
                  <div>
                    <div className={`text-lg font-bold ${
                      ahpResult.recommendation === 'GO' ? 'text-emerald-400'
                      : ahpResult.recommendation === 'CONSIDER' ? 'text-yellow-400'
                      : 'text-red-400'
                    }`}>{ahpResult.recommendation_pl}</div>
                    <div className="text-xs text-earth-500">Wynik AHP: {ahpResult.total.toFixed(1)}/100</div>
                  </div>
                  <div className="ml-auto text-3xl font-bold text-earth-200">{ahpResult.total.toFixed(0)}</div>
                </div>

                {/* Score bar */}
                <div className="w-full bg-earth-800 rounded-full h-2 mb-4">
                  <div
                    className={`h-2 rounded-full transition-all duration-700 ${
                      ahpResult.recommendation === 'GO' ? 'bg-emerald-500'
                      : ahpResult.recommendation === 'CONSIDER' ? 'bg-yellow-500'
                      : 'bg-red-500'
                    }`}
                    style={{ width: `${ahpResult.total}%` }}
                  />
                </div>

                {/* Breakdown */}
                <div className="space-y-2">
                  {ahpResult.breakdown.map(b => (
                    <div key={b.criterion_id} className="flex items-center gap-2 text-xs">
                      <span className="text-earth-400 w-44 shrink-0">{b.criterion}</span>
                      <div className="flex-1 bg-earth-800 rounded-full h-1">
                        <div
                          className="bg-accent-primary/60 h-1 rounded-full"
                          style={{ width: `${(b.score / 10) * 100}%` }}
                        />
                      </div>
                      <span className="text-earth-400 w-16 text-right">+{b.contribution.toFixed(1)} pkt</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* ── Bidding Tab ── */}
        {tab === 'bidding' && (
          <div className="max-w-2xl space-y-5">
            <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target className="w-4 h-4 text-accent-primary" />
                <span className="text-sm font-semibold text-earth-200">Model Friedman-Gates</span>
                <span className="text-xs text-earth-500 ml-auto">Maksymalizacja E[zysk]</span>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="text-xs text-earth-400 block mb-1.5">Koszt własny (PLN)</label>
                  <input
                    type="number"
                    value={costEst}
                    onChange={e => setCostEst(parseFloat(e.target.value) || 0)}
                    className="w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-200 focus:border-accent-primary/50 outline-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-earth-400 block mb-1.5">Liczba konkurentów</label>
                  <input
                    type="number" min={1} max={30}
                    value={nComp}
                    onChange={e => setNComp(parseInt(e.target.value) || 1)}
                    className="w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-200 focus:border-accent-primary/50 outline-none"
                  />
                </div>
              </div>

              <button
                onClick={runBidding}
                disabled={loading}
                className="w-full py-2 rounded-lg bg-accent-primary text-white text-sm font-semibold hover:bg-accent-primary/90 transition-colors disabled:opacity-50"
              >
                {loading ? 'Obliczam…' : 'Oblicz optymalną ofertę'}
              </button>
            </div>

            {biddingResult && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-earth-900/60 border border-earth-800 rounded-xl p-5 space-y-4"
              >
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: 'Optymalna marża', value: `${biddingResult.optimal_markup_pct.toFixed(1)}%`, color: 'text-accent-primary' },
                    { label: 'Szansa wygrania', value: `${biddingResult.win_probability_pct.toFixed(0)}%`, color: 'text-emerald-400' },
                    { label: 'Oczekiwany zysk', value: fmtPLN(biddingResult.expected_profit), color: 'text-accent-warning' },
                    { label: 'Cena oferty', value: fmtPLN(biddingResult.bid_price), color: 'text-sky-400' },
                  ].map(kpi => (
                    <div key={kpi.label} className="bg-earth-800/60 rounded-lg p-3">
                      <div className="text-xs text-earth-500 mb-1">{kpi.label}</div>
                      <div className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</div>
                    </div>
                  ))}
                </div>

                {/* Simple chart */}
                <div className="space-y-1.5">
                  <div className="text-xs text-earth-500 mb-2">Oczekiwany zysk vs marża</div>
                  {biddingResult.chart_data.filter((_, i) => i % 4 === 0).map(pt => (
                    <div key={pt.markup_pct} className="flex items-center gap-2 text-xs">
                      <span className="text-earth-500 w-12">{pt.markup_pct.toFixed(0)}%</span>
                      <div className="flex-1 bg-earth-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-accent-primary/70 h-1.5 rounded-full"
                          style={{ width: `${Math.min(100, (pt.expected_profit / (biddingResult.expected_profit * 1.2)) * 100)}%` }}
                        />
                      </div>
                      <span className="text-earth-400 w-20 text-right">{fmtPLN(pt.expected_profit)}</span>
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* ── Risk Tab ── */}
        {tab === 'risk' && (
          <div className="max-w-2xl space-y-5">
            <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-3">
                <AlertTriangle className="w-4 h-4 text-accent-warning" />
                <span className="text-sm font-semibold text-earth-200">Analiza ryzyka SWZ</span>
              </div>
              <p className="text-xs text-earth-500 mb-3">Wklej fragment Specyfikacji Warunków Zamówienia do analizy</p>
              <textarea
                value={swzText}
                onChange={e => setSwzText(e.target.value)}
                rows={8}
                placeholder="Wklej tutaj tekst SWZ, warunki umowy lub klauzule…"
                className="w-full bg-earth-800 border border-earth-700 rounded-lg px-3 py-2 text-sm text-earth-300 focus:border-accent-primary/50 outline-none resize-none placeholder:text-earth-600"
              />
              <button
                onClick={runRisk}
                disabled={loading || !swzText.trim()}
                className="mt-3 w-full py-2 rounded-lg bg-accent-warning/90 text-black text-sm font-semibold hover:bg-accent-warning transition-colors disabled:opacity-50"
              >
                {loading ? 'Analizuję…' : 'Analizuj ryzyka'}
              </button>
            </div>

            {riskResult && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Red flags */}
                {riskResult.red_flags.length > 0 && (
                  <div className="bg-earth-900/60 border border-red-500/30 rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      <span className="text-sm font-semibold text-red-400">Red Flags ({riskResult.red_flags.length})</span>
                    </div>
                    <div className="space-y-2">
                      {riskResult.red_flags.map((f, i) => (
                        <div key={i} className={`rounded-lg p-3 ${
                          f.severity === 'high' ? 'bg-red-500/10 border border-red-500/20'
                          : 'bg-yellow-500/10 border border-yellow-500/20'
                        }`}>
                          <div className="flex items-start gap-2">
                            <span className={`text-xs font-bold uppercase px-1.5 py-0.5 rounded mt-0.5 ${
                              f.severity === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                            }`}>{f.severity}</span>
                            <span className="text-xs text-earth-300">{f.message}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Summary */}
                <div className="grid grid-cols-2 gap-3">
                  <div className={`rounded-lg p-3 ${riskResult.valorization ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                    <div className="text-xs text-earth-400 mb-1">Waloryzacja ceny</div>
                    <div className={`text-sm font-bold ${riskResult.valorization ? 'text-emerald-400' : 'text-red-400'}`}>
                      {riskResult.valorization ? '✓ Jest' : '✗ Brak'}
                    </div>
                  </div>
                  <div className="bg-earth-800/60 border border-earth-700 rounded-lg p-3">
                    <div className="text-xs text-earth-400 mb-1">Kary umowne</div>
                    <div className="text-sm font-bold text-earth-200">{riskResult.penalties.length} wzmiank.</div>
                  </div>
                </div>

                {riskResult.red_flags.length === 0 && (
                  <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-4 flex items-center gap-3">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                    <span className="text-sm text-emerald-300">Nie wykryto krytycznych ryzyk w podanym tekście.</span>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* ── Dashboard Tab ── */}
        {tab === 'dashboard' && (
          <div className="max-w-3xl space-y-4">
            {!dashData ? (
              <div className="text-center py-16 text-earth-500">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p className="text-sm">Ładowanie danych…</p>
              </div>
            ) : (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-4">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { label: 'Aktywne oferty', value: dashData.active_bids as number, fmt: (v: number) => String(v), color: 'text-accent-info' },
                    { label: 'Wartość pipeline', value: dashData.pipeline_value as number, fmt: fmtPLN, color: 'text-accent-primary' },
                    { label: 'Win rate', value: dashData.win_rate_pct as number, fmt: (v: number) => v.toFixed(1) + '%', color: 'text-emerald-400' },
                    { label: 'Śr. marża', value: dashData.avg_margin_pct as number, fmt: (v: number) => v.toFixed(1) + '%', color: 'text-accent-warning' },
                  ].map(kpi => (
                    <div key={kpi.label} className="bg-earth-900/60 border border-earth-800 rounded-xl p-4">
                      <div className="text-xs text-earth-500 mb-1">{kpi.label}</div>
                      <div className={`text-xl font-bold ${kpi.color}`}>{kpi.fmt(kpi.value ?? 0)}</div>
                    </div>
                  ))}
                </div>

                {/* Funnel */}
                {Array.isArray((dashData as any).funnel) && (dashData as any).funnel.length > 0 && (
                  <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
                    <div className="text-xs font-semibold text-earth-400 mb-3">Lejek przetargów</div>
                    <div className="space-y-2">
                      {((dashData as any).funnel as Array<{status: string; count: number}>).map(f => (
                        <div key={f.status} className="flex items-center gap-3 text-xs">
                          <span className="text-earth-400 w-28 shrink-0">{f.status}</span>
                          <div className="flex-1 bg-earth-800 rounded-full h-2">
                            <div
                              className="bg-accent-primary/60 h-2 rounded-full"
                              style={{ width: `${Math.min(100, (f.count / 20) * 100)}%` }}
                            />
                          </div>
                          <span className="text-earth-300 font-bold w-6 text-right">{f.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* ── Win Rate Tab ── */}
        {tab === 'win' && (
          <div className="max-w-2xl space-y-4">
            {!winData ? (
              <div className="text-center py-16 text-earth-500">
                <TrendingUp className="w-12 h-12 mx-auto mb-3 opacity-40" />
                <p className="text-sm">{loading ? 'Ładowanie danych…' : 'Brak danych'}</p>
              </div>
            ) : (
              <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                {/* KPI Cards */}
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Win Rate', value: `${winData.win_rate.toFixed(1)}%`, color: 'text-accent-primary' },
                    { label: 'Łączne oferty', value: String(winData.total_bids), color: 'text-earth-200' },
                    { label: 'Wygrane', value: String(winData.wins), color: 'text-emerald-400' },
                  ].map(kpi => (
                    <div key={kpi.label} className="bg-earth-900/60 border border-earth-800 rounded-xl p-4">
                      <div className="text-xs text-earth-500 mb-1">{kpi.label}</div>
                      <div className={`text-2xl font-bold ${kpi.color}`}>{kpi.value}</div>
                    </div>
                  ))}
                </div>

                {/* Win Rate progress bar */}
                <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-earth-400">Skuteczność ofertowania</span>
                    <span className="text-xs text-accent-primary font-bold">{winData.win_rate.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-earth-800 rounded-full h-3">
                    <div
                      className="bg-accent-primary h-3 rounded-full transition-all duration-700"
                      style={{ width: `${Math.min(100, winData.win_rate)}%` }}
                    />
                  </div>
                </div>

                {/* Trend bar chart */}
                {winData.trend.length > 0 && (
                  <div className="bg-earth-900/60 border border-earth-800 rounded-xl p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <TrendingUp className="w-4 h-4 text-accent-primary" />
                      <span className="text-sm font-semibold text-earth-200">Trend Win Rate</span>
                    </div>
                    <div className="space-y-2">
                      {winData.trend.map(pt => (
                        <div key={pt.month} className="flex items-center gap-3 text-xs">
                          <span className="text-earth-400 w-16 shrink-0">{pt.month}</span>
                          <div className="flex-1 bg-earth-800 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-accent-primary/70 h-2 rounded-full transition-all duration-500"
                              style={{ width: `${Math.min(100, pt.rate)}%` }}
                            />
                          </div>
                          <span className="text-earth-300 font-semibold w-12 text-right">{pt.rate.toFixed(1)}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}
      </div>

      {/* Market Intelligence Dashboard */}
      <div className="mt-8">
        <MarketIntelligenceDashboard />
      </div>

      {/* ICB Price Explorer */}
      <div className="mt-6">
        <ICBPriceExplorer />
      </div>

      {/* Full-text Tender Search */}
      <div className="mt-6">
        <TenderFTSSearch />
      </div>
    </motion.div>
  );
}
