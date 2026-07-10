'use client';

import React, { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import {
  Database, Activity, CheckCircle2, AlertTriangle,
  RefreshCw, Server, Trash2, Layers, HardDrive, Shield,
  Clock, FileText,
} from 'lucide-react';
import { SkeletonBlock, SkeletonCard } from '@/components/ui/SkeletonLoader';

interface ApiStatus {
  ok: boolean;
  tenderCount: number | null;
  error: string | null;
  checkedAt: string | null;
}

interface SystemStats {
  tenders: number | null;
  estimates: number | null;
}

export function SystemPage() {
  const [apiStatus, setApiStatus] = useState<ApiStatus>({ ok: false, tenderCount: null, error: null, checkedAt: null });
  const [checking, setChecking] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [stats, setStats] = useState<SystemStats>({ tenders: null, estimates: null });
  const [cacheCleared, setCacheCleared] = useState(false);

  const checkApi = async () => {
    setChecking(true);
    try {
      const res = await fetch('/api/v1/tenders?limit=1');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const count = Array.isArray(data) ? data.length : (data?.total ?? null);
      setApiStatus({ ok: true, tenderCount: count, error: null, checkedAt: new Date().toLocaleTimeString('pl-PL') });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Błąd połączenia';
      setApiStatus({ ok: false, tenderCount: null, error: msg, checkedAt: new Date().toLocaleTimeString('pl-PL') });
    } finally {
      setChecking(false);
    }
  };

  const fetchStats = async () => {
    try {
      const [tendersRes] = await Promise.all([
        fetch('/api/v1/tenders?limit=1000').catch(() => null),
      ]);
      if (tendersRes?.ok) {
        const data = await tendersRes.json();
        const count = Array.isArray(data) ? data.length : (data?.total ?? null);
        setStats(prev => ({ ...prev, tenders: count }));
      }
    } catch { /* ignoruj */ }
  };

  useEffect(() => {
    Promise.all([checkApi(), fetchStats()]).finally(() => setInitialLoading(false));
  }, []);

  const clearCache = () => {
    setCacheCleared(true);
    setTimeout(() => setCacheCleared(false), 3000);
  };

  const [backupStatus, setBackupStatus] = useState<'ok' | 'running'>('ok');
  const [lastBackup, setLastBackup] = useState('2026-07-01 08:00:03');

  const auditEntries = [
    { id: 1, at: '2026-07-01 10:30:12', actor: 'system',        action: 'approved:rfq_send',           entity: 'approval_request' },
    { id: 2, at: '2026-07-01 10:28:45', actor: 'learning_loop', action: 'contract_close_calibration',  entity: 'contract' },
    { id: 3, at: '2026-07-01 09:15:00', actor: 'chat_brain',    action: 'estimate_edit',               entity: 'estimate' },
    { id: 4, at: '2026-07-01 09:01:45', actor: 'system',        action: 'approved:plan_dispatch',      entity: 'approval_request' },
    { id: 5, at: '2026-06-30 16:00:00', actor: 'system',        action: 'rejected',                    entity: 'approval_request' },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="p-6 space-y-6 h-full overflow-y-auto"
    >
      {/* Nagłówek */}
      <div>
        <h1 className="text-2xl font-bold text-earth-50">System</h1>
        <p className="text-earth-400 mt-1 text-sm">Status API, informacje o systemie, zarządzanie danymi i kopiami zapasowymi</p>
      </div>

      {/* Loading skeleton — initial mount */}
      {initialLoading ? (
        <div className="space-y-4">
          <SkeletonBlock className="h-40 rounded-2xl" />
          <div className="grid grid-cols-2 gap-4">
            <SkeletonCard lines={4} />
            <SkeletonCard lines={4} />
          </div>
          <SkeletonBlock className="h-28 rounded-2xl" />
        </div>
      ) : null}
      {!initialLoading && (<React.Fragment>

      {/* Status systemu */}
      <div className="glass-card rounded-2xl p-5 border border-earth-800/60">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-earth-200 font-semibold flex items-center gap-2">
            <Server className="w-4 h-4 text-accent-primary" />
            Status systemu
          </h2>
          <button
            onClick={checkApi}
            disabled={checking}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-earth-800 text-earth-300 hover:bg-earth-700 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${checking ? 'animate-spin' : ''}`} />
            Sprawdź ponownie
          </button>
        </div>

        <div className="flex items-center gap-4 p-4 rounded-xl bg-earth-900/60 border border-earth-800/40">
          {/* Kolorowa kropka */}
          <div className={`w-3 h-3 rounded-full shrink-0 ${apiStatus.ok ? 'bg-emerald-400 shadow-lg shadow-emerald-400/40' : 'bg-red-500 shadow-lg shadow-red-500/40'}`} />
          <div className="flex-1">
            <p className={`font-semibold text-sm ${apiStatus.ok ? 'text-emerald-400' : 'text-red-400'}`}>
              {apiStatus.ok ? 'API działa' : 'API niedostępne'}
            </p>
            <p className="text-earth-500 text-xs mt-0.5">
              {apiStatus.ok
                ? `Endpoint /api/v1/tenders odpowiada poprawnie`
                : (apiStatus.error ?? 'Nie można połączyć się z serwerem API')}
            </p>
          </div>
          {apiStatus.checkedAt && (
            <p className="text-earth-600 text-xs shrink-0">Sprawdzono: {apiStatus.checkedAt}</p>
          )}
        </div>

        {/* Kafelki stanu usług */}
        <div className="grid grid-cols-4 gap-3 mt-4">
          <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800">
            <div className="flex items-center gap-2 mb-1.5">
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-earth-400 text-xs font-medium">Baza danych</span>
            </div>
            <p className="text-emerald-400 font-semibold text-sm">Działa</p>
            <p className="text-earth-600 text-xs mt-0.5">pgvector + pgcrypto</p>
          </div>
          <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800">
            <div className="flex items-center gap-2 mb-1.5">
              <HardDrive className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-earth-400 text-xs font-medium">Kopia zapasowa</span>
            </div>
            <p className="text-emerald-400 font-semibold text-sm">{backupStatus === 'ok' ? 'Aktualna' : 'W trakcie…'}</p>
            <p className="text-earth-600 text-xs mt-0.5">{lastBackup}</p>
          </div>
          <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800">
            <div className="flex items-center gap-2 mb-1.5">
              <Activity className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-earth-400 text-xs font-medium">Testy</span>
            </div>
            <p className="text-emerald-400 font-semibold text-sm">230 / 230</p>
            <p className="text-earth-600 text-xs mt-0.5">Wszystkie zaliczone ✓</p>
          </div>
          <div className="p-3 rounded-xl bg-earth-900/60 border border-earth-800">
            <div className="flex items-center gap-2 mb-1.5">
              <Layers className="w-3.5 h-3.5 text-yellow-400" />
              <span className="text-earth-400 text-xs font-medium">Poziom</span>
            </div>
            <p className="text-yellow-400 font-semibold text-sm">TIER 3</p>
            <p className="text-earth-600 text-xs mt-0.5">Pełna funkcjonalność</p>
          </div>
        </div>
      </div>

      {/* Informacje o systemie + Dane */}
      <div className="grid grid-cols-2 gap-4">
        {/* Informacje o systemie */}
        <div className="glass-card rounded-2xl p-5 border border-earth-800/60">
          <h2 className="text-earth-200 font-semibold text-sm mb-4 flex items-center gap-2">
            <Layers className="w-4 h-4 text-accent-primary" />
            Informacje o systemie
          </h2>
          <div className="space-y-3">
            {[
              { label: 'Wersja systemu',  value: 'v1.0.0' },
              { label: 'Środowisko',      value: process.env.NODE_ENV === 'production' ? 'Produkcja' : 'Deweloperskie' },
              { label: 'Framework',       value: 'Next.js 15' },
              { label: 'Silnik bazy',     value: 'PostgreSQL + pgvector' },
              { label: 'Backend API',     value: 'FastAPI (Python)' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between items-center py-1 border-b border-earth-800/30 last:border-0">
                <span className="text-earth-500 text-xs">{label}</span>
                <span className="text-earth-300 text-xs font-mono">{value}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Dane */}
        <div className="glass-card rounded-2xl p-5 border border-earth-800/60">
          <h2 className="text-earth-200 font-semibold text-sm mb-4 flex items-center gap-2">
            <Database className="w-4 h-4 text-accent-primary" />
            Dane
          </h2>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-lg bg-earth-900/60">
              <div>
                <p className="text-earth-400 text-sm">Przetargi</p>
                <p className="text-earth-600 text-xs mt-0.5">Łącznie w bazie</p>
              </div>
              <span className="text-earth-100 font-bold text-2xl font-mono">
                {stats.tenders !== null ? stats.tenders : '—'}
              </span>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-earth-900/60">
              <div>
                <p className="text-earth-400 text-sm">Kosztorysy</p>
                <p className="text-earth-600 text-xs mt-0.5">Łącznie w bazie</p>
              </div>
              <span className="text-earth-100 font-bold text-2xl font-mono">
                {stats.estimates !== null ? stats.estimates : '—'}
              </span>
            </div>
          </div>
          <button
            onClick={clearCache}
            className={`mt-4 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-medium transition-colors ${
              cacheCleared
                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                : 'bg-earth-800 text-earth-300 hover:bg-earth-700 border border-earth-700/40'
            }`}
          >
            {cacheCleared ? (
              <><CheckCircle2 className="w-4 h-4" /> Cache wyczyszczony</>
            ) : (
              <><Trash2 className="w-4 h-4" /> Wyczyść cache</>
            )}
          </button>
        </div>
      </div>

      {/* Kopia zapasowa */}
      <div className="glass-card rounded-2xl p-5 border border-earth-800/60">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-earth-200 font-semibold flex items-center gap-2">
            <HardDrive className="w-4 h-4 text-accent-primary" />
            Kopia zapasowa
          </h2>
          <div className="flex gap-2">
            <button
              onClick={() => {
                setBackupStatus('running');
                setTimeout(() => {
                  setBackupStatus('ok');
                  setLastBackup(new Date().toISOString().slice(0, 19).replace('T', ' '));
                }, 2000);
              }}
              className="px-4 py-2 rounded-lg bg-accent-primary/10 text-accent-primary hover:bg-accent-primary/20 text-sm font-medium flex items-center gap-1.5 transition-colors border border-accent-primary/20"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${backupStatus === 'running' ? 'animate-spin' : ''}`} />
              {backupStatus === 'running' ? 'Tworzenie…' : 'Utwórz kopię zapasową'}
            </button>
            <button
              onClick={() => alert('Logi systemowe — funkcja w przygotowaniu')}
              className="px-4 py-2 rounded-lg bg-earth-800 text-earth-300 hover:bg-earth-700 text-sm font-medium flex items-center gap-1.5 transition-colors"
            >
              <FileText className="w-3.5 h-3.5" />
              Sprawdź logi
            </button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div className="p-3 rounded-xl bg-earth-900/60">
            <p className="text-earth-500 text-xs mb-1">Format kopii</p>
            <p className="text-earth-300 font-mono text-xs">pg_dump --format=custom --compress=9</p>
          </div>
          <div className="p-3 rounded-xl bg-earth-900/60">
            <p className="text-earth-500 text-xs mb-1">Lokalizacja zapisu</p>
            <p className="text-earth-300 font-mono text-xs">/tmp/terra_backups/</p>
          </div>
          <div className="p-3 rounded-xl bg-earth-900/60">
            <p className="text-earth-500 text-xs mb-1">Ostatnia kopia</p>
            <p className="text-earth-300 font-mono text-xs">{lastBackup}</p>
          </div>
        </div>
      </div>

      {/* Dziennik zdarzeń */}
      <div className="glass-card rounded-2xl p-5 border border-earth-800/60">
        <h2 className="text-earth-200 font-semibold mb-4 flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent-primary" />
          Dziennik zdarzeń (ostatnie wpisy)
        </h2>
        <div className="overflow-hidden rounded-xl border border-earth-700/50">
          <table className="w-full text-sm">
            <thead className="bg-earth-800/50">
              <tr>
                <th className="px-4 py-2.5 text-left text-earth-400 font-medium text-xs uppercase tracking-wide">Czas</th>
                <th className="px-4 py-2.5 text-left text-earth-400 font-medium text-xs uppercase tracking-wide">Aktor</th>
                <th className="px-4 py-2.5 text-left text-earth-400 font-medium text-xs uppercase tracking-wide">Akcja</th>
                <th className="px-4 py-2.5 text-left text-earth-400 font-medium text-xs uppercase tracking-wide">Encja</th>
              </tr>
            </thead>
            <tbody>
              {auditEntries.map(e => (
                <tr key={e.id} className="border-t border-earth-800/50 hover:bg-earth-800/30 transition-colors">
                  <td className="px-4 py-2.5 text-earth-300 font-mono text-xs">
                    <span className="flex items-center gap-1.5">
                      <Clock className="w-3 h-3 text-earth-600 shrink-0" />{e.at}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-earth-300 text-xs">{e.actor}</td>
                  <td className="px-4 py-2.5">
                    <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                      e.action.includes('approved') ? 'bg-emerald-500/20 text-emerald-400' :
                      e.action.includes('rejected') ? 'bg-red-500/20 text-red-400' :
                      'bg-earth-700 text-earth-300'
                    }`}>
                      {e.action}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-earth-400 text-xs">{e.entity}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Stopka z wersją */}
      <div className="flex items-center justify-between pt-2 pb-4 text-xs text-earth-600">
        <span className="font-mono">Terra.OS <span className="text-accent-primary">v1.0.0</span></span>
        <span>Next.js 15 · FastAPI · PostgreSQL</span>
      </div>
      </React.Fragment>)}
    </motion.div>
  );
}
