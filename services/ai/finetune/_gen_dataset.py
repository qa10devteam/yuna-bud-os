"""Generator script — produces dataset_v1.jsonl with 50 SFT examples.

Run once:  python services/ai/finetune/_gen_dataset.py
Output:    services/ai/finetune/dataset_v1.jsonl
"""
import json
import pathlib

SYS_CLASSIFY = (
    "Jesteś klasyfikatorem dokumentów przetargowych. "
    "Zwróć JSON: {\"kind\": \"przedmiar|swz|opis|umowa|oferta|inne\", \"confidence\": 0.0-1.0}."
)
SYS_EXTRACT_FIELDS = (
    "Jesteś ekstrakcją strukturalną danych przetargowych z ogłoszeń BZP/TED. "
    "Zwróć JSON z polami: cpv, value_pln, deadline, buyer, requirements[]."
)
SYS_SUMMARIZE = (
    "Jesteś ekspertem przetargów budowlanych. Piszesz po polsku, zwięźle. "
    "Zwróć JSON: {\"summary_md\": \"...\", \"key_facts\": {\"value_pln\": N, \"deadline_days\": N, \"cpv\": \"...\", \"region\": \"...\"}}."
)
SYS_RISK_FLAGS = (
    "Analizujesz klauzule umowne pod kątem ryzyka dla wykonawcy robót budowlanych. "
    "Zwróć JSON: {\"red_flags\": [{\"severity\": \"high|medium|low\", \"category\": \"...\", "
    "\"message\": \"...\", \"provenance\": {\"section\": \"...\", \"quote\": \"...\"}, \"confidence\": 0.0-1.0}]}."
)
SYS_DECISION = (
    "Jesteś doradcą decyzji przetargowych dla firmy budowlanej. "
    "Zwróć JSON: {\"verdict\": \"bid|skip|watch\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\", \"risk_level\": \"low|medium|high\"}."
)
SYS_PRZEDMIAR = (
    "Jesteś parserem przedmiarów robót budowlanych (KNR). "
    "Zwróć JSON: {\"items\": [{\"position_no\": \"...\", \"description\": \"...\", \"unit\": \"...\", "
    "\"quantity\": N, \"knr_code\": \"...\", \"confidence\": N}]}."
)


examples = []

# ─── CLASSIFY (9 examples) ────────────────────────────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "SPECYFIKACJA WARUNKÓW ZAMÓWIENIA\n"
        "Zamawiający: Gmina Kraków, ul. Wyspiańskiego 9\n"
        "Tryb zamówienia: Przetarg nieograniczony\n"
        "Przedmiot zamówienia: Przebudowa drogi gminnej nr 501234K w miejscowości Zielonki\n"
        "Wymagania dla wykonawców: min. 5 lat doświadczenia, polisa OC 2 000 000 PLN\n"
        "Termin składania ofert: 30.06.2025 r., godz. 12:00\n"
        "Miejsce składania ofert: Urząd Gminy Kraków, Dziennik Podawczy"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "swz", "confidence": 0.97})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "PRZEDMIAR ROBÓT\n"
        "Obiekt: Przebudowa drogi powiatowej nr 1023L\n"
        "Kod CPV: 45233142-6\n"
        "\nLp.  Podstawa  Opis robót                                  Jedn.  Ilość\n"
        "1    KNR 2-31  Frezowanie nawierzchni asfaltowej gr. 5cm    m2    4 200\n"
        "2    KNR 2-31  Ułożenie warstwy wiążącej z AC16W gr. 7cm    m2    4 200\n"
        "3    KNR 2-31  Ułożenie warstwy ścieralnej z AC11S gr. 5cm  m2    4 200\n"
        "4    KNR 2-01  Roboty ziemne — korekta poboczy              m3      840"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "przedmiar", "confidence": 0.99})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "OPIS PRZEDMIOTU ZAMÓWIENIA\n"
        "Zamówienie dotyczy wykonania robót budowlanych polegających na budowie budynku\n"
        "szkoły podstawowej w Gdańsku przy ul. Morskiej 14. Zakres prac obejmuje:\n"
        "- roboty ziemne i fundamentowe,\n"
        "- stan surowy zamknięty (mury, stropy, dach),\n"
        "- instalacje wewnętrzne: elektryczna, wod-kan, c.o., wentylacja mechaniczna,\n"
        "- wykończenie wnętrz zgodnie z programem funkcjonalno-użytkowym.\n"
        "Szczegółowy zakres określa dokumentacja projektowa (projekt budowlany + wykonawczy)."
    )},
    {"role": "assistant", "content": json.dumps({"kind": "opis", "confidence": 0.95})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "UMOWA O ROBOTY BUDOWLANE NR 12/2025\n"
        "zawarta w Warszawie dnia 15 marca 2025 r. pomiędzy:\n"
        "Zamawiającym: Miasto Stołeczne Warszawa, reprezentowanym przez Prezydenta Miasta\n"
        "a Wykonawcą: Budimex SA, ul. Stawki 40, 01-040 Warszawa\n"
        "§1. Przedmiot umowy\n"
        "Zamawiający zleca, a Wykonawca przyjmuje do wykonania roboty budowlane\n"
        "polegające na przebudowie Ronda Waszyngtona wraz z infrastrukturą towarzyszącą.\n"
        "§2. Wynagrodzenie\n"
        "Strony ustalają wynagrodzenie ryczałtowe w kwocie 12 800 000 PLN netto."
    )},
    {"role": "assistant", "content": json.dumps({"kind": "umowa", "confidence": 0.98})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "PRZEDMIAR ROBÓT — INSTALACJE ELEKTRYCZNE\n"
        "Inwestycja: Modernizacja oświetlenia ul. Lipowej w Lublinie\n"
        "\n"
        "1.  KNR E-04 0101-01  Demontaż opraw oświetleniowych sodowych 150W    szt.   48\n"
        "2.  KNR E-04 0102-03  Montaż opraw LED 80W na słupach istniejących     szt.   48\n"
        "3.  KNR E-04 0201-02  Wymiana kabla YAKY 4x35mm2 w kanale             m     620\n"
        "4.  KNR E-04 0301-01  Szafka oświetlenia ulicznego SO-8               szt.    2\n"
        "5.  KNR E-04 0401-01  Pomiary i badania odbiorcze instalacji           kpl.    1"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "przedmiar", "confidence": 0.98})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "SPECYFIKACJA WARUNKÓW ZAMÓWIENIA — DOSTAWA\n"
        "Postępowanie prowadzone w trybie: podstawowym bez negocjacji\n"
        "Przedmiot: Dostawa i wdrożenie systemu informatycznego ERP dla Urzędu Marszałkowskiego\n"
        "Województwa Podkarpackiego\n"
        "Wymagana licencja wieczysta. Gwarancja min. 36 miesięcy. Szkolenia dla 150 użytkowników.\n"
        "Kryterium oceny ofert: cena 60%, parametry techniczne 30%, czas wdrożenia 10%.\n"
        "Termin realizacji: 12 miesięcy od daty podpisania umowy."
    )},
    {"role": "assistant", "content": json.dumps({"kind": "swz", "confidence": 0.94})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "OFERTA WYKONAWCY\n"
        "W odpowiedzi na ogłoszenie o zamówieniu nr 2025/BZP/0123456/01\n"
        "składamy niniejszą ofertę na wykonanie robót budowlanych:\n"
        "Cena oferty brutto: 3 456 789,00 PLN\n"
        "Okres gwarancji: 60 miesięcy\n"
        "Termin realizacji: 180 dni kalendarzowych od podpisania umowy\n"
        "Nazwa wykonawcy: Strabag Sp. z o.o., ul. Domaniewska 50A, 02-672 Warszawa\n"
        "Podpisano: Jan Kowalski, Prezes Zarządu"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "oferta", "confidence": 0.97})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "UMOWA NR 45/REM/2025\n"
        "zawarta dnia 1 kwietnia 2025 r. w Poznaniu\n"
        "Zamawiający: Spółdzielnia Mieszkaniowa \"Zielone Wzgórza\" w Poznaniu\n"
        "Wykonawca: RemBud Sp. z o.o., ul. Przemysłowa 12, 61-001 Poznań\n"
        "Przedmiot: Remont elewacji budynków przy ul. Góreckiej 45-49\n"
        "§3. Termin realizacji: 01.06.2025 – 30.09.2025\n"
        "§4. Wynagrodzenie: 780 000 PLN brutto (stawka VAT 8%)\n"
        "§5. Kary umowne: 0.3% wartości umowy za każdy dzień zwłoki"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "umowa", "confidence": 0.96})},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_CLASSIFY},
    {"role": "user", "content": (
        "Program Funkcjonalno-Użytkowy\n"
        "Przedmiot: Zaprojektowanie i wykonanie hali sportowej przy Szkole Podstawowej nr 14\n"
        "w Katowicach przy ul. Śląskiej 23.\n"
        "Zakres opracowania PFU:\n"
        "1. Wymagania ogólne inwestora: sala 24x44m, trybuny na 200 miejsc\n"
        "2. Wymagania techniczne: klasa odporności pożarowej B, izolacja akustyczna Rw≥50dB\n"
        "3. Wymagania materiałowe: posadzka sportowa homologowana FIBA\n"
        "4. Infrastruktura: parking 60 miejsc, boisko zewnętrzne"
    )},
    {"role": "assistant", "content": json.dumps({"kind": "opis", "confidence": 0.91})},
]})

# ─── EXTRACT_FIELDS (9 examples) ─────────────────────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Ogłoszenie o zamówieniu — BZP Nr 2025/BZP/0234567/01\n"
        "Zamawiający: Zarząd Dróg Powiatowych w Tarnowie, ul. Kościuszki 106, 33-100 Tarnów\n"
        "Przedmiot zamówienia: Przebudowa drogi powiatowej nr 1284K na odcinku Tarnów–Skrzyszów, km 0+000 do 4+200\n"
        "Kod CPV: 45233120-6\n"
        "Szacunkowa wartość zamówienia: 4 200 000,00 PLN netto\n"
        "Termin składania ofert: 2025-07-15\n"
        "Warunki udziału: doświadczenie min. 2 roboty drogowe o wartości ≥1 500 000 PLN każda w ostatnich 5 latach\n"
        "Wymagana polisa OC: 2 000 000 PLN"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45233120-6",
        "value_pln": 4200000.0,
        "deadline": "2025-07-15",
        "buyer": "Zarząd Dróg Powiatowych w Tarnowie",
        "requirements": [
            "min. 2 roboty drogowe ≥1 500 000 PLN / 5 lat",
            "polisa OC 2 000 000 PLN",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Numer ogłoszenia: 2025/BZP/0398712/01\n"
        "Nazwa zamówienia: Budowa budynku szkoły podstawowej w Rzeszowie\n"
        "Zamawiający: Gmina Miasto Rzeszów, Rynek 1, 35-064 Rzeszów\n"
        "CPV główny: 45214200-2 (Roboty budowlane w zakresie budowy obiektów budowlanych związanych ze szkolnictwem)\n"
        "Wartość szacunkowa: 18 600 000 PLN bez VAT\n"
        "Termin składania ofert: 2025-09-30 godz. 10:00\n"
        "Termin realizacji: 30 miesięcy od zawarcia umowy\n"
        "Warunki: zdolność kredytowa lub środki własne ≥5 000 000 PLN, referencje na obiekt kubaturowy ≥10 000 000 PLN"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45214200-2",
        "value_pln": 18600000.0,
        "deadline": "2025-09-30",
        "buyer": "Gmina Miasto Rzeszów",
        "requirements": [
            "zdolność kredytowa lub środki własne ≥5 000 000 PLN",
            "referencje na obiekt kubaturowy ≥10 000 000 PLN",
            "termin realizacji 30 miesięcy",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "BZP 2025/BZP/0445231/02 — Zmiana ogłoszenia\n"
        "Zamawiający: Miejskie Przedsiębiorstwo Wodociągów i Kanalizacji SA w Krakowie\n"
        "Przedmiot: Budowa sieci wodociągowej i kanalizacji sanitarnej w dzielnicy Prokocim\n"
        "CPV: 45231300-8 (Roboty budowlane w zakresie budowy wodociągów i rurociągów do odprowadzania ścieków)\n"
        "Wartość: 7 830 000,00 zł netto\n"
        "Termin ofert: 15.08.2025\n"
        "Wymagania kwalifikacyjne:\n"
        "— min. 1 zadanie wodociągowe o wartości ≥3 000 000 PLN\n"
        "— kierownik budowy z uprawnieniami wod.-kan.\n"
        "— polisa OC 3 000 000 PLN"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45231300-8",
        "value_pln": 7830000.0,
        "deadline": "2025-08-15",
        "buyer": "Miejskie Przedsiębiorstwo Wodociągów i Kanalizacji SA w Krakowie",
        "requirements": [
            "min. 1 zadanie wodociągowe ≥3 000 000 PLN",
            "kierownik budowy z uprawnieniami wod.-kan.",
            "polisa OC 3 000 000 PLN",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Postępowanie przetargowe nr ZP/14/2025\n"
        "Zamawiający: Szpital Kliniczny im. K. Jonschera, ul. Szpitalna 27/33, 60-572 Poznań\n"
        "Opis: Dostawa i montaż instalacji klimatyzacji i wentylacji mechanicznej w bloku operacyjnym\n"
        "Kod CPV: 45331000-6\n"
        "Budżet zamawiającego: 2 450 000 PLN brutto\n"
        "Termin składania ofert: 2025-06-20\n"
        "Wymagania: doświadczenie w instalacjach medycznych (sale operacyjne/cleanroom), "
        "certyfikat ISO 9001, gwarancja min. 36 mies."
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45331000-6",
        "value_pln": 2040650.41,
        "deadline": "2025-06-20",
        "buyer": "Szpital Kliniczny im. K. Jonschera w Poznaniu",
        "requirements": [
            "doświadczenie w instalacjach medycznych (sale operacyjne/cleanroom)",
            "certyfikat ISO 9001",
            "gwarancja min. 36 miesięcy",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Ogłoszenie nr 2025/BZP/0512890/01\n"
        "Jednostka ogłaszająca: Generalna Dyrekcja Dróg Krajowych i Autostrad, Oddział Łódź\n"
        "Przedmiot: Remont nawierzchni autostrady A1, odcinek węzeł Łódź Południe – węzeł Piotrków, km 330–345\n"
        "Kody CPV: 45233142-6, 45233220-7\n"
        "Szacunkowa wartość zamówienia bez VAT: 34 700 000,00 PLN\n"
        "Termin składania ofert: 2025-10-10 godzina 09:00\n"
        "Wymagania podmiotowe: min. 3 kontrakty drogowe ≥15 000 000 PLN każdy; "
        "laboratorium drogowe lub umowa z akredytowanym laboratorium"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45233142-6",
        "value_pln": 34700000.0,
        "deadline": "2025-10-10",
        "buyer": "Generalna Dyrekcja Dróg Krajowych i Autostrad Oddział Łódź",
        "requirements": [
            "min. 3 kontrakty drogowe ≥15 000 000 PLN każdy",
            "laboratorium drogowe lub umowa z akredytowanym laboratorium",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Numer referencyjny: ZP/2025/024/EL\n"
        "Zamawiający: Energa Operator SA, ul. Marynarki Polskiej 130, 80-557 Gdańsk\n"
        "Nazwa: Budowa stacji transformatorowej 110/15 kV GPZ Gdańsk Południe\n"
        "CPV: 45315600-4\n"
        "Wartość kontraktu szacunkowa: 9 200 000 PLN netto\n"
        "Termin złożenia oferty: 22 września 2025 r.\n"
        "Warunki: uprawnienia energetyczne SEP, doświadczenie w budowie GPZ ≥3 szt., ubezpieczenie OC 5 mln PLN"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45315600-4",
        "value_pln": 9200000.0,
        "deadline": "2025-09-22",
        "buyer": "Energa Operator SA",
        "requirements": [
            "uprawnienia energetyczne SEP",
            "doświadczenie w budowie GPZ ≥3 szt.",
            "ubezpieczenie OC 5 000 000 PLN",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Ogłoszenie o przetargu nieograniczonym\n"
        "Zamawiający: Zarząd Zieleni Miejskiej w Krakowie\n"
        "Przedmiot: Budowa parku linearnego wzdłuż rzeki Białuchy, etap II\n"
        "CPV: 45112711-2 (Roboty w zakresie kształtowania parków)\n"
        "Wartość szacunkowa: 3 100 000 zł\n"
        "Termin składania ofert: 2025-07-01\n"
        "Minimalne warunki: min. 2 realizacje terenów zielonych ≥1 000 000 PLN, "
        "ogrodnik z min. 3-letnim doświadczeniem w projekcie"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45112711-2",
        "value_pln": 3100000.0,
        "deadline": "2025-07-01",
        "buyer": "Zarząd Zieleni Miejskiej w Krakowie",
        "requirements": [
            "min. 2 realizacje terenów zielonych ≥1 000 000 PLN",
            "ogrodnik z min. 3-letnim doświadczeniem",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Referencja postępowania: RZP-271.18.2025\n"
        "Zamawiający: Gmina Białystok, ul. Słonimska 1, 15-950 Białystok\n"
        "Tytuł: Termomodernizacja 12 budynków komunalnych w Białymstoku wraz z wymianą źródeł ciepła na pompy ciepła\n"
        "Kod CPV główny: 45321000-3\n"
        "Wartość szacunkowa: 11 400 000,00 PLN\n"
        "Termin złożenia ofert: 05.08.2025\n"
        "Wymagania: Wykonanie ≥3 termomodernizacji z EC pompy ciepła, "
        "kierownik z uprawnieniami budowlanymi w specjalności konstrukcyjno-budowlanej"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "45321000-3",
        "value_pln": 11400000.0,
        "deadline": "2025-08-05",
        "buyer": "Gmina Białystok",
        "requirements": [
            "min. 3 termomodernizacje z pompami ciepła",
            "kierownik z uprawnieniami konstrukcyjno-budowlanymi",
        ],
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_EXTRACT_FIELDS},
    {"role": "user", "content": (
        "Nr zamówienia publicznego: ZP/IT/2025/007\n"
        "Zamawiający: Ministerstwo Finansów, ul. Świętokrzyska 12, 00-916 Warszawa\n"
        "Nazwa: Rozbudowa i utrzymanie infrastruktury sieciowej centrum danych MF\n"
        "CPV: 32420000-3 (Urządzenia sieciowe)\n"
        "Wartość zamówienia: 6 500 000 PLN netto\n"
        "Termin składania ofert: 2025-11-15\n"
        "Wymagania: Certyfikat partnera dostawcy sprzętu (Cisco/Juniper), "
        "doświadczenie w projektach ≥2 000 000 PLN, klauzula bezpieczeństwa min. poufne"
    )},
    {"role": "assistant", "content": json.dumps({
        "cpv": "32420000-3",
        "value_pln": 6500000.0,
        "deadline": "2025-11-15",
        "buyer": "Ministerstwo Finansów",
        "requirements": [
            "certyfikat partnera Cisco lub Juniper",
            "doświadczenie w projektach ≥2 000 000 PLN",
            "klauzula bezpieczeństwa min. poufne",
        ],
    })},
]})

# ─── SUMMARIZE (8 examples) ────────────────────────────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Przebudowa i rozbudowa drogi powiatowej nr 2140W relacji Grójec–Nowe Miasto nad Pilicą\n"
        "Zamawiający: Zarząd Powiatu Grójeckiego\n"
        "CPV: 45233120-6\n"
        "Opis: Zamówienie obejmuje przebudowę drogi powiatowej na odcinku 8,3 km. "
        "Zakres: frezowanie istniejącej nawierzchni, ułożenie nowych warstw bitumicznych (wiążąca + ścieralna), "
        "regulacja istniejącego odwodnienia, wymiana uszkodzonych przepustów (4 szt.), "
        "budowa chodnika po lewej stronie drogi (2,1 km), oznakowanie pionowe i poziome. "
        "Wymagane doświadczenie: min. 2 roboty drogowe o wartości ≥2 000 000 PLN w ciągu ostatnich 5 lat. "
        "Termin realizacji: 150 dni od podpisania umowy. Wartość szacunkowa: 5 600 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Przebudowa drogi powiatowej nr 2140W (pow. grójecki)\n\n"
            "Zamówienie na przebudowę **8,3 km** drogi powiatowej Grójec–Nowe Miasto nad Pilicą. "
            "Kluczowy zakres: nowe warstwy bitumiczne, wymiana przepustów (4 szt.), "
            "chodnik 2,1 km oraz kompletne oznakowanie. "
            "Wymagane 2 referencje na roboty drogowe ≥2 mln PLN. "
            "Termin: **150 dni**. Szacowana wartość: **5,6 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 5600000,
            "deadline_days": 150,
            "cpv": "45233120-6",
            "region": "mazowieckie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Budowa budynku szkoły podstawowej na 600 uczniów w Gdańsku-Oliwie\n"
        "Zamawiający: Gmina Miasto Gdańsk\n"
        "CPV: 45214200-2\n"
        "Opis: Przedmiotem zamówienia jest zaprojektowanie i wybudowanie szkoły podstawowej "
        "na 600 uczniów (24 klasy). Budynek 3-kondygnacyjny, pow. użytkowa ~6 500 m2. "
        "Zakres: roboty ziemne i fundamentowe, konstrukcja żelbetowa, izolacje, "
        "dachy płaskie, okna i drzwi aluminiowe, wykończenia, instalacje: elektryczna, "
        "wod-kan, c.o. (pompa ciepła + gruntowe), wentylacja mechaniczna z rekuperacją, "
        "fotowoltaika 100 kWp, zagospodarowanie terenu, boiska, parking 80 miejsc. "
        "Termin realizacji: 30 miesięcy. Wartość szacunkowa: 38 000 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Budowa szkoły podstawowej w Gdańsku-Oliwie (600 uczniów)\n\n"
            "Zamówienie 'zaprojektuj i wybuduj' na **3-kondygnacyjny** budynek szkolny "
            "o pow. ~6 500 m². Instalacje niskoenergetyczne: pompa ciepła, FV 100 kWp, "
            "wentylacja z rekuperacją. W zakresie również zagospodarowanie terenu i boiska. "
            "Realizacja: **30 miesięcy**. Wartość: **38 mln PLN** — największy przetarg edukacyjny "
            "w Trójmieście w 2025 r."
        ),
        "key_facts": {
            "value_pln": 38000000,
            "deadline_days": 912,
            "cpv": "45214200-2",
            "region": "pomorskie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Modernizacja stacji uzdatniania wody w Rzeszowie przy ul. Podkarpackiej\n"
        "Zamawiający: Rzeszowska Agencja Rozwoju Regionalnego SA\n"
        "CPV: 45252126-7\n"
        "Opis: Zamówienie obejmuje kompleksową modernizację SUW Rzeszów o przepustowości 25 000 m3/dobę. "
        "Zakres: wymiana filtrów pośpiesznych (8 szt.), nowa instalacja ozonowania, "
        "system UV dezynfekcji, wymiana pomp II stopnia (12 szt. × 450 kW), "
        "nowy system SCADA + BMS, budowa zbiornika wyrównawczego 3 000 m3. "
        "Wymagania: doświadczenie w modernizacji SUW >10 000 m3/dobę, "
        "specjalista ds. uzdatniania wody. Czas realizacji: 24 miesiące. "
        "Wartość zamówienia: 22 500 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Modernizacja SUW Rzeszów — 25 000 m³/dobę\n\n"
            "Kompleksowa modernizacja stacji uzdatniania wody: wymiana 8 filtrów, "
            "instalacja ozonowania i UV, 12 pomp II stopnia oraz nowy SCADA/BMS. "
            "Nowy zbiornik wyrównawczy 3 000 m³. Wymaga udokumentowanego doświadczenia "
            "w SUW >10 000 m³/dobę. Realizacja: **24 miesiące**. Wartość: **22,5 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 22500000,
            "deadline_days": 730,
            "cpv": "45252126-7",
            "region": "podkarpackie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Remont kapitalny bloku mieszkalnego przy ul. Słowackiego 17 w Łodzi\n"
        "Zamawiający: Łódzkie TBS Sp. z o.o.\n"
        "CPV: 45453000-7\n"
        "Opis: Zakres robót: docieplenie ścian zewnętrznych (styropian 20 cm, tynk silikonowy), "
        "docieplenie dachu (wełna mineralna 25 cm), wymiana okien i drzwi balkonowych "
        "(242 szt. PVC), wymiana instalacji c.o. (wymiennik + grzejniki + rury), "
        "wymiana pionów wod-kan, remont klatek schodowych (12 kl. schodowych), "
        "modernizacja węzła cieplnego. Budynek: 12-kondygnacyjny, 144 lokale, 1967 r. "
        "Wymagania: min. 3 remonty budynków wielorodzinnych ≥2 000 000 PLN. "
        "Termin: 18 miesięcy. Wartość: 8 900 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Remont kapitalny bloku przy ul. Słowackiego 17, Łódź (144 lokale)\n\n"
            "Kompleksowy remont 12-kondygnacyjnego budynku z 1967 r.: "
            "termomodernizacja (styropian 20 cm + wełna dach 25 cm), wymiana 242 okien PVC, "
            "pełna wymiana instalacji c.o. i wod-kan oraz remont 12 klatek schodowych. "
            "Wymagane referencje na 3 podobne remonty ≥2 mln PLN. "
            "Termin: **18 miesięcy**. Wartość: **8,9 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 8900000,
            "deadline_days": 548,
            "cpv": "45453000-7",
            "region": "łódzkie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Przebudowa mostu drogowego na rzece Warta w ciągu drogi wojewódzkiej nr 432\n"
        "Zamawiający: Zarząd Dróg Wojewódzkich w Poznaniu\n"
        "CPV: 45221100-3\n"
        "Opis: Przebudowa mostu żelbetowego z 1958 r., długość 94 m, klasa obciążenia docelowa F. "
        "Zakres: rozbiórka istniejącej konstrukcji, pale fundamentowe (CFA Ø620), "
        "nowe przyczółki i filary żelbetowe, przęsło stalowe zespolone, "
        "nawierzchnia z betonu asfaltowego, bariery energochłonne, oświetlenie LED. "
        "Wymagania: kierownik z uprawnieniami mostowymi, referencja na most ≥40 m dł. "
        "Termin realizacji: 18 miesięcy. Wartość: 14 200 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Przebudowa mostu na Warcie, DW432 — 94 m, klasa F\n\n"
            "Kompleksowa przebudowa mostu żelbetowego z lat 50.: fundamenty CFA Ø620, "
            "nowe żelbetowe podpory i przęsło stalowo-betonowe. W zakres wchodzi "
            "nawierzchnia, bariery energochłonne i oświetlenie LED. "
            "Wymaga kierownika z uprawnieniami mostowymi i referencji na most ≥40 m. "
            "Termin: **18 miesięcy**. Wartość: **14,2 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 14200000,
            "deadline_days": 548,
            "cpv": "45221100-3",
            "region": "wielkopolskie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Budowa kanalizacji deszczowej w ul. Lipowej i przyległych w Wrocławiu\n"
        "Zamawiający: Wrocławskie Inwestycje Sp. z o.o.\n"
        "CPV: 45232130-2\n"
        "Opis: Budowa kanalizacji deszczowej DN400–DN800 na długości 2 140 m "
        "wraz z separatorem i osadnikiem lamelowym, 4 wylotami do rowu melioracyjnego, "
        "studniami rewizyjnymi i wpustami ulicznymi (68 szt.). "
        "Odtworzenie nawierzchni drogi po rozkopaniu (masa asfaltowa). "
        "Wymagania: doświadczenie w robotach wod.-kan. ≥2 000 000 PLN, inspektor robót san. "
        "Termin: 120 dni kalendarzowych. Wartość: 4 800 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Kanalizacja deszczowa ul. Lipowa, Wrocław — 2 140 m\n\n"
            "Budowa deszczówki DN400–DN800 z separatorem, 4 wylotami do rowu i 68 wpustami. "
            "W zakresie odtworzenie nawierzchni asfaltowej po rozkopaniu. "
            "Kwalifikacja: roboty wod.-kan. ≥2 mln PLN + inspektor robót sanitarnych. "
            "Termin: **120 dni**. Wartość: **4,8 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 4800000,
            "deadline_days": 120,
            "cpv": "45232130-2",
            "region": "dolnośląskie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Dostawa i montaż instalacji fotowoltaicznej 500 kWp na dachach obiektów gminnych\n"
        "Zamawiający: Urząd Miejski w Częstochowie\n"
        "CPV: 45261215-4\n"
        "Opis: Zaprojektowanie, dostawa i montaż mikroinstalacji PV na 12 obiektach gminnych "
        "(szkoły, przedszkola, urząd), łączna moc 500 kWp. Panele monokrystaliczne min. 400 Wp, "
        "inwertery hybrydowe z możliwością przyłączenia magazynu energii, "
        "system monitoringu on-line, okablowanie DC/AC, zabezpieczenia p.poż. "
        "Wymagania: min. 5 instalacji PV ≥50 kWp każda, projektant z uprawnieniami elektrycznymi. "
        "Termin: 90 dni. Wartość szacunkowa: 3 750 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Instalacja PV 500 kWp na 12 obiektach gminnych, Częstochowa\n\n"
            "Zamówienie D+M mikroinstalacji fotowoltaicznych (12 budynków, 500 kWp łącznie). "
            "Panele monokrystaliczne ≥400 Wp, inwertery hybrydowe ready na magazyn energii, "
            "monitoring on-line. Wymagane 5 referencji PV ≥50 kWp. "
            "Termin: **90 dni**. Wartość: **3,75 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 3750000,
            "deadline_days": 90,
            "cpv": "45261215-4",
            "region": "śląskie",
        },
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_SUMMARIZE},
    {"role": "user", "content": (
        "Przetarg: Rewitalizacja centrum Radomia — roboty budowlane na Placu Jagiellońskim\n"
        "Zamawiający: Gmina Miasto Radom\n"
        "CPV: 45453100-8\n"
        "Opis: Rewitalizacja historycznego centrum: wymiana nawierzchni placu (kostka granitowa 4 000 m2), "
        "nowa fontanna multimedialna z podświetleniem LED, przebudowa układu drogowego "
        "z wyłączeniem ruchu kołowego, montaż małej architektury (ławki, kosze, słupy oświetleniowe), "
        "nasadzenia zieleni (40 drzew, 500 krzewów), przebudowa sieci elektroenergetycznej "
        "i wodociągowej w pasie robót. Wymagania: referencja na plac miejski/deptak ≥1 500 000 PLN. "
        "Termin: 210 dni. Wartość: 7 200 000 PLN."
    )},
    {"role": "assistant", "content": json.dumps({
        "summary_md": (
            "## Rewitalizacja Placu Jagiellońskiego w Radomiu\n\n"
            "Kompleksowa rewitalizacja historycznego centrum: granitowa nawierzchnia 4 000 m², "
            "multimedialna fontanna LED, wyłączenie ruchu kołowego, mała architektura "
            "oraz nasadzenia (40 drzew, 500 krzewów). Towarzysząca przebudowa sieci elektro i wodociągowej. "
            "Referencja wymagana: plac/deptak ≥1,5 mln PLN. "
            "Termin: **210 dni**. Wartość: **7,2 mln PLN**."
        ),
        "key_facts": {
            "value_pln": 7200000,
            "deadline_days": 210,
            "cpv": "45453100-8",
            "region": "mazowieckie",
        },
    })},
]})

# ─── RISK_FLAGS / REASON_REDFLAGS (8 examples) ───────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§14 KARY UMOWNE\n"
        "1. Wykonawca zapłaci Zamawiającemu karę umowną:\n"
        "   a) za opóźnienie w wykonaniu przedmiotu umowy — 0,5% wynagrodzenia umownego brutto "
        "za każdy dzień opóźnienia;\n"
        "   b) za opóźnienie w usunięciu wad w okresie gwarancji — 0,3% wynagrodzenia brutto "
        "za każdy dzień opóźnienia;\n"
        "   c) za odstąpienie od umowy z przyczyn leżących po stronie Wykonawcy — 15% "
        "wynagrodzenia umownego brutto.\n"
        "2. Zamawiający ma prawo kumulować kary umowne bez ograniczeń.\n"
        "3. Zamawiający zastrzega prawo do dochodzenia odszkodowania uzupełniającego "
        "do pełnej wysokości poniesionej szkody."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "kary_umowne",
                "message": "Kara 0,5%/dzień za opóźnienie przekracza bezpieczny próg rynkowy (0,2–0,3%/dzień); przy 30-dniowym opóźnieniu pochłania 15% kontraktu.",
                "provenance": {"section": "§14 ust. 1 lit. a", "quote": "0,5% wynagrodzenia umownego brutto za każdy dzień opóźnienia"},
                "confidence": 0.97,
            },
            {
                "severity": "high",
                "category": "kumulacja_kar",
                "message": "Brak górnego limitu kumulacji kar umownych — wykonawca naraża się na kary przekraczające wartość kontraktu.",
                "provenance": {"section": "§14 ust. 2", "quote": "prawo kumulować kary umowne bez ograniczeń"},
                "confidence": 0.95,
            },
            {
                "severity": "medium",
                "category": "odszkodowanie_uzupelniajace",
                "message": "Klauzula odszkodowania uzupełniającego ponad kary umowne podwaja ryzyko finansowe; brak wymogu wykazania szkody.",
                "provenance": {"section": "§14 ust. 3", "quote": "do pełnej wysokości poniesionej szkody"},
                "confidence": 0.88,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§9 GWARANCJA I RĘKOJMIA\n"
        "1. Wykonawca udziela gwarancji na wykonane roboty budowlane na okres 84 miesięcy "
        "licząc od dnia podpisania protokołu odbioru końcowego.\n"
        "2. W przypadku ujawnienia wad w okresie gwarancji, Wykonawca zobowiązany jest do "
        "usunięcia wad w terminie 3 dni roboczych od zgłoszenia, bez względu na porę roku.\n"
        "3. Każdorazowe zgłoszenie wady restartuje bieg okresu gwarancji dla całego przedmiotu zamówienia.\n"
        "4. Koszty ekspertyz potwierdzających wadę ponosi Wykonawca."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "gwarancja_restart",
                "message": "Klauzula restartu gwarancji dla CAŁEGO przedmiotu po każdym zgłoszeniu wady może skutkować gwarancją wieczystą w praktyce.",
                "provenance": {"section": "§9 ust. 3", "quote": "Każdorazowe zgłoszenie wady restartuje bieg okresu gwarancji dla całego przedmiotu"},
                "confidence": 0.98,
            },
            {
                "severity": "medium",
                "category": "termin_usuwania_wad",
                "message": "3 dni robocze na usunięcie wady bez względu na porę roku jest nierealnym terminem dla robót budowlanych w okresie zimowym.",
                "provenance": {"section": "§9 ust. 2", "quote": "3 dni roboczych od zgłoszenia, bez względu na porę roku"},
                "confidence": 0.91,
            },
            {
                "severity": "low",
                "category": "koszty_ekspertyz",
                "message": "Obowiązek pokrycia kosztów ekspertyz przez Wykonawcę nawet przy odrzuceniu reklamacji — brak symetrycznej klauzuli.",
                "provenance": {"section": "§9 ust. 4", "quote": "Koszty ekspertyz potwierdzających wadę ponosi Wykonawca"},
                "confidence": 0.82,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§6 TERMINY REALIZACJI\n"
        "1. Wykonawca zobowiązuje się wykonać przedmiot umowy w terminie 60 dni "
        "od daty podpisania umowy.\n"
        "2. Termin uważa się za dotrzymany wyłącznie po uzyskaniu prawomocnego pozwolenia "
        "na użytkowanie obiektu.\n"
        "3. Przedłużenie terminu możliwe jest jedynie w przypadku siły wyższej rozumianej "
        "wyłącznie jako klęski żywiołowe (powódź, trzęsienie ziemi, huragan).\n"
        "4. Zamawiający nie odpowiada za opóźnienia wynikłe z decyzji organów administracyjnych."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "termin_niewykonalny",
                "message": "60 dni na uzyskanie prawomocnego pozwolenia na użytkowanie jest terminem nierealnym — sam organ ma ustawowe 14–21 dni, a droga odwoławcza nie zależy od Wykonawcy.",
                "provenance": {"section": "§6 ust. 1–2", "quote": "60 dni... wyłącznie po uzyskaniu prawomocnego pozwolenia na użytkowanie"},
                "confidence": 0.96,
            },
            {
                "severity": "high",
                "category": "sila_wyzsza_zawezenie",
                "message": "Definicja siły wyższej ograniczona tylko do klęsk żywiołowych — wyklucza strajki, pandemia, zmiany prawa, opóźnienia dostawców strategicznych.",
                "provenance": {"section": "§6 ust. 3", "quote": "wyłącznie jako klęski żywiołowe (powódź, trzęsienie ziemi, huragan)"},
                "confidence": 0.94,
            },
            {
                "severity": "high",
                "category": "ryzyko_administracyjne",
                "message": "Zamawiający wyłącza odpowiedzialność za opóźnienia decyzji administracyjnych — całe ryzyko przerzucone na Wykonawcę.",
                "provenance": {"section": "§6 ust. 4", "quote": "Zamawiający nie odpowiada za opóźnienia wynikłe z decyzji organów administracyjnych"},
                "confidence": 0.93,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§11 ZMIANY UMOWY\n"
        "1. Zamawiający zastrzega sobie prawo do jednostronnej zmiany zakresu robót "
        "do 30% wartości kontraktu bez zmiany wynagrodzenia.\n"
        "2. Zamawiający może wstrzymać roboty bez podania przyczyny na okres do 60 dni; "
        "Wykonawcy nie przysługuje z tego tytułu roszczenie o wynagrodzenie postojowe.\n"
        "3. Zmiany w dokumentacji technicznej wprowadzone przez Zamawiającego nie uprawniają "
        "Wykonawcy do żądania zmiany wynagrodzenia, jeżeli nie przekraczają 15% zakresu."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "jednostronna_zmiana_zakresu",
                "message": "Prawo do redukcji lub rozszerzenia zakresu o 30% bez zmiany wynagrodzenia jest klauzulą niedozwoloną w umowach B2B i narusza zasadę ekwiwalentności świadczeń.",
                "provenance": {"section": "§11 ust. 1", "quote": "jednostronnej zmiany zakresu robót do 30% wartości kontraktu bez zmiany wynagrodzenia"},
                "confidence": 0.97,
            },
            {
                "severity": "high",
                "category": "wstrzymanie_robot",
                "message": "Prawo wstrzymania robót do 60 dni bez wynagrodzenia postojowego generuje bezpośrednie straty (koszty utrzymania sprzętu i brygad) bez możliwości regresu.",
                "provenance": {"section": "§11 ust. 2", "quote": "wstrzymać roboty bez podania przyczyny na okres do 60 dni"},
                "confidence": 0.95,
            },
            {
                "severity": "medium",
                "category": "zmiany_dokumentacji",
                "message": "Próg 15% zmian dokumentacji bez prawa do zmiany wynagrodzenia jest zbyt wysoki — standardem rynkowym jest 5%.",
                "provenance": {"section": "§11 ust. 3", "quote": "nie przekraczają 15% zakresu"},
                "confidence": 0.85,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§8 WARUNKI PŁATNOŚCI\n"
        "1. Zamawiający dokona zapłaty faktury w terminie 60 dni od jej wpływu.\n"
        "2. Wykonawcy nie przysługują odsetki ustawowe za opóźnienie w płatnościach "
        "przez pierwsze 30 dni zwłoki.\n"
        "3. Zamawiający może wstrzymać płatność faktury częściowej do czasu "
        "przedstawienia dokumentów powykonawczych w pełnym zakresie.\n"
        "4. Faktury częściowe nie mogą przekroczyć 70% wartości wykonanych robót "
        "potwierdzonych przez inspektora nadzoru."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "termin_platnosci",
                "message": "Termin płatności 60 dni przekracza ustawowy maksymalny termin 30 dni w transakcjach handlowych (Ustawa z 8.03.2013 o terminach zapłaty) — klauzula prawnie wątpliwa.",
                "provenance": {"section": "§8 ust. 1", "quote": "zapłaty faktury w terminie 60 dni od jej wpływu"},
                "confidence": 0.96,
            },
            {
                "severity": "medium",
                "category": "wylaczenie_odsetek",
                "message": "Wyłączenie odsetek ustawowych przez 30 dni zwłoki narusza art. 7 ust. 1 ustawy o terminach zapłaty — klauzula nieważna, ale jej obecność utrudnia dochodzenie roszczeń.",
                "provenance": {"section": "§8 ust. 2", "quote": "nie przysługują odsetki ustawowe... przez pierwsze 30 dni zwłoki"},
                "confidence": 0.92,
            },
            {
                "severity": "medium",
                "category": "retencja_platnosci",
                "message": "Wstrzymanie płatności za brak dokumentów powykonawczych bez określenia terminu na ich dostarczenie daje Zamawiającemu nieokreślone prawo blokowania płatności.",
                "provenance": {"section": "§8 ust. 3", "quote": "wstrzymać płatność faktury częściowej do czasu przedstawienia dokumentów"},
                "confidence": 0.87,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§16 ZABEZPIECZENIE NALEŻYTEGO WYKONANIA UMOWY\n"
        "1. Wykonawca wniesie zabezpieczenie należytego wykonania umowy w wysokości 10% "
        "wynagrodzenia brutto.\n"
        "2. 70% zabezpieczenia zostanie zwrócone w terminie 30 dni od podpisania protokołu "
        "odbioru końcowego.\n"
        "3. Pozostałe 30% zostanie zatrzymane jako kaucja gwarancyjna na okres 84 miesięcy.\n"
        "4. W przypadku jakiegokolwiek sporu dotyczącego umowy, Zamawiający może wstrzymać "
        "zwrot zabezpieczenia do czasu prawomocnego rozstrzygnięcia sporu."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "zabezpieczenie_wysokosc",
                "message": "Zabezpieczenie 10% wartości brutto jest maksymalną dopuszczalną ustawowo kwotą (art. 452 PZP) i wiąże znaczne środki finansowe przez 7 lat.",
                "provenance": {"section": "§16 ust. 1", "quote": "10% wynagrodzenia brutto"},
                "confidence": 0.90,
            },
            {
                "severity": "high",
                "category": "kaucja_gwarancyjna",
                "message": "Zatrzymanie 30% zabezpieczenia na 84 miesiące (7 lat) to wyjątkowo długi okres — standard rynkowy wynosi 36–60 miesięcy.",
                "provenance": {"section": "§16 ust. 3", "quote": "30% zostanie zatrzymane jako kaucja gwarancyjna na okres 84 miesięcy"},
                "confidence": 0.93,
            },
            {
                "severity": "high",
                "category": "zamrozenie_przy_sporze",
                "message": "Możliwość zamrożenia zwrotu zabezpieczenia podczas jakiegokolwiek sporu (nawet drobnego) przy wieloletnich sprawach sądowych paraliżuje płynność finansową.",
                "provenance": {"section": "§16 ust. 4", "quote": "wstrzymać zwrot zabezpieczenia do czasu prawomocnego rozstrzygnięcia sporu"},
                "confidence": 0.95,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§5 WARUNKI WYKONANIA UMOWY\n"
        "1. Wykonawca zobowiązuje się do zatrudnienia na umowę o pracę co najmniej 80% "
        "pracowników fizycznych przez cały czas trwania umowy.\n"
        "2. Zamawiający ma prawo do kontroli zatrudnienia w dowolnym momencie; brak "
        "stosownych dokumentów w ciągu 24 godzin od wezwania skutkuje karą 5 000 PLN/dzień.\n"
        "3. Wykonawca jest zobowiązany zgłosić każdą zmianę personalną w brygadzie "
        "nie później niż 48 godzin przed jej nastąpieniem."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "medium",
                "category": "wymog_zatrudnienia",
                "message": "Wymóg 80% pracowników na etat przez cały czas trwania umowy uniemożliwia elastyczne zarządzanie podwykonawstwem i sezonowym zatrudnieniem.",
                "provenance": {"section": "§5 ust. 1", "quote": "zatrudnienia na umowę o pracę co najmniej 80% pracowników fizycznych"},
                "confidence": 0.85,
            },
            {
                "severity": "high",
                "category": "kara_za_dokumenty",
                "message": "Kara 5 000 PLN/dzień za niedostarczenie dokumentów w 24h jest nieproporcjonalna — standardem jest 1 000–2 000 PLN/dzień i termin 3–5 dni roboczych.",
                "provenance": {"section": "§5 ust. 2", "quote": "brak stosownych dokumentów w ciągu 24 godzin... skutkuje karą 5 000 PLN/dzień"},
                "confidence": 0.92,
            },
            {
                "severity": "medium",
                "category": "zmiany_personalne",
                "message": "Obowiązek zgłoszenia zmiany personalnej 48h z wyprzedzeniem jest nierealistyczny przy nagłych zdarzeniach (choroba, wypadek) i generuje ryzyko kar.",
                "provenance": {"section": "§5 ust. 3", "quote": "48 godzin przed jej nastąpieniem"},
                "confidence": 0.88,
            },
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_RISK_FLAGS},
    {"role": "user", "content": (
        "§19 ODSTĄPIENIE OD UMOWY\n"
        "1. Zamawiający może odstąpić od umowy w każdym czasie bez podania przyczyny, "
        "płacąc Wykonawcy wynagrodzenie jedynie za roboty faktycznie wykonane.\n"
        "2. W przypadku odstąpienia przez Zamawiającego z przyczyn nietkwiących po stronie "
        "Wykonawcy, Wykonawcy przysługuje wynagrodzenie za roboty wykonane, pomniejszone "
        "o oszczędności Wykonawcy.\n"
        "3. Zamawiający może żądać zwrotu wypłaconych zaliczek w pełnej wysokości w terminie "
        "7 dni od odstąpienia, bez względu na stopień zaawansowania robót."
    )},
    {"role": "assistant", "content": json.dumps({
        "red_flags": [
            {
                "severity": "high",
                "category": "odstapienie_bez_przyczyny",
                "message": "Prawo do odstąpienia w każdym czasie bez podania przyczyny przy braku odszkodowania za utracony zysk i koszty mobilizacji jest klauzulą rażąco niekorzystną.",
                "provenance": {"section": "§19 ust. 1", "quote": "może odstąpić od umowy w każdym czasie bez podania przyczyny"},
                "confidence": 0.97,
            },
            {
                "severity": "high",
                "category": "pomniejszenie_o_oszczednosci",
                "message": "Klauzula \"pomniejszenia o oszczędności Wykonawcy\" jest nieprecyzyjna i daje Zamawiającemu narzędzie do arbitralnego zmniejszania wynagrodzenia przy odstąpieniu.",
                "provenance": {"section": "§19 ust. 2", "quote": "pomniejszone o oszczędności Wykonawcy"},
                "confidence": 0.88,
            },
            {
                "severity": "high",
                "category": "zwrot_zaliczek",
                "message": "Żądanie zwrotu zaliczek w 7 dni przy odstąpieniu (niezależnie od zaawansowania robót) grozi Wykonawcy utratą płynności finansowej — zaliczki mogły już być wydane na materiały.",
                "provenance": {"section": "§19 ust. 3", "quote": "zwrotu wypłaconych zaliczek w pełnej wysokości w terminie 7 dni od odstąpienia"},
                "confidence": 0.94,
            },
        ]
    })},
]})

# ─── DECISION (8 examples) ────────────────────────────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Przebudowa drogi gminnej nr 104567L w gminie Puławy\n"
        "- CPV: 45233120-6 (roboty drogowe)\n"
        "- Wartość: 3 200 000 PLN\n"
        "- Region: lubelskie\n"
        "- Termin realizacji: 120 dni\n"
        "- Wymagania: 2 roboty drogowe ≥1 mln PLN, polisa OC 1,5 mln PLN\n"
        "- Ocena ryzyka umownego: niskie (brak red_flags)\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: roboty drogowe i ziemne\n"
        "- Region działania: lubelskie, podkarpackie\n"
        "- Referencje: 8 robót drogowych ≥1 mln PLN w ostatnich 3 latach\n"
        "- Polisa OC: 5 mln PLN\n"
        "- Obecne obłożenie: 65% (ma wolne moce przerobowe)\n"
        "- Wynik dopasowania ML: 0.87"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "bid",
        "confidence": 0.92,
        "reasoning": "Przetarg idealnie pasuje do profilu firmy — CPV i region zgodne, referencje z dużą nadwyżką spełniają wymogi, polisa OC ponad wymaganą, firma ma wolne moce. Brak ryzyk umownych i korzystny wynik ML (0.87) potwierdzają dobrą szansę na wygraną.",
        "risk_level": "low",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Budowa mostu przez rzekę San na DK nr 77 w Leżajsku\n"
        "- CPV: 45221100-3 (roboty mostowe)\n"
        "- Wartość: 48 000 000 PLN\n"
        "- Region: podkarpackie\n"
        "- Termin realizacji: 36 miesięcy\n"
        "- Wymagania: min. 3 mosty ≥20 mln PLN, kierownik z uprawnieniami mostowymi, "
        "zdolność kredytowa 15 mln PLN\n"
        "- Ocena ryzyka umownego: wysokie (kary 0,5%/dzień, restart gwarancji)\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: roboty drogowe i ziemne (brak specjalizacji mostowej)\n"
        "- Region działania: podkarpackie\n"
        "- Referencje: roboty drogowe, 1 przepust ≥2 mln PLN (nie most)\n"
        "- Zdolność kredytowa: 4 mln PLN\n"
        "- Wynik dopasowania ML: 0.21"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "skip",
        "confidence": 0.96,
        "reasoning": "Firma nie spełnia kluczowych wymagań: brak referencji mostowych (wymagane 3 mosty ≥20 mln PLN), zdolność kredytowa 4× poniżej wymaganej. Specjalizacja drogowa nie jest transferowalna do mostów tej klasy. Wysoki profil ryzyka umownego dodatkowo pogarsza bilans.",
        "risk_level": "high",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Termomodernizacja 5 budynków gminnych w Nowym Sączu\n"
        "- CPV: 45321000-3\n"
        "- Wartość: 6 800 000 PLN\n"
        "- Region: małopolskie\n"
        "- Termin realizacji: 14 miesięcy\n"
        "- Wymagania: min. 2 termomodernizacje ≥2 mln PLN, kierownik z uprawnieniami bud.\n"
        "- Ocena ryzyka umownego: średnie (60-dniowy termin płatności)\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: roboty budowlane ogólne, termomodernizacje\n"
        "- Region działania: małopolskie, śląskie\n"
        "- Referencje: 3 termomodernizacje ≥2 mln PLN\n"
        "- Obłożenie: 90% (jeden duży kontrakt kończy się za 2 miesiące)\n"
        "- Wynik dopasowania ML: 0.74"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "watch",
        "confidence": 0.78,
        "reasoning": "Firma spełnia wymagania merytoryczne i działa w odpowiednim regionie, jednak obecne obłożenie 90% jest ryzykowne — potencjalny konflikt zasobów. Warto obserwować: jeśli bieżący kontrakt skończy się przed ofertowaniem, bilans przemawia za złożeniem oferty. Termin płatności 60 dni wymaga analizy płynności.",
        "risk_level": "medium",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Dostawa i montaż instalacji OZE (PV + pompy ciepła) w 8 placówkach oświatowych w Gdyni\n"
        "- CPV: 45261215-4, 45331000-6\n"
        "- Wartość: 4 500 000 PLN\n"
        "- Region: pomorskie\n"
        "- Termin realizacji: 6 miesięcy\n"
        "- Wymagania: min. 5 instalacji PV ≥50 kWp, min. 3 instalacje PC ≥50 kW, "
        "certyfikat projektanta OZE\n"
        "- Ocena ryzyka umownego: niskie\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: instalacje elektryczne i sanitarne, brak portfolio OZE\n"
        "- Region działania: pomorskie\n"
        "- Referencje: instalacje elektryczne ≥1 mln PLN (brak referencji PV/PC)\n"
        "- Wynik dopasowania ML: 0.38"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "skip",
        "confidence": 0.89,
        "reasoning": "Firma nie ma wymaganych referencji w technologiach OZE — brakuje zarówno instalacji PV jak i pomp ciepła w wymaganej skali. Ogólne doświadczenie elektryczne i sanitarne nie wystarczy do spełnienia wymogów. Niski wynik ML (0.38) potwierdza słabe dopasowanie.",
        "risk_level": "medium",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Remont i modernizacja hali sportowej Centrum Sportu Mokotów w Warszawie\n"
        "- CPV: 45212200-8\n"
        "- Wartość: 12 400 000 PLN\n"
        "- Region: mazowieckie\n"
        "- Termin realizacji: 18 miesięcy\n"
        "- Wymagania: min. 2 obiekty sportowe ≥5 mln PLN, kierownik z uprawnieniami bud., doświadczenie w obiektach użyteczności publicznej\n"
        "- Ocena ryzyka umownego: średnie (kary 0,3%/dzień, gwarancja 84 mies.)\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: budynki użyteczności publicznej, obiekty sportowe\n"
        "- Region: mazowieckie, łódzkie\n"
        "- Referencje: 4 hale sportowe w zakresie 4–18 mln PLN\n"
        "- Obłożenie: 55%, wolne zasoby\n"
        "- Wynik ML: 0.82"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "bid",
        "confidence": 0.88,
        "reasoning": "Doskonałe dopasowanie profilowe: 4 hale sportowe w portfolio, region zgodny, wolne moce. Kary 0,3%/dzień są w górnym zakresie dopuszczalnym — wymaga precyzyjnego harmonogramu. Gwarancja 84 mies. zwiększa ryzyko, ale jest do zaakceptowania przy dobrej jakości robót.",
        "risk_level": "medium",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Budowa centrum logistycznego dla POCZTA POLSKA SA, Łódź\n"
        "- CPV: 45213150-9\n"
        "- Wartość: 85 000 000 PLN\n"
        "- Region: łódzkie\n"
        "- Termin realizacji: 24 miesiące\n"
        "- Wymagania: min. 2 magazyny/centrum log. ≥30 mln PLN, zdolność kredytowa 25 mln PLN, "
        "certyfikat AQAP lub ISO 9001\n"
        "- Ocena ryzyka umownego: wysokie (kary bez limitu, płatność 60 dni, wstrzymanie robót 60 dni)\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: hale przemysłowe, magazyny\n"
        "- Region: łódzkie, mazowieckie\n"
        "- Referencje: 2 magazyny ≥35 mln PLN\n"
        "- Zdolność kredytowa: 28 mln PLN\n"
        "- ISO 9001: tak\n"
        "- Wynik ML: 0.68"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "watch",
        "confidence": 0.71,
        "reasoning": "Firma spełnia wymagania formalne, ale profil ryzyka umownego jest bardzo wysoki (kary bez limitu, 60-dniowe wstrzymanie bez rekompensaty). Przy kontrakcie 85 mln PLN nawet 30-dniowe opóźnienie generuje kary rzędu ~1,3 mln PLN. Zalecana szczegółowa analiza prawna warunków przed ofertowaniem oraz negocjacja kluczowych klauzul.",
        "risk_level": "high",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Przebudowa ulicy Kwiatowej wraz z kanalizacją deszczową w Suwałkach\n"
        "- CPV: 45233120-6, 45232130-2\n"
        "- Wartość: 2 100 000 PLN\n"
        "- Region: podlaskie\n"
        "- Termin realizacji: 90 dni\n"
        "- Wymagania: 1 robota drogowa ≥1 mln PLN, polisa OC 1 mln PLN\n"
        "- Ocena ryzyka umownego: niskie\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: roboty drogowe i sanitarne\n"
        "- Region: warmińsko-mazurskie, mazowieckie (brak bazy na Podlasiu)\n"
        "- Referencje: 6 robót drogowych ≥1 mln PLN\n"
        "- Obłożenie: 40%\n"
        "- Wynik ML: 0.55"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "watch",
        "confidence": 0.65,
        "reasoning": "Firma spełnia wymogi formalne, ale brak bazy operacyjnej w województwie podlaskim zwiększa koszty mobilizacji i logistyki. Wartość 2,1 mln PLN przy wyjazdowej brygadzie może nie być opłacalna. Należy przeanalizować marżowość przed decyzją. Jeśli w regionie jest aktualnie inna realizacja — bid.",
        "risk_level": "medium",
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_DECISION},
    {"role": "user", "content": (
        "Przetarg:\n"
        "- Tytuł: Remont dachu i elewacji Ratusza Miejskiego w Toruniu (obiekt zabytkowy)\n"
        "- CPV: 45453000-7\n"
        "- Wartość: 3 900 000 PLN\n"
        "- Region: kujawsko-pomorskie\n"
        "- Termin realizacji: 12 miesięcy\n"
        "- Wymagania: min. 2 remonty obiektów zabytkowych ≥1,5 mln PLN, "
        "kierownik robót z uprawnieniami do robót przy zabytkach (art. 37c PrZab)\n"
        "- Ocena ryzyka umownego: średnie\n\n"
        "Profil firmy:\n"
        "- Specjalizacja: roboty ogólnobudowlane, remonty — brak doświadczenia przy zabytkach\n"
        "- Region: kujawsko-pomorskie\n"
        "- Referencje: remonty budynków (nie zabytkowych)\n"
        "- Wynik ML: 0.29"
    )},
    {"role": "assistant", "content": json.dumps({
        "verdict": "skip",
        "confidence": 0.91,
        "reasoning": "Wymagania kwalifikacyjne są jasne i specjalistyczne: doświadczenie przy zabytkach i kierownik z uprawnieniami art. 37c PrZab — firma nie spełnia obu warunków. Oferta złożona bez spełnienia wymagań zostanie odrzucona. Niski wynik ML (0.29) potwierdza brak dopasowania.",
        "risk_level": "low",
    })},
]})

# ─── EXTRACT_PRZEDMIAR (8 examples) ──────────────────────────────────────────

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR ROBÓT — DZIAŁ 1: ROBOTY ZIEMNE\n\n"
        "Lp.  Podstawa         Opis                                          Jm    Ilość\n"
        "1.1  KNR 2-01 0111-03  Korytowanie mechaniczne gr. 30 cm             m2    6 200\n"
        "1.2  KNR 2-01 0211-03  Wykopy mechaniczne w gr. kat. III pod ławy    m3    1 540\n"
        "1.3  KNR 2-01 0307-02  Nasypy z gruntu kat. II z zagęszczeniem       m3    3 200\n"
        "1.4  KNR 2-01 0510-01  Transport urobku samochodami na 5 km          m3      820\n"
        "1.5  KNR 2-01 0601-02  Profilowanie i zagęszczenie podłoża gruntowego m2   6 200"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "1.1", "description": "Korytowanie mechaniczne gr. 30 cm", "unit": "m2", "quantity": 6200.0, "knr_code": "KNR 2-01 0111-03", "confidence": 0.97},
            {"position_no": "1.2", "description": "Wykopy mechaniczne w gr. kat. III pod ławy", "unit": "m3", "quantity": 1540.0, "knr_code": "KNR 2-01 0211-03", "confidence": 0.96},
            {"position_no": "1.3", "description": "Nasypy z gruntu kat. II z zagęszczeniem", "unit": "m3", "quantity": 3200.0, "knr_code": "KNR 2-01 0307-02", "confidence": 0.95},
            {"position_no": "1.4", "description": "Transport urobku samochodami na 5 km", "unit": "m3", "quantity": 820.0, "knr_code": "KNR 2-01 0510-01", "confidence": 0.94},
            {"position_no": "1.5", "description": "Profilowanie i zagęszczenie podłoża gruntowego", "unit": "m2", "quantity": 6200.0, "knr_code": "KNR 2-01 0601-02", "confidence": 0.96},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR ROBÓT — DZIAŁ 2: PODBUDOWY I NAWIERZCHNIE\n\n"
        "Pos.  KNR                Opis robót                                     Jm    Ilość\n"
        "2.1   KNR 2-31 0101-02   Podbudowa z kruszywa łamanego 0/31,5 gr.20cm   m2    5 400\n"
        "2.2   KNR 2-31 0201-01   Podbudowa z betonu asfaltowego AC22P gr.8cm    m2    5 400\n"
        "2.3   KNR 2-31 0301-03   Warstwa wiążąca z AC16W gr.7cm                 m2    5 400\n"
        "2.4   KNR 2-31 0401-02   Warstwa ścieralna z AC11S gr.5cm               m2    5 400\n"
        "2.5   KNR 2-31 0501-01   Nawierzchnia z kostki betonowej 8cm (chodnik)  m2      870\n"
        "2.6   KNR 2-31 0601-01   Krawężnik betonowy 15×30cm na ławie beton.     m     1 240"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "2.1", "description": "Podbudowa z kruszywa łamanego 0/31,5 gr. 20 cm", "unit": "m2", "quantity": 5400.0, "knr_code": "KNR 2-31 0101-02", "confidence": 0.97},
            {"position_no": "2.2", "description": "Podbudowa z betonu asfaltowego AC22P gr. 8 cm", "unit": "m2", "quantity": 5400.0, "knr_code": "KNR 2-31 0201-01", "confidence": 0.95},
            {"position_no": "2.3", "description": "Warstwa wiążąca z AC16W gr. 7 cm", "unit": "m2", "quantity": 5400.0, "knr_code": "KNR 2-31 0301-03", "confidence": 0.96},
            {"position_no": "2.4", "description": "Warstwa ścieralna z AC11S gr. 5 cm", "unit": "m2", "quantity": 5400.0, "knr_code": "KNR 2-31 0401-02", "confidence": 0.96},
            {"position_no": "2.5", "description": "Nawierzchnia z kostki betonowej 8 cm (chodnik)", "unit": "m2", "quantity": 870.0, "knr_code": "KNR 2-31 0501-01", "confidence": 0.95},
            {"position_no": "2.6", "description": "Krawężnik betonowy 15×30 cm na ławie betonowej", "unit": "m", "quantity": 1240.0, "knr_code": "KNR 2-31 0601-01", "confidence": 0.94},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR — DZIAŁ 3: INSTALACJE ELEKTRYCZNE\n\n"
        "Nr   Norma              Opis                                          Jm    Ilość\n"
        "3.1  KNR E-04 0201-01   Układanie kabla YKY 3×2,5mm2 w rurce         m     2 100\n"
        "3.2  KNR E-04 0201-03   Układanie kabla YKY 4×16mm2 w ziemi          m       380\n"
        "3.3  KNR E-04 0301-01   Rozdzielnica elektryczna RG-48               szt.      4\n"
        "3.4  KNR E-04 0401-02   Montaż gniazda 230V podtynkowego             szt.    186\n"
        "3.5  KNR E-04 0401-06   Montaż wyłącznika łącznikowego               szt.     92\n"
        "3.6  KNR E-04 0501-01   Oprawa świetlówkowa 2×36W hermetyczna       szt.     64\n"
        "3.7  KNR E-04 0601-02   Pomiary instalacji elektrycznej (obwody)     kpl.      1"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "3.1", "description": "Układanie kabla YKY 3×2,5mm2 w rurce", "unit": "m", "quantity": 2100.0, "knr_code": "KNR E-04 0201-01", "confidence": 0.96},
            {"position_no": "3.2", "description": "Układanie kabla YKY 4×16mm2 w ziemi", "unit": "m", "quantity": 380.0, "knr_code": "KNR E-04 0201-03", "confidence": 0.95},
            {"position_no": "3.3", "description": "Rozdzielnica elektryczna RG-48", "unit": "szt.", "quantity": 4.0, "knr_code": "KNR E-04 0301-01", "confidence": 0.94},
            {"position_no": "3.4", "description": "Montaż gniazda 230V podtynkowego", "unit": "szt.", "quantity": 186.0, "knr_code": "KNR E-04 0401-02", "confidence": 0.97},
            {"position_no": "3.5", "description": "Montaż wyłącznika łącznikowego", "unit": "szt.", "quantity": 92.0, "knr_code": "KNR E-04 0401-06", "confidence": 0.96},
            {"position_no": "3.6", "description": "Oprawa świetlówkowa 2×36W hermetyczna", "unit": "szt.", "quantity": 64.0, "knr_code": "KNR E-04 0501-01", "confidence": 0.94},
            {"position_no": "3.7", "description": "Pomiary instalacji elektrycznej (obwody)", "unit": "kpl.", "quantity": 1.0, "knr_code": "KNR E-04 0601-02", "confidence": 0.93},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR — DZIAŁ 4: ROBOTY BETONOWE I ŻELBETOWE\n\n"
        "Poz.  Katalog            Opis pozycji                                  Jm    Ilość\n"
        "4.1   KNR 2-02 0101-04   Ławy fundamentowe betonowe C20/25             m3      240\n"
        "4.2   KNR 2-02 0201-02   Ściany fundamentowe żelbetowe C25/30          m3      180\n"
        "4.3   KNR 2-02 0301-01   Słupy żelbetowe kwadratowe 40×40cm C30/37     m3       48\n"
        "4.4   KNR 2-02 0401-03   Strop Filigran gr.24cm, nadbeton C25/30       m2    1 800\n"
        "4.5   KNR 2-02 0501-01   Schody żelbetowe monolityczne C25/30          m3       22\n"
        "4.6   KNR 2-02 0601-02   Zbrojenie stalą A-IIIN (B500SP) — ogółem      kg   48 200"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "4.1", "description": "Ławy fundamentowe betonowe C20/25", "unit": "m3", "quantity": 240.0, "knr_code": "KNR 2-02 0101-04", "confidence": 0.97},
            {"position_no": "4.2", "description": "Ściany fundamentowe żelbetowe C25/30", "unit": "m3", "quantity": 180.0, "knr_code": "KNR 2-02 0201-02", "confidence": 0.96},
            {"position_no": "4.3", "description": "Słupy żelbetowe kwadratowe 40×40cm C30/37", "unit": "m3", "quantity": 48.0, "knr_code": "KNR 2-02 0301-01", "confidence": 0.95},
            {"position_no": "4.4", "description": "Strop Filigran gr. 24 cm, nadbeton C25/30", "unit": "m2", "quantity": 1800.0, "knr_code": "KNR 2-02 0401-03", "confidence": 0.94},
            {"position_no": "4.5", "description": "Schody żelbetowe monolityczne C25/30", "unit": "m3", "quantity": 22.0, "knr_code": "KNR 2-02 0501-01", "confidence": 0.95},
            {"position_no": "4.6", "description": "Zbrojenie stalą A-IIIN (B500SP) — ogółem", "unit": "kg", "quantity": 48200.0, "knr_code": "KNR 2-02 0601-02", "confidence": 0.92},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR — DZIAŁ 5: ROBOTY DEKARSKIE I IZOLACJE DACHU\n\n"
        "Poz.  Norma              Opis                                          Jm    Ilość\n"
        "5.1   KNR 2-02 1101-01   Izolacja termiczna dachu — wełna mineralna 20cm m2   920\n"
        "5.2   KNR 2-02 1102-01   Paroizolacja z folii PE 0,2mm               m2      920\n"
        "5.3   KNR 2-02 1201-02   Pokrycie dachu papą termozgrzewalną 2-warstwowo m2   920\n"
        "5.4   KNR 2-02 1301-01   Obróbki blacharskie z blachy ocynkowanej     m        84\n"
        "5.5   KNR 2-02 1401-01   Rynny i rury spustowe PVC Ø150/110mm         m       210\n"
        "5.6   KNR 2-02 1501-02   Wyłaz dachowy Fakro DRL 60×80cm              szt.      2"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "5.1", "description": "Izolacja termiczna dachu — wełna mineralna 20 cm", "unit": "m2", "quantity": 920.0, "knr_code": "KNR 2-02 1101-01", "confidence": 0.97},
            {"position_no": "5.2", "description": "Paroizolacja z folii PE 0,2 mm", "unit": "m2", "quantity": 920.0, "knr_code": "KNR 2-02 1102-01", "confidence": 0.96},
            {"position_no": "5.3", "description": "Pokrycie dachu papą termozgrzewalną 2-warstwowo", "unit": "m2", "quantity": 920.0, "knr_code": "KNR 2-02 1201-02", "confidence": 0.95},
            {"position_no": "5.4", "description": "Obróbki blacharskie z blachy ocynkowanej", "unit": "m", "quantity": 84.0, "knr_code": "KNR 2-02 1301-01", "confidence": 0.94},
            {"position_no": "5.5", "description": "Rynny i rury spustowe PVC Ø150/110mm", "unit": "m", "quantity": 210.0, "knr_code": "KNR 2-02 1401-01", "confidence": 0.95},
            {"position_no": "5.6", "description": "Wyłaz dachowy Fakro DRL 60×80cm", "unit": "szt.", "quantity": 2.0, "knr_code": "KNR 2-02 1501-02", "confidence": 0.93},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR — DZIAŁ 6: INSTALACJE SANITARNE (CO i CWU)\n\n"
        "Nr   KNR               Opis robót                                    Jm    Ilość\n"
        "6.1  KNR 3-01 0101-02  Rurociąg stalowy czarny Ø32mm — montaż       m       240\n"
        "6.2  KNR 3-01 0101-04  Rurociąg stalowy czarny Ø50mm — montaż       m       120\n"
        "6.3  KNR 3-01 0201-01  Grzejnik płytowy PURMO C22 600×1200mm        szt.     48\n"
        "6.4  KNR 3-01 0301-01  Zawór termostatyczny RTL Ø1/2\"               szt.     48\n"
        "6.5  KNR 3-01 0401-02  Kocioł kondensacyjny gazowy 60kW z zasobnikiem kpl.    1\n"
        "6.6  KNR 3-01 0501-01  Naczynia wzbiorcze i armatura bezpieczeństwa  kpl.    1\n"
        "6.7  KNR 3-01 0601-01  Próba szczelności i płukanie instalacji CO    kpl.    1"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "6.1", "description": "Rurociąg stalowy czarny Ø32mm — montaż", "unit": "m", "quantity": 240.0, "knr_code": "KNR 3-01 0101-02", "confidence": 0.96},
            {"position_no": "6.2", "description": "Rurociąg stalowy czarny Ø50mm — montaż", "unit": "m", "quantity": 120.0, "knr_code": "KNR 3-01 0101-04", "confidence": 0.95},
            {"position_no": "6.3", "description": "Grzejnik płytowy PURMO C22 600×1200mm", "unit": "szt.", "quantity": 48.0, "knr_code": "KNR 3-01 0201-01", "confidence": 0.97},
            {"position_no": "6.4", "description": "Zawór termostatyczny RTL Ø1/2\"", "unit": "szt.", "quantity": 48.0, "knr_code": "KNR 3-01 0301-01", "confidence": 0.96},
            {"position_no": "6.5", "description": "Kocioł kondensacyjny gazowy 60kW z zasobnikiem", "unit": "kpl.", "quantity": 1.0, "knr_code": "KNR 3-01 0401-02", "confidence": 0.94},
            {"position_no": "6.6", "description": "Naczynia wzbiorcze i armatura bezpieczeństwa", "unit": "kpl.", "quantity": 1.0, "knr_code": "KNR 3-01 0501-01", "confidence": 0.93},
            {"position_no": "6.7", "description": "Próba szczelności i płukanie instalacji CO", "unit": "kpl.", "quantity": 1.0, "knr_code": "KNR 3-01 0601-01", "confidence": 0.95},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR ROBÓT ROZBIÓRKOWYCH — DZIAŁ 7\n\n"
        "Poz.  Podstawa          Opis                                          Jm    Ilość\n"
        "7.1   KNR 4-01 0101-02   Rozbiórka nawierzchni bitumicznej gr.8cm      m2    3 600\n"
        "7.2   KNR 4-01 0201-01   Rozbiórka podbudowy tłuczniowej gr.20cm       m2    3 600\n"
        "7.3   KNR 4-01 0301-03   Rozbiórka krawężników betonowych              m       760\n"
        "7.4   KNR 4-01 0401-01   Rozbiórka przepustów betonowych Ø500mm        m        36\n"
        "7.5   KNR 4-01 0501-02   Wywóz gruzu na odległość do 10km              m3      420\n"
        "7.6   KNR 4-01 0601-01   Utylizacja materiałów z rozbiórki (asfalt)    Mg       94"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "7.1", "description": "Rozbiórka nawierzchni bitumicznej gr. 8 cm", "unit": "m2", "quantity": 3600.0, "knr_code": "KNR 4-01 0101-02", "confidence": 0.97},
            {"position_no": "7.2", "description": "Rozbiórka podbudowy tłuczniowej gr. 20 cm", "unit": "m2", "quantity": 3600.0, "knr_code": "KNR 4-01 0201-01", "confidence": 0.96},
            {"position_no": "7.3", "description": "Rozbiórka krawężników betonowych", "unit": "m", "quantity": 760.0, "knr_code": "KNR 4-01 0301-03", "confidence": 0.95},
            {"position_no": "7.4", "description": "Rozbiórka przepustów betonowych Ø500mm", "unit": "m", "quantity": 36.0, "knr_code": "KNR 4-01 0401-01", "confidence": 0.94},
            {"position_no": "7.5", "description": "Wywóz gruzu na odległość do 10 km", "unit": "m3", "quantity": 420.0, "knr_code": "KNR 4-01 0501-02", "confidence": 0.95},
            {"position_no": "7.6", "description": "Utylizacja materiałów z rozbiórki (asfalt)", "unit": "Mg", "quantity": 94.0, "knr_code": "KNR 4-01 0601-01", "confidence": 0.92},
        ]
    })},
]})

examples.append({"messages": [
    {"role": "system", "content": SYS_PRZEDMIAR},
    {"role": "user", "content": (
        "PRZEDMIAR — DZIAŁ 8: ZAGOSPODAROWANIE TERENU\n\n"
        "Poz.  Norma              Opis pozycji                                  Jm    Ilość\n"
        "8.1   KNR 2-21 0101-01   Trawnik z siewu na przygotowanej glebie       m2    2 400\n"
        "8.2   KNR 2-21 0201-02   Sadzenie drzew liściastych o bryłce 60L       szt.    24\n"
        "8.3   KNR 2-21 0301-01   Sadzenie krzewów ozdobnych w grupach           szt.   180\n"
        "8.4   KNR 2-21 0401-02   Nawierzchnia żwirowa stabilizowana Ø8–16mm   m2      640\n"
        "8.5   KNR 2-21 0501-01   Ogrodzenie panelowe ocynk. wys. 1,5m z słupami m      210\n"
        "8.6   KNR 2-21 0601-03   Ławka parkowa betonowa z oparciem             szt.    12\n"
        "8.7   KNR 2-21 0701-01   Kosz na odpadki 60L z podstawą               szt.     8"
    )},
    {"role": "assistant", "content": json.dumps({
        "items": [
            {"position_no": "8.1", "description": "Trawnik z siewu na przygotowanej glebie", "unit": "m2", "quantity": 2400.0, "knr_code": "KNR 2-21 0101-01", "confidence": 0.97},
            {"position_no": "8.2", "description": "Sadzenie drzew liściastych o bryłce 60L", "unit": "szt.", "quantity": 24.0, "knr_code": "KNR 2-21 0201-02", "confidence": 0.96},
            {"position_no": "8.3", "description": "Sadzenie krzewów ozdobnych w grupach", "unit": "szt.", "quantity": 180.0, "knr_code": "KNR 2-21 0301-01", "confidence": 0.95},
            {"position_no": "8.4", "description": "Nawierzchnia żwirowa stabilizowana Ø8–16mm", "unit": "m2", "quantity": 640.0, "knr_code": "KNR 2-21 0401-02", "confidence": 0.94},
            {"position_no": "8.5", "description": "Ogrodzenie panelowe ocynk. wys. 1,5m z słupami", "unit": "m", "quantity": 210.0, "knr_code": "KNR 2-21 0501-01", "confidence": 0.93},
            {"position_no": "8.6", "description": "Ławka parkowa betonowa z oparciem", "unit": "szt.", "quantity": 12.0, "knr_code": "KNR 2-21 0601-03", "confidence": 0.95},
            {"position_no": "8.7", "description": "Kosz na odpadki 60L z podstawą", "unit": "szt.", "quantity": 8.0, "knr_code": "KNR 2-21 0701-01", "confidence": 0.94},
        ]
    })},
]})

# ─── Write JSONL ────────────────────────────────────────────────────────────

assert len(examples) == 50, f"Expected 50 examples, got {len(examples)}"

output_path = pathlib.Path(__file__).parent / "dataset_v1.jsonl"
with open(output_path, "w", encoding="utf-8") as fh:
    for ex in examples:
        fh.write(json.dumps(ex, ensure_ascii=False) + "\n")

print(f"Written {len(examples)} examples to {output_path}")

# Verify all assistant responses are valid JSON
errors = []
for i, ex in enumerate(examples):
    asst = ex["messages"][-1]["content"]
    try:
        json.loads(asst)
    except json.JSONDecodeError as e:
        errors.append(f"  example {i}: {e}")

if errors:
    print("VALIDATION ERRORS:")
    for e in errors:
        print(e)
else:
    print("All 50 assistant responses are valid JSON ✓")

# Print task distribution
from collections import Counter
task_map = {
    SYS_CLASSIFY: "CLASSIFY",
    SYS_EXTRACT_FIELDS: "EXTRACT_FIELDS",
    SYS_SUMMARIZE: "SUMMARIZE",
    SYS_RISK_FLAGS: "RISK_FLAGS",
    SYS_DECISION: "DECISION",
    SYS_PRZEDMIAR: "EXTRACT_PRZEDMIAR",
}
counts = Counter(task_map.get(ex["messages"][0]["content"], "UNKNOWN") for ex in examples)
print("\nTask distribution:")
for task, count in sorted(counts.items()):
    print(f"  {task}: {count}")
