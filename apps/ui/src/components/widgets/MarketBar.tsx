'use client';

import { useState, useEffect, useCallback } from 'react';

// ── Types ─────────────────────────────────────────────────────────────────────

interface CurrencyRate {
  code: string;
  rate: number;
  change: number;      // percentage change vs previous day
  change_abs: number;  // absolute change
}

interface CurrenciesResponse {
  rates: CurrencyRate[];
  updated_at: string;
}

// ── Mock fallback ─────────────────────────────────────────────────────────────

const MOCK_RATES: CurrencyRate[] = [
  { code: 'EUR', rate: 4.2963, change:  0.01, change_abs:  0.0004 },
  { code: 'USD', rate: 3.9412, change: -0.23, change_abs: -0.0091 },
  { code: 'CHF', rate: 4.4521, change:  0.08, change_abs:  0.0036 },
];

// ── Live clock ────────────────────────────────────────────────────────────────

function useLiveClock() {
  const [time, setTime] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setTime(
        now.toLocaleTimeString('pl-PL', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: false,
        }),
      );
    };
    tick(); // immediate
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return time;
}

// ── Single currency chip ──────────────────────────────────────────────────────

function CurrencyChip({ rate }: { rate: CurrencyRate }) {
  const positive = rate.change >= 0;
  const arrow = positive ? '↑' : '↓';
  const changeStr = `${arrow}${Math.abs(rate.change).toFixed(2)}%`;

  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-earth-800/60 border border-earth-700/40 select-none">
      <span className="text-[11px] font-bold text-earth-300 tracking-wide">{rate.code}</span>
      <span className="font-mono text-[11px] font-medium text-earth-100 stat-value">
        {rate.rate.toFixed(4)}
      </span>
      <span className="text-[10px] text-earth-600">PLN</span>
      <span
        className={`text-[10px] font-semibold tabular-nums ${
          positive ? 'text-accent-primary' : 'text-accent-danger'
        }`}
      >
        {changeStr}
      </span>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export function MarketBar() {
  const [rates, setRates] = useState<CurrencyRate[]>(MOCK_RATES);
  const [updatedAt, setUpdatedAt] = useState<string>('');
  const [error, setError] = useState(false);
  const clock = useLiveClock();

  const fetchRates = useCallback(() => {
    fetch('/api/v1/market/currencies')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: any) => {
        // API returns rates as object {EUR: {mid, name}, ...} — convert to array
        if (data.rates && !Array.isArray(data.rates)) {
          const parsed: CurrencyRate[] = Object.entries(data.rates).map(([code, val]: [string, any]) => ({
            code,
            rate: val.mid ?? 0,
            change: val.change_pct ?? 0,
            change_abs: val.change_abs ?? 0,
          }));
          setRates(parsed);
        } else if (Array.isArray(data.rates)) {
          setRates(data.rates);
        }
        setUpdatedAt(data.effective_date || data.updated_at || '');
        setError(false);
      })
      .catch(() => {
        setError(true);
        // keep previous rates (or mock)
      });
  }, []);

  useEffect(() => {
    fetchRates();
    const timer = setInterval(fetchRates, 300_000); // 5 minutes — NBP data changes at most once/day
    return () => clearInterval(timer);
  }, [fetchRates]);

  const lastUpdateStr = updatedAt
    ? new Date(updatedAt).toLocaleTimeString('pl-PL', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : null;

  return (
    <div className="sticky top-0 z-40 h-10 flex items-center gap-2 px-4 bg-earth-900/95 border-b border-earth-800/80 backdrop-blur-md">
      {/* Label */}
      <span className="text-[10px] font-bold text-earth-600 uppercase tracking-widest hidden sm:block mr-1">
        NBP
      </span>

      {/* Separator */}
      <div className="h-4 w-px bg-earth-800 hidden sm:block" />

      {/* Currency chips */}
      <div className="flex items-center gap-1.5 flex-1 min-w-0 overflow-x-auto scrollbar-none">
        {rates.map((r) => (
          <CurrencyChip key={r.code} rate={r} />
        ))}
      </div>

      {/* Right-side status */}
      <div className="ml-auto flex items-center gap-3 flex-shrink-0">
        {/* Last update */}
        {lastUpdateStr && (
          <span className="text-[10px] text-earth-600 font-mono hidden md:block">
            akt.&nbsp;{lastUpdateStr}
          </span>
        )}

        {/* Demo badge when API unavailable */}
        {error && (
          <span className="text-[10px] text-accent-warning/80 font-mono">demo</span>
        )}

        {/* Separator */}
        <div className="h-4 w-px bg-earth-800" />

        {/* Live clock */}
        <span className="font-mono text-[11px] font-semibold text-earth-300 tabular-nums tracking-tight stat-value">
          {clock}
        </span>

        {/* Live indicator */}
        <div className="w-1.5 h-1.5 rounded-full bg-accent-primary animate-pulse" />
      </div>
    </div>
  );
}
