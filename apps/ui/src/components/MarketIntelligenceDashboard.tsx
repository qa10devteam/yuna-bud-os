'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import {
  TrendingUp, TrendingDown, Users, Building2, BarChart3,
  DollarSign, Activity, Globe, Flame, Target,
} from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';

// ── Types ──────────────────────────────────────────────────────────────────────

interface TrendRow {
  quarter: string;
  avg_value_pln: number;
  count: number;
  yoy_change_pct: number | null;
}

interface ContractorTop {
  name: string;
  nip: string | null;
  wins: number;
  total_value_pln: number;
  avg_value_pln: number;
}

interface BuyerTop {
  name: string;
  tenders_count: number;
  total_value_pln: number;
}

interface InflationRow {
  quarter: string;
  category: string;
  index_value: number;
  yoy_pct: number;
}

interface WinRateRow {
  cpv_prefix: string;
  total: number;
  won: number;
  rate: number;
}

interface ICBPrice {
  symbol: string;
  nazwa: string;
  jm: string;
  cena_netto: number;
  typ: string;
}

// ── Formatters ─────────────────────────────────────────────────────────────────

function fmtPLN(v: number): string {
  const n = v ?? 0;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M PLN`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k PLN`;
  return `${n.toFixed(0)} PLN`;
}

function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return '—';
  const n = v ?? 0;
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

// ── Mini chart (sparkline) ─────────────────────────────────────────────────────

function Sparkline({ data, color = '#10b981' }: { data: number[]; color?: string }) {
  if (!data.length) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const w = 120;
  const h = 32;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - ((v - min) / range) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="inline-block">
      <polyline points={points} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  );
}

// ── Card wrapper ───────────────────────────────────────────────────────────────

function Card({ title, icon: Icon, children, className = '' }: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className={`card ${className}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4 text-accent-primary" />
        <h3 className="section-label">{title}</h3>
      </div>
      {children}
    </motion.div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────────

export default function MarketIntelligenceDashboard() {
  const authFetch = useAuthFetch();
  const [trends, setTrends] = useState<TrendRow[]>([]);
  const [contractors, setContractors] = useState<ContractorTop[]>([]);
  const [buyers, setBuyers] = useState<BuyerTop[]>([]);
  const [inflation, setInflation] = useState<InflationRow[]>([]);
  const [winRates, setWinRates] = useState<WinRateRow[]>([]);
  const [icbPrices, setIcbPrices] = useState<ICBPrice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [tRes, cRes, bRes, iRes, wRes, pRes] = await Promise.allSettled([
        authFetch('/api/v2/intelligence/trends?quarters=8'),
        authFetch('/api/v2/intelligence/competitors/top?limit=10'),
        authFetch('/api/v2/intelligence/buyers/top?limit=10'),
        authFetch('/api/v2/intelligence/prices/inflation?quarters=8'),
        authFetch('/api/v2/intelligence/win-rates'),
        authFetch('/api/v2/intelligence/prices/icb?q=robocizna&limit=10'),
      ]);

      if (tRes.status === 'fulfilled') setTrends(tRes.value?.data || []);
      if (cRes.status === 'fulfilled') setContractors(cRes.value?.data || []);
      if (bRes.status === 'fulfilled') setBuyers(bRes.value?.data || []);
      if (iRes.status === 'fulfilled') setInflation(iRes.value?.data || []);
      if (wRes.status === 'fulfilled') setWinRates(wRes.value?.data || []);
      if (pRes.status === 'fulfilled') setIcbPrices(pRes.value?.data || pRes.value?.items || []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Nieznany błąd');
    } finally {
      setLoading(false);
    }
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 animate-pulse">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-48 bg-earth-900/50 rounded-token-lg border border-earth-700/50" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-accent-danger text-sm">{error}</p>
        <button onClick={load} className="mt-2 text-xs text-accent-primary hover:underline">
          Spróbuj ponownie
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-earth-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-accent-primary" />
            Market Intelligence
          </h2>
          <p className="text-xs text-earth-500 mt-0.5">
            Dane: 1.4M przetargów · 784k cen ICB · 81k wykonawców
          </p>
        </div>
        <button
          onClick={load}
          className="btn-ghost text-xs px-3 py-1.5"
        >
          Odśwież
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {/* 1. Trends */}
        <Card title="Trendy wartości przetargów" icon={TrendingUp}>
          {trends.length > 0 ? (
            <div className="space-y-2">
              <Sparkline
                data={trends.map(t => t.avg_value_pln)}
                color={trends[trends.length - 1]?.yoy_change_pct && trends[trends.length - 1].yoy_change_pct! > 0 ? '#10b981' : '#ef4444'}
              />
              <div className="grid grid-cols-2 gap-2 mt-2">
                {trends.slice(-4).map(t => (
                  <div key={t.quarter} className="text-xs">
                    <span className="text-earth-500">{t.quarter}</span>
                    <div className="text-earth-100 font-medium">{fmtPLN(t.avg_value_pln)}</div>
                    <span className={t.yoy_change_pct && t.yoy_change_pct > 0 ? 'text-accent-primary' : 'text-accent-danger'}>
                      {fmtPct(t.yoy_change_pct)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ) : <p className="text-xs text-earth-500">Brak danych trendów</p>}
        </Card>

        {/* 2. Top Contractors */}
        <Card title="Top 10 wykonawców" icon={Users}>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {contractors.slice(0, 10).map((c, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-earth-600 w-4">{i + 1}.</span>
                  <span className="text-earth-300 truncate max-w-[140px]">{c.name}</span>
                </div>
                <div className="text-right">
                  <span className="text-accent-primary font-medium">{c.wins}</span>
                  <span className="text-earth-600 ml-1">wygranych</span>
                </div>
              </div>
            ))}
            {contractors.length === 0 && <p className="text-xs text-earth-500">Brak danych</p>}
          </div>
        </Card>

        {/* 3. Top Buyers */}
        <Card title="Top zamawiający" icon={Building2}>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {buyers.slice(0, 10).map((b, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-earth-300 truncate max-w-[160px]">{b.name}</span>
                <span className="text-earth-400">{fmtPLN(b.total_value_pln)}</span>
              </div>
            ))}
            {buyers.length === 0 && <p className="text-xs text-earth-500">Brak danych</p>}
          </div>
        </Card>

        {/* 4. Inflation Index */}
        <Card title="Indeks inflacji robocizny" icon={Flame}>
          {inflation.length > 0 ? (
            <div className="space-y-2">
              {/* accent-warning = #f59e0b */}
              <Sparkline data={inflation.map(i => i.index_value)} color="#f59e0b" />
              <div className="flex items-center justify-between text-xs mt-2">
                <span className="text-earth-500">Ostatni kwartał</span>
                <span className={inflation[inflation.length - 1]?.yoy_pct > 0 ? 'text-accent-danger' : 'text-accent-primary'}>
                  {fmtPct(inflation[inflation.length - 1]?.yoy_pct)}
                </span>
              </div>
            </div>
          ) : <p className="text-xs text-earth-500">Brak danych inflacji</p>}
        </Card>

        {/* 5. Win Rates by CPV */}
        <Card title="Win-rate per CPV" icon={Target}>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {winRates.slice(0, 8).map((w, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-earth-400 font-mono">{w.cpv_prefix}</span>
                <div className="flex items-center gap-2">
                  <div className="w-16 h-1.5 bg-earth-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent-primary rounded-full"
                      style={{ width: `${w.rate * 100}%` }}
                    />
                  </div>
                  <span className="text-earth-300 w-10 text-right">{(w.rate * 100).toFixed(0)}%</span>
                </div>
              </div>
            ))}
            {winRates.length === 0 && <p className="text-xs text-earth-500">Brak danych</p>}
          </div>
        </Card>

        {/* 6. ICB Prices */}
        <Card title="Ceny ICB (robocizna)" icon={DollarSign}>
          <div className="space-y-1.5 max-h-48 overflow-y-auto">
            {icbPrices.slice(0, 8).map((p, i) => (
              <div key={i} className="flex items-center justify-between text-xs">
                <span className="text-earth-300 truncate max-w-[140px]">{p.nazwa || p.symbol}</span>
                <span className="text-accent-primary font-medium">{(p.cena_netto ?? 0).toFixed(2)} PLN/{p.jm}</span>
              </div>
            ))}
            {icbPrices.length === 0 && <p className="text-xs text-earth-500">Brak danych ICB</p>}
          </div>
        </Card>
      </div>
    </div>
  );
}
