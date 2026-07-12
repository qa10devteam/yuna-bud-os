export const metadata = {
  title: 'Dokumentacja — YU-NA',
  description: 'Dokumentacja YU-NA — szybki start, moduły, API reference, FAQ',
};

export default function DocsPage() {
  return (
    <div className="min-h-screen bg-[#0f1117] text-white">
      <div className="max-w-4xl mx-auto px-6 py-16">
        {/* Header */}
        <div className="mb-12">
          <div className="text-[#c8a96e] text-sm font-semibold uppercase tracking-wider mb-2">YU-NA</div>
          <h1 className="text-4xl font-bold text-white mb-4">Dokumentacja</h1>
          <p className="text-[#8b9eb0] text-lg">
            Wszystko, czego potrzebujesz, aby zacząć zarządzać przetargami w YU-NA.
          </p>
        </div>

        {/* Quick Start */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 pb-2 border-b border-[#2a2d3a]">
            🚀 Szybki start — 3 kroki
          </h2>
          <div className="space-y-4">
            {[
              {
                step: '1',
                title: 'Zarejestruj konto organizacji',
                desc: (
                  <>
                    Wejdź na <a href="/register" className="text-[#c8a96e] hover:underline">/register</a>,
                    podaj email, hasło i nazwę firmy. Twoje konto jest gotowe w 30 sekund.
                    Otrzymasz e-mail powitalny z linkiem do dokumentacji.
                  </>
                ),
              },
              {
                step: '2',
                title: 'Skonfiguruj moduł Zwiad (BZP sync)',
                desc:
                  'W panelu przejdź do modułu Zwiad → Dodaj przetarg lub pozwól systemowi automatycznie pobrać ogłoszenia z BZP pasujące do Twojego profilu firmy (kody CPV, wartość, region).',
              },
              {
                step: '3',
                title: 'Uruchom analizę AI i wystaw ofertę',
                desc:
                  'Kliknij „Analizuj SWZ" aby AI oceniło ryzyko dokumentacji. Następnie przejdź do modułu Kosztorys, wygeneruj wycenę i przenieś przetarg do Pipeline.',
              },
            ].map((item) => (
              <div key={item.step} className="flex gap-4 bg-[#141720] border border-[#2a2d3a] rounded-xl p-5">
                <div className="w-10 h-10 rounded-full bg-[#c8a96e] text-[#0f1117] flex items-center justify-center font-bold text-lg shrink-0">
                  {item.step}
                </div>
                <div>
                  <h3 className="font-bold text-white mb-1">{item.title}</h3>
                  <p className="text-[#8b9eb0] text-sm leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Modules */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 pb-2 border-b border-[#2a2d3a]">
            📦 Opis modułów
          </h2>
          <div className="space-y-4">
            {[
              {
                name: 'Zwiad',
                icon: '🔍',
                desc: 'Moduł rozpoznania przetargów. Automatyczny sync z BZP, filtrowanie po CPV/regionie/wartości, alerty o nowych ogłoszeniach. Pozwala szybko ocenić czy warto złożyć ofertę.',
                route: '/api/v2/zwiad/*',
              },
              {
                name: 'Pipeline',
                icon: '📋',
                desc: 'Kanban do zarządzania lejkiem przetargów. Kolumny: Rozpoznanie → Analiza → Wycena → Złożona → Wygrany/Przegrany. Śledzenie terminów, przypisywanie zadań.',
                route: '/api/v2/tenders/*',
              },
              {
                name: 'Kosztorys',
                icon: '🧮',
                desc: 'Moduł wyceny oparty na katalogach KNR. Import SWZ i rysunków, automatyczne przedmiary, baza cen materiałów i robocizny aktualizowana kwartalnie.',
                route: '/api/v2/estimator/*',
              },
              {
                name: 'Silnik',
                icon: '⚙️',
                desc: 'Silnik kalkulacyjny Terra. Oblicza narzuty, ryzyko, marżę. Generuje ostateczną cenę ofertową z uzasadnieniem dla każdej pozycji kosztorysu.',
                route: '/api/v2/engine/*',
              },
            ].map((mod) => (
              <div key={mod.name} className="bg-[#141720] border border-[#2a2d3a] rounded-xl p-5">
                <div className="flex items-center gap-3 mb-2">
                  <span className="text-2xl">{mod.icon}</span>
                  <h3 className="font-bold text-white text-lg">{mod.name}</h3>
                  <code className="ml-auto text-xs bg-[#0f1117] text-[#c8a96e] px-2 py-0.5 rounded font-mono">
                    {mod.route}
                  </code>
                </div>
                <p className="text-[#8b9eb0] text-sm leading-relaxed">{mod.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* API Reference */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 pb-2 border-b border-[#2a2d3a]">
            🔌 API Reference
          </h2>
          <div className="bg-[#141720] border border-[#2a2d3a] rounded-xl p-6">
            <p className="text-[#8b9eb0] mb-4">
              YU-NA udostępnia pełne REST API. Interaktywna dokumentacja Swagger UI dostępna pod:
            </p>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 bg-[#1a1d26] border border-[#c8a96e]/40 text-[#c8a96e] px-4 py-2 rounded-lg text-sm font-semibold hover:border-[#c8a96e] transition-colors"
            >
              📖 Otwórz Swagger UI
              <span className="text-xs opacity-60">/docs</span>
            </a>
            <div className="mt-6 space-y-2 text-sm">
              <div className="text-[#8b9eb0] font-semibold mb-3">Autentykacja:</div>
              {[
                { method: 'POST', path: '/api/v2/auth/register', desc: 'Rejestracja nowego użytkownika' },
                { method: 'POST', path: '/api/v2/auth/login', desc: 'Logowanie, zwraca JWT + refresh token' },
                { method: 'POST', path: '/api/v2/auth/refresh', desc: 'Odświeżenie tokenu dostępu' },
                { method: 'GET', path: '/api/v2/auth/me', desc: 'Dane zalogowanego użytkownika' },
                { method: 'GET', path: '/api/v1/health', desc: 'Health check serwisu' },
                { method: 'GET', path: '/api/v2/metrics', desc: 'Metryki systemowe' },
              ].map((ep) => (
                <div key={ep.path} className="flex gap-3 items-center">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded font-mono w-14 text-center ${
                    ep.method === 'GET' ? 'bg-green-900/50 text-green-400' : 'bg-blue-900/50 text-blue-400'
                  }`}>
                    {ep.method}
                  </span>
                  <code className="text-[#c8a96e] text-xs font-mono">{ep.path}</code>
                  <span className="text-[#8b9eb0] text-xs">{ep.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-white mb-6 pb-2 border-b border-[#2a2d3a]">
            ❓ FAQ
          </h2>
          <div className="space-y-4">
            {[
              {
                q: 'Czy mogę używać YU-NA bez połączenia z Internetem?',
                a: 'Tak, część modułów (Kosztorys, Silnik, Pipeline) działa offline. BZP sync i analiza AI wymagają połączenia z Internetem.',
              },
              {
                q: 'Jak skonfigurować automatyczny sync z BZP?',
                a: 'W module Zwiad przejdź do Ustawienia → BZP i podaj kody CPV oraz region. System będzie automatycznie pobierał nowe ogłoszenia co godzinę.',
              },
              {
                q: 'Czy moje dane są bezpieczne?',
                a: 'Tak. Dane przechowywane są lokalnie na Twoim serwerze (on-premise). Opcjonalnie można skonfigurować backup do chmury. Połączenia szyfrowane HTTPS.',
              },
              {
                q: 'Jak wygenerować klucz API do integracji?',
                a: 'Przejdź do Ustawienia → Klucze API. Kliknij „Wygeneruj nowy klucz", nadaj nazwę i wybierz uprawnienia (scopes). Klucz wyświetlany jest jednorazowo.',
              },
              {
                q: 'Co się stanie po przekroczeniu limitu przetargów na planie Free?',
                a: 'System poinformuje Cię o zbliżaniu się do limitu. Po przekroczeniu możesz przejść na plan Pro (499 PLN/mies.) lub usunąć zakończone przetargi.',
              },
            ].map((item, i) => (
              <details
                key={i}
                className="bg-[#141720] border border-[#2a2d3a] rounded-xl overflow-hidden group"
              >
                <summary className="flex justify-between items-center p-5 cursor-pointer hover:bg-[#1a1d26] transition-colors">
                  <span className="font-semibold text-white text-sm">{item.q}</span>
                  <span className="text-[#c8a96e] text-lg group-open:rotate-45 transition-transform">+</span>
                </summary>
                <div className="px-5 pb-5 text-[#8b9eb0] text-sm leading-relaxed border-t border-[#2a2d3a] pt-4">
                  {item.a}
                </div>
              </details>
            ))}
          </div>
        </section>

        {/* Footer nav */}
        <div className="flex gap-4 text-sm text-[#8b9eb0]">
          <a href="/landing" className="hover:text-[#c8a96e] transition-colors">← Strona główna</a>
          <a href="/pricing" className="hover:text-[#c8a96e] transition-colors">Cennik</a>
          <a href="mailto:support@terra.os" className="hover:text-[#c8a96e] transition-colors">Wsparcie</a>
        </div>
      </div>
    </div>
  );
}
