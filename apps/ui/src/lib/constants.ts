// ─── Shared constants for YU-NA ────────────────────────────────────────────
// Single source of truth — import from here, never redefine locally.

export const STATUS_LABELS: Record<string, string> = {
  new:          'Nowy',
  matched:      'Dopasowany',
  analyzing:    'Analiza',
  estimated:    'Wyceniony',
  decided_go:   'GO ✓',
  decided_nogo: 'NO-GO ✗',
  archived:     'Archiwum',
  watching:     'Obserwowany',
};

export const STATUS_COLORS: Record<string, string> = {
  new:          'bg-zinc-500/20 text-zinc-300',
  matched:      'bg-blue-500/20 text-blue-300',
  analyzing:    'bg-yellow-500/20 text-yellow-300',
  estimated:    'bg-purple-500/20 text-purple-300',
  decided_go:   'bg-green-500/20 text-green-300',
  decided_nogo: 'bg-red-500/20 text-red-300',
  archived:     'bg-zinc-700/20 text-zinc-500',
  watching:     'bg-cyan-500/20 text-cyan-300',
};
