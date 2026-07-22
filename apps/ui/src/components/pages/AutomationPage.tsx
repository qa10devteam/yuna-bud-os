'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Zap, Send, CheckCircle, AlertTriangle, Clock, Search,
  FileText, TrendingDown, Bell, Settings, Plus, Trash2,
  ExternalLink, Activity, ToggleLeft, ToggleRight, GitBranch
} from 'lucide-react';
import { PageShell } from '@/components/PageShell';
import { GlassCard } from '@/components/ui/GlassCard';
import { StatusBadge } from '@/components/ui/StatusBadge';

interface Suggestion {
  event: string;
  label: string;
  description: string;
  priority: 'critical' | 'high' | 'medium' | 'low';
  icon: string;
}

interface WebhookItem {
  id: string;
  name: string;
  url: string;
  events: string[];
  active: boolean;
  created_at: string;
}

interface EventLogItem {
  id: string;
  event: string;
  entity_id: string;
  triggered_by: string;
  triggered_at: string;
  status: string;
  response_code: number;
}

const ICON_MAP: Record<string, React.ReactNode> = {
  'send': <Send className="w-4 h-4" />,
  'check-circle': <CheckCircle className="w-4 h-4" />,
  'alert-triangle': <AlertTriangle className="w-4 h-4" />,
  'clock': <Clock className="w-4 h-4" />,
  'search': <Search className="w-4 h-4" />,
  'file-plus': <FileText className="w-4 h-4" />,
  'trending-down': <TrendingDown className="w-4 h-4" />,
};

const PRIORITY_TOKEN: Record<string, string> = {
  critical: 'bg-nogo/15 border border-nogo/30 text-nogo hover:bg-nogo/25',
  high:     'bg-warn/15 border border-warn/30 text-warn hover:bg-warn/25',
  medium:   'bg-indigo/15 border border-indigo/30 text-indigo hover:bg-indigo/25',
  low:      'bg-ink-800/60 border border-ink-700/40 text-slate-400 hover:bg-ink-800',
};

// ─── BPMN 2.0 Tender Workflow Diagram ─────────────────────────────────────────

type NodeType = 'start' | 'task' | 'gateway' | 'end' | 'end_danger';

interface BpmnNode {
  id: string;
  type: NodeType;
  x: number;
  y: number;
  label: string;
  sublabel?: string;
  icon?: string;
}

interface BpmnEdge {
  from: string;
  to: string;
  label?: string;
  labelY?: number;
  labelX?: number;
  path: string;
}

const NODES: BpmnNode[] = [
  { id: 'start',      type: 'start',      x: 55,   y: 95,  label: 'Nowy\nprzetarg BZP',     sublabel: '847 przetargów' },
  { id: 'scraping',   type: 'task',       x: 190,  y: 95,  label: 'Scraping +\nwalidacja',   sublabel: 'BZP, TED, UZP',    icon: '⬇' },
  { id: 'scoring',    type: 'task',       x: 355,  y: 95,  label: 'AI Match\nScore',         sublabel: 'NLP · cosine',     icon: '🤖' },
  { id: 'gw1',        type: 'gateway',    x: 490,  y: 95,  label: 'Score\n> 0.6?' },
  { id: 'ahp',        type: 'task',       x: 625,  y: 95,  label: 'Analiza AHP\n+ Friedman', sublabel: '8 kryteriów',      icon: '📊' },
  { id: 'reko',       type: 'task',       x: 790,  y: 95,  label: 'Rekomendacja\nAI',        sublabel: 'Claude Sonnet',    icon: '💡' },
  { id: 'gw2',        type: 'gateway',    x: 925,  y: 95,  label: 'Decyzja\nGO?' },
  { id: 'knr',        type: 'task',       x: 1060, y: 95,  label: 'Kosztorys\nKNR',          sublabel: 'Normy branżowe',   icon: '📋' },
  { id: 'pdf',        type: 'task',       x: 1215, y: 95,  label: 'Generuj\nOfertę PDF',     sublabel: 'Auto-podpisana',   icon: '📄' },
  { id: 'end_ok',     type: 'end',        x: 1360, y: 95,  label: 'Złożona\noferta',         sublabel: '~23/mies.' },
  { id: 'end_ignore', type: 'end_danger', x: 490,  y: 230, label: 'Zignorowano',             sublabel: 'Score < 0.6' },
  { id: 'end_nogo',   type: 'end_danger', x: 925,  y: 230, label: 'Odrzucono',               sublabel: 'Decyzja NO-GO' },
];

// Helper: get connection point on node edge
function getPort(nodeId: string, side: 'right' | 'left' | 'bottom' | 'top'): [number, number] {
  const n = NODES.find(x => x.id === nodeId)!;
  const TW = 55; // task half-width
  const TH = 22; // task half-height
  const GH = 28; // gateway diamond half-size
  const CR = 20; // circle radius

  if (n.type === 'start' || n.type === 'end' || n.type === 'end_danger') {
    if (side === 'right')  return [n.x + CR, n.y];
    if (side === 'left')   return [n.x - CR, n.y];
    if (side === 'top')    return [n.x, n.y - CR];
    if (side === 'bottom') return [n.x, n.y + CR];
  }
  if (n.type === 'gateway') {
    if (side === 'right')  return [n.x + GH, n.y];
    if (side === 'left')   return [n.x - GH, n.y];
    if (side === 'top')    return [n.x, n.y - GH];
    if (side === 'bottom') return [n.x, n.y + GH];
  }
  // task
  if (side === 'right')  return [n.x + TW, n.y];
  if (side === 'left')   return [n.x - TW, n.y];
  if (side === 'top')    return [n.x, n.y - TH];
  if (side === 'bottom') return [n.x, n.y + TH];
  return [n.x, n.y];
}

const EDGES: BpmnEdge[] = (() => {
  const line = (
    from: string, fSide: 'right' | 'bottom',
    to: string,   tSide: 'left' | 'top',
    label?: string, lx?: number, ly?: number
  ): BpmnEdge => {
    const [x1, y1] = getPort(from, fSide);
    const [x2, y2] = getPort(to, tSide);
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;
    const path = x1 === x2
      ? `M ${x1} ${y1} L ${x2} ${y2}`
      : y1 === y2
        ? `M ${x1} ${y1} L ${x2} ${y2}`
        : `M ${x1} ${y1} C ${x1} ${y1 + (y2 - y1) * 0.5} ${x2} ${y1 + (y2 - y1) * 0.5} ${x2} ${y2}`;
    return { from, to, label, labelX: lx ?? mx, labelY: ly ?? my - 8, path };
  };

  return [
    line('start',   'right',  'scraping',  'left'),
    line('scraping','right',  'scoring',   'left'),
    line('scoring', 'right',  'gw1',       'left'),
    line('gw1',     'right',  'ahp',       'left',  'Tak',  537, 80),
    line('gw1',     'bottom', 'end_ignore','top',   'Nie',  505, 163),
    line('ahp',     'right',  'reko',      'left'),
    line('reko',    'right',  'gw2',       'left'),
    line('gw2',     'right',  'knr',       'left',  'GO',   975, 80),
    line('gw2',     'bottom', 'end_nogo',  'top',   'NO-GO',940, 163),
    line('knr',     'right',  'pdf',       'left'),
    line('pdf',     'right',  'end_ok',    'left'),
  ];
})();

function BpmnTaskNode({ node, selected, onClick }: { node: BpmnNode; selected: boolean; onClick: () => void }) {
  const TW = 55; const TH = 22;
  const isGateway = node.type === 'gateway';
  const isCircle   = node.type === 'start' || node.type === 'end' || node.type === 'end_danger';

  const accentColor = node.type === 'start'      ? '#10b981'
                    : node.type === 'end'         ? '#10b981'
                    : node.type === 'end_danger'  ? '#ef4444'
                    : node.type === 'gateway'     ? '#f59e0b'
                    : '#6ee7b7';

  const fillColor = selected ? `${accentColor}22` : '#1a1815';
  const strokeColor = selected ? accentColor : (isCircle || isGateway ? accentColor : '#3d3830');
  const strokeWidth = (node.type === 'end' || node.type === 'end_danger') ? 2 : (node.type === 'start' ? 3 : 1.5);
  const CR = 20;
  const GH = 28;

  return (
    <g
      style={{ cursor: 'pointer' }}
      onClick={onClick}
      className="bpmn-node"
    >
      {isCircle && (
        <>
          <circle cx={node.x} cy={node.y} r={CR} fill={fillColor} stroke={strokeColor} strokeWidth={strokeWidth} />
          {(node.type === 'end' || node.type === 'end_danger') && (
            <circle cx={node.x} cy={node.y} r={CR - 4} fill="none" stroke={strokeColor} strokeWidth={1.5} />
          )}
          {node.type === 'start' && (
            <circle cx={node.x} cy={node.y} r={8} fill={accentColor} />
          )}
        </>
      )}
      {isGateway && (
        <>
          <polygon
            points={`${node.x},${node.y - GH} ${node.x + GH},${node.y} ${node.x},${node.y + GH} ${node.x - GH},${node.y}`}
            fill={fillColor}
            stroke={strokeColor}
            strokeWidth={1.5}
          />
          <text x={node.x} y={node.y + 1} textAnchor="middle" dominantBaseline="middle" fontSize={8} fill={accentColor} fontWeight="600">✦</text>
        </>
      )}
      {!isCircle && !isGateway && (
        <>
          <rect
            x={node.x - TW} y={node.y - TH}
            width={TW * 2} height={TH * 2}
            rx={7} ry={7}
            fill={fillColor}
            stroke={strokeColor}
            strokeWidth={selected ? 2 : 1.5}
          />
          {selected && (
            <rect
              x={node.x - TW + 0.5} y={node.y - TH + 0.5}
              width={TW * 2 - 1} height={TH * 2 - 1}
              rx={6.5} ry={6.5}
              fill="none"
              stroke={accentColor}
              strokeWidth={1}
              opacity={0.4}
            />
          )}
          {node.icon && (
            <text x={node.x - TW + 12} y={node.y + 1} fontSize={11} dominantBaseline="middle">{node.icon}</text>
          )}
        </>
      )}

      {/* Label */}
      {node.label.split('\n').map((line, i) => (
        <text
          key={i}
          x={isCircle ? node.x : (isGateway ? node.x : node.x + (node.icon ? 6 : 0))}
          y={isCircle
            ? node.y + CR + 14 + i * 13
            : isGateway
              ? node.y + GH + 14 + i * 13
              : node.y - 7 + i * 13}
          textAnchor="middle"
          fontSize={isCircle || isGateway ? 9 : 8.5}
          fill={selected ? '#e7e5e4' : '#a8a29e'}
          fontWeight={selected ? '600' : '400'}
          fontFamily="'Space Grotesk', sans-serif"
        >
          {line}
        </text>
      ))}

      {/* Sublabel (counts/info) */}
      {node.sublabel && (
        <text
          x={node.x}
          y={isCircle
            ? node.y + CR + 14 + node.label.split('\n').length * 13
            : isGateway
              ? node.y + GH + 14 + node.label.split('\n').length * 13
              : node.y + 9 + node.label.split('\n').length * 8}
          textAnchor="middle"
          fontSize={7.5}
          fill="#57534e"
          fontFamily="'Space Grotesk', sans-serif"
        >
          {node.sublabel}
        </text>
      )}
    </g>
  );
}

interface DetailInfo {
  title: string;
  desc: string;
  stats?: { label: string; value: string }[];
}

const NODE_DETAILS: Record<string, DetailInfo> = {
  start:      { title: 'Nowy przetarg BZP/TED', desc: 'Automatyczne pobieranie ogłoszeń z platform zamówień publicznych.', stats: [{ label: 'Dziennie', value: '~120' }, { label: 'Razem', value: '847' }] },
  scraping:   { title: 'Scraping + walidacja danych', desc: 'Parsowanie XML/JSON z BZP, TED, UZP. Filtrowanie CPV, kwoty, terminy.', stats: [{ label: 'Czas', value: '<2s' }, { label: 'Skuteczność', value: '98.2%' }] },
  scoring:    { title: 'AI Match Score', desc: 'Model NLP porównuje opis przetargu z profilem firmy. Cosine similarity + fine-tuned classifier.', stats: [{ label: 'Próg', value: '0.60' }, { label: 'Avg score', value: '0.74' }] },
  gw1:        { title: 'Bramka: Score > 0.6?', desc: 'Decyzja na podstawie AI Match Score. Przetargi poniżej progu są ignorowane.', stats: [{ label: 'Przechodzi', value: '~34%' }, { label: 'Ignoruje', value: '~66%' }] },
  ahp:        { title: 'Analiza AHP + Friedman', desc: 'Wielokryterialna analiza decyzyjna. 8 kryteriów: wartość, termin, ryzyko, branża…', stats: [{ label: 'Kryteria', value: '8' }, { label: 'Czas', value: '~5s' }] },
  reko:       { title: 'Rekomendacja AI', desc: 'Claude Sonnet generuje rekomendację tekstową z uzasadnieniem GO/NO-GO.', stats: [{ label: 'Model', value: 'Claude Sonnet' }, { label: 'Tokeny', value: '~2k' }] },
  gw2:        { title: 'Bramka: Decyzja GO?', desc: 'Człowiek lub auto-reguły zatwierdzają lub odrzucają ofertę na podstawie rekomendacji.', stats: [{ label: 'GO rate', value: '~71%' }, { label: 'Avg czas', value: '4h' }] },
  knr:        { title: 'Kosztorys KNR', desc: 'Automatyczne generowanie kosztorysu na podstawie norm KNR. Import z Normy PRO.', stats: [{ label: 'Pozycji', value: '50–200' }, { label: 'Dokładność', value: '±3%' }] },
  pdf:        { title: 'Generuj Ofertę PDF', desc: 'Kompilacja oferty: kosztorys + dane firmy + podpis elektroniczny. Format ZP-ORG.', stats: [{ label: 'Czas', value: '<10s' }, { label: 'Format', value: 'PDF/A-1b' }] },
  end_ok:     { title: 'Złożona oferta', desc: 'Oferta przesłana do platformy zamówień. Status monitorowany automatycznie.', stats: [{ label: 'Miesięcznie', value: '~23' }, { label: 'Win rate', value: '38%' }] },
  end_ignore: { title: 'Zignorowano', desc: 'Przetarg nie spełnił minimalnego progu dopasowania AI. Bez dalszych działań.', stats: [{ label: 'Dziennie', value: '~79' }] },
  end_nogo:   { title: 'Odrzucono (NO-GO)', desc: 'Przetarg nie uzyskał decyzji GO. Może wrócić do analizy przy zmianie parametrów.', stats: [{ label: 'Miesięcznie', value: '~12' }] },
};

export function BpmnTenderFlow() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = selectedId ? NODES.find(n => n.id === selectedId) : null;
  const detail = selectedId ? NODE_DETAILS[selectedId] : null;

  return (
    <GlassCard className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-em" />
          Przepływ przetargowy BPMN 2.0
        </h3>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="w-2 h-2 rounded-full bg-em inline-block" /> Start
          <span className="w-2 h-2 rounded-full bg-warn inline-block ml-2" /> Bramka
          <span className="w-2 h-2 rounded-full bg-nogo inline-block ml-2" /> Koniec ✗
        </div>
      </div>

      {/* SVG Diagram */}
      <div className="overflow-x-auto rounded-lg border border-ink-800/60 bg-ink-950/60">
        <svg
          viewBox="0 0 1420 295"
          style={{ minWidth: 900, width: '100%', height: 'auto', minHeight: 200, maxHeight: 300 }}
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill="#57534e" />
            </marker>
            <marker id="arrow-sel" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
              <path d="M0,0 L0,6 L8,3 z" fill="#10b981" />
            </marker>
          </defs>

          {/* Background grid dots */}
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="0.8" fill="#292524" />
          </pattern>
          <rect width="1420" height="295" fill="url(#grid)" />

          {/* Swim lane hint */}
          <rect x="10" y="10" width="1400" height="158" rx="6" fill="none" stroke="#292524" strokeWidth="1" strokeDasharray="4 4" />
          <text x="18" y="23" fontSize="8" fill="#44403c" fontFamily="'Space Grotesk', sans-serif">LANE: Automatyczny pipeline</text>
          <rect x="10" y="178" width="1400" height="108" rx="6" fill="none" stroke="#292524" strokeWidth="1" strokeDasharray="4 4" />
          <text x="18" y="191" fontSize="8" fill="#44403c" fontFamily="'Space Grotesk', sans-serif">LANE: Ścieżki odrzucenia</text>

          {/* Edges */}
          {EDGES.map((edge) => {
            const isSel = selectedId === edge.from || selectedId === edge.to;
            return (
              <g key={`${edge.from}-${edge.to}`}>
                <path
                  d={edge.path}
                  fill="none"
                  stroke={isSel ? '#10b981' : '#44403c'}
                  strokeWidth={isSel ? 2 : 1.5}
                  markerEnd={isSel ? 'url(#arrow-sel)' : 'url(#arrow)'}
                  opacity={isSel ? 1 : 0.7}
                />
                {edge.label && (
                  <text
                    x={edge.labelX}
                    y={edge.labelY}
                    textAnchor="middle"
                    fontSize={8}
                    fill={isSel ? '#10b981' : '#78716c'}
                    fontWeight="600"
                    fontFamily="'Space Grotesk', sans-serif"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => (
            <BpmnTaskNode
              key={node.id}
              node={node}
              selected={selectedId === node.id}
              onClick={() => setSelectedId(selectedId === node.id ? null : node.id)}
            />
          ))}
        </svg>
      </div>

      {/* Detail panel */}
      <AnimatePresence>
        {selected && detail && (
          <motion.div
            key={selected.id}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="flex items-start gap-4 px-4 py-3 rounded-lg border border-em/20 bg-em/5">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-slate-100 mb-1">{detail.title}</div>
                <div className="text-xs text-slate-400">{detail.desc}</div>
              </div>
              {detail.stats && (
                <div className="flex gap-4 shrink-0">
                  {detail.stats.map(s => (
                    <div key={s.label} className="text-center">
                      <div className="text-base font-bold text-em">{s.value}</div>
                      <div className="text-xs text-slate-500">{s.label}</div>
                    </div>
                  ))}
                </div>
              )}
              <button type="button"
                onClick={() => setSelectedId(null)}
                className="text-slate-600 hover:text-slate-400 text-xs shrink-0"
              >✕</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!selected && (
        <p className="text-xs text-slate-600 text-center">Kliknij element diagramu, aby zobaczyć szczegóły</p>
      )}
    </GlassCard>
  );
}

// ─── Action Button ────────────────────────────────────────────────────────────

function ActionButton({
  suggestion,
  onTrigger,
  loading,
}: {
  suggestion: Suggestion;
  onTrigger: () => void;
  loading: boolean;
}) {
  return (
    <motion.button
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={onTrigger}
      disabled={loading}
      className={`
        w-full flex items-center gap-3 px-4 py-3 rounded-md transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 text-left
        ${PRIORITY_TOKEN[suggestion.priority]}
        ${loading ? 'opacity-50 cursor-wait' : 'cursor-pointer'}
      `}
    >
      <div className="shrink-0">
        {ICON_MAP[suggestion.icon] || <Zap className="w-4 h-4" />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-medium text-sm">{suggestion.label}</div>
        <div className="text-xs opacity-75 truncate">{suggestion.description}</div>
      </div>
      {loading && (
        <div className="animate-spin w-4 h-4 border-2 border-current border-t-transparent rounded-full" />
      )}
    </motion.button>
  );
}

// ─── Smart Suggestions Panel ──────────────────────────────────────────────────

export function AutomationSuggestions({
  entityType,
  entityId,
  authFetch,
}: {
  entityType: 'kosztorys' | 'tender';
  entityId: string;
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading, setLoading] = useState<string | null>(null);
  const [triggered, setTriggered] = useState<string[]>([]);

  useEffect(() => {
    authFetch(`/api/v2/automations/suggestions/${entityType}/${entityId}`)
      .then(r => r.json())
      .then(data => setSuggestions(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [entityType, entityId, authFetch]);

  const handleTrigger = async (suggestion: Suggestion) => {
    setLoading(suggestion.event);
    try {
      await authFetch('/api/v2/automations/trigger', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event: suggestion.event,
          entity_id: entityId,
          payload: {},
        }),
      });
      setTriggered(prev => [...prev, suggestion.event]);
    } catch (e) {
      console.error('Trigger failed:', e);
    } finally {
      setLoading(null);
    }
  };

  if (!suggestions.length) return null;

  return (
    <div className="space-y-2">
      <div className="section-label flex items-center gap-2">
        <Zap className="w-3 h-3" />
        <span>Akcje</span>
      </div>
      <AnimatePresence>
        {suggestions.map((s) => (
          <motion.div
            key={s.event}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, x: -20 }}
          >
            {triggered.includes(s.event) ? (
              <div className="flex items-center gap-2 px-4 py-3 rounded-md bg-em/10 border border-em/20 text-em text-sm">
                <CheckCircle className="w-4 h-4" />
                <span>{s.label} — wysłano!</span>
              </div>
            ) : (
              <ActionButton
                suggestion={s}
                onTrigger={() => handleTrigger(s)}
                loading={loading === s.event}
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

// ─── Webhook Manager ──────────────────────────────────────────────────────────

export function WebhookManager({
  authFetch,
}: {
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [webhooks, setWebhooks] = useState<WebhookItem[]>([]);
  const [showAdd, setShowAdd] = useState(false);
  const [newName, setNewName] = useState('');
  const [newUrl, setNewUrl] = useState('');

  const loadWebhooks = useCallback(() => {
    authFetch('/api/v2/automations/webhooks')
      .then(r => r.json())
      .then(data => setWebhooks(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [authFetch]);

  useEffect(() => {
    loadWebhooks();
  }, [loadWebhooks]);

  const addWebhook = async () => {
    if (!newName || !newUrl) return;
    await authFetch('/api/v2/automations/webhooks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName, url: newUrl, events: [] }),
    });
    setNewName('');
    setNewUrl('');
    setShowAdd(false);
    loadWebhooks();
  };

  const toggleWebhook = async (wid: string, active: boolean) => {
    await authFetch(`/api/v2/automations/webhooks/${wid}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !active }),
    });
    loadWebhooks();
  };

  const deleteWebhook = async (wid: string) => {
    await authFetch(`/api/v2/automations/webhooks/${wid}`, { method: 'DELETE' });
    loadWebhooks();
  };

  return (
    <GlassCard className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
          <Settings className="w-4 h-4 text-slate-500" />
          Webhooki n8n
        </h3>
        <button type="button"
          onClick={() => setShowAdd(!showAdd)}
          className="btn-ghost flex items-center gap-1 text-xs px-3 py-1.5"
        >
          <Plus className="w-3 h-3" /> Dodaj
        </button>
      </div>

      {showAdd && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="p-3 rounded-xl border border-ink-700/40 bg-ink-800/30 space-y-2"
        >
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Nazwa (np. 'n8n — powiadomienia')"
            className="input-base w-full text-sm"
          />
          <input
            value={newUrl}
            onChange={e => setNewUrl(e.target.value)}
            placeholder="URL webhook (np. http://localhost:5678/webhook/...)"
            className="input-base w-full text-sm"
          />
          <div className="flex gap-2">
            <button type="button" onClick={addWebhook} className="btn-primary px-3 py-1.5 text-xs">
              Zapisz
            </button>
            <button type="button" onClick={() => setShowAdd(false)} className="btn-ghost px-3 py-1.5 text-xs">
              Anuluj
            </button>
          </div>
        </motion.div>
      )}

      <div className="space-y-2">
        {webhooks.map(wh => (
          <div key={wh.id} className="flex items-center gap-3 px-3 py-2 rounded-md border border-ink-800/60 bg-ink-900/40">
            <button type="button" onClick={() => toggleWebhook(wh.id, wh.active)}>
              {wh.active ? (
                <ToggleRight className="w-5 h-5 text-em" />
              ) : (
                <ToggleLeft className="w-5 h-5 text-slate-600" />
              )}
            </button>
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium text-slate-200 truncate">{wh.name}</div>
              <div className="text-xs text-slate-500 truncate">{wh.url}</div>
            </div>
            <a href={wh.url} target="_blank" rel="noopener" className="text-slate-600 hover:text-slate-400 transition-colors">
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button type="button" onClick={() => deleteWebhook(wh.id)} className="text-slate-600 hover:text-nogo transition-colors">
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {!webhooks.length && (
          <div className="text-center py-6 text-sm text-slate-500">
            <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
            Brak webhooków. Dodaj URL n8n aby aktywować automatyzacje.
          </div>
        )}
      </div>
    </GlassCard>
  );
}

// ─── Event History ────────────────────────────────────────────────────────────

export function AutomationHistory({
  authFetch,
}: {
  authFetch: (url: string, opts?: RequestInit) => Promise<Response>;
}) {
  const [events, setEvents] = useState<EventLogItem[]>([]);

  useEffect(() => {
    authFetch('/api/v2/automations/history?limit=10')
      .then(r => r.json())
      .then(data => setEvents(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [authFetch]);

  if (!events.length) return null;

  return (
    <GlassCard className="p-4 space-y-3">
      <div className="section-label flex items-center gap-2">
        <Activity className="w-3 h-3" />
        <span>Historia automatyzacji</span>
      </div>
      <div className="space-y-1">
        {events.map(ev => (
          <div key={ev.id} className="flex items-center gap-2 text-xs py-1.5 px-2 rounded-md hover:bg-ink-800/40 transition-colors">
            <div className={`w-1.5 h-1.5 rounded-full ${
              ev.status === 'delivered' ? 'bg-em' :
              ev.status === 'failed' ? 'bg-nogo' : 'bg-warn'
            }`} />
            <span className="font-mono text-slate-400">{ev.event}</span>
            <span className="text-slate-700">|</span>
            <span className="text-slate-500 truncate">
              {new Date(ev.triggered_at).toLocaleString('pl-PL', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}
            </span>
            {ev.response_code > 0 && (
              <span className={`ml-auto font-mono ${ev.response_code < 300 ? 'text-em' : 'text-nogo'}`}>
                {ev.response_code}
              </span>
            )}
          </div>
        ))}
      </div>
    </GlassCard>
  );
}

// ─── N8n Status Panel ─────────────────────────────────────────────────────────

interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export function N8nStatusPanel({ authFetch }: { authFetch: (url: string, opts?: RequestInit) => Promise<Response> }) {
  const [status, setStatus] = useState<{ healthy: boolean; version?: string; workflow_count?: number } | null>(null);
  const [workflows, setWorkflows] = useState<N8nWorkflow[]>([]);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    authFetch('/api/v2/automations/n8n/status')
      .then(r => r.json())
      .then(data => setStatus(data?.n8n || data))
      .catch(() => setStatus({ healthy: false }));
    authFetch('/api/v2/automations/n8n/workflows')
      .then(r => r.json())
      .then(data => setWorkflows(Array.isArray(data?.workflows) ? data.workflows : []))
      .catch(() => {});
  }, [authFetch]);

  return (
    <GlassCard className="p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2 font-semibold text-slate-100 text-sm">
          <Activity className="w-4 h-4 text-violet" />
          <span>n8n Engine</span>
          {status && (
            <StatusBadge
              status={status.healthy ? 'success' : 'danger'}
              label={status.healthy ? `v${status.version || '?'} — aktywny` : 'niedostępny'}
            />
          )}
        </div>
        {status && (
          <div className={`w-2 h-2 rounded-full ${status.healthy ? 'bg-em shadow-glow' : 'bg-nogo'}`} />
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-slate-500 mb-3">
        <span>Workflows: <strong className="text-slate-300">{status?.workflow_count ?? workflows.length}</strong></span>
        <span>Aktywne: <strong className="text-slate-300">{workflows.filter(w => w.active).length}</strong></span>
        <button type="button"
          onClick={() => setExpanded(v => !v)}
          className="btn-ghost ml-auto flex items-center gap-1 text-xs px-2 py-1"
        >
          <Settings className="w-3 h-3" />
          {expanded ? 'Ukryj' : 'Szczegóły'}
        </button>
      </div>

      {expanded && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          exit={{ opacity: 0, height: 0 }}
          className="space-y-2 mt-2"
        >
          {workflows.length === 0 ? (
            <p className="text-xs text-slate-600 italic">Brak wdrożonych workflow.</p>
          ) : (
            workflows.map(wf => (
              <div key={wf.id} className="flex items-center gap-2 text-xs bg-ink-800/40 rounded-md px-3 py-2">
                {wf.active
                  ? <ToggleRight className="w-4 h-4 text-em shrink-0" />
                  : <ToggleLeft className="w-4 h-4 text-slate-600 shrink-0" />
                }
                <span className="flex-1 truncate text-slate-300">{wf.name}</span>
                <span className="text-slate-600 font-mono">{wf.id.substring(0, 8)}</span>
              </div>
            ))
          )}
          <a
            href="http://localhost:5678"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-violet hover:underline mt-1"
          >
            <ExternalLink className="w-3 h-3" />
            Otwórz n8n UI
          </a>
        </motion.div>
      )}
    </GlassCard>
  );
}

// ─── Full Automation Page ────────────────────────────────────────────────────

type PageTab = 'przepływ' | 'webhooks' | 'historia';

const TABS: { id: PageTab; label: string; icon: React.ReactNode }[] = [
  { id: 'przepływ', label: 'Przepływ',  icon: <GitBranch className="w-3.5 h-3.5" /> },
  { id: 'webhooks', label: 'Webhooks',  icon: <Settings className="w-3.5 h-3.5" /> },
  { id: 'historia', label: 'Historia',  icon: <Activity className="w-3.5 h-3.5" /> },
];

export default function AutomationPage() {
  const [activeTab, setActiveTab] = useState<PageTab>('przepływ');

  const authFetch = async (url: string, opts?: RequestInit) => {
    const token = localStorage.getItem('token');
    return fetch(url, {
      ...opts,
      headers: { ...opts?.headers, Authorization: `Bearer ${token}` },
    });
  };

  return (
    <PageShell
      title="Automatyzacja"
      subtitle="Reguły i workflow AI"
      actions={
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-violet/10 border border-violet/20 text-violet text-xs font-medium">
          <Zap className="w-3.5 h-3.5" />
          n8n połączony
        </div>
      }
    >
      <div className="space-y-6">
        {/* Tab navigation */}
        <div className="flex gap-1 p-1 rounded-xl bg-ink-900/60 border border-ink-800/60 w-fit">
          {TABS.map(tab => (
            <button type="button"
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`
                flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200
                ${activeTab === tab.id
                  ? 'bg-em/15 text-em border border-em/25 shadow-sm'
                  : 'text-slate-500 hover:text-slate-300 hover:bg-ink-800/40'
                }
              `}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <AnimatePresence mode="wait">
          {activeTab === 'przepływ' && (
            <motion.div
              key="przepływ"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              <BpmnTenderFlow />
              <N8nStatusPanel authFetch={authFetch} />
            </motion.div>
          )}

          {activeTab === 'webhooks' && (
            <motion.div
              key="webhooks"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <WebhookManager authFetch={authFetch} />
            </motion.div>
          )}

          {activeTab === 'historia' && (
            <motion.div
              key="historia"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <AutomationHistory authFetch={authFetch} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </PageShell>
  );
}
