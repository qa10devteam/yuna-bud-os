'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'motion/react';
import { Activity, TrendingUp, TrendingDown, DollarSign, Users, FileText, Zap } from 'lucide-react';
import { useAuthFetch } from '@/lib/api-v2';

interface MarketKPI {
  total_tenders: number;
  total_value_pln: number;
  avg_value_pln: number;
  tenders_this_month: number;
  tenders_last_month: number;
  month_change_pct: number;
  active_buyers: number;
  active_contractors: number;
  top_cpv_code: string | null;
  top_cpv_count: number;
}

function fmtPLN(v: number): string {
  const n = v ?? 0;
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B PLN`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M PLN`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}k PLN`;
  return `${n.toFixed(0)} PLN`;
}

export default function MarketKPIBar() {
  const authFetch = useAuthFetch();
  const [kpi, setKpi] = useState<MarketKPI | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await authFetch('/api/v2/intelligence/summary');
      setKpi(data);
    } catch { }
    setLoading(false);
  }, [authFetch]);

  useEffect(() => { load(); }, [load]);

  if (loading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3 animate-pulse">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-20 bg-earth-900/50 rounded-token-lg border border-earth-800" />
        ))}
      </div>
    );
  }

  if (!kpi) return null;

  const cards = [
    {
      icon: FileText,
      label: 'Przetargów w bazie',
      value: kpi.total_tenders?.toLocaleString() || '—',
      sub: `${kpi.tenders_this_month || 0} w tym miesiącu`,
      colorCls: 'text-accent-primary',
    },
    {
      icon: DollarSign,
      label: 'Łączna wartość',
      value: fmtPLN(kpi.total_value_pln || 0),
      sub: `Śr. ${fmtPLN(kpi.avg_value_pln || 0)}`,
      colorCls: 'text-accent-primary',
    },
    {
      icon: kpi.month_change_pct >= 0 ? TrendingUp : TrendingDown,
      label: 'Zmiana m/m',
      value: `${kpi.month_change_pct >= 0 ? '+' : ''}${kpi.month_change_pct?.toFixed(1) || 0}%`,
      sub: `vs poprzedni miesiąc`,
      colorCls: kpi.month_change_pct >= 0 ? 'text-accent-primary' : 'text-accent-danger',
    },
    {
      icon: Users,
      label: 'Zamawiający',
      value: kpi.active_buyers?.toLocaleString() || '—',
      sub: 'aktywnych',
      colorCls: 'text-accent-info',
    },
    {
      icon: Activity,
      label: 'Wykonawcy',
      value: kpi.active_contractors?.toLocaleString() || '—',
      sub: 'aktywnych',
      colorCls: 'text-accent-violet',
    },
    {
      icon: Zap,
      label: 'Top CPV',
      value: kpi.top_cpv_code || '—',
      sub: `${kpi.top_cpv_count || 0} przetargów`,
      colorCls: 'text-accent-warning',
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3">
      {cards.map((card, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          className="bg-earth-900/80 border border-earth-700/50 rounded-token-lg p-3"
        >
          <div className="flex items-center gap-1.5 mb-1">
            <card.icon className={`w-3.5 h-3.5 ${card.colorCls}`} />
            <span className="text-xs text-earth-500 truncate">{card.label}</span>
          </div>
          <p className={`text-lg font-bold ${card.colorCls}`}>{card.value}</p>
          <p className="text-xs text-earth-600 mt-0.5">{card.sub}</p>
        </motion.div>
      ))}
    </div>
  );
}
