export default function PrivacyPage() {
  return (
    <main className="min-h-dvh bg-[#0A0A0F] px-4 py-16 text-gray-300">
      <article className="mx-auto max-w-3xl space-y-8">
        <h1 className="text-3xl font-bold text-white">Polityka Prywatności</h1>
        <p className="text-sm text-gray-500">Ostatnia aktualizacja: 14 lipca 2026 r.</p>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">1. Administrator danych</h2>
          <p>
            Administratorem Twoich danych osobowych jest QA10 sp. z o.o. z siedzibą w Katowicach,
            ul. Mariacka 37, 40-014 Katowice, NIP: 9542906279, wpisana do rejestru przedsiębiorców
            KRS (dalej: &ldquo;Administrator&rdquo; lub &ldquo;my&rdquo;).
          </p>
          <p>
            Kontakt w sprawach ochrony danych osobowych:{' '}
            <a href="mailto:privacy@terra-os.io" className="text-[#B8FF00] hover:underline">
              privacy@terra-os.io
            </a>
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">2. Podstawa prawna i cel przetwarzania</h2>
          <p>Przetwarzamy Twoje dane osobowe na podstawie:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>Art. 6 ust. 1 lit. b RODO — wykonanie umowy o świadczenie usług platformy Terra.OS</li>
            <li>Art. 6 ust. 1 lit. a RODO — zgoda na pliki cookie analityczne i marketingowe</li>
            <li>Art. 6 ust. 1 lit. c RODO — wypełnienie obowiązków prawnych (np. rachunkowość)</li>
            <li>Art. 6 ust. 1 lit. f RODO — prawnie uzasadniony interes Administratora (bezpieczeństwo, zapobieganie nadużyciom)</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">3. Zakres przetwarzanych danych</h2>
          <p>W ramach korzystania z platformy Terra.OS przetwarzamy:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>Dane identyfikacyjne: imię, nazwisko, adres e-mail, nazwa firmy</li>
            <li>Dane techniczne: adres IP, identyfikator sesji, informacje o przeglądarce</li>
            <li>Dane dotyczące korzystania z usługi: logi aktywności, preferencje, dane projektów</li>
            <li>Dane rozliczeniowe: dane do faktury, historia płatności</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">4. Okres przechowywania danych</h2>
          <p>
            Dane osobowe przechowujemy przez okres trwania umowy, a po jej zakończeniu przez okres
            wymagany przepisami prawa (w tym przepisami podatkowymi — do 5 lat) lub do czasu
            przedawnienia roszczeń. Dane przetwarzane na podstawie zgody — do momentu jej wycofania.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">5. Prawa osoby, której dane dotyczą</h2>
          <p>Przysługują Ci następujące prawa wynikające z RODO:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>Prawo dostępu do danych (Art. 15 RODO)</li>
            <li>Prawo do sprostowania danych (Art. 16 RODO)</li>
            <li>Prawo do usunięcia danych — &ldquo;prawo do bycia zapomnianym&rdquo; (Art. 17 RODO)</li>
            <li>Prawo do ograniczenia przetwarzania (Art. 18 RODO)</li>
            <li>Prawo do przenoszenia danych (Art. 20 RODO)</li>
            <li>Prawo do sprzeciwu wobec przetwarzania (Art. 21 RODO)</li>
            <li>Prawo do wycofania zgody w dowolnym momencie (Art. 7 ust. 3 RODO)</li>
          </ul>
          <p>
            Aby skorzystać z powyższych praw, skontaktuj się z nami pod adresem{' '}
            <a href="mailto:privacy@terra-os.io" className="text-[#B8FF00] hover:underline">
              privacy@terra-os.io
            </a>{' '}
            lub skorzystaj z funkcji eksportu/usunięcia danych w ustawieniach konta.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">6. Pliki cookie</h2>
          <p>
            Platforma Terra.OS wykorzystuje pliki cookie w celu zapewnienia prawidłowego działania
            serwisu, analizy ruchu oraz personalizacji treści. Szczegółowe informacje o stosowanych
            plikach cookie:
          </p>
          <ul className="list-disc space-y-1 pl-6">
            <li><strong>Niezbędne</strong> — wymagane do funkcjonowania platformy (sesja, CSRF, preferencje)</li>
            <li><strong>Analityczne</strong> — zbieranie anonimowych statystyk użytkowania (za zgodą)</li>
            <li><strong>Marketingowe</strong> — personalizacja komunikacji (za zgodą)</li>
            <li><strong>Zewnętrzne</strong> — integracje z usługami podmiotów trzecich (za zgodą)</li>
          </ul>
          <p>
            Zgodę na pliki cookie możesz wyrazić lub wycofać w dowolnym momencie za pomocą banera
            cookie wyświetlanego na stronie.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">7. Odbiorcy danych</h2>
          <p>Twoje dane mogą być przekazywane:</p>
          <ul className="list-disc space-y-1 pl-6">
            <li>Dostawcom usług hostingowych i infrastruktury IT</li>
            <li>Dostawcom usług płatniczych</li>
            <li>Organom państwowym na podstawie obowiązujących przepisów prawa</li>
          </ul>
          <p>
            Nie przekazujemy danych osobowych do państw trzecich spoza EOG bez odpowiednich
            zabezpieczeń (standardowe klauzule umowne, decyzja o adekwatności).
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">8. Bezpieczeństwo danych</h2>
          <p>
            Stosujemy odpowiednie środki techniczne i organizacyjne w celu ochrony danych osobowych,
            w tym szyfrowanie transmisji (TLS), szyfrowanie danych w spoczynku, kontrolę dostępu
            oraz regularne audyty bezpieczeństwa.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">9. Skarga do organu nadzorczego</h2>
          <p>
            Jeżeli uważasz, że przetwarzanie Twoich danych osobowych narusza przepisy RODO, masz
            prawo wniesienia skargi do Prezesa Urzędu Ochrony Danych Osobowych (ul. Stawki 2,
            00-193 Warszawa,{' '}
            <a href="https://uodo.gov.pl" className="text-[#B8FF00] hover:underline" target="_blank" rel="noopener noreferrer">
              uodo.gov.pl
            </a>
            ).
          </p>
        </section>
      </article>
    </main>
  );
}
