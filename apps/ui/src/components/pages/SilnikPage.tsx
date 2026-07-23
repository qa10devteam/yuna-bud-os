'use client';
import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { MetricCard } from '@/components/ui/MetricCard';
import { PageShell } from '@/components/PageShell';
import { showToast } from '@/components/Toast';
import { motion, AnimatePresence } from 'motion/react';
import { PageTransition } from '@/components/ui/PageTransition';
import {
  Sliders, BarChart3, Grid3X3, History as HistoryIcon, Save, RotateCcw,
  Target, TrendingUp,
} from 'lucide-react';

// ─── Types ───────────────────────────────────────────────────────────────────

interface ScoringWeights {
  cpv_match: number;
  value_range: number;
  deadline_pressure: number;
  buyer_history: number;
  document_quality: number;
}

interface ScoringConfig {
  weights: ScoringWeights;
}

interface TenderPreview {
  id: string;
  title: string;
  match_score: number;
  prev_score?: number;
}

interface ScoreBreakdown {
  criterion: string;
  weight: number;
  score: number;
  contribution: number;
}

interface TenderAnalysis {
  score_breakdown: ScoreBreakdown[];
  total_score: number;
  percentile?: number;
  average_score?: number;
}

interface CpvHeatmapCell {
  cpv_code: string;
  cpv_name: string;
  quarter: string;
  win_rate: number;
  count: number;
}

interface AuditEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  details: {
    old_weights?: ScoringWeights;
    new_weights?: ScoringWeights;
  };
}

// ─── Constants ───────────────────────────────────────────────────────────────

const WEIGHT_LABELS: Record<keyof ScoringWeights, string> = {
  cpv_match: 'Dopasowanie CPV',
  value_range: 'Zakres wartości',
  deadline_pressure: 'Presja terminowa',
  buyer_history: 'Historia zamawiającego',
  document_quality: 'Jakość dokumentacji',
};

const TABS = [
  { id: 'weights',   label: 'Konfiguracja Wag',    icon: Sliders   },
  { id: 'analytics', label: 'Score Analytics',      icon: BarChart3 },
  { id: 'heatmap',   label: 'CPV Heatmap',          icon: Grid3X3   },
  { id: 'history',   label: 'Historia Kalibracji',  icon: HistoryIcon   },
] as const;

type TabId = (typeof TABS)[number]['id'];


const DEADLINE_BONUS_DATA = [
  { days: 0,  bonus: 50 },
  { days: 7,  bonus: 30 },
  { days: 14, bonus: 15 },
  { days: 30, bonus: 5  },
  { days: 60, bonus: 0  },
];

// ─── Utility Functions ───────────────────────────────────────────────────────

function interpolateColor(value: number): string {
  const cold = { r: 30, g: 41, b: 59  };  // #1E293B (ink-800)
  const hot  = { r: 16, g: 185,b: 129 };  // #10b981 (em)
  const t = Math.max(0, Math.min(1, value));
  const r = Math.round(cold.r + (hot.r - cold.r) * t);
  const g = Math.round(cold.g + (hot.g - cold.g) * t);
  const b = Math.round(cold.b + (hot.b - cold.b) * t);
  return `rgb(${r}, ${g}, ${b})`;
}

function formatTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleString('pl-PL', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

// ─── Component ───────────────────────────────────────────────────────────────

export function SilnikPage() {
  const authFetch       = useAuthFetch();
  const setCurrentModule = useStore((s) => s.setCurrentModule);

  const [activeTab, setActiveTab]   = useState<TabId>('weights');
  const [loading,   setLoading]     = useState(false);

  // Tab 1 state
  const [weights, setWeights]       = useState<ScoringWeights>({
    cpv_match: 30, value_range: 20, deadline_pressure: 20,
    buyer_history: 15, document_quality: 15,
  });
  const originalWeightsRef = useRef<ScoringWeights | null>(null);
  const [topTenders,  setTopTenders]  = useState<TenderPreview[]>([]);
  const [saving,      setSaving]      = useState(false);

  // Tab 2 state
  const [tenderList,      setTenderList]      = useState<{ id: string; title: string }[]>([]);
  const [selectedTenderId, setSelectedTenderId] = useState<string>('');
  const [analysis,        setAnalysis]        = useState<TenderAnalysis | null>(null);

  // Tab 3 state
  const [heatmapData,    setHeatmapData]    = useState<CpvHeatmapCell[]>([]);
  const [heatmapTooltip, setHeatmapTooltip] = useState<{ cell: CpvHeatmapCell; x: number; y: number } | null>(null);

  // Tab 4 state
  const [auditHistory, setAuditHistory] = useState<AuditEntry[]>([]);

  // ─── Computed values ─────────────────────────────────────────────────────

  const weightSum  = useMemo(() => Object.values(weights).reduce((sum, v) => sum + v, 0), [weights]);
  const isValidSum = weightSum === 100;

  // ─── Data fetching ───────────────────────────────────────────────────────

  const fetchScoringConfig = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/scoring/config') as ScoringConfig;
      if (data?.weights) {
        setWeights(data.weights);
        originalWeightsRef.current = (data.weights);
      }
    } catch (err) { console.error('Failed to fetch scoring config:', err); }
  }, [authFetch]);

  const fetchTopTenders = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/tenders?sort=match_score&limit=10') as { items?: TenderPreview[]; data?: TenderPreview[] };
      const items = data?.items || data?.data || [];
      setTopTenders(Array.isArray(items) ? items : []);
    } catch (err) { console.error('Failed to fetch top tenders:', err); }
  }, [authFetch]);

  const fetchTenderList = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/tenders?limit=50') as { items?: { id: string; title: string }[]; data?: { id: string; title: string }[] };
      const items = data?.items || data?.data || [];
      setTenderList(Array.isArray(items) ? items : []);
    } catch (err) { console.error('Failed to fetch tender list:', err); }
  }, [authFetch]);

  const fetchAnalysis = useCallback(async (tenderId: string) => {
    if (!tenderId) return;
    setLoading(true);
    try {
      const data = await authFetch(`/api/v2/tenders/${tenderId}/analysis`) as TenderAnalysis;
      setAnalysis(data || null);
    } catch (err) {
      console.error('Failed to fetch analysis:', err);
      setAnalysis(null);
    } finally { setLoading(false); }
  }, [authFetch]);

  const fetchHeatmap = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/market/cpv-heatmap') as CpvHeatmapCell[] | { data?: CpvHeatmapCell[] };
      const cells = Array.isArray(data) ? data : data?.data;
      setHeatmapData(cells && cells.length > 0 ? cells : []);
    } catch {
      setHeatmapData([]);
    }
  }, [authFetch]);

  const fetchAuditHistory = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/audit/recent?limit=20') as { items?: AuditEntry[]; data?: AuditEntry[] };
      const items = data?.items || data?.data || [];
      const filtered = (Array.isArray(items) ? items : []).filter(
        (entry) => entry.action === 'scoring_config_update'
      );
      setAuditHistory(filtered);
    } catch (err) {
      console.error('Failed to fetch audit history:', err);
      setAuditHistory([]);
    }
  }, [authFetch]);

  // ─── Effects ─────────────────────────────────────────────────────────────

  useEffect(() => { setCurrentModule('silnik'); }, [setCurrentModule]);

  useEffect(() => {
    if      (activeTab === 'weights')   { fetchScoringConfig(); fetchTopTenders(); }
    else if (activeTab === 'analytics') { fetchTenderList(); }
    else if (activeTab === 'heatmap')   { fetchHeatmap(); }
    else if (activeTab === 'history')   { fetchAuditHistory(); }
  }, [activeTab, fetchScoringConfig, fetchTopTenders, fetchTenderList, fetchHeatmap, fetchAuditHistory]);

  // Debounced refetch on weight change
  useEffect(() => {
    if (activeTab !== 'weights') return;
    const timer = setTimeout(() => { fetchTopTenders(); }, 500);
    return () => clearTimeout(timer);
  }, [weights, activeTab, fetchTopTenders]);

  // ─── Handlers ────────────────────────────────────────────────────────────

  const handleWeightChange = useCallback((key: keyof ScoringWeights, value: number) => {
    setWeights((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSaveWeights = useCallback(async () => {
    if (!isValidSum) return;
    setSaving(true);
    try {
      await authFetch('/api/v2/scoring/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weights }),
      });
      originalWeightsRef.current = (weights);
      showToast('success', 'Konfiguracja wag zapisana pomyślnie');
    } catch (err) {
      console.error('Failed to save weights:', err);
      showToast('error', 'Błąd zapisu konfiguracji');
    } finally { setSaving(false); }
  }, [authFetch, weights, isValidSum]);

  const handleResetWeights = useCallback(() => {
    if (originalWeightsRef.current) setWeights(originalWeightsRef.current!);
  }, []);

  const handleRestoreConfig = useCallback(async (entry: AuditEntry) => {
    if (!entry.details?.new_weights) return;
    try {
      await authFetch('/api/v2/scoring/config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ weights: entry.details.new_weights }),
      });
      setWeights(entry.details.new_weights);
      originalWeightsRef.current = (entry.details.new_weights);
      showToast('success', 'Przywrócono konfigurację z ' + formatTimestamp(entry.timestamp));
    } catch {
      showToast('error', 'Błąd przywracania konfiguracji');
    }
  }, [authFetch]);

  const handleSelectTender = useCallback((id: string) => {
    setSelectedTenderId(id);
    if (id) fetchAnalysis(id);
  }, [fetchAnalysis]);

  // ─── Tab Bar ─────────────────────────────────────────────────────────────

  const renderTabBar = () => (
    <div className="flex gap-1 p-1 bg-ink-900/60 rounded-2xl border border-ink-800 mb-6">
      {TABS.map((tab) => {
        const Icon     = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <Button
            key={tab.id}
            variant={isActive ? 'primary' : 'secondary'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
            iconLeft={<Icon size={15} />}
            className="flex-1 justify-center"
          >
            <span className="hidden md:inline">{tab.label}</span>
          </Button>
        );
      })}
    </div>
  );

  // ─── Radar Chart Helper ──────────────────────────────────────────────────

  const renderRadarChart = () => {
    const weightKeys = Object.keys(WEIGHT_LABELS) as (keyof ScoringWeights)[];
    const cx = 140, cy = 140, maxR = 110;
    const angleStep = (2 * Math.PI) / 5;
    const startAngle = -Math.PI / 2; // top

    const getPoint = (index: number, value: number) => {
      const angle = startAngle + index * angleStep;
      const r = (value / 100) * maxR;
      return { x: cx + r * Math.cos(angle), y: cy + r * Math.sin(angle) };
    };

    // Pentagon grid rings
    const rings = [20, 40, 60, 80, 100];

    // Data polygon points
    const dataPoints = weightKeys.map((key, i) => getPoint(i, weights[key]));
    const dataPath = dataPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') + ' Z';

    return (
      <div className="flex justify-center mb-6">
        <svg viewBox="0 0 280 280" className="w-full max-w-[280px] h-auto">
          {/* Grid rings */}
          {rings.map((ringVal) => {
            const ringPoints = Array.from({ length: 5 }, (_, i) => getPoint(i, ringVal));
            const ringPath = ringPoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ') + ' Z';
            return <path key={ringVal} d={ringPath} fill="none" stroke="#334155" strokeWidth="0.5" opacity={0.6} />;
          })}
          {/* Axes */}
          {weightKeys.map((_, i) => {
            const end = getPoint(i, 100);
            return <line key={i} x1={cx} y1={cy} x2={end.x} y2={end.y} stroke="#475569" strokeWidth="0.5" />;
          })}
          {/* Data polygon */}
          <path d={dataPath} fill="rgba(16,185,129,0.15)" stroke="#10b981" strokeWidth="2" strokeLinejoin="round" />
          {/* Data points */}
          {dataPoints.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={4} fill="#10b981" stroke="#0f172a" strokeWidth="2" />
          ))}
          {/* Labels */}
          {weightKeys.map((key, i) => {
            const labelPoint = getPoint(i, 125);
            return (
              <text
                key={key}
                x={labelPoint.x}
                y={labelPoint.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="9"
                fill="#94a3b8"
                fontWeight="500"
              >
                {WEIGHT_LABELS[key].split(' ').slice(0, 2).join(' ')}
              </text>
            );
          })}
        </svg>
      </div>
    );
  };

  // ─── Live Preview Cards ─────────────────────────────────────────────────

  const renderLivePreview = () => {
    const previewCards = [
      { label: 'Top przetarg', score: 87, color: 'text-go', bg: 'bg-go/15', border: 'border-go/30' },
      { label: 'Średni', score: 64, color: 'text-amber-400', bg: 'bg-amber-400/15', border: 'border-amber-400/30' },
      { label: 'Najgorszy', score: 41, color: 'text-nogo', bg: 'bg-nogo/15', border: 'border-nogo/30' },
    ];

    return (
      <div className="mt-4 pt-4 border-t border-ink-800">
        <p className="text-xs text-slate-500 mb-3 font-medium">Przykładowy scoring</p>
        <div className="grid grid-cols-3 gap-2">
          {previewCards.map((card) => (
            <div key={card.label} className={`rounded-xl px-3 py-2.5 ${card.bg} border ${card.border} text-center`}>
              <p className="text-[10px] text-slate-400 mb-0.5">{card.label}</p>
              <p className={`text-lg font-bold ${card.color}`}>{card.score}</p>
            </div>
          ))}
        </div>
      </div>
    );
  };

  // ─── Tab 1: Konfiguracja Wag ─────────────────────────────────────────────

  const renderWeightsTab = () => (
    <div className="space-y-6">
      <GlassCard>
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-em/20 flex items-center justify-center">
                <Target size={20} className="text-em" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-100">Wagi Scoringowe</h2>
                <p className="text-sm text-slate-500">Dostosuj priorytety algorytmu oceny</p>
              </div>
            </div>
            {/* Sum badge */}
            <div className={[
              'px-4 py-2 rounded-md text-sm font-bold border',
              isValidSum
                ? 'bg-go/15 text-go border-go/30'
                : 'bg-nogo/15 text-nogo border-nogo/30',
            ].join(' ')}>
              Suma: {weightSum}/100
              {!isValidSum && <span className="ml-2">⚠️</span>}
            </div>
          </div>

          {/* Radar Chart */}
          {renderRadarChart()}

          {/* Live Preview */}
          {renderLivePreview()}

          {/* Sliders */}
          <div className="space-y-5">
            {(Object.keys(WEIGHT_LABELS) as (keyof ScoringWeights)[]).map((key) => (
              <div key={key} className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="label-base text-sm">{WEIGHT_LABELS[key]}</label>
                  <span className="px-2.5 py-0.5 rounded-md bg-em/20 text-em text-sm font-bold min-w-[3rem] text-center">
                    {weights[key]}
                  </span>
                </div>
                {/* Range slider — em thumb via Tailwind arbitrary + CSS var */}
                <div className="relative">
                  <input
                    type="range"
                    aria-label="Waga parametru"
                    min={0}
                    max={100}
                    value={weights[key]}
                    onChange={(e) => handleWeightChange(key, parseInt(e.target.value))}
                    className="w-full h-2 rounded-full appearance-none cursor-pointer
                      [&::-webkit-slider-track]:rounded-full [&::-webkit-slider-track]:bg-ink-800
                      [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:h-4
                      [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-em
                      [&::-webkit-slider-thumb]:shadow-md-glow
                      [&::-moz-range-track]:rounded-full [&::-moz-range-track]:bg-ink-800
                      [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:h-4
                      [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-em [&::-moz-range-thumb]:border-0"
                  />
                  {/* Progress fill */}
                  <div
                    className="absolute top-0 left-0 h-2 rounded-full bg-em/40 pointer-events-none"
                    style={{ width: `${weights[key]}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Action buttons */}
          <div className="flex gap-3 mt-6 pt-6 border-t border-ink-800">
            <Button
              variant="primary"
              size="md"
              onClick={handleSaveWeights}
              disabled={!isValidSum}
              loading={saving}
              iconLeft={<Save size={15} />}
            >
              {saving ? 'Zapisywanie…' : 'Zapisz konfigurację'}
            </Button>
            <Button
              variant="secondary"
              size="md"
              onClick={handleResetWeights}
              iconLeft={<RotateCcw size={15} />}
            >
              Resetuj
            </Button>
          </div>
        </div>
      </GlassCard>

      {/* Top 10 Preview */}
      <GlassCard>
        <div className="p-6">
          <div className="flex items-center gap-3 mb-4">
            <TrendingUp size={18} className="text-em" />
            <h3 className="text-base font-semibold text-slate-100">Podgląd Top 10</h3>
            <span className="text-xs text-slate-600">(live preview)</span>
          </div>

          {topTenders.length > 0 ? (
            <div className="space-y-2">
              {topTenders.map((tender, idx) => {
                const score = tender.match_score || 0;
                const delta = tender.prev_score ? score - tender.prev_score : 0;
                return (
                  <motion.div
                    key={tender.id || idx}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="flex items-center gap-3 px-3 py-2 rounded-xl bg-ink-900/40 hover:bg-ink-900/60 transition-colors"
                  >
                    <span className="text-xs font-bold text-em w-6 text-center">
                      #{idx + 1}
                    </span>
                    <span className="text-sm text-slate-200 flex-1 truncate">
                      {tender.title || `Przetarg ${tender.id}`}
                    </span>
                    <div className="flex items-center gap-2 min-w-[140px]">
                      <div className="flex-1 h-2 bg-ink-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-em/60 to-em rounded-full transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-500"
                          style={{ width: `${Math.min(100, score)}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-slate-500 w-8 text-right">
                         {(score ?? 0).toFixed(0)}
                      </span>
                      {delta !== 0 && (
                        <span className={`text-xs font-bold ${delta > 0 ? 'text-go' : 'text-nogo'}`}>
                           {delta > 0 ? '↑' : '↓'}{Math.abs(delta ?? 0).toFixed(1)}
                        </span>
                      )}
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-slate-600 text-sm">
              Brak danych przetargów do wyświetlenia
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );

  // ─── Tab 2: Score Analytics ──────────────────────────────────────────────

  const renderAnalyticsTab = () => {
    const breakdown  = analysis?.score_breakdown || [];
    const totalScore = analysis?.total_score || 0;
    const percentile = analysis?.percentile || Math.max(1, Math.round((1 - totalScore / 100) * 100));

    return (
      <div className="space-y-6">
        <GlassCard>
          <div className="p-6">
            <h3 className="text-base font-semibold text-slate-100 mb-4">Wybierz przetarg do analizy</h3>
            <select
              value={selectedTenderId}
              aria-label="Wybierz przetarg do analizy"
              onChange={(e) => handleSelectTender(e.target.value)}
              className="w-full px-4 py-2.5 rounded-xl bg-ink-900/60 border border-ink-800 text-slate-100 text-sm focus:outline-none focus:border-em/50 transition-colors"
            >
              <option value="">— Wybierz przetarg —</option>
              {tenderList.map((t) => (
                <option key={t.id} value={t.id}>{t.title || t.id}</option>
              ))}
            </select>
          </div>
        </GlassCard>

        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="w-8 h-8 border-2 border-em border-t-transparent rounded-full animate-spin" />
          </div>
        )}

        {!loading && analysis && (
          <>
            {/* Percentile Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="flex items-center justify-center"
            >
              <div className="px-6 py-3 rounded-full bg-em/15 border border-em/30">
                <span className="text-em font-bold text-lg">
                  Top {percentile}% w kategorii CPV
                </span>
              </div>
            </motion.div>

            {/* Waterfall Chart */}
            <GlassCard>
              <div className="p-6">
                <h3 className="text-base font-semibold text-slate-100 mb-4">Rozkład Score — Waterfall</h3>
                <svg viewBox="0 0 600 260" className="w-full" role="img" aria-label="Score waterfall chart">
                  {breakdown.length > 0 ? breakdown.map((item, idx) => {
                    const barWidth = Math.max(10, (item.contribution / 100) * 450);
                    const y = 10 + idx * 48;
                    const gradientId = `grad-${idx}`;
                    return (
                      <g key={item.criterion || idx}>
                        <defs>
                          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%"   stopColor="#10b981" stopOpacity="0.4" />
                            <stop offset="100%" stopColor="#10b981" stopOpacity="1"   />
                          </linearGradient>
                        </defs>
                        <rect x={130} y={y} width={barWidth} height={32} rx={6} fill={`url(#${gradientId})`} />
                        <text x={4} y={y + 20} fontSize="11" fill="#e2e8f0" fontWeight="500">
                          {item.criterion}
                        </text>
                        <text x={135 + barWidth + 8} y={y + 20} fontSize="11" fill="#10b981" fontWeight="700">
                           +{(item.contribution ?? 0).toFixed(1)}
                        </text>
                      </g>
                    );
                  }) : (
                    <text x={300} y={130} textAnchor="middle" fontSize="13" fill="#64748b">
                      Brak danych breakdown
                    </text>
                  )}
                  {breakdown.length > 0 && (
                    <g>
                      <line x1={130} y1={250} x2={580} y2={250} stroke="#334155" strokeWidth="1" />
                      <text x={130} y={248} fontSize="12" fill="#94a3b8" fontWeight="600">
                         Total: {(totalScore ?? 0).toFixed(1)} / 100
                      </text>
                    </g>
                  )}
                </svg>
              </div>
            </GlassCard>

            {/* Contribution Bars */}
            <GlassCard>
              <div className="p-6">
                <h3 className="text-base font-semibold text-slate-100 mb-4">Contribution Breakdown</h3>
                <div className="space-y-4">
                  {breakdown.length > 0 ? breakdown.map((item, idx) => {
                    const maxContribution = Math.max(...breakdown.map(b => b.contribution), 1);
                    const widthPct = (item.contribution / maxContribution) * 100;
                    return (
                      <motion.div
                        key={item.criterion || idx}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.08 }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm text-slate-300">{item.criterion}</span>
                          <span className="text-sm font-bold text-em">+{(item.contribution ?? 0).toFixed(1)}</span>
                        </div>
                        <div className="w-full h-1.5 bg-ink-800 rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-500"
                            style={{ width: `${widthPct}%` }}
                          />
                        </div>
                      </motion.div>
                    );
                  }) : (
                    <div className="text-center py-6 text-slate-600 text-sm">Brak danych contribution</div>
                  )}
                </div>
              </div>
            </GlassCard>

            {/* Deadline Bonus Chart */}
            <GlassCard>
              <div className="p-6">
                <h3 className="text-base font-semibold text-slate-100 mb-4">Deadline Bonus — Krzywa czasowa</h3>
                <svg viewBox="0 0 600 220" className="w-full" role="img" aria-label="Deadline bonus curve">
                  {/* Grid lines */}
                  {[0, 25, 50].map((v) => {
                    const y = 20 + (1 - v / 50) * 160;
                    return (
                      <g key={v}>
                        <line x1={60} y1={y} x2={560} y2={y} stroke="#334155" strokeWidth="0.5" strokeDasharray="4,4" />
                        <text x={50} y={y + 4} textAnchor="end" fontSize="10" fill="#64748b">{v}%</text>
                      </g>
                    );
                  })}
                  {/* X axis labels */}
                  {DEADLINE_BONUS_DATA.map((pt, idx) => {
                    const x = 60 + (idx / (DEADLINE_BONUS_DATA.length - 1)) * 500;
                    return (
                      <text key={pt.days} x={x} y={205} textAnchor="middle" fontSize="10" fill="#64748b">
                        {pt.days}d
                      </text>
                    );
                  })}
                  {/* Area fill */}
                  <path
                    d={(() => {
                      const points = DEADLINE_BONUS_DATA.map((pt, idx) => ({
                        x: 60 + (idx / (DEADLINE_BONUS_DATA.length - 1)) * 500,
                        y: 20 + (1 - pt.bonus / 50) * 160,
                      }));
                      const parts = [`M ${points[0].x} ${points[0].y}`];
                      for (let i = 1; i < points.length; i++) {
                        const cp1x = points[i - 1].x + (points[i].x - points[i - 1].x) * 0.5;
                        const cp2x = cp1x;
                        parts.push(`C ${cp1x} ${points[i - 1].y} ${cp2x} ${points[i].y} ${points[i].x} ${points[i].y}`);
                      }
                      parts.push(`L ${points[points.length - 1].x} 180 L ${points[0].x} 180 Z`);
                      return parts.join(' ');
                    })()}
                    fill="url(#areaGradient)"
                  />
                  {/* Curve line */}
                  <path
                    d={(() => {
                      const points = DEADLINE_BONUS_DATA.map((pt, idx) => ({
                        x: 60 + (idx / (DEADLINE_BONUS_DATA.length - 1)) * 500,
                        y: 20 + (1 - pt.bonus / 50) * 160,
                      }));
                      const parts = [`M ${points[0].x} ${points[0].y}`];
                      for (let i = 1; i < points.length; i++) {
                        const cp1x = points[i - 1].x + (points[i].x - points[i - 1].x) * 0.5;
                        const cp2x = cp1x;
                        parts.push(`C ${cp1x} ${points[i - 1].y} ${cp2x} ${points[i].y} ${points[i].x} ${points[i].y}`);
                      }
                      return parts.join(' ');
                    })()}
                    fill="none"
                    stroke="#10b981"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                  />
                  {/* Dots */}
                  {DEADLINE_BONUS_DATA.map((pt, idx) => {
                    const x = 60 + (idx / (DEADLINE_BONUS_DATA.length - 1)) * 500;
                    const y = 20 + (1 - pt.bonus / 50) * 160;
                    return <circle key={idx} cx={x} cy={y} r={4} fill="#10b981" stroke="#0f172a" strokeWidth="2" />;
                  })}
                  <defs>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%"   stopColor="#10b981" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
            </GlassCard>
          </>
        )}

        {!loading && !analysis && selectedTenderId && (
          <div className="text-center py-12 text-slate-600 text-sm">
            Brak danych analizy dla wybranego przetargu
          </div>
        )}
      </div>
    );
  };

  // ─── Tab 3: CPV Heatmap ──────────────────────────────────────────────────

  const renderHeatmapTab = () => {
    // eslint-disable-next-line react-hooks/rules-of-hooks
    const uniqueCpv = useMemo(() => {
      const seen = new Map<string, string>();
      heatmapData.forEach((cell) => {
        if (!seen.has(cell.cpv_code)) seen.set(cell.cpv_code, cell.cpv_name);
      });
      return Array.from(seen.entries()).slice(0, 10);
    }, [heatmapData]);

    // eslint-disable-next-line react-hooks/rules-of-hooks
    const quarters = useMemo(() => {
      const qs = new Set<string>();
      heatmapData.forEach((cell) => qs.add(cell.quarter));
      return Array.from(qs).sort().slice(-4);
    }, [heatmapData]);

    const cellSize    = 56;
    const labelWidth  = 180;
    const headerHeight = 40;
    const svgWidth    = labelWidth + quarters.length * (cellSize + 4) + 20;
    const svgHeight   = headerHeight + uniqueCpv.length * (cellSize + 4) + 20;

    return (
      <div className="space-y-6">
        <GlassCard>
          <div className="p-6">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-em/20 flex items-center justify-center">
                <Grid3X3 size={20} className="text-em" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-100">CPV Win Rate Heatmap</h2>
                <p className="text-sm text-slate-500">Analiza skuteczności w kategoriach CPV</p>
              </div>
            </div>

            <div className="overflow-x-auto relative">
              <svg
                viewBox={`0 0 ${svgWidth} ${svgHeight}`}
                className="w-full min-w-[500px]"
                role="img"
                aria-label="CPV heatmap"
              >
                {/* Quarter headers */}
                {quarters.map((q, colIdx) => (
                  <text
                    key={q}
                    x={labelWidth + colIdx * (cellSize + 4) + cellSize / 2}
                    y={25}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#94a3b8"
                    fontWeight="600"
                  >
                    {q}
                  </text>
                ))}

                {/* Rows */}
                {uniqueCpv.map(([code, name], rowIdx) => (
                  <g key={code}>
                    <text
                      x={labelWidth - 8}
                      y={headerHeight + rowIdx * (cellSize + 4) + cellSize / 2 + 4}
                      textAnchor="end"
                      fontSize="10"
                      fill="#cbd5e1"
                    >
                      {name.length > 20 ? name.slice(0, 20) + '…' : name}
                    </text>
                    {quarters.map((q, colIdx) => {
                      const cell    = heatmapData.find((c) => c.cpv_code === code && c.quarter === q);
                      const winRate = cell?.win_rate || 0;
                      const x = labelWidth + colIdx * (cellSize + 4);
                      const y = headerHeight + rowIdx * (cellSize + 4);
                      return (
                        <rect
                          key={`${code}-${q}`}
                          x={x} y={y}
                          width={cellSize} height={cellSize}
                          rx={8}
                          fill={interpolateColor(winRate)}
                          className="cursor-pointer transition-opacity hover:opacity-80"
                          onMouseEnter={(e) => {
                            if (cell) {
                              const rect = (e.target as SVGRectElement).getBoundingClientRect();
                              setHeatmapTooltip({ cell, x: rect.left + rect.width / 2, y: rect.top - 10 });
                            }
                          }}
                          onMouseLeave={() => setHeatmapTooltip(null)}
                        />
                      );
                    })}
                  </g>
                ))}
              </svg>

              {/* Tooltip */}
              {heatmapTooltip && (
                <div
                  className="fixed z-50 px-3 py-2 rounded-xl bg-ink-950 border border-ink-800 shadow-xl pointer-events-none"
                  style={{
                    left: heatmapTooltip.x,
                    top:  heatmapTooltip.y,
                    transform: 'translate(-50%, -100%)',
                  }}
                >
                  <div className="text-xs font-semibold text-slate-100">{heatmapTooltip.cell.cpv_name}</div>
                  <div className="text-xs text-em font-bold">
                     Win rate: {((heatmapTooltip.cell.win_rate ?? 0) * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-slate-500">
                    Przetargów: {heatmapTooltip.cell.count}
                  </div>
                </div>
              )}
            </div>

            {/* Color Legend */}
            <div className="mt-6 flex items-center gap-3">
              <span className="text-xs text-slate-600">Niska</span>
              <div className="flex-1 h-3 rounded-full overflow-hidden flex">
                {Array.from({ length: 20 }).map((_, i) => (
                  <div key={`item-${i}`} className="flex-1 h-full" style={{ backgroundColor: interpolateColor(i / 19) }} />
                ))}
              </div>
              <span className="text-xs text-slate-600">Wysoka</span>
              <span className="text-xs text-slate-700 ml-2">Win Rate</span>
            </div>
          </div>
        </GlassCard>
      </div>
    );
  };

  // ─── Tab 4: Historia Kalibracji ──────────────────────────────────────────

  const renderHistoryTab = () => (
    <div className="space-y-6">
      <GlassCard>
        <div className="p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-em/20 flex items-center justify-center">
              <HistoryIcon size={20} className="text-em" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">Historia Kalibracji</h2>
              <p className="text-sm text-slate-500">Zmiany konfiguracji wag scoringowych</p>
            </div>
          </div>

          {auditHistory.length === 0 ? (
            <div className="text-center py-16">
              <HistoryIcon size={48} className="mx-auto mb-4 text-ink-800" />
              <p className="text-slate-600 text-sm">Brak historii kalibracji</p>
              <p className="text-slate-700 text-xs mt-1">Zmiany wag będą rejestrowane tutaj</p>
            </div>
          ) : (
            <div className="space-y-4">
              {auditHistory.map((entry, idx) => (
                <motion.div
                  key={entry.id || idx}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.05 }}
                  className="relative pl-8 pb-4 border-l-2 border-ink-800 last:border-l-transparent"
                >
                  {/* Timeline dot */}
                  <div className="absolute left-[-5px] top-1 w-2.5 h-2.5 rounded-full bg-em border-2 border-ink-950" />

                  <div className="bg-ink-900/40 rounded-xl p-4 border border-ink-800/50">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-500">
                          {formatTimestamp(entry.timestamp)}
                        </span>
                        <span className="section-label px-2 py-0.5 rounded-md">
                          {entry.user || 'system'}
                        </span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleRestoreConfig(entry)}
                        iconLeft={<RotateCcw size={12} />}
                      >
                        Przywróć
                      </Button>
                    </div>

                    {/* Changes summary */}
                    {entry.details?.old_weights && entry.details?.new_weights && (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 mt-2">
                        {(Object.keys(WEIGHT_LABELS) as (keyof ScoringWeights)[]).map((key) => {
                          const oldVal = entry.details.old_weights?.[key];
                          const newVal = entry.details.new_weights?.[key];
                          if (oldVal === undefined || newVal === undefined || oldVal === newVal) return null;
                          return (
                            <div key={key} className="flex items-center gap-1 text-xs">
                              <span className="text-slate-500">{WEIGHT_LABELS[key]}:</span>
                              <span className="text-nogo/70">{oldVal}</span>
                              <span className="text-slate-700">→</span>
                              <span className="text-go">{newVal}</span>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </GlassCard>
    </div>
  );

  // ─── Main Render ─────────────────────────────────────────────────────────

  // KPI metrics for header (sum indicator)
  const kpiActions = (
    <div className={[
      'px-4 py-2 rounded-md text-sm font-bold border',
      isValidSum
        ? 'bg-go/15 text-go border-go/30'
        : 'bg-nogo/15 text-nogo border-nogo/30',
    ].join(' ')}>
      Suma wag: {weightSum}/100
      {!isValidSum && <span className="ml-2">⚠️</span>}
    </div>
  );

  return (
    <PageShell
      title="Silnik Decyzyjny"
      subtitle="Konfiguracja i kalibracja AI scoring"
      actions={activeTab === 'weights' ? kpiActions : undefined}
    >
      {/* Tab Bar */}
      {renderTabBar()}

      {/* Tab Content */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {activeTab === 'weights'   && renderWeightsTab()}
          {activeTab === 'analytics' && renderAnalyticsTab()}
          {activeTab === 'heatmap'   && renderHeatmapTab()}
          {activeTab === 'history'   && renderHistoryTab()}
        </motion.div>
      </AnimatePresence>
    </PageShell>
  );
}
