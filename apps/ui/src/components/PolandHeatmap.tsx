'use client';

// PolandHeatmap – Grid 4×4 choropleth for Polish voivodeships (NUTS2)
// Props: data: Array<{ province: string; n: number }>

import React from 'react';

// ── NUTS2 → display name mapping ──────────────────────────────────────────────
const NUTS2_NAMES: Record<string, string> = {
  PL11: 'Łódzkie',
  PL12: 'Mazowieckie',
  PL14: 'Kuj.-Pom.',
  PL21: 'Małopolskie',
  PL22: 'Śląskie',
  PL23: 'Lubelskie',
  PL24: 'Podkarpackie',
  PL31: 'Lubuskie',
  PL32: 'Wielkopolskie',
  PL33: 'Zachodniopom.',
  PL34: 'Dolnośląskie',
  PL41: 'Opolskie',
  PL51: 'Warm.-Maz.',
  PL61: 'Podlaskie',
  PL62: 'Świętokrzyskie',
  PL63: 'Pomorskie',
};

// Fixed grid order: 4 columns × 4 rows, roughly geographic N→S, W→E layout
const GRID_ORDER: string[] = [
  'PL33', // Zachodniopomorskie  – NW
  'PL63', // Pomorskie           – N
  'PL51', // Warmińsko-Mazurskie – NE
  'PL61', // Podlaskie           – E-N
  'PL32', // Wielkopolskie       – W-C
  'PL14', // Kujawsko-Pom.       – C-N
  'PL11', // Łódzkie             – C
  'PL12', // Mazowieckie         – C-E
  'PL31', // Lubuskie            – SW-W
  'PL34', // Dolnośląskie        – SW
  'PL41', // Opolskie            – S-W
  'PL22', // Śląskie             – S-C
  'PL21', // Małopolskie         – S-E
  'PL62', // Świętokrzyskie      – C-SE
  'PL23', // Lubelskie           – SE
  'PL24', // Podkarpackie        – SE
];

interface PolandHeatmapProps {
  data: Array<{ province: string; n: number }>;
}

export function PolandHeatmap({ data }: PolandHeatmapProps) {
  // Build lookup: NUTS2 code → count
  const lookup = React.useMemo(() => {
    const map: Record<string, number> = {};
    for (const row of data) {
      map[row.province] = (map[row.province] ?? 0) + row.n;
    }
    return map;
  }, [data]);

  const maxN = React.useMemo(
    () => Math.max(1, ...Object.values(lookup)),
    [lookup],
  );

  return (
    <div className="grid grid-cols-4 gap-1">
      {GRID_ORDER.map((code) => {
        const n = lookup[code] ?? 0;
        const intensity = n / maxN; // 0..1
        const label = NUTS2_NAMES[code] ?? code;
        const tooltipText = label + ': ' + n.toLocaleString('pl-PL') + ' przetargów';
        // em (#10b981) RGBA overlay: base opacity 0.08 + up to 0.72 based on intensity
        const overlayOpacity = n > 0 ? (0.08 + intensity * 0.72).toFixed(3) : '0';
        const boxShadow = n > 0
          ? `inset 0 0 0 100px rgba(16,185,129,${overlayOpacity})`
          : undefined;

        return (
          <div
            key={code}
            title={tooltipText}
            className="relative flex flex-col items-center justify-center rounded-md border border-ink-700/40 p-1 cursor-default select-none transition-[color,background-color,border-color,opacity,transform,box-shadow] duration-200 hover:scale-105 hover:z-10 bg-ink-900/60"
            style={{ boxShadow, minHeight: '3rem' }}
          >
            <span className="text-[8px] font-medium leading-tight text-center text-slate-300 drop-shadow-sm">
              {label}
            </span>
            {n > 0 && (
              <span className="text-[9px] font-bold tabular-nums text-white/90 mt-0.5 drop-shadow">
                {n >= 1000 ? (n / 1000).toFixed(1) + 'k' : String(n)}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
