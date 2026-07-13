'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { useStore } from '@/store/useStore';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import { AlertTriangle, Shield, Zap, Target, Clock, TrendingUp, Play, Briefcase, RefreshCw } from 'lucide-react';

interface Alert {
  tender_id: string;
  title: string;
  buyer: string;
  deadline_at: string;
  value_pln: number | null;
  days_left: number;
  severity: 'critical' | 'warning' | 'info';
  action_required: string;
  pipeline_status: string;
}

interface PortfolioItem {
  tender_id: string;
  title: string;
  value_pln: number;
  win_probability: number;
  effort_hours: number;
  expected_value: number;
  efficiency: number;
  status: string;
}

interface PortfolioResult {
  optimal_portfolio: PortfolioItem[];
  metrics: { total_expected_value: number; total_effort_hours: number; portfolio_efficiency: number; utilization_pct: number };
  dropped: PortfolioItem[];
}

interface ScanResult {
  total_found: number;
  high_priority: number;
  recommendations: Array<{ tender_id: string; title: string; value_pln: number; priority: number; recommendation: string }>;
}

type Tab = 'alerts' | 'portfolio' | 'scan';

export function ProactivePage() {
  const authFetch = useAuthFetch();
  const { setCurrentModule, setSelectedTender } = useStore();
  const [tab, setTab] = useState<Tab>('alerts');
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [portfolio, setPortfolio] = useState<PortfolioResult | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(false);

  const fetchAlerts = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/proactive/alerts?days_ahead=30');
      setAlerts(Array.isArray(data) ? data : []);
    } catch { setAlerts([]); }
    setLoading(false);
  }, [authFetch]);

  const fetchPortfolio = useCallback(async () => {
    setLoading(true);
    try {
      const data = await authFetch('/api/v2/proactive/portfolio?max_concurrent=5&budget_hours=200');
      setPortfolio(data);
    } catch { setPortfolio(null); }
    setLoading(false);
  }, [authFetch]);

  const runScan = useCallback(async () => {
    setScanning(true);
    try {
      const data = await authFetch('/api/v2/proactive/scan', { method: 'POST' });
      setScanResult(data);
    } catch { setScanResult(null); }
    setScanning(false);
  }, [authFetch]);

  useEffect(() => {
    if (tab === 'alerts') fetchAlerts();
    else if (tab === 'portfolio') fetchPortfolio();
  }, [tab, fetchAlerts, fetchPortfolio]);

  const severityConfig = {
    critical: { color: 'text-danger', bg: 'bg-danger/10 border-danger/30', icon: AlertTriangle },
    warning:  { color: 'text-warning', bg: 'bg-warning/10 border-warning/30', icon: Clock },
    info:     { color: 'text-info', bg: 'bg-info/10 border-info/30', icon: Shield },
  };

  const formatPLN = (v: number) => v ? `${(v / 1_000_000).toFixed(2)}M PLN` : '-';

  const actions = (
    <span className="flex items-center gap-1 px-3 py-1 rounded-full bg-success/10 text-success text-xs border border-success/20">
      <span className="w-2 h-2 bg-success rounded-full animate-pulse-soft" />
      Agent aktywny
    </span>
  );

  return (
    <PageShell
      title="Alerty Proaktywne"
      subtitle="AI wykrywanie szans rynkowych"
      actions={actions}
    >
      {/* Tabs */}
      <div className="flex gap-2 mb-6">
        {([
          { id: 'alerts' as Tab, label: 'Alerty', icon: AlertTriangle, count: alerts.filter(a => a.severity === 'critical').length },
          { id: 'portfolio' as Tab, label: 'Portfolio', icon: Briefcase },
          { id: 'scan' as Tab, label: 'Scan AI', icon: Zap },
        ]).map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-token text-sm font-medium transition-all ${
              tab === t.id
                ? 'bg-info/20 text-info border border-info/30'
                : 'text-earth-400 hover:text-earth-200 hover:bg-earth-800/50'
            }`}
          >
            <t.icon size={14} />
            {t.label}
            {'count' in t && t.count! > 0 && (
              <span className="ml-1 px-1.5 py-0.5 bg-danger text-white text-xs rounded-full">{t.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Alerts */}
      {tab === 'alerts' && (
        <div className="space-y-3">
          {alerts.length === 0 ? (
            <GlassCard className="p-8 text-center">
              <Shield size={48} className="mx-auto text-success mb-3" />
              <p className="text-earth-300">Brak pilnych alertów</p>
              <p className="text-earth-500 text-sm">Wszystkie deadline&apos;y pod kontrolą</p>
            </GlassCard>
          ) : (
            alerts.map((alert, i) => {
              const cfg = severityConfig[alert.severity];
              const Icon = cfg.icon;
              return (
                <motion.div
                  key={alert.tender_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <div
                    className={`p-4 border rounded-token-lg bg-earth-900/60 backdrop-blur-sm ${cfg.bg} cursor-pointer hover:scale-[1.01] transition-transform`}
                    onClick={() => { setSelectedTender({ id: alert.tender_id } as any); setCurrentModule('decyzja'); }}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-3">
                        <Icon size={20} className={cfg.color} />
                        <div>
                          <h3 className="text-earth-100 font-medium text-sm">{alert.title?.slice(0, 80)}</h3>
                          <p className="text-earth-400 text-xs mt-1">{alert.buyer}</p>
                          <p className={`text-xs mt-2 ${cfg.color}`}>{alert.action_required}</p>
                        </div>
                      </div>
                      <div className="text-right shrink-0 ml-4">
                        <div className={`text-lg font-bold ${cfg.color}`}>{alert.days_left.toFixed(0)}d</div>
                        <div className="text-earth-500 text-xs">{alert.deadline_at?.slice(0, 10)}</div>
                        {alert.value_pln && <div className="text-earth-300 text-xs mt-1">{formatPLN(alert.value_pln)}</div>}
                      </div>
                    </div>
                  </div>
                </motion.div>
              );
            })
          )}
        </div>
      )}

      {/* Portfolio */}
      {tab === 'portfolio' && portfolio && (
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Expected Value', value: formatPLN(portfolio.metrics.total_expected_value), icon: TrendingUp },
              { label: 'Effort', value: `${portfolio.metrics.total_effort_hours.toFixed(0)}h`, icon: Clock },
              { label: 'Efficiency', value: `${(portfolio.metrics.portfolio_efficiency / 1000).toFixed(1)}k/h`, icon: Target },
              { label: 'Utilization', value: `${portfolio.metrics.utilization_pct}%`, icon: Zap },
            ].map((kpi, i) => (
              <GlassCard key={i} className="p-4 text-center">
                <kpi.icon size={16} className="mx-auto text-info mb-1" />
                <div className="text-earth-100 font-bold text-lg">{kpi.value}</div>
                <div className="text-earth-500 text-xs">{kpi.label}</div>
              </GlassCard>
            ))}
          </div>
          <GlassCard className="p-4">
            <h3 className="text-earth-100 font-semibold mb-3">Optymalny portfel ({portfolio.optimal_portfolio.length} przetargów)</h3>
            <div className="space-y-2">
              {portfolio.optimal_portfolio.map((item, i) => (
                <div
                  key={item.tender_id}
                  className="flex items-center justify-between p-3 bg-earth-900/40 rounded-token hover:bg-earth-800/50 cursor-pointer"
                  onClick={() => { setSelectedTender({ id: item.tender_id } as any); setCurrentModule('decyzja'); }}
                >
                  <div className="flex items-center gap-3">
                    <span className="w-6 h-6 flex items-center justify-center bg-info/20 text-info rounded text-xs font-bold">
                      {i + 1}
                    </span>
                    <div>
                      <div className="text-earth-200 text-sm">{item.title?.slice(0, 60)}</div>
                      <div className="text-earth-500 text-xs">P(win)={(item.win_probability * 100).toFixed(0)}% · {item.effort_hours}h</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-earth-100 font-medium">{formatPLN(item.expected_value)}</div>
                    <div className="text-earth-500 text-xs">{item.efficiency.toFixed(0)} PLN/h</div>
                  </div>
                </div>
              ))}
            </div>
          </GlassCard>
        </div>
      )}

      {/* Scan */}
      {tab === 'scan' && (
        <div className="space-y-4">
          <GlassCard className="p-6 text-center">
            <Zap size={40} className="mx-auto text-info mb-3" />
            <h3 className="text-earth-100 font-semibold mb-2">Proactive AI Scan</h3>
            <p className="text-earth-400 text-sm mb-4">Znajdź przetargi o wysokim potencjale, które nie zostały jeszcze przeanalizowane</p>
            <button
              onClick={runScan}
              disabled={scanning}
              className="btn-primary flex items-center gap-2 mx-auto disabled:opacity-50"
            >
              {scanning ? <RefreshCw size={16} className="animate-spin" /> : <Play size={16} />}
              {scanning ? 'Skanowanie...' : 'Uruchom scan'}
            </button>
          </GlassCard>

          {scanResult && (
            <GlassCard className="p-4">
              <div className="flex items-center gap-3 mb-3">
                <span className="text-success font-bold text-lg">{scanResult.total_found}</span>
                <span className="text-earth-400">znalezionych</span>
                <span className="px-2 py-0.5 bg-danger/10 text-danger rounded text-xs">{scanResult.high_priority} high-priority</span>
              </div>
              <div className="space-y-2">
                {scanResult.recommendations.slice(0, 10).map((rec) => (
                  <div key={rec.tender_id} className="flex items-center justify-between p-2 bg-earth-900/40 rounded-token">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full" style={{ background: `hsl(${rec.priority * 120}, 70%, 50%)` }} />
                      <span className="text-earth-200 text-sm">{rec.title?.slice(0, 50)}</span>
                    </div>
                    <span className="text-earth-400 text-xs">{rec.recommendation}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}
        </div>
      )}
    </PageShell>
  );
}
