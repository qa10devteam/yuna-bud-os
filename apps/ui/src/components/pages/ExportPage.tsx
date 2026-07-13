'use client';

import { useState } from 'react';
import { Download, FileText, FileSpreadsheet, Shield, Loader2 } from 'lucide-react';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';
import { PageShell } from '@/components/PageShell';

// ── Polish provinces ──────────────────────────────────────────────────────────

const PROVINCES = [
  'dolnośląskie',
  'kujawsko-pomorskie',
  'lubelskie',
  'lubuskie',
  'łódzkie',
  'małopolskie',
  'mazowieckie',
  'opolskie',
  'podkarpackie',
  'podlaskie',
  'pomorskie',
  'śląskie',
  'świętokrzyskie',
  'warmińsko-mazurskie',
  'wielkopolskie',
  'zachodniopomorskie',
];

const TENDER_LIMITS = [50, 200, 500, 1000] as const;
type TenderLimit = (typeof TENDER_LIMITS)[number];

// ── Helper: trigger file download from blob ───────────────────────────────────

async function downloadBlob(
  url: string,
  filename: string,
  token: string | null,
): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(url, { headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`);
  }

  const blob = await res.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(href);
}

// ── Format badge ──────────────────────────────────────────────────────────────

function FormatBadge({ format }: { format: 'CSV' | 'XLSX' | 'JSON' }) {
  const colors: Record<typeof format, string> = {
    CSV:  'bg-accent-primary/15 text-accent-primary border-accent-primary/30',
    XLSX: 'bg-accent-info/15 text-accent-info border-accent-info/30',
    JSON: 'bg-accent-warning/15 text-accent-warning border-accent-warning/30',
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-mono font-semibold border ${colors[format]}`}
    >
      {format}
    </span>
  );
}

// ── Card wrapper ──────────────────────────────────────────────────────────────

function ExportCard({
  icon: Icon,
  title,
  description,
  format,
  children,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  format: 'CSV' | 'XLSX' | 'JSON';
  children: React.ReactNode;
}) {
  return (
    <div className="card card-hover rounded-token-xl p-6 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="w-10 h-10 rounded-token-lg bg-earth-800/80 border border-earth-700/50 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-earth-300" />
        </div>
        <FormatBadge format={format} />
      </div>

      {/* Title + description */}
      <div className="space-y-1">
        <h3 className="text-sm font-semibold text-earth-100">{title}</h3>
        <p className="text-xs text-earth-400 leading-relaxed">{description}</p>
      </div>

      {/* Slot for filters + button */}
      <div className="mt-auto">{children}</div>
    </div>
  );
}

// ── Download button ───────────────────────────────────────────────────────────

function DownloadButton({
  label,
  loading,
  onClick,
}: {
  label: string;
  loading: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      className="btn-primary w-full flex items-center justify-center gap-2 py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
    >
      {loading ? (
        <Loader2 className="w-4 h-4 animate-spin" />
      ) : (
        <Download className="w-4 h-4" />
      )}
      {loading ? 'Pobieranie...' : label}
    </button>
  );
}

// ── Card 1: Bookmarks CSV ─────────────────────────────────────────────────────

function BookmarksCsvCard() {
  const { accessToken } = useStore();
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      await downloadBlob('/api/v2/bookmarks/export', 'zakładki.csv', accessToken);
      showToast('success', 'Plik zakładki.csv został pobrany');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Nie udało się pobrać pliku');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ExportCard
      icon={FileText}
      title="Zakładki Pipeline"
      description="Eksportuj wszystkie zakładki z etapami, tagami i notatkami"
      format="CSV"
    >
      <DownloadButton label="Pobierz CSV" loading={loading} onClick={handleDownload} />
    </ExportCard>
  );
}

// ── Card 2: Tenders XLSX ──────────────────────────────────────────────────────

function TendersXlsxCard() {
  const { accessToken } = useStore();
  const [loading, setLoading] = useState(false);
  const [cpvPrefix, setCpvPrefix] = useState('');
  const [province, setProvince] = useState('');
  const [limit, setLimit] = useState<TenderLimit>(50);

  const handleDownload = async () => {
    setLoading(true);
    try {
      const q = new URLSearchParams({ limit: String(limit) });
      if (cpvPrefix.trim()) q.set('cpv_prefix', cpvPrefix.trim());
      if (province) q.set('province', province);

      await downloadBlob(
        `/api/v1/excel/export/tenders?${q}`,
        'przetargi.xlsx',
        accessToken,
      );
      showToast('success', 'Plik przetargi.xlsx został pobrany');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Nie udało się pobrać pliku');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ExportCard
      icon={FileSpreadsheet}
      title="Przetargi"
      description="Eksportuj listę przetargów z filtrami CPV i regionem"
      format="XLSX"
    >
      <div className="space-y-3 mb-4">
        {/* CPV prefix */}
        <div className="space-y-1">
          <label className="label-base">Prefiks CPV</label>
          <input
            type="text"
            value={cpvPrefix}
            onChange={(e) => setCpvPrefix(e.target.value)}
            placeholder="45230000"
            maxLength={8}
            className="input-base w-full"
          />
        </div>

        {/* Province */}
        <div className="space-y-1">
          <label className="label-base">Województwo</label>
          <select
            value={province}
            onChange={(e) => setProvince(e.target.value)}
            className="input-base w-full appearance-none"
          >
            <option value="">Wszystkie</option>
            {PROVINCES.map((p) => (
              <option key={p} value={p}>
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </option>
            ))}
          </select>
        </div>

        {/* Limit */}
        <div className="space-y-1">
          <label className="label-base">Liczba wyników</label>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value) as TenderLimit)}
            className="input-base w-full appearance-none"
          >
            {TENDER_LIMITS.map((l) => (
              <option key={l} value={l}>
                {l} rekordów
              </option>
            ))}
          </select>
        </div>
      </div>

      <DownloadButton label="Pobierz XLSX" loading={loading} onClick={handleDownload} />
    </ExportCard>
  );
}

// ── Card 3: GDPR JSON ─────────────────────────────────────────────────────────

function GdprJsonCard() {
  const { accessToken } = useStore();
  const [loading, setLoading] = useState(false);

  const handleDownload = async () => {
    setLoading(true);
    try {
      await downloadBlob('/api/v2/gdpr/export', 'moje-dane.json', accessToken);
      showToast('success', 'Plik moje-dane.json został pobrany');
    } catch (e: unknown) {
      showToast('error', (e as Error).message || 'Nie udało się pobrać pliku');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ExportCard
      icon={Shield}
      title="Moje dane (RODO)"
      description="Pobierz wszystkie dane powiązane z Twoim kontem zgodnie z wymogami RODO"
      format="JSON"
    >
      <div className="mb-4 p-3 rounded-token bg-earth-800/40 border border-earth-700/30">
        <p className="text-[11px] text-earth-500 leading-relaxed">
          Eksport obejmuje profil, zakładki, alerty, historię aktywności oraz wszystkie dane
          powiązane z kontem.
        </p>
      </div>
      <DownloadButton label="Pobierz dane" loading={loading} onClick={handleDownload} />
    </ExportCard>
  );
}

// ── Main ExportPage ───────────────────────────────────────────────────────────

export default function ExportPage() {
  return (
    <PageShell title="Eksport Danych" subtitle="Raporty i eksport do Excel/PDF">
      <div className="space-y-6 max-w-5xl">
        {/* Export cards grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <BookmarksCsvCard />
          <TendersXlsxCard />
          <GdprJsonCard />
        </div>

        {/* Info footer */}
        <div className="flex items-start gap-3 p-4 rounded-token-lg bg-earth-900/40 border border-earth-800/50">
          <div className="w-5 h-5 rounded-full bg-earth-700/60 border border-earth-600/40 flex items-center justify-center flex-shrink-0 mt-0.5">
            <span className="text-[10px] font-bold text-earth-400">i</span>
          </div>
          <p className="text-xs text-earth-500 leading-relaxed">
            Pliki są generowane na podstawie aktualnych danych Twojego konta. Eksport RODO
            zawiera pełne dane zgodnie z art. 20 RODO (prawo do przenoszenia danych).
            W razie pytań skontaktuj się z administratorem systemu.
          </p>
        </div>
      </div>
    </PageShell>
  );
}
