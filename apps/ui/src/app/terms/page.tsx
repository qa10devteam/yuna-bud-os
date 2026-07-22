import Link from 'next/link';

export default function TermsPage() {
  return (
    <main className="min-h-dvh bg-[#0A0A0F] px-4 py-16 text-gray-300">
      <article className="mx-auto max-w-3xl space-y-8">
        <h1 className="text-3xl font-bold text-white">Regulamin platformy Terra.OS</h1>
        <p className="text-sm text-gray-500">Ostatnia aktualizacja: 14 lipca 2026 r.</p>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§1. Postanowienia ogólne</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>
              Niniejszy Regulamin określa zasady korzystania z platformy Terra.OS (dalej:
              &ldquo;Platforma&rdquo; lub &ldquo;Usługa&rdquo;) świadczonej drogą elektroniczną.
            </li>
            <li>
              Usługodawcą jest QA10 sp. z o.o. z siedzibą w Katowicach, ul. Mariacka 37, 40-014
              Katowice, NIP: 9542906279, wpisana do rejestru przedsiębiorców KRS (dalej:
              &ldquo;Usługodawca&rdquo;).
            </li>
            <li>
              Platforma Terra.OS jest narzędziem B2B przeznaczonym dla firm i profesjonalistów w
              zakresie zarządzania projektami, automatyzacji procesów i współpracy zespołowej.
            </li>
            <li>
              Korzystanie z Platformy oznacza akceptację niniejszego Regulaminu oraz{' '}
              <Link href="/privacy" className="text-[#B8FF00] hover:underline">
                Polityki Prywatności
              </Link>
              .
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§2. Definicje</h2>
          <ul className="list-disc space-y-1 pl-6">
            <li><strong>Użytkownik</strong> — osoba fizyczna korzystająca z Platformy w imieniu podmiotu gospodarczego</li>
            <li><strong>Konto</strong> — indywidualne konto Użytkownika w Platformie</li>
            <li><strong>Organizacja</strong> — podmiot gospodarczy, w ramach którego Użytkownik korzysta z Platformy</li>
            <li><strong>Subskrypcja</strong> — odpłatny plan dostępu do funkcjonalności Platformy</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§3. Rejestracja i konto</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>Rejestracja wymaga podania adresu e-mail służbowego oraz utworzenia hasła.</li>
            <li>Użytkownik zobowiązuje się do podania prawdziwych danych i ich aktualizacji.</li>
            <li>Użytkownik jest odpowiedzialny za zachowanie poufności danych logowania.</li>
            <li>Usługodawca zastrzega sobie prawo do zawieszenia Konta w przypadku naruszenia Regulaminu.</li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§4. Zakres usług</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>
              Usługodawca zapewnia dostęp do Platformy w modelu SaaS (Software as a Service) zgodnie
              z wybranym planem subskrypcyjnym.
            </li>
            <li>
              Usługodawca dokłada starań, aby zapewnić dostępność Platformy na poziomie 99,9%
              w skali miesiąca (SLA), z wyłączeniem planowanych przerw technicznych.
            </li>
            <li>
              Usługodawca zastrzega sobie prawo do modyfikacji funkcjonalności Platformy, o czym
              poinformuje Użytkowników z odpowiednim wyprzedzeniem.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§5. Płatności</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>Opłaty za korzystanie z Platformy naliczane są zgodnie z wybranym planem subskrypcyjnym.</li>
            <li>Faktury VAT wystawiane są w formie elektronicznej na koniec okresu rozliczeniowego.</li>
            <li>Brak terminowej płatności może skutkować ograniczeniem dostępu do Platformy.</li>
            <li>Ceny podawane są w kwotach netto i powiększone o obowiązującą stawkę VAT.</li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§6. Własność intelektualna</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>
              Platforma Terra.OS, jej kod źródłowy, interfejs, dokumentacja i znaki towarowe stanowią
              własność intelektualną Usługodawcy.
            </li>
            <li>
              Dane wprowadzone przez Użytkownika pozostają własnością Użytkownika lub jego Organizacji.
            </li>
            <li>
              Usługodawca udziela Użytkownikowi niewyłącznej, niezbywalnej licencji na korzystanie
              z Platformy w okresie trwania subskrypcji.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§7. Ochrona danych osobowych</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>
              Zasady przetwarzania danych osobowych określa{' '}
              <Link href="/privacy" className="text-[#B8FF00] hover:underline">
                Polityka Prywatności
              </Link>
              .
            </li>
            <li>
              W przypadku przetwarzania danych osobowych w imieniu Użytkownika (procesor), strony
              zawierają odrębną umowę powierzenia przetwarzania danych osobowych (DPA).
            </li>
            <li>
              Usługodawca stosuje środki techniczne i organizacyjne zgodne z wymogami RODO w celu
              ochrony powierzonych danych.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§8. Odpowiedzialność</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>
              Usługodawca nie ponosi odpowiedzialności za szkody wynikające z siły wyższej, działań
              osób trzecich lub nieprawidłowego korzystania z Platformy przez Użytkownika.
            </li>
            <li>
              Odpowiedzialność Usługodawcy ograniczona jest do wysokości opłat uiszczonych przez
              Użytkownika w okresie 12 miesięcy poprzedzających zdarzenie.
            </li>
            <li>
              Usługodawca nie ponosi odpowiedzialności za utratę danych wynikającą z działań
              Użytkownika, w tym usunięcia konta.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§9. Rozwiązanie umowy</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>Użytkownik może w każdym momencie zrezygnować z usługi, usuwając swoje Konto.</li>
            <li>
              Usługodawca może rozwiązać umowę ze skutkiem natychmiastowym w przypadku istotnego
              naruszenia Regulaminu.
            </li>
            <li>
              Po rozwiązaniu umowy dane Użytkownika przechowywane są przez okres wymagany prawem,
              a następnie trwale usuwane.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">§10. Postanowienia końcowe</h2>
          <ol className="list-decimal space-y-2 pl-6">
            <li>Regulamin podlega prawu polskiemu.</li>
            <li>
              Wszelkie spory wynikające z niniejszego Regulaminu będą rozstrzygane przez sąd
              właściwy dla siedziby Usługodawcy.
            </li>
            <li>
              Usługodawca zastrzega sobie prawo do zmiany Regulaminu. O zmianach Użytkownicy
              zostaną poinformowani drogą elektroniczną z 14-dniowym wyprzedzeniem.
            </li>
            <li>
              W sprawach nieuregulowanych niniejszym Regulaminem zastosowanie mają przepisy prawa
              polskiego, w szczególności Kodeksu cywilnego i ustawy o świadczeniu usług drogą
              elektroniczną.
            </li>
          </ol>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-white">Kontakt</h2>
          <p>
            QA10 sp. z o.o.<br />
            ul. Mariacka 37<br />
            40-014 Katowice<br />
            NIP: 9542906279<br />
            E-mail:{' '}
            <a href="mailto:kontakt@terra-os.io" className="text-[#B8FF00] hover:underline">
              kontakt@terra-os.io
            </a>
          </p>
        </section>
      </article>
    </main>
  );
}
