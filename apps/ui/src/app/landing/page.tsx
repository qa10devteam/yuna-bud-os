import Link from 'next/link';

export const metadata = {
  title: 'YU-NA — Wygrywaj przetargi budowlane 3x szybciej',
  description:
    'Platforma do zarządzania przetargami budowlanymi. AI analiza ryzyka SWZ, automatyczny BZP sync, silnik kalkulacji.',
};

const features = [
  {
    icon: '🔄',
    title: 'BZP Auto-sync',
    desc: 'Automatyczne pobieranie nowych przetargów z Biuletynu Zamówień Publicznych co godzinę.',
  },
  {
    icon: '🧠',
    title: 'AI Ryzyko SWZ',
    desc: 'Sztuczna inteligencja analizuje Specyfikację Warunków Zamówienia i identyfikuje ryzyka w 3 minuty.',
  },
  {
    icon: '🧮',
    title: 'Silnik kalkulacji',
    desc: 'Automatyczne kosztorysy KNR z historyczną bazą cen materiałów i robocizny.',
  },
  {
    icon: '📋',
    title: 'Kanban Pipeline',
    desc: 'Zarządzaj całym lejkiem przetargów — od rozpoznania przez wycenę po podpisanie umowy.',
  },
  {
    icon: '📊',
    title: 'Raporty Win/Loss',
    desc: 'Analizy skuteczności ofert, porównanie z konkurencją, rekomendacje poprawy marży.',
  },
];

const testimonials = [
  {
    quote:
      'YU-NA skróciła czas przygotowania oferty z 3 dni do 4 godzin. Wygrywamy 40% więcej przetargów.',
    name: 'Marek Kowalski',
    role: 'Dyrektor ds. ofertowania',
    company: 'BudMaster Sp. z o.o.',
  },
  {
    quote:
      'Synchronizacja z BZP i automatyczna analiza ryzyka to game-changer. Polecam każdej firmie budowlanej.',
    name: 'Anna Wiśniewska',
    role: 'Prezes',
    company: 'Konstrukt Pro S.A.',
  },
  {
    quote:
      'Najlepsza inwestycja w 2024 roku. ROI zwrócił się w 2 miesiące dzięki lepszym marżom.',
    name: 'Tomasz Nowak',
    role: 'CEO',
    company: 'Inżbud Kielce Sp. z o.o.',
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#0f1117] text-white font-sans">
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0f1117]/90 backdrop-blur border-b border-[#1e2130]">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <span className="text-xl font-bold text-[#c8a96e]">YU-NA</span>
          <div className="flex items-center gap-4">
            <Link href="/landing#pricing" className="text-[#8b9eb0] hover:text-white text-sm transition-colors">
              Cennik
            </Link>
            <Link href="/docs" className="text-[#8b9eb0] hover:text-white text-sm transition-colors">
              Dokumentacja
            </Link>
            <Link
              href="/register"
              className="bg-[#c8a96e] text-[#0f1117] px-4 py-2 rounded-lg text-sm font-semibold hover:bg-[#d4b87e] transition-colors"
            >
              Zacznij bezpłatnie
            </Link>
          </div>
        </div>
      </nav>

      {/* 1. Hero */}
      <section className="pt-32 pb-20 px-6 text-center">
        <div className="max-w-4xl mx-auto">
          <div className="inline-block bg-[#1a1d26] border border-[#c8a96e]/30 text-[#c8a96e] text-xs font-semibold px-3 py-1 rounded-full mb-6 uppercase tracking-wider">
            50+ firm budowlanych zaufało YU-NA
          </div>
          <h1 className="text-5xl md:text-6xl font-extrabold text-white leading-tight mb-6">
            Wygrywaj przetargi budowlane{' '}
            <span className="text-[#c8a96e]">3x szybciej</span>
          </h1>
          <p className="text-xl text-[#8b9eb0] mb-10 max-w-2xl mx-auto">
            Automatyczna analiza BZP, AI ocena ryzyka SWZ i silnik kalkulacji w jednej platformie.
            Więcej wygranych ofert, mniej pracy manualnej.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/register"
              className="bg-[#c8a96e] text-[#0f1117] px-8 py-4 rounded-xl font-bold text-lg hover:bg-[#d4b87e] transition-all shadow-lg shadow-[#c8a96e]/20"
            >
              Zacznij bezpłatnie
            </Link>
            <a
              href="mailto:demo@terra.os"
              className="border border-[#3a3d4a] text-white px-8 py-4 rounded-xl font-bold text-lg hover:border-[#c8a96e] hover:text-[#c8a96e] transition-all"
            >
              Umów demo
            </a>
          </div>
          <p className="text-[#8b9eb0] text-sm mt-4">
            Bez karty kredytowej • 14 dni bezpłatnie • Anuluj kiedy chcesz
          </p>
        </div>
      </section>

      {/* 2. Problem */}
      <section className="py-16 px-6 bg-[#141720]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-6">
            Analiza przetargu zajmuje <span className="text-red-400">3 godziny</span>.
            YU-NA robi to w <span className="text-[#4caf7d]">3 minuty</span>.
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-10">
            {[
              { before: 'Ręczne przeszukiwanie BZP', after: 'Automatyczny sync co godzinę', icon: '⏰' },
              { before: 'Analiza SWZ zajmuje cały dzień', after: 'AI ocena ryzyka w 3 min', icon: '📄' },
              { before: 'Kosztorysy w arkuszach Excel', after: 'Automatyczny silnik KNR', icon: '💰' },
            ].map((item) => (
              <div key={item.before} className="bg-[#1a1d26] rounded-xl p-6 border border-[#2a2d3a] text-left">
                <div className="text-3xl mb-3">{item.icon}</div>
                <div className="text-red-400 text-sm line-through mb-1">{item.before}</div>
                <div className="text-[#4caf7d] text-sm font-semibold">{item.after}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 3. Features */}
      <section className="py-20 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Wszystko czego potrzebujesz</h2>
            <p className="text-[#8b9eb0]">Jeden system zamiast pięciu arkuszy</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="bg-[#141720] border border-[#2a2d3a] rounded-xl p-6 hover:border-[#c8a96e]/50 transition-all"
              >
                <div className="text-4xl mb-4">{f.icon}</div>
                <h3 className="text-lg font-bold text-white mb-2">{f.title}</h3>
                <p className="text-[#8b9eb0] text-sm leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 4. Social proof */}
      <section className="py-20 px-6 bg-[#141720]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-white mb-4">Co mówią nasi klienci</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {testimonials.map((t) => (
              <div
                key={t.name}
                className="bg-[#1a1d26] border border-[#2a2d3a] rounded-xl p-6"
              >
                <p className="text-[#c5ccd6] text-sm leading-relaxed mb-6 italic">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div>
                  <div className="font-semibold text-white text-sm">{t.name}</div>
                  <div className="text-[#8b9eb0] text-xs">{t.role}</div>
                  <div className="text-[#c8a96e] text-xs">{t.company}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. Pricing mini */}
      <section id="pricing" className="py-20 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-white mb-4">Prosty cennik</h2>
          <p className="text-[#8b9eb0] mb-8">
            Od <span className="text-white font-semibold">0 PLN</span> do pełnego enterprise — bez ukrytych kosztów
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            {[
              { name: 'Free', price: '0 PLN', note: 'do 5 przetargów' },
              { name: 'Pro', price: '499 PLN', note: 'do 50 przetargów + AI', popular: true },
              { name: 'Business', price: '1 499 PLN', note: 'unlimited + API' },
              { name: 'Enterprise', price: 'Wycena', note: 'on-premise + SSO' },
            ].map((p) => (
              <div
                key={p.name}
                className={`rounded-xl p-4 border text-center ${
                  p.popular
                    ? 'border-[#c8a96e] bg-[#1a1d26]'
                    : 'border-[#2a2d3a] bg-[#141720]'
                }`}
              >
                <div className={`font-bold text-sm mb-1 ${p.popular ? 'text-[#c8a96e]' : 'text-white'}`}>
                  {p.name}
                </div>
                <div className="text-white font-extrabold">{p.price}</div>
                <div className="text-[#8b9eb0] text-xs mt-1">{p.note}</div>
              </div>
            ))}
          </div>
          <Link
            href="/pricing"
            className="text-[#c8a96e] hover:text-[#d4b87e] font-semibold text-sm underline underline-offset-4"
          >
            Zobacz pełny cennik →
          </Link>
        </div>
      </section>

      {/* 6. CTA */}
      <section className="py-20 px-6 bg-gradient-to-b from-[#141720] to-[#0f1117]">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Dołącz do <span className="text-[#c8a96e]">50+ firm budowlanych</span>
          </h2>
          <p className="text-[#8b9eb0] mb-8">
            Zacznij bezpłatnie i przekonaj się, że wygrywanie przetargów może być prostsze.
          </p>
          <Link
            href="/register"
            className="inline-block bg-[#c8a96e] text-[#0f1117] px-10 py-4 rounded-xl font-bold text-lg hover:bg-[#d4b87e] transition-all shadow-lg shadow-[#c8a96e]/20"
          >
            Zacznij bezpłatnie — to nic nie kosztuje
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[#1e2130] py-8 px-6">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4 text-[#8b9eb0] text-sm">
          <span className="font-bold text-[#c8a96e]">YU-NA</span>
          <div className="flex gap-6">
            <Link href="/docs" className="hover:text-white transition-colors">Dokumentacja</Link>
            <Link href="/pricing" className="hover:text-white transition-colors">Cennik</Link>
            <a href="mailto:support@terra.os" className="hover:text-white transition-colors">Kontakt</a>
          </div>
          <span>© 2026 YU-NA. Wszelkie prawa zastrzeżone.</span>
        </div>
      </footer>
    </div>
  );
}
