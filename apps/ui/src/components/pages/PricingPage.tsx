'use client';

import Link from 'next/link';
import { PageShell } from '@/components/PageShell';
import { Check } from 'lucide-react';

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: '0 PLN',
    period: 'bezpłatny',
    popular: false,
    features: [
      'Do 5 przetargów',
      'Ręczne zarządzanie',
      'Podstawowe raporty',
      'Wsparcie e-mail',
    ],
    cta: 'Zacznij bezpłatnie',
    ctaHref: '/register',
    highlight: false,
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '499 PLN',
    period: '/miesiąc',
    popular: true,
    features: [
      'Do 50 przetargów',
      'AI analiza ryzyka SWZ',
      'Automatyczny BZP sync',
      'Silnik kalkulacji',
      '5 członków zespołu',
      'Eksport Excel / PDF',
      'Priorytetowe wsparcie',
    ],
    cta: 'Wybierz Pro',
    ctaHref: '/register?plan=pro',
    highlight: true,
  },
  {
    id: 'business',
    name: 'Business',
    price: '1 499 PLN',
    period: '/miesiąc',
    popular: false,
    features: [
      'Nielimitowane przetargi',
      'Pełne AI analizy',
      'Dostęp API',
      'Nieograniczony zespół',
      'Zaawansowane raporty',
      'Dedykowany opiekun',
    ],
    cta: 'Wybierz Business',
    ctaHref: '/register?plan=business',
    highlight: false,
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Wycena',
    period: 'indywidualna',
    popular: false,
    features: [
      'On-premise / self-hosted',
      'SSO / SAML',
      'SLA 99.9%',
      'Dedykowany opiekun',
      'Własne integracje',
      'Audyt bezpieczeństwa',
    ],
    cta: 'Skontaktuj się',
    ctaHref: 'mailto:sales@terra.os',
    highlight: false,
  },
];

export function PricingPage() {
  return (
    <PageShell title="Cennik" subtitle="Plany i subskrypcje budos">
      {/* Intro */}
      <div className="text-center mb-10">
        <p className="text-earth-400 text-base max-w-2xl mx-auto">
          Zacznij bezpłatnie, skaluj w miarę wzrostu. Bez ukrytych kosztów.
        </p>
      </div>

      {/* Plan Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={`relative rounded-token-xl border flex flex-col p-6 transition-all ${
              plan.highlight
                ? 'border-accent-primary bg-earth-900/80 shadow-glow'
                : 'border-earth-800/60 bg-earth-900/40 card-hover'
            }`}
          >
            {/* Popular badge */}
            {plan.popular && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                <span className="bg-accent-primary text-earth-950 text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wide">
                  Najpopularniejszy
                </span>
              </div>
            )}

            {/* Plan name */}
            <h2 className={`text-xl font-bold mb-1 ${plan.highlight ? 'text-accent-primary' : 'text-earth-100'}`}>
              {plan.name}
            </h2>

            {/* Price */}
            <div className="mb-6">
              <span className="text-3xl font-extrabold text-earth-100">{plan.price}</span>
              <span className="text-earth-500 text-sm ml-1">{plan.period}</span>
            </div>

            {/* Features */}
            <ul className="space-y-2 flex-1 mb-8">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2 text-sm text-earth-300">
                  <Check size={14} className="text-success mt-0.5 shrink-0" />
                  {feature}
                </li>
              ))}
            </ul>

            {/* CTA */}
            <Link
              href={plan.ctaHref}
              className={`block text-center rounded-token-lg py-3 px-4 font-semibold text-sm transition-all ${
                plan.highlight
                  ? 'btn-primary'
                  : 'btn-secondary'
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>

      {/* Footer note */}
      <p className="text-center text-earth-500 text-sm mt-10">
        Wszystkie plany zawierają 14-dniowy bezpłatny okres próbny. Rezygnacja w dowolnym momencie.
      </p>
    </PageShell>
  );
}
