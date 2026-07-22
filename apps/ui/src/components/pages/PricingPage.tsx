'use client';

import { useState } from 'react';
import Link from 'next/link';
import { PageShell } from '@/components/PageShell';
import { Check, Loader2 } from 'lucide-react';

// ── Plan definitions — matches landing page FEATURE_ROWS ──────────────────────
const PLANS = [
  {
    id: 'fundament',
    name: 'Fundament',
    price: '0 zł',
    period: 'Na start — bez karty',
    popular: false,
    highlight: false,
    features: [
      'Monitoring 100 przetargów/miesiąc',
      'GO/NO-GO AI scoring',
      'Pipeline Kanban',
      '1 kosztorys ICB/miesiąc',
    ],
    locked: [
      'Silnik AI — konfiguracja wag',
      'Decyzja — brief AI',
      'Kreator oferty PDF',
      'Proaktywne alerty',
      'Bid Intelligence — win rate',
      'Competitor tracking',
      'API access + Webhooks',
    ],
  },
  {
    id: 'silnik',
    name: 'Silnik',
    price: '290 zł',
    period: '/miesiąc',
    popular: true,
    highlight: true,
    features: [
      'Monitoring nieograniczony',
      'GO/NO-GO AI scoring',
      'Pipeline Kanban',
      'Kosztorys ICB/Sekocenbud — bez limitu',
      'Silnik AI — konfiguracja wag',
      'Decyzja — brief AI z p10/p50/p90',
      'Kreator oferty PDF',
      'Proaktywne alerty',
    ],
    locked: [
      'Bid Intelligence — win rate',
      'Competitor tracking',
      'API access + Webhooks',
      'Priorytetowe wsparcie',
    ],
  },
  {
    id: 'mozg',
    name: 'Mózg',
    price: '690 zł',
    period: '/miesiąc',
    popular: false,
    highlight: false,
    features: [
      'Wszystko z Silnik',
      'Bid Intelligence — win rate heatmapa',
      'Competitor tracking',
      'API access + Webhooks',
      'Priorytetowe wsparcie (SLA < 4h)',
    ],
    locked: [],
  },
];

// ── PlanCard ──────────────────────────────────────────────────────────────────

interface PlanCardProps {
  id: string;
  name: string;
  price: string;
  period: string;
  popular: boolean;
  highlight: boolean;
  features: string[];
}

function PlanCard({ id, name, price, period, popular, highlight, features }: PlanCardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSelectPlan() {
    if (id === 'free') {
      window.location.href = '/register';
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch('/api/v2/billing/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          plan_id: id,
          success_url: '/billing?success=1',
          cancel_url: '/pricing',
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || 'Błąd podczas tworzenia sesji płatności');
      }

      const data = await res.json();
      if (data.redirect_url && data.redirect_url !== '#stripe-not-configured') {
        window.location.href = data.redirect_url;
      } else {
        setError(data.message || 'Stripe nie jest jeszcze skonfigurowany. Skontaktuj się z nami.');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nieoczekiwany błąd');
    } finally {
      setLoading(false);
    }
  }

  const ctaLabel = id === 'free' ? 'Zacznij za darmo' : `Wybierz ${name}`;

  return (
    <div
      className={`relative rounded-2xl border flex flex-col p-6 transition-[color,background-color,border-color,opacity,transform,box-shadow] ${
        highlight
          ? 'border-em bg-ink-900/80 shadow-glow'
          : 'border-ink-800/60 bg-ink-900/40 card-hover'
      }`}
    >
      {/* Popularne badge */}
      {popular && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 z-10">
          <span className="bg-em text-ink-950 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
            Popularne
          </span>
        </div>
      )}

      {/* Nazwa planu */}
      <h2 className={`text-xl font-bold mb-1 ${highlight ? 'text-em' : 'text-slate-100'}`}>
        {name}
      </h2>

      {/* Cena */}
      <div className="mb-6">
        <span className="text-3xl font-extrabold text-slate-100">{price}</span>
        <span className="text-slate-500 text-sm ml-1">{period}</span>
      </div>

      {/* Lista features */}
      <ul className="space-y-2 flex-1 mb-8">
        {features.map((feature) => (
          <li key={feature} className="flex items-start gap-2 text-sm text-slate-300">
            <Check size={14} className="text-success mt-0.5 shrink-0" />
            {feature}
          </li>
        ))}
      </ul>

      {/* Błąd */}
      {error && (
        <p className="text-xs text-nogo mb-3 text-center">{error}</p>
      )}

      {/* CTA */}
      <button type="button"
        onClick={handleSelectPlan}
        disabled={loading}
        className={`flex items-center justify-center gap-2 rounded-xl py-3 px-4 font-semibold text-sm transition-[color,background-color,border-color,opacity,transform,box-shadow] disabled:opacity-60 disabled:cursor-not-allowed ${
          highlight ? 'btn-primary' : 'btn-secondary'
        }`}
      >
        {loading && <Loader2 size={14} className="animate-spin" />}
        {ctaLabel}
      </button>
    </div>
  );
}

// ── PricingPage ───────────────────────────────────────────────────────────────

export function PricingPage() {
  return (
    <PageShell title="Cennik" subtitle="Wybierz plan dla swojego zespołu">
      {/* Intro */}
      <div className="text-center mb-10">
        <p className="text-slate-400 text-base max-w-2xl mx-auto">
          Zacznij bezpłatnie, skaluj w miarę wzrostu. Bez ukrytych kosztów. Rezygnacja w dowolnym momencie.
        </p>
      </div>

      {/* Karty planów */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {PLANS.map((plan) => (
          <PlanCard key={plan.id} {...plan} />
        ))}
      </div>

      {/* Enterprise link */}
      <div className="mt-12 text-center rounded-2xl border border-ink-800/60 bg-ink-900/40 p-8">
        <h3 className="text-lg font-bold text-slate-100 mb-2">Enterprise</h3>
        <p className="text-slate-400 text-sm mb-4 max-w-lg mx-auto">
          On-premise, SSO/SAML, SLA 99.9%, dedykowany opiekun, własne integracje i audyt bezpieczeństwa.
          Wycena indywidualna.
        </p>
        <Link
          href="mailto:sales@terra.os"
          className="inline-flex items-center gap-2 btn-secondary rounded-xl py-2.5 px-6 font-semibold text-sm"
        >
          Skontaktuj się z nami
        </Link>
      </div>

      {/* Przypis */}
      <p className="text-center text-slate-500 text-sm mt-8">
        Wszystkie plany zawierają 14-dniowy bezpłatny okres próbny. Rezygnacja w dowolnym momencie.
      </p>
    </PageShell>
  );
}
