import type { ReactNode } from 'react';

/**
 * Marketing layout — no sidebar, no auth required.
 * Covers: /, /budos, /pricing, /signup, /login, /terms, /privacy
 *
 * NOTE: globals.css sets body { background: #050508 } for BudOS dark theme.
 * YU-NA landing (/) uses a light theme — we inject a style tag here
 * so the body bg doesn't bleed through the page's root div on load.
 * Each child page manages its own background via its root element.
 */
export default function MarketingLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <style>{`
        body { background: transparent !important; }
      `}</style>
      {children}
    </>
  );
}
