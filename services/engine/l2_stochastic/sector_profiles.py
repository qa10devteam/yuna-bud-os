"""
Terra.OS — Sector profiles for Variant B.
Każdy profil to Bayesian prior dla Lognormal(mu, sigma) i zakres CPV.

Profiles:
  EARTHWORKS     — roboty ziemne, drenaż, nasypy         CPV 45111x, 45112x
  ROADS          — drogi, mosty, chodniki                CPV 451x, 452x (drogowe)
  CUBATURE       — kubatura: budynki, hale, remonty       CPV 4521x, 4526x, 4527x
  UTILITIES      — sieci: wod-kan, gaz, teletechnika      CPV 4523x, 4524x, 4525x
  SPECIALISED    — mosty, tunele, specjalistyczne         CPV 4521x most., 4522x
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class RiskFactor:
    name: str
    mu: float          # lognormal mean
    sigma: float       # lognormal std
    description: str = ""

@dataclass
class SectorProfile:
    key: str           # 'earthworks' | 'roads' | 'cubature' | 'utilities' | 'specialised'
    label_pl: str
    cpv_prefixes: List[str]
    factors: List[RiskFactor]
    base_margin_mu: float = 0.08
    base_margin_sigma: float = 0.04


# --- 5 profili ---

EARTHWORKS = SectorProfile(
    key="earthworks",
    label_pl="Roboty ziemne i drenaż",
    cpv_prefixes=["45111", "45112", "45113"],
    base_margin_mu=0.07, base_margin_sigma=0.045,
    factors=[
        RiskFactor("grunty",        mu=1.00, sigma=0.28, description="Warunki gruntowe"),
        RiskFactor("odwodnienie",   mu=1.00, sigma=0.22, description="Odwodnienie i pompowanie"),
        RiskFactor("robocizna",     mu=1.00, sigma=0.14, description="Koszt robocizny"),
        RiskFactor("paliwo",        mu=1.00, sigma=0.18, description="Paliwo i maszyny"),
        RiskFactor("materialy",     mu=1.00, sigma=0.12, description="Materiały (kruszywa)"),
        RiskFactor("czas",          mu=1.00, sigma=0.16, description="Ryzyko opóźnień"),
    ]
)

ROADS = SectorProfile(
    key="roads",
    label_pl="Drogi i infrastruktura drogowa",
    cpv_prefixes=["45100", "45200", "45221", "45233"],
    base_margin_mu=0.08, base_margin_sigma=0.04,
    factors=[
        RiskFactor("asfalt",        mu=1.00, sigma=0.22, description="Ceny bitumu i asfaltu"),
        RiskFactor("kruszywa",      mu=1.00, sigma=0.16, description="Kruszywa drogowe"),
        RiskFactor("robocizna",     mu=1.00, sigma=0.13, description="Koszt robocizny"),
        RiskFactor("utrudnienia",   mu=1.00, sigma=0.20, description="Organizacja ruchu, utrudnienia"),
        RiskFactor("podloze",       mu=1.00, sigma=0.18, description="Nośność podłoża"),
        RiskFactor("czas",          mu=1.00, sigma=0.14, description="Ryzyko opóźnień"),
    ]
)

CUBATURE = SectorProfile(
    key="cubature",
    label_pl="Kubatura (budynki, hale, remonty)",
    cpv_prefixes=["45210", "45260", "45270", "45310", "45320", "45330", "45400"],
    base_margin_mu=0.10, base_margin_sigma=0.05,
    factors=[
        RiskFactor("stal",          mu=1.00, sigma=0.25, description="Ceny stali i zbrojenia"),
        RiskFactor("beton",         mu=1.00, sigma=0.15, description="Beton i prefabrykaty"),
        RiskFactor("robocizna",     mu=1.00, sigma=0.15, description="Koszt robocizny"),
        RiskFactor("instalacje",    mu=1.00, sigma=0.20, description="Podwykonawcy instalacyjni"),
        RiskFactor("projekt",       mu=1.00, sigma=0.18, description="Ryzyko projektowe / kolizje"),
        RiskFactor("czas",          mu=1.00, sigma=0.13, description="Ryzyko opóźnień"),
    ]
)

UTILITIES = SectorProfile(
    key="utilities",
    label_pl="Sieci i instalacje (wod-kan, gaz, tele)",
    cpv_prefixes=["45230", "45231", "45232", "45233", "45234"],
    base_margin_mu=0.09, base_margin_sigma=0.045,
    factors=[
        RiskFactor("rury_materialy", mu=1.00, sigma=0.20, description="Materiały rurociągowe"),
        RiskFactor("kolizje",        mu=1.00, sigma=0.30, description="Kolizje z istniejącą infrastrukturą"),
        RiskFactor("robocizna",      mu=1.00, sigma=0.14, description="Koszt robocizny"),
        RiskFactor("wykopy",         mu=1.00, sigma=0.22, description="Roboty ziemne towarzyszące"),
        RiskFactor("odbior",         mu=1.00, sigma=0.16, description="Ryzyko odbioru / prób szczelności"),
        RiskFactor("czas",           mu=1.00, sigma=0.17, description="Ryzyko opóźnień"),
    ]
)

SPECIALISED = SectorProfile(
    key="specialised",
    label_pl="Specjalistyczne (mosty, tunele, hydro)",
    cpv_prefixes=["45221", "45222", "45240", "45247"],
    base_margin_mu=0.12, base_margin_sigma=0.06,
    factors=[
        RiskFactor("projekt_spec",  mu=1.00, sigma=0.28, description="Ryzyko projektowe specjalistyczne"),
        RiskFactor("materialy",     mu=1.00, sigma=0.22, description="Materiały specjalistyczne"),
        RiskFactor("robocizna",     mu=1.00, sigma=0.18, description="Specjalistyczna siła robocza"),
        RiskFactor("geotechnika",   mu=1.00, sigma=0.30, description="Ryzyko geotechniczne"),
        RiskFactor("regulacje",     mu=1.00, sigma=0.20, description="Zezwolenia, RDOŚ, Wody Polskie"),
        RiskFactor("czas",          mu=1.00, sigma=0.20, description="Ryzyko opóźnień"),
    ]
)

ALL_PROFILES: Dict[str, SectorProfile] = {
    p.key: p for p in [EARTHWORKS, ROADS, CUBATURE, UTILITIES, SPECIALISED]
}

GENERIC_PROFILE = SectorProfile(
    key="generic",
    label_pl="Ogólne roboty budowlane",
    cpv_prefixes=["45"],
    base_margin_mu=0.09, base_margin_sigma=0.05,
    factors=[
        RiskFactor("materialy",  mu=1.00, sigma=0.20, description="Materiały"),
        RiskFactor("robocizna",  mu=1.00, sigma=0.16, description="Robocizna"),
        RiskFactor("podwykon",   mu=1.00, sigma=0.22, description="Podwykonawcy"),
        RiskFactor("czas",       mu=1.00, sigma=0.15, description="Opóźnienia"),
        RiskFactor("projekt",    mu=1.00, sigma=0.18, description="Dokumentacja"),
        RiskFactor("ryzyka_ogol",mu=1.00, sigma=0.14, description="Inne ryzyka"),
    ]
)


def detect_sector(cpv_codes: list[str]) -> SectorProfile:
    """Wykryj profil na podstawie kodów CPV przetargu."""
    if not cpv_codes:
        return GENERIC_PROFILE
    for code in cpv_codes:
        code_clean = code.replace("-", "").replace(" ", "")
        for profile in ALL_PROFILES.values():
            for prefix in profile.cpv_prefixes:
                if code_clean.startswith(prefix):
                    return profile
    return GENERIC_PROFILE
