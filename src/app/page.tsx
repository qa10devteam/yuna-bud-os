import { ArrowRight, Map } from 'lucide-react';
import Link from 'next/link';
import { TenderCard } from '@/components/TenderCard';
import { Dashboard } from '@/components/Dashboard';
import { Sidebar } from '@/components/Sidebar';
import { tenders } from '@/lib/mockData';

export default function Home() {
  return (
    <div className="flex min-h-screen bg-surface-base text-text-primary font-body">
      <Sidebar />
      <main className="flex-1 p-6 md:p-8 overflow-y-auto">
        {/* HERO SECTION */}
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-4xl md:text-5xl font-display font-bold text-neutral-600 mb-2">
                Witaj, Macieju
              </h1>
              <p className="text-lg text-neutral-400">
                Terra.OS v1.0 — System Zarządzania Ziemią
              </p>
            </div>
            <div className="hidden md:block">
              <span className="badge-success px-4 py-2">Aktywnych przetargów: 5</span>
            </div>
          </div>

          <Dashboard />
        </section>

        {/* ZWIAD SECTION */}
        <section className="mb-12">
          <div className="flex items-center gap-3 mb-6">
            <Map className="w-6 h-6 text-accent-success" />
            <h2 className="text-2xl font-display font-bold text-neutral-600">
              ZWIAD — Moduł 1: Trzonek
            </h2>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {tenders.map((tender) => (
              <TenderCard key={tender.id} tender={tender} />
            ))}
          </div>
        </section>

        {/* ACTION SECTION */}
        <section className="bg-neutral-600 text-neutral-100 rounded-xl p-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <h3 className="text-2xl font-display font-bold mb-2">
              Rozpocznij nowy projekt
            </h3>
            <p className="text-neutral-300">
              Załaduj dokumentację przetargową i uruchom symulację Terra.OS.
            </p>
          </div>
          <Link href="/kostorys" className="btn-primary flex items-center gap-2">
            STARTUJMY <ArrowRight className="w-5 h-5" />
          </Link>
        </section>
      </main>
    </div>
  );
}
