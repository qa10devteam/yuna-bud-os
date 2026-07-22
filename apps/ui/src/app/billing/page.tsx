'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';

interface Subscription {
  plan: string;
  status: string;
  current_period_end?: string;
}

interface Invoice {
  id: string;
  date: string;
  amount: string;
  status: string;
  pdf_url?: string;
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Darmowy',
  starter: 'Starter',
  pro: 'Pro',
  enterprise: 'Enterprise',
};

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesAvailable, setInvoicesAvailable] = useState(true);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const subRes = await fetch('/api/v2/billing/subscription');
        if (subRes.ok) {
          const subData = await subRes.json();
          setSubscription(subData);
        }
      } catch {
        // ignore
      }

      try {
        const invRes = await fetch('/api/v2/billing/invoices');
        if (invRes.ok) {
          const invData = await invRes.json();
          setInvoices(invData.items || invData || []);
        } else {
          setInvoicesAvailable(false);
        }
      } catch {
        setInvoicesAvailable(false);
      }

      setLoading(false);
    }

    fetchData();
  }, []);

  const planLabels = PLAN_LABELS;

  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center" style={{ backgroundColor: '#0A0A0F' }}>
        <p className="text-gray-400 text-lg">Ładowanie...</p>
      </div>
    );
  }

  return (
    <div className="min-h-dvh p-8" style={{ backgroundColor: '#0A0A0F' }}>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-3xl font-bold text-white mb-8">Rozliczenia</h1>

        {/* Current Plan */}
        <section className="rounded-xl border border-gray-800 p-6 mb-8" style={{ backgroundColor: '#12121A' }}>
          <h2 className="text-xl font-semibold text-white mb-4">Aktualny plan</h2>
          {subscription ? (
            <div className="flex items-center justify-between">
              <div>
                <p className="text-2xl font-bold" style={{ color: '#B8FF00' }}>
                  {planLabels[subscription.plan] || subscription.plan}
                </p>
                <p className="text-gray-400 mt-1">
                  Status: {subscription.status === 'active' ? 'Aktywny' : subscription.status}
                </p>
                {subscription.current_period_end && (
                  <p className="text-gray-500 text-sm mt-1">
                    Następne odnowienie: {new Date(subscription.current_period_end).toLocaleDateString('pl-PL')}
                  </p>
                )}
              </div>
              <Link
                href="/pricing"
                className="px-6 py-3 rounded-lg font-semibold text-black transition-colors hover:opacity-90"
                style={{ backgroundColor: '#B8FF00' }}
              >
                Zmień plan
              </Link>
            </div>
          ) : (
            <div className="flex items-center justify-between">
              <p className="text-gray-400">Brak aktywnej subskrypcji</p>
              <Link
                href="/pricing"
                className="px-6 py-3 rounded-lg font-semibold text-black transition-colors hover:opacity-90"
                style={{ backgroundColor: '#B8FF00' }}
              >
                Wybierz plan
              </Link>
            </div>
          )}
        </section>

        {/* Invoice History */}
        <section className="rounded-xl border border-gray-800 p-6" style={{ backgroundColor: '#12121A' }}>
          <h2 className="text-xl font-semibold text-white mb-4">Historia faktur</h2>
          {!invoicesAvailable ? (
            <p className="text-gray-400">Historia faktur będzie dostępna wkrótce</p>
          ) : invoices.length === 0 ? (
            <p className="text-gray-400">Brak faktur do wyświetlenia</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="pb-3 text-gray-400 font-medium">Data</th>
                    <th className="pb-3 text-gray-400 font-medium">Kwota</th>
                    <th className="pb-3 text-gray-400 font-medium">Status</th>
                    <th className="pb-3 text-gray-400 font-medium">Pobierz</th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => (
                    <tr key={invoice.id} className="border-b border-gray-800">
                      <td className="py-3 text-white">
                        {new Date(invoice.date).toLocaleDateString('pl-PL')}
                      </td>
                      <td className="py-3 text-white">{invoice.amount}</td>
                      <td className="py-3">
                        <span
                          className={`px-2 py-1 rounded text-xs font-medium ${
                            invoice.status === 'paid'
                              ? 'bg-go/10 text-go'
                              : 'bg-warn/10 text-warn'
                          }`}
                        >
                          {invoice.status === 'paid' ? 'Opłacona' : invoice.status}
                        </span>
                      </td>
                      <td className="py-3">
                        {invoice.pdf_url ? (
                          <a
                            href={invoice.pdf_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hover:underline"
                            style={{ color: '#B8FF00' }}
                          >
                            PDF
                          </a>
                        ) : (
                          <span className="text-gray-500">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
