# -*- coding: utf-8 -*-
"""Mapeo canonico de las 48 selecciones del Mundial 2026.

Nombre canonico = el que usa el dataset historico martj42 (results.csv).
"""

GROUPS = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia and Herzegovina"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curaçao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Tunisia", "Sweden"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Norway", "Iraq"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "Uzbekistan", "Colombia", "DR Congo"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

TEAMS = {t for g in GROUPS.values() for t in g}

TEAM_GROUP = {t: g for g, ts in GROUPS.items() for t in ts}

# Nombre para mostrar en castellano
ES = {
    "Mexico": "México", "South Africa": "Sudáfrica", "South Korea": "Corea del Sur",
    "Czech Republic": "Chequia", "Canada": "Canadá", "Switzerland": "Suiza",
    "Qatar": "Catar", "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Brazil": "Brasil", "Morocco": "Marruecos", "Haiti": "Haití", "Scotland": "Escocia",
    "United States": "Estados Unidos", "Paraguay": "Paraguay", "Australia": "Australia",
    "Turkey": "Turquía", "Germany": "Alemania", "Curaçao": "Curazao",
    "Ivory Coast": "Costa de Marfil", "Ecuador": "Ecuador", "Netherlands": "Países Bajos",
    "Japan": "Japón", "Tunisia": "Túnez", "Sweden": "Suecia", "Belgium": "Bélgica",
    "Egypt": "Egipto", "Iran": "Irán", "New Zealand": "Nueva Zelanda",
    "Spain": "España", "Cape Verde": "Cabo Verde", "Saudi Arabia": "Arabia Saudita",
    "Uruguay": "Uruguay", "France": "Francia", "Senegal": "Senegal", "Norway": "Noruega",
    "Iraq": "Irak", "Argentina": "Argentina", "Algeria": "Argelia", "Austria": "Austria",
    "Jordan": "Jordania", "Portugal": "Portugal", "Uzbekistan": "Uzbekistán",
    "Colombia": "Colombia", "DR Congo": "RD Congo", "England": "Inglaterra",
    "Croatia": "Croacia", "Ghana": "Ghana", "Panama": "Panamá",
}

# Alias que aparecen en Wikipedia / FIFA / otros datasets -> canonico
ALIASES = {
    "Korea Republic": "South Korea", "Korea, South": "South Korea", "Republic of Korea": "South Korea",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey", "Turkiye": "Turkey",
    "Cabo Verde": "Cape Verde", "Cape Verde Islands": "Cape Verde",
    "Côte d'Ivoire": "Ivory Coast", "Cote d'Ivoire": "Ivory Coast", "Cote dIvoire": "Ivory Coast",
    "USA": "United States", "United States of America": "United States",
    "Congo DR": "DR Congo", "Congo, Democratic Republic of the": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo", "DR Congo": "DR Congo", "Congo Kinshasa": "DR Congo",
    "Curacao": "Curaçao",
    "IR Iran": "Iran", "Iran, Islamic Republic of": "Iran",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina", "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Saudi-Arabia": "Saudi Arabia",
    "Netherlands ": "Netherlands", "Holland": "Netherlands",
}


def canon(name: str) -> str:
    """Normaliza un nombre de seleccion al canonico. Devuelve el nombre limpio
    aunque no sea una de las 48 (para el historico hace falta cubrir a todos)."""
    if name is None:
        return ""
    n = name.replace("\xa0", " ").replace("​", "").strip()
    return ALIASES.get(n, n)


# Ciudades sede -> pais (para la ventaja de localia de los 3 anfitriones)
CITY_COUNTRY = {
    "mexico city": "Mexico", "zapopan": "Mexico", "guadalajara": "Mexico",
    "monterrey": "Mexico", "guadalupe": "Mexico",
    "toronto": "Canada", "vancouver": "Canada",
}


def venue_country(venue_text: str) -> str:
    v = (venue_text or "").lower()
    for city, country in CITY_COUNTRY.items():
        if city in v:
            return country
    return "United States"
