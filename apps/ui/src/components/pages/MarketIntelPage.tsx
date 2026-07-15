'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import { BarChart3, TrendingUp, Calendar, Users, Layers, RefreshCw } from 'lucide-react';

interface OlapRow {
  year: number;
  quarter: number;
  cpv_division: string;
  tender_count: number;
  total_value: number;
  avg_value: number;
  win_rate: number;
}

interface PriceIndex {
  cpv_group: string;
  quarter: string;
  avg_price: number;
  change_pct: number | null;
  sample_size: number;
}

interface Forecast {
  period: number;
  date: string;
  forecast: number;
  lower_ci: number;
  upper_ci: number;
}

interface SeasonalMonth {
  month: number;
  count: number;
  seasonal_index: number;
  peak: boolean;
  trough: boolean;
}

type Tab = 'olap' | 'price' | 'forecast' | 'seasonal' | 'cohort';

export function MarketIntelPage() {
  const authFetch = useAuthFetch();
  const [tab, setTab] = useState<Tab>('olap');
  const [olapData, setOlapData] = useState<OlapRow[]>([]);
  const [priceData, setPriceData] = useState<PriceIndex[]>([]);
  const [forecastData, setForecastData] = useState<Forecast[]>([]);
  const [seasonalData, setSeasonalData] = useState<SeasonalMonth[]>([]);
  const [cohortData, setCohortData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [cpvFilter, setCpvFilter] = useState('');
  const [forecastInsight, setForecastInsight] = useState('');
  const [seasonalInsight, setSeasonalInsight] = useState('');

  const fetchOlap = useCallback(async () => {
    setLoading(true);
    try {
      const params = cpvFilter ? `?cpv_division=${cpvFilter}` : '';
      const data = await authFetch(`/api/v2/analytics/olap${params}`);
      setOlapData(Array.isArray(data) ? data : []);
    } catch { setOlapData([]); }
    setLoading(false);
  }, [authFetch, cpvFilter]);

  const fetchPrice = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/analytics/price-index');
      setPriceData(Array.isArray(data) ? data : []);
    } catch { setPriceData([]); }
    setLoading(false);
  }, [authFetch]);

  const fetchForecast = useCallback(async () => {
    setLoading(true);
    try {
      const params = cpvFilter ? `?cpv_division=${cpvFilter}&periods=6` : '?periods=6';
      const data = await authFetch(`/api/v2/forecast/predict${params}`);
      setForecastData(data?.forecasts || []);
      setForecastInsight(`Metoda: ${data?.method || 'holt_winters'}, dane: ${data?.historical_points || 0} punktów`);
    } catch { setForecastData([]); }
    setLoading(false);
  }, [authFetch, cpvFilter]);

  const fetchSeasonal = useCallback(async () => {
    setLoading(true);
    try {
      const params = cpvFilter ? `?cpv_division=${cpvFilter}` : '';
      const data = await authFetch(`/api/v2/forecast/seasonality${params}`);
      setSeasonalData(data?.months || []);
      setSeasonalInsight(data?.insight || '');
    } catch { setSeasonalData([]); }
    setLoading(false);
  }, [authFetch, cpvFilter]);

  const fetchCohort = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/analytics/cohort');
      setCohortData(Array.isArray(data) ? data : []);
    } catch { setCohortData([]); }
    setLoading(false);
  }, [authFetch]);

  useEffect(() => {
    if (tab === 'olap') fetchOlap();
    else if (tab === 'price') fetchPrice();
    else if (tab === 'forecast') fetchForecast();
    else if (tab === 'seasonal') fetchSeasonal();
    else if (tab === 'cohort') fetchCohort();
  }, [tab, fetchOlap, fetchPrice, fetchForecast, fetchSeasonal, fetchCohort]);

  const tabs: { id: Tab; label: string; icon: typeof BarChart3 }[] = [
    { id: 'olap',     label: 'OLAP Explorer', icon: Layers    },
    { id: 'price',    label: 'Indeks cen',    icon: TrendingUp },
    { id: 'forecast', label: 'Prognoza',      icon: BarChart3  },
    { id: 'seasonal', label: 'Sezonowość',    icon: Calendar   },
    { id: 'cohort',   label: 'Kohorty',       icon: Users      },
  ];

  const monthNames = ['Sty','Lut','Mar','Kwi','Maj','Cze','Lip','Sie','Wrz','Paź','Lis','Gru'];

  const formatPLN = (v: number) => v >= 1_000_000
    ? `${(v/1_000_000).toFixed(1)}M`
    : v >= 1_000
    ? `${(v/1_000).toFixed(0)}k`
    : v.toFixed(0);

  return (
    <PageShell
      title="Analiza Rynku Przetargowego"
      subtitle="OLAP · Indeks cen · Prognozy sezonowe · Kohorty zamawiających"
      actions={
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Filtr CPV (np. 45)"
            value={cpvFilter}
            onChange={e => setCpvFilter(e.target.value)}
            className="input-base w-36"
          />
          <button
            onClick={() => {
              if (tab === 'olap') fetchOlap();
              else if (tab === 'forecast') fetchForecast();
              else if (tab === 'seasonal') fetchSeasonal();
            }}
            className="btn-secondary p-2"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      }
    >
      <div className="space-y-6">

        {/* ── Tab Bar ──────────────────────────────────────────────────────── */}
        <div className="flex gap-1 bg-earth-900/40 p-1 rounded-token-lg border border-earth-800/50">
          {tabs.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={[
                'flex items-center gap-2 px-4 py-2 rounded-token text-sm font-medium transition-all',
                tab === t.id
                  ? 'bg-accent-primary/15 text-accent-primary border border-accent-primary/30'
                  : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/50',
              ].join(' ')}
            >
              <t.icon size={14} />
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Content ──────────────────────────────────────────────────────── */}
        <motion.div
          key={tab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >

          {/* OLAP Tab */}
          {tab === 'olap' && (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-earth-100 mb-4">OLAP — Ewolucja rynku</h2>
              {olapData.length === 0 ? (
                <p className="text-earth-400">Brak danych OLAP{cpvFilter ? ` dla CPV ${cpvFilter}` : ''}</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-earth-700">
                        <th className="text-left py-2 text-earth-400 font-medium">Rok</th>
                        <th className="text-left py-2 text-earth-400 font-medium">Q</th>
                        <th className="text-left py-2 text-earth-400 font-medium">CPV</th>
                        <th className="text-right py-2 text-earth-400 font-medium">Ilość</th>
                        <th className="text-right py-2 text-earth-400 font-medium">Wartość</th>
                        <th className="text-right py-2 text-earth-400 font-medium">Śr. wartość</th>
                        <th className="text-right py-2 text-earth-400 font-medium">Win%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {olapData.slice(0, 30).map((row, i) => (
                        <tr key={i} className="border-b border-earth-800/50 hover:bg-earth-800/30 transition-colors">
                          <td className="py-2 text-earth-200">{row.year}</td>
                          <td className="py-2 text-earth-300">Q{row.quarter}</td>
                          <td className="py-2">
                            <span className="px-2 py-0.5 bg-accent-info/10 text-accent-info rounded-token text-xs">
                              {row.cpv_division}
                            </span>
                          </td>
                          <td className="py-2 text-right text-earth-200">{row.tender_count}</td>
                          <td className="py-2 text-right text-earth-200">{formatPLN(row.total_value)} PLN</td>
                          <td className="py-2 text-right text-earth-300">{formatPLN(row.avg_value)} PLN</td>
                          <td className="py-2 text-right">
                            <span className={
                              row.win_rate > 30 ? 'text-accent-success' :
                              row.win_rate > 0  ? 'text-accent-warning' :
                              'text-earth-500'
                            }>
                              {row.win_rate}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>
          )}

          {/* Price Index Tab */}
          {tab === 'price' && (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-earth-100 mb-4">Indeks cen CPV — kwartalne zmiany</h2>
              {priceData.length === 0 ? (
                <p className="text-earth-400">Brak danych cenowych (za mało przetargów w danej kategorii)</p>
              ) : (
                <div className="space-y-3">
                  {priceData.slice(0, 20).map((row, i) => (
                    <div key={i} className="card-hover flex items-center justify-between p-3">
                      <div>
                        <span className="text-earth-200 font-medium">{row.cpv_group}</span>
                        <span className="ml-3 text-earth-500 text-xs">{row.quarter?.slice(0, 10)}</span>
                      </div>
                      <div className="flex items-center gap-4">
                        <span className="text-earth-300">{formatPLN(row.avg_price)} PLN</span>
                        {row.change_pct !== null && (
                          <span className={`text-sm font-medium ${row.change_pct > 0 ? 'text-accent-danger' : 'text-accent-success'}`}>
                            {row.change_pct > 0 ? '+' : ''}{row.change_pct}%
                          </span>
                        )}
                        <span className="text-earth-500 text-xs">(n={row.sample_size})</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </GlassCard>
          )}

          {/* Forecast Tab */}
          {tab === 'forecast' && (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-earth-100 mb-2">Prognoza — Holt-Winters</h2>
              <p className="text-earth-500 text-sm mb-4">{forecastInsight}</p>
              {forecastData.length === 0 ? (
                <p className="text-earth-400">Brak danych do prognozowania</p>
              ) : (
                <div className="space-y-4">
                  {/* SVG forecast chart */}
                  <svg viewBox="0 0 600 200" className="w-full h-48">
                    {forecastData.map((f, i) => {
                      const x = 50 + i * (500 / forecastData.length);
                      const maxVal = Math.max(...forecastData.map(d => d.upper_ci ?? 0));
                      const scale = 160 / (maxVal || 1);
                      const y = 180 - (f.forecast ?? 0) * scale;
                      const yLow = 180 - (f.lower_ci ?? 0) * scale;
                      const yHigh = 180 - (f.upper_ci ?? 0) * scale;
                      return (
                        <g key={i}>
                          {/* CI band */}
                          <rect x={x - 15} y={yHigh} width={30} height={yLow - yHigh} fill="#10b981" opacity={0.12} rx={4} />
                          {/* Point */}
                          <circle cx={x} cy={y} r={5} fill="#10b981" />
                          {/* Value label */}
                          <text x={x} y={y - 12} textAnchor="middle" fill="#9c8e7e" fontSize="10">
                            {(f.forecast ?? 0).toFixed(0)}
                          </text>
                          {/* Period label */}
                          <text x={x} y={195} textAnchor="middle" fill="#6b5e50" fontSize="9">
                            Q+{f.period}
                          </text>
                        </g>
                      );
                    })}
                    {/* Connect dots */}
                    {forecastData.length > 1 && (
                      <polyline
                        points={forecastData.map((f, i) => {
                          const x = 50 + i * (500 / forecastData.length);
                          const maxVal = Math.max(...forecastData.map(d => d.upper_ci ?? 0));
                          const scale = 160 / (maxVal || 1);
                          return `${x},${180 - f.forecast * scale}`;
                        }).join(' ')}
                        fill="none" stroke="#10b981" strokeWidth={2}
                      />
                    )}
                  </svg>
                  {/* Table */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    {forecastData.map((f, i) => (
                      <div key={i} className="card p-3 text-center">
                        <div className="section-label mb-1">Q+{f.period}</div>
                        <div className="text-earth-100 font-bold text-lg">{(f.forecast ?? 0).toFixed(0)}</div>
                        <div className="text-earth-500 text-xs">{(f.lower_ci ?? 0).toFixed(0)}–{(f.upper_ci ?? 0).toFixed(0)}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </GlassCard>
          )}

          {/* Seasonal Tab */}
          {tab === 'seasonal' && (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-earth-100 mb-2">Sezonowość przetargów</h2>
              <p className="text-earth-500 text-sm mb-4">{seasonalInsight}</p>
              {seasonalData.length === 0 ? (
                <p className="text-earth-400">Brak danych sezonowych</p>
              ) : (
                <div className="grid grid-cols-12 gap-2">
                  {seasonalData.map((m, i) => {
                    const maxIdx = Math.max(...seasonalData.map(s => s.seasonal_index));
                    const height = (m.seasonal_index / (maxIdx || 1)) * 120;
                    return (
                      <div key={i} className="flex flex-col items-center">
                        <div className="relative w-full flex justify-center" style={{ height: 130 }}>
                          <motion.div
                            initial={{ height: 0 }}
                            animate={{ height }}
                            transition={{ delay: i * 0.05 }}
                            className={`w-6 rounded-t-md absolute bottom-0 ${
                              m.peak ? 'bg-accent-primary' : m.trough ? 'bg-accent-danger/60' : 'bg-earth-600'
                            }`}
                          />
                        </div>
                        <div className="text-earth-400 text-xs mt-1">{monthNames[m.month - 1]}</div>
                        <div className="text-earth-500 text-[10px]">{(m.seasonal_index ?? 0).toFixed(2)}</div>
                      </div>
                    );
                  })}
                </div>
              )}
            </GlassCard>
          )}

          {/* Cohort Tab */}
          {tab === 'cohort' && (
            <GlassCard className="p-6">
              <h2 className="text-lg font-semibold text-earth-100 mb-4">Kohorty zamawiających</h2>
              {cohortData.length === 0 ? (
                <p className="text-earth-400">Brak danych kohortowych</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-earth-700">
                        <th className="text-left py-2 text-earth-400">Kohorta</th>
                        <th className="text-right py-2 text-earth-400">Miesiąc+</th>
                        <th className="text-right py-2 text-earth-400">Aktywni</th>
                        <th className="text-right py-2 text-earth-400">Przetargi</th>
                        <th className="text-right py-2 text-earth-400">Wartość</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cohortData.slice(0, 30).map((row, i) => (
                        <tr key={i} className="border-b border-earth-800/50 hover:bg-earth-800/30 transition-colors">
                          <td className="py-2 text-earth-200">{row.cohort_month?.slice(0, 7)}</td>
                          <td className="py-2 text-right text-earth-300">+{row.months_since_first}</td>
                          <td className="py-2 text-right text-earth-200">{row.active_buyers}</td>
                          <td className="py-2 text-right text-earth-200">{row.tender_count}</td>
                          <td className="py-2 text-right text-earth-200">{formatPLN(row.total_value || 0)} PLN</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </GlassCard>
          )}

        </motion.div>
      </div>
    </PageShell>
  );
}
