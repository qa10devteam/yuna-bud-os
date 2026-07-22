'use client';
import { useEffect, useState, useCallback } from 'react';
import { useAuthFetch } from '@/lib/api-v2';
import { GlassCard } from '@/components/ui/GlassCard';
import { PageShell } from '@/components/PageShell';
import { motion } from 'motion/react';
import { Database, Server, Activity, Shield, Cpu, HardDrive, Users, Bell, RefreshCw } from 'lucide-react';

interface Metrics {
  platform: string;
  version: string;
  database: {
    size: string;
    tenders: number;
    embeddings: number;
    doc_chunks: number;
    icb_records: number;
    icb_forecast: number;
    users: number;
    organizations: number;
    audit_entries: number;
    unread_notifications: number;
  };
  pipeline: Record<string, number>;
  ai: {
    embedding_coverage: number;
    rag_chunks: number;
    model: string;
    vector_dim: number;
  };
}

interface DbTable {
  table: string;
  rows: number;
  size: string;
  size_bytes: number;
}

export function SystemPage() {
  const authFetch = useAuthFetch();
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [tables, setTables]   = useState<DbTable[]>([]);
  const [routeCount, setRouteCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [tab, setTab]         = useState<'overview' | 'database' | 'routes'>('overview');

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [m, t, r] = await Promise.all([
        authFetch('/api/v2/system/metrics'),
        authFetch('/api/v2/system/db-stats'),
        authFetch('/api/v2/system/routes'),
      ]);
      setMetrics(m);
      setTables(Array.isArray(t) ? t : []);
      setRouteCount(r?.total_routes || 0);
    } catch {}
    setLoading(false);
  }, [authFetch]);

  useEffect(() => { refresh(); }, [refresh]);

  const stats = metrics ? [
    { label: 'Przetargi',      value: metrics.database.tenders,                    icon: Database,  color: 'text-info' },
    { label: 'Embeddings',     value: `${metrics.ai.embedding_coverage}%`,          icon: Cpu,       color: 'text-success' },
    { label: 'ICB Records',    value: (metrics.database.icb_records ?? 0).toLocaleString(),icon: HardDrive, color: 'text-violet' },
    { label: 'API Routes',     value: routeCount,                                   icon: Server,    color: 'text-warning' },
    { label: 'Users',          value: metrics.database.users,                       icon: Users,     color: 'text-info' },
    { label: 'Notifications',  value: metrics.database.unread_notifications,        icon: Bell,      color: 'text-warning' },
    { label: 'Audit Log',      value: metrics.database.audit_entries,               icon: Shield,    color: 'text-danger' },
    { label: 'DB Size',        value: metrics.database.size,                        icon: Activity,  color: 'text-slate-300' },
  ] : [];

  const actions = (
    <button type="button" onClick={refresh} className="btn-secondary flex items-center gap-2">
      <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Odśwież
    </button>
  );

  return (
    <PageShell
      title="System"
      subtitle={metrics ? `${metrics.platform} v${metrics.version}` : 'Status i diagnostyka platformy'}
      actions={actions}
    >
      {/* Tabs */}
      <div className="flex gap-1 bg-ink-900/60 rounded-xl p-1 w-fit mb-6">
        {(['overview', 'database', 'routes'] as const).map(t => (
          <button type="button"
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? 'bg-em text-ink-950' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {t === 'overview' ? 'Przegląd' : t === 'database' ? 'Baza danych' : 'API Routes'}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <div className="space-y-6">
          {/* Stats grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {stats.map((stat, i) => {
              const Icon = stat.icon;
              return (
                <motion.div
                  key={stat.label}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                >
                  <GlassCard className="p-4 shadow-md-sm">
                    <div className="flex items-center gap-3">
                      <Icon size={18} className={stat.color} />
                      <div>
                        <div className="text-slate-100 font-bold text-lg">{stat.value}</div>
                        <div className="text-slate-500 text-xs">{stat.label}</div>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              );
            })}
          </div>

          {/* Pipeline */}
          {metrics?.pipeline && Object.keys(metrics.pipeline).length > 0 && (
            <GlassCard className="p-4">
              <h3 className="text-slate-100 font-semibold mb-3">Pipeline Status</h3>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(metrics.pipeline).map(([status, count]) => (
                  <div key={status} className="bg-ink-900/60 rounded-xl p-3 text-center border border-ink-800/40">
                    <div className="text-slate-100 font-bold">{count}</div>
                    <div className="text-slate-500 text-xs capitalize">{status}</div>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* AI info */}
          {metrics?.ai && (
            <GlassCard className="p-4">
              <h3 className="text-slate-100 font-semibold mb-3">AI Engine</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Model:</span>
                  <div className="text-slate-200 font-mono text-xs mt-1">{metrics.ai.model}</div>
                </div>
                <div>
                  <span className="text-slate-500">Vector Dim:</span>
                  <div className="text-slate-200">{metrics.ai.vector_dim}</div>
                </div>
                <div>
                  <span className="text-slate-500">Coverage:</span>
                  <div className="text-success font-bold">{metrics.ai.embedding_coverage}%</div>
                </div>
                <div>
                  <span className="text-slate-500">RAG Chunks:</span>
                  <div className="text-slate-200">{metrics.ai.rag_chunks}</div>
                </div>
              </div>
            </GlassCard>
          )}
        </div>
      )}

      {tab === 'database' && (
        <GlassCard className="p-4">
          <h3 className="text-slate-100 font-semibold mb-3">Tabele ({tables.length})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-slate-500 border-b border-ink-800">
                  <th className="text-left py-2 px-2">Tabela</th>
                  <th className="text-right py-2 px-2">Wiersze</th>
                  <th className="text-right py-2 px-2">Rozmiar</th>
                </tr>
              </thead>
              <tbody>
                {tables.map(t => (
                  <tr key={t.table} className="border-b border-ink-900 hover:bg-ink-900/40">
                    <td className="py-2 px-2 text-slate-200 font-mono text-xs">{t.table}</td>
                    <td className="py-2 px-2 text-right text-slate-300">{(t.rows ?? 0).toLocaleString()}</td>
                    <td className="py-2 px-2 text-right text-slate-400">{t.size}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      )}

      {tab === 'routes' && (
        <GlassCard className="p-4">
          <h3 className="text-slate-100 font-semibold mb-3">{routeCount} zarejestrowanych endpointów</h3>
          <p className="text-slate-400 text-sm">Pełna lista API dostępna pod <code className="bg-ink-800 px-1 rounded-md">/api/v2/system/routes</code></p>
        </GlassCard>
      )}
    </PageShell>
  );
}
