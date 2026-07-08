"""NUTS code → Polish voivodeship mapping.

Supports NUTS2 (4-char prefix, e.g. PL91) and NUTS3 (5-char, e.g. PL911)
by normalising to the 4-char NUTS2 prefix.

Usage:
    from services.ingestion.nuts_mapping import nuts_to_voivodeship
    nuts_to_voivodeship("PL911")   # → "mazowieckie"
    nuts_to_voivodeship("PL21")    # → "małopolskie"
    nuts_to_voivodeship(None)      # → None
"""
from __future__ import annotations

# NUTS2 prefix (4 chars) → canonical Polish voivodeship name
NUTS2_TO_VOIVODESHIP: dict[str, str] = {
    "PL21": "małopolskie",
    "PL22": "śląskie",
    "PL41": "wielkopolskie",
    "PL42": "zachodniopomorskie",
    "PL43": "lubuskie",
    "PL51": "dolnośląskie",
    "PL52": "opolskie",
    "PL61": "kujawsko-pomorskie",
    "PL62": "warmińsko-mazurskie",
    "PL63": "pomorskie",
    "PL71": "łódzkie",
    "PL72": "świętokrzyskie",
    "PL81": "lubelskie",
    "PL82": "podkarpackie",
    "PL84": "podlaskie",
    "PL91": "mazowieckie",
    "PL92": "mazowieckie",
}


def nuts_to_voivodeship(nuts_code: str | None) -> str | None:
    """Map a NUTS2 or NUTS3 code to a Polish voivodeship name.

    Args:
        nuts_code: NUTS code string, e.g. "PL911", "PL91", "PL213".
                   Case-insensitive.  None / empty returns None.

    Returns:
        Canonical lowercase voivodeship name, or None if not mappable.
    """
    if not nuts_code:
        return None
    code = nuts_code.strip().upper()
    # Try exact NUTS2 match first (4 chars)
    if len(code) >= 4:
        prefix = code[:4]
        if prefix in NUTS2_TO_VOIVODESHIP:
            return NUTS2_TO_VOIVODESHIP[prefix]
    return None


def nuts_codes_to_voivodeship(nuts_codes: list[str] | None) -> str | None:
    """Try each code in a list and return the first successful mapping."""
    if not nuts_codes:
        return None
    for code in nuts_codes:
        result = nuts_to_voivodeship(code)
        if result:
            return result
    return None


# ---------------------------------------------------------------------------
# City → voivodeship fallback lookup (for TED records that lack NUTS codes)
# ---------------------------------------------------------------------------

# Comprehensive mapping of major Polish cities / towns to voivodeships.
# Keys are lowercase, stripped, accents-preserved for exact match;
# also handled with simple ASCII fallback in the lookup function.
CITY_TO_VOIVODESHIP: dict[str, str] = {
    # dolnośląskie
    "wrocław": "dolnośląskie",
    "jelenia góra": "dolnośląskie",
    "legnica": "dolnośląskie",
    "wałbrzych": "dolnośląskie",
    "lubin": "dolnośląskie",
    "świdnica": "dolnośląskie",
    "bolesławiec": "dolnośląskie",
    "głogów": "dolnośląskie",
    "dzierżoniów": "dolnośląskie",
    "polkowice": "dolnośląskie",
    "oleśnica": "dolnośląskie",
    "oława": "dolnośląskie",
    "nowa ruda": "dolnośląskie",
    "kamienna góra": "dolnośląskie",
    "lubań": "dolnośląskie",
    "długołęka": "dolnośląskie",
    "zgorzelec": "dolnośląskie",
    "trzebnica": "dolnośląskie",
    "środa śląska": "dolnośląskie",
    "kłodzko": "dolnośląskie",
    "bielawa": "dolnośląskie",
    "bystrzyca kłodzka": "dolnośląskie",
    "strzelin": "dolnośląskie",
    "ząbkowice śląskie": "dolnośląskie",
    "góra": "dolnośląskie",
    # kujawsko-pomorskie
    "bydgoszcz": "kujawsko-pomorskie",
    "toruń": "kujawsko-pomorskie",
    "włocławek": "kujawsko-pomorskie",
    "grudziądz": "kujawsko-pomorskie",
    "inowrocław": "kujawsko-pomorskie",
    "świecie": "kujawsko-pomorskie",
    "nakło nad notecią": "kujawsko-pomorskie",
    "brodnica": "kujawsko-pomorskie",
    "chełmno": "kujawsko-pomorskie",
    "kruszwica": "kujawsko-pomorskie",
    "żnin": "kujawsko-pomorskie",
    "tuchola": "kujawsko-pomorskie",
    "lipno": "kujawsko-pomorskie",
    "rypin": "kujawsko-pomorskie",
    # lubelskie
    "lublin": "lubelskie",
    "zamość": "lubelskie",
    "chełm": "lubelskie",
    "biała podlaska": "lubelskie",
    "puławy": "lubelskie",
    "kraśnik": "lubelskie",
    "świdnik": "lubelskie",
    "hrubieszów": "lubelskie",
    "krasnystaw": "lubelskie",
    "radzyń podlaski": "lubelskie",
    "tomaszów lubelski": "lubelskie",
    "bychawa": "lubelskie",
    "łęczna": "lubelskie",
    "poniatowa": "lubelskie",
    "opole lubelskie": "lubelskie",
    "annopol": "lubelskie",
    # lubuskie
    "zielona góra": "lubuskie",
    "gorzów wielkopolski": "lubuskie",
    "nowa sól": "lubuskie",
    "żagań": "lubuskie",
    "żary": "lubuskie",
    "świebodzin": "lubuskie",
    "krosno odrzańskie": "lubuskie",
    "gubin": "lubuskie",
    "sulęcin": "lubuskie",
    "słubice": "lubuskie",
    "kalisz pomorski": "lubuskie",
    # łódzkie
    "łódź": "łódzkie",
    "piotrków trybunalski": "łódzkie",
    "pabianice": "łódzkie",
    "tomaszów mazowiecki": "łódzkie",
    "bełchatów": "łódzkie",
    "zgierz": "łódzkie",
    "skierniewice": "łódzkie",
    "zduńska wola": "łódzkie",
    "radomsko": "łódzkie",
    "sieradz": "łódzkie",
    "łowicz": "łódzkie",
    "aleksandrów łódzki": "łódzkie",
    "konstantynów łódzki": "łódzkie",
    "kutno": "łódzkie",
    "wieluń": "łódzkie",
    "opoczno": "łódzkie",
    "głuchów": "łódzkie",
    # małopolskie
    "kraków": "małopolskie",
    "tarnów": "małopolskie",
    "nowy sącz": "małopolskie",
    "nowy targ": "małopolskie",
    "olkusz": "małopolskie",
    "oświęcim": "małopolskie",
    "chrzanów": "małopolskie",
    "wieliczka": "małopolskie",
    "zakopane": "małopolskie",
    "gorlice": "małopolskie",
    "sucha beskidzka": "małopolskie",
    "myślenice": "małopolskie",
    "wadowice": "małopolskie",
    "limanowa": "małopolskie",
    "jodłownik": "małopolskie",
    "brzesko": "małopolskie",
    "proszowice": "małopolskie",
    "miechów": "małopolskie",
    "dąbrowa tarnowska": "małopolskie",
    "tuchów": "małopolskie",
    "jordanów": "małopolskie",
    "bystra podhalańska": "małopolskie",
    "raba wyżna": "małopolskie",
    "rabka-zdrój": "małopolskie",
    # mazowieckie
    "warszawa": "mazowieckie",
    "radom": "mazowieckie",
    "płock": "mazowieckie",
    "siedlce": "mazowieckie",
    "ostrołęka": "mazowieckie",
    "pruszków": "mazowieckie",
    "legionowo": "mazowieckie",
    "ciechanów": "mazowieckie",
    "żyrardów": "mazowieckie",
    "otwock": "mazowieckie",
    "wołomin": "mazowieckie",
    "piastów": "mazowieckie",
    "piaseczno": "mazowieckie",
    "nowy dwór mazowiecki": "mazowieckie",
    "grodzisk mazowiecki": "mazowieckie",
    "konstancin-jeziorna": "mazowieckie",
    "konstancin – jeziorna": "mazowieckie",
    "konstancin": "mazowieckie",
    "celestynów": "mazowieckie",
    "cegłów": "mazowieckie",
    "kozienice": "mazowieckie",
    "mińsk mazowiecki": "mazowieckie",
    "białobrzegi": "mazowieckie",
    "zwoleń": "mazowieckie",
    "garwolin": "mazowieckie",
    "maków mazowiecki": "mazowieckie",
    "pułtusk": "mazowieckie",
    "łomianki": "mazowieckie",
    "mszczonów": "mazowieckie",
    "starachowice": "mazowieckie",
    # opolskie
    "opole": "opolskie",
    "kędzierzyn-koźle": "opolskie",
    "nysa": "opolskie",
    "brzeg": "opolskie",
    "strzelce opolskie": "opolskie",
    "kluczbork": "opolskie",
    "namysłów": "opolskie",
    "głubczyce": "opolskie",
    "kup": "opolskie",
    "prószków": "opolskie",
    # podkarpackie
    "rzeszów": "podkarpackie",
    "przemyśl": "podkarpackie",
    "stalowa wola": "podkarpackie",
    "mielec": "podkarpackie",
    "tarnobrzeg": "podkarpackie",
    "krosno": "podkarpackie",
    "jasło": "podkarpackie",
    "sanok": "podkarpackie",
    "dębica": "podkarpackie",
    "leżajsk": "podkarpackie",
    "łańcut": "podkarpackie",
    "ropczyce": "podkarpackie",
    "jarosław": "podkarpackie",
    "jasionka": "podkarpackie",
    "kolbuszowa": "podkarpackie",
    "lubaczów": "podkarpackie",
    # podlaskie
    "białystok": "podlaskie",
    "suwałki": "podlaskie",
    "łomża": "podlaskie",
    "augustów": "podlaskie",
    "bielsk podlaski": "podlaskie",
    "hajnówka": "podlaskie",
    "wysokie mazowieckie": "podlaskie",
    "zambrów": "podlaskie",
    "goniądz": "podlaskie",
    "sokółka": "podlaskie",
    "siemiatycze": "podlaskie",
    # pomorskie
    "gdańsk": "pomorskie",
    "gdynia": "pomorskie",
    "sopot": "pomorskie",
    "słupsk": "pomorskie",
    "tczew": "pomorskie",
    "starogard gdański": "pomorskie",
    "chojnice": "pomorskie",
    "człuchów": "pomorskie",
    "malbork": "pomorskie",
    "kościerzyna": "pomorskie",
    "lębork": "pomorskie",
    "wejherowo": "pomorskie",
    "kosakowo": "pomorskie",
    "lubichowo": "pomorskie",
    "puck": "pomorskie",
    "kartuzy": "pomorskie",
    # śląskie
    "katowice": "śląskie",
    "sosnowiec": "śląskie",
    "gliwice": "śląskie",
    "zabrze": "śląskie",
    "bielsko-biała": "śląskie",
    "bytom": "śląskie",
    "ruda śląska": "śląskie",
    "rybnik": "śląskie",
    "tychy": "śląskie",
    "dąbrowa górnicza": "śląskie",
    "chorzów": "śląskie",
    "jastrzębie-zdrój": "śląskie",
    "jaworzno": "śląskie",
    "siemianowice śląskie": "śląskie",
    "żory": "śląskie",
    "mysłowice": "śląskie",
    "piekary śląskie": "śląskie",
    "tarnowskie góry": "śląskie",
    "mikołów": "śląskie",
    "czechowice-dziedzice": "śląskie",
    "będzin": "śląskie",
    "myszków": "śląskie",
    "zawiercie": "śląskie",
    "wodzisław śląski": "śląskie",
    "pszczyna": "śląskie",
    "kornowac": "śląskie",
    "częstochowa": "śląskie",
    "knurów": "śląskie",
    "cieszyn": "śląskie",
    "skoczów": "śląskie",
    "lędziny": "śląskie",
    "łaziska górne": "śląskie",
    # świętokrzyskie
    "kielce": "świętokrzyskie",
    "ostrowiec świętokrzyski": "świętokrzyskie",
    "skarżysko-kamienna": "świętokrzyskie",
    "końskie": "świętokrzyskie",
    "starachowice": "świętokrzyskie",
    "busko-zdrój": "świętokrzyskie",
    "jędrzejów": "świętokrzyskie",
    "sandomierz": "świętokrzyskie",
    "staszów": "świętokrzyskie",
    "kazimierza wielka": "świętokrzyskie",
    # warmińsko-mazurskie
    "olsztyn": "warmińsko-mazurskie",
    "elbląg": "warmińsko-mazurskie",
    "ełk": "warmińsko-mazurskie",
    "ostróda": "warmińsko-mazurskie",
    "iława": "warmińsko-mazurskie",
    "kętrzyn": "warmińsko-mazurskie",
    "giżycko": "warmińsko-mazurskie",
    "mrągowo": "warmińsko-mazurskie",
    "olecko": "warmińsko-mazurskie",
    "pisz": "warmińsko-mazurskie",
    "bartoszyce": "warmińsko-mazurskie",
    "lidzbark warmiński": "warmińsko-mazurskie",
    "działdowo": "warmińsko-mazurskie",
    # wielkopolskie
    "poznań": "wielkopolskie",
    "kalisz": "wielkopolskie",
    "konin": "wielkopolskie",
    "piła": "wielkopolskie",
    "gniezno": "wielkopolskie",
    "leszno": "wielkopolskie",
    "ostrów wielkopolski": "wielkopolskie",
    "nowy tomyśl": "wielkopolskie",
    "szamotuły": "wielkopolskie",
    "gostyń": "wielkopolskie",
    "kościan": "wielkopolskie",
    "środa wielkopolska": "wielkopolskie",
    "jarocin": "wielkopolskie",
    "turek": "wielkopolskie",
    "swarzędz": "wielkopolskie",
    "czempiń": "wielkopolskie",
    "kleczew": "wielkopolskie",
    "komorniki": "wielkopolskie",
    "buk": "wielkopolskie",
    "czerwonak": "wielkopolskie",
    "wolsztyn": "wielkopolskie",
    "pleszew": "wielkopolskie",
    # zachodniopomorskie
    "szczecin": "zachodniopomorskie",
    "koszalin": "zachodniopomorskie",
    "stargard": "zachodniopomorskie",
    "kołobrzeg": "zachodniopomorskie",
    "police": "zachodniopomorskie",
    "świnoujście": "zachodniopomorskie",
    "goleniów": "zachodniopomorskie",
    "gryfino": "zachodniopomorskie",
    "pyrzyce": "zachodniopomorskie",
    "myślibórz": "zachodniopomorskie",
    "drawsko pomorskie": "zachodniopomorskie",
    "mielno": "zachodniopomorskie",
    "białogard": "zachodniopomorskie",
    "świdwin": "zachodniopomorskie",
    "międzyrzecz": "lubuskie",
    # lubelskie
    "parczew": "lubelskie",
    "ryki": "lubelskie",
    # łódzkie
    "spała": "łódzkie",
    "żychlin": "łódzkie",
    "oporów": "łódzkie",
    # małopolskie
    "niepołomice": "małopolskie",
    "brzeszcze": "małopolskie",
    "porąbka": "małopolskie",
    "ujsoły": "śląskie",
    "strumień": "śląskie",
    # mazowieckie
    "ożarów mazowiecki": "mazowieckie",
    "zielonka": "mazowieckie",
    "węgrów": "mazowieckie",
    "rybno": "mazowieckie",
    # podlaskie
    "wizna": "podlaskie",
    # pomorskie
    "rumia": "pomorskie",
    # śląskie
    "radlin": "śląskie",
    # warmińsko-mazurskie
    "szczytno": "warmińsko-mazurskie",
    # wielkopolskie
    "złotów": "wielkopolskie",
    "odolanów": "wielkopolskie",
    # dolnośląskie
    "strzegom": "dolnośląskie",
    "żarów": "dolnośląskie",
    "mysłakowice": "dolnośląskie",
    "zawonia": "dolnośląskie",
    # opolskie
    "turawa": "opolskie",
}


def city_to_voivodeship(city: str | None) -> str | None:
    """Map a city name to a voivodeship, with case/whitespace normalisation.

    Args:
        city: City name string, may be None.

    Returns:
        Canonical lowercase voivodeship name, or None if not found.
    """
    if not city:
        return None
    normalised = city.strip().lower()
    return CITY_TO_VOIVODESHIP.get(normalised)


def extract_nuts_from_raw(raw: dict) -> tuple[str | None, str | None]:
    """Extract (nuts_code, voivodeship) from a TED raw notice dict.

    Tries, in order:
      1. NUTS code fields (place-of-performance-nuts, nuts-code, etc.)
      2. City name fallback via CITY_TO_VOIVODESHIP

    Returns:
        Tuple of (nuts_code or None, voivodeship or None)
    """
    if not raw:
        return None, None

    # 1. Try known NUTS fields
    nuts_code: str | None = None
    nuts_fields = [
        "place-of-performance-nuts",
        "nuts-code",
        "nuts_code",
        "nuts_codes",
        "place-performance-nuts-lot",
        "place-performance-nuts-part",
    ]
    for field in nuts_fields:
        val = raw.get(field)
        if not val:
            continue
        if isinstance(val, list):
            val = val[0] if val else None
        if val:
            nuts_code = str(val).strip().upper()
            break

    voivodeship: str | None = None
    if nuts_code:
        voivodeship = nuts_to_voivodeship(nuts_code)

    # 2. City fallback if no NUTS→voivodeship mapping
    if not voivodeship:
        city_raw = raw.get("organisation-city-buyer")
        if isinstance(city_raw, list):
            # Try each city in the list
            for c in city_raw:
                v = city_to_voivodeship(c)
                if v:
                    voivodeship = v
                    break
        elif isinstance(city_raw, str):
            voivodeship = city_to_voivodeship(city_raw)

    return nuts_code, voivodeship
