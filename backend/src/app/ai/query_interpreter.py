"""AI Query Interpreter - Converts natural language to structured search criteria."""

import json
import re
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.logging_config import get_logger
from app.settings import settings

logger = get_logger(__name__)


@dataclass
class InterpretedQuery:
    """Structured search criteria from natural language."""

    # Core search
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # Location
    country: str = "IT"
    countries: list[str] = field(default_factory=list)  # All countries for multi-country search
    regions: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)

    # Filters
    keywords_include: list[str] = field(default_factory=list)
    keywords_exclude: list[str] = field(default_factory=list)

    # Inferred intent
    business_type: str | None = None  # B2B, B2C, etc.
    company_size: str | None = None  # small, medium, large, enterprise
    industry: str | None = None

    # Advanced filters
    technologies: list[str] = field(default_factory=list)  # SAP, Salesforce, etc.
    employee_count_min: int | None = None
    employee_count_max: int | None = None
    revenue_min: int | None = None  # In EUR
    revenue_max: int | None = None
    year_founded_min: int | None = None
    year_founded_max: int | None = None

    # Confidence
    confidence: float = 0.0
    suggestions: list[str] = field(default_factory=list)

    # Original
    original_query: str = ""

    def to_search_query(self) -> str:
        """Convert to search query string."""
        parts = []
        if self.categories:
            parts.extend(self.categories)
        if self.keywords:
            parts.extend(self.keywords)
        return " ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "categories": self.categories,
            "keywords": self.keywords,
            "country": self.country,
            "countries": self.countries,  # All countries for multi-country search
            "regions": self.regions,
            "cities": self.cities,
            "keywords_include": self.keywords_include,
            "keywords_exclude": self.keywords_exclude,
            "business_type": self.business_type,
            "company_size": self.company_size,
            "industry": self.industry,
            "technologies": self.technologies,
            "employee_count_min": self.employee_count_min,
            "employee_count_max": self.employee_count_max,
            "revenue_min": self.revenue_min,
            "revenue_max": self.revenue_max,
            "year_founded_min": self.year_founded_min,
            "year_founded_max": self.year_founded_max,
            "confidence": self.confidence,
            "suggestions": self.suggestions,
            "original_query": self.original_query,
            "search_query": self.to_search_query(),
        }


# European country mappings
EUROPEAN_COUNTRIES = {
    # German
    "deutschland": "DE",
    "germany": "DE",
    "germania": "DE",
    "tedesco": "DE",
    "tedeschi": "DE",
    "de": "DE",  # Country code in query
    # Austria
    "österreich": "AT",
    "oesterreich": "AT",  # Without umlaut
    "austria": "AT",
    "austriaco": "AT",
    "at": "AT",  # Country code in query
    # Switzerland
    "schweiz": "CH",
    "switzerland": "CH",
    "svizzera": "CH",
    "suisse": "CH",
    "svizzero": "CH",
    "ch": "CH",  # Country code in query
    # France
    "france": "FR",
    "francia": "FR",
    "francese": "FR",
    "frankreich": "FR",
    "fr": "FR",  # Country code in query
    # Italy
    "italia": "IT",
    "italy": "IT",
    "italiano": "IT",
    "italien": "IT",
    "it": "IT",  # Country code in query
    # Spain
    "españa": "ES",
    "spanien": "ES",
    "spain": "ES",
    "spagna": "ES",
    "spagnolo": "ES",
    "es": "ES",  # Country code in query
    # Netherlands
    "niederlande": "NL",
    "netherlands": "NL",
    "olanda": "NL",
    "paesi bassi": "NL",
    # Belgium
    "belgien": "BE",
    "belgium": "BE",
    "belgio": "BE",
    # Poland
    "polen": "PL",
    "poland": "PL",
    "polonia": "PL",
    # Czech Republic
    "tschechien": "CZ",
    "czech": "CZ",
    "cechia": "CZ",
    "repubblica ceca": "CZ",
    # Portugal
    "portugal": "PT",
    "portogallo": "PT",
    # UK
    "uk": "GB",
    "united kingdom": "GB",
    "gran bretagna": "GB",
    "inghilterra": "GB",
    "regno unito": "GB",
}

# European regions/states by country
EUROPEAN_REGIONS = {
    # Italy
    "IT": {
        "lombardia": ["Milano", "Bergamo", "Brescia", "Como", "Cremona", "Lecco", "Lodi", "Mantova", "Monza", "Pavia", "Sondrio", "Varese"],
        "piemonte": ["Torino", "Alessandria", "Asti", "Biella", "Cuneo", "Novara", "Verbania", "Vercelli"],
        "veneto": ["Venezia", "Verona", "Padova", "Vicenza", "Treviso", "Rovigo", "Belluno"],
        "emilia-romagna": ["Bologna", "Modena", "Parma", "Reggio Emilia", "Ferrara", "Forlì-Cesena", "Piacenza", "Ravenna", "Rimini"],
        "toscana": ["Firenze", "Pisa", "Siena", "Livorno", "Arezzo", "Lucca", "Massa-Carrara", "Pistoia", "Prato", "Grosseto"],
        "lazio": ["Roma", "Latina", "Frosinone", "Rieti", "Viterbo"],
        "campania": ["Napoli", "Salerno", "Caserta", "Avellino", "Benevento"],
        "sicilia": ["Palermo", "Catania", "Messina", "Siracusa", "Trapani", "Agrigento", "Caltanissetta", "Enna", "Ragusa"],
        "puglia": ["Bari", "Lecce", "Taranto", "Foggia", "Brindisi", "Barletta-Andria-Trani"],
        "calabria": ["Reggio Calabria", "Catanzaro", "Cosenza", "Crotone", "Vibo Valentia"],
        "sardegna": ["Cagliari", "Sassari", "Nuoro", "Oristano", "Sud Sardegna"],
        "liguria": ["Genova", "La Spezia", "Savona", "Imperia"],
        "marche": ["Ancona", "Pesaro", "Macerata", "Fermo", "Ascoli Piceno"],
        "abruzzo": ["L'Aquila", "Teramo", "Pescara", "Chieti"],
        "friuli-venezia giulia": ["Trieste", "Udine", "Pordenone", "Gorizia"],
        "trentino-alto adige": ["Trento", "Bolzano"],
        "umbria": ["Perugia", "Terni"],
        "basilicata": ["Potenza", "Matera"],
        "molise": ["Campobasso", "Isernia"],
        "valle d'aosta": ["Aosta"],
    },
    # Germany
    "DE": {
        "bayern": ["München", "Nürnberg", "Augsburg", "Regensburg", "Würzburg", "Ingolstadt"],
        "baden-württemberg": ["Stuttgart", "Mannheim", "Karlsruhe", "Freiburg", "Heidelberg", "Ulm"],
        "nordrhein-westfalen": ["Köln", "Düsseldorf", "Dortmund", "Essen", "Duisburg", "Bochum", "Wuppertal", "Bonn"],
        "hessen": ["Frankfurt", "Wiesbaden", "Kassel", "Darmstadt", "Offenbach"],
        "niedersachsen": ["Hannover", "Braunschweig", "Oldenburg", "Osnabrück", "Wolfsburg", "Göttingen"],
        "sachsen": ["Dresden", "Leipzig", "Chemnitz", "Zwickau"],
        "berlin": ["Berlin"],
        "hamburg": ["Hamburg"],
        "rheinland-pfalz": ["Mainz", "Ludwigshafen", "Koblenz", "Trier", "Kaiserslautern"],
        "schleswig-holstein": ["Kiel", "Lübeck", "Flensburg"],
        "brandenburg": ["Potsdam", "Cottbus", "Frankfurt (Oder)"],
        "thüringen": ["Erfurt", "Jena", "Gera", "Weimar"],
        "sachsen-anhalt": ["Magdeburg", "Halle", "Dessau"],
        "mecklenburg-vorpommern": ["Rostock", "Schwerin", "Stralsund"],
        "saarland": ["Saarbrücken"],
        "bremen": ["Bremen", "Bremerhaven"],
    },
    # Austria
    "AT": {
        "wien": ["Wien"],
        "niederösterreich": ["St. Pölten", "Wiener Neustadt", "Krems"],
        "oberösterreich": ["Linz", "Wels", "Steyr"],
        "steiermark": ["Graz", "Leoben", "Kapfenberg"],
        "tirol": ["Innsbruck", "Kufstein", "Schwaz"],
        "kärnten": ["Klagenfurt", "Villach", "Wolfsberg"],
        "salzburg": ["Salzburg", "Hallein"],
        "vorarlberg": ["Bregenz", "Dornbirn", "Feldkirch"],
        "burgenland": ["Eisenstadt", "Oberwart"],
    },
    # Switzerland
    "CH": {
        "zürich": ["Zürich", "Winterthur"],
        "bern": ["Bern", "Biel", "Thun"],
        "genf": ["Genf", "Genève"],
        "basel": ["Basel"],
        "lausanne": ["Lausanne"],
        "luzern": ["Luzern"],
        "st. gallen": ["St. Gallen"],
        "tessin": ["Lugano", "Bellinzona", "Locarno"],
    },
    # France
    "FR": {
        "île-de-france": ["Paris", "Versailles", "Boulogne-Billancourt"],
        "provence-alpes-côte d'azur": ["Marseille", "Nice", "Toulon", "Cannes"],
        "auvergne-rhône-alpes": ["Lyon", "Grenoble", "Saint-Étienne"],
        "nouvelle-aquitaine": ["Bordeaux", "Limoges", "Poitiers"],
        "occitanie": ["Toulouse", "Montpellier", "Nîmes"],
        "hauts-de-france": ["Lille", "Amiens", "Roubaix"],
        "grand est": ["Strasbourg", "Reims", "Metz", "Nancy"],
        "pays de la loire": ["Nantes", "Angers", "Le Mans"],
        "bretagne": ["Rennes", "Brest", "Lorient"],
        "normandie": ["Rouen", "Le Havre", "Caen"],
    },
}

# Backward compatibility - Italian regions
ITALIAN_REGIONS = EUROPEAN_REGIONS.get("IT", {})

# Category mappings (multilingual -> EN)
CATEGORY_MAPPINGS = {
    # Healthcare - Italian
    "dentista": ["dentist", "dental clinic", "zahnarzt"],
    "dentisti": ["dentist", "dental clinic", "zahnarzt"],
    "medico": ["doctor", "medical practice", "arzt"],
    "medici": ["doctor", "medical practice", "arzt"],
    "fisioterapista": ["physiotherapist", "physical therapy"],
    "veterinario": ["veterinarian", "vet clinic", "tierarzt"],
    "farmacia": ["pharmacy", "apotheke"],
    "ottico": ["optician", "optiker"],
    "psicologo": ["psychologist", "psychologe"],

    # Healthcare - German
    "zahnarzt": ["dentist", "dental clinic", "zahnarztpraxis"],
    "zahnärzte": ["dentist", "dental clinic", "zahnarztpraxis"],
    "zahnarztpraxis": ["dentist", "dental clinic"],
    "arzt": ["doctor", "medical practice", "arztpraxis"],
    "ärzte": ["doctor", "medical practice", "arztpraxis"],
    "tierarzt": ["veterinarian", "vet clinic", "tierarztpraxis"],
    "apotheke": ["pharmacy", "apotheken"],
    "physiotherapeut": ["physiotherapist", "physical therapy"],
    "psychologe": ["psychologist", "psychotherapeut"],

    # Healthcare - French
    "dentiste": ["dentist", "dental clinic", "cabinet dentaire"],
    "médecin": ["doctor", "medical practice", "cabinet médical"],
    "pharmacie": ["pharmacy"],
    "vétérinaire": ["veterinarian", "vet clinic"],

    # Food & Hospitality - Italian
    "ristorante": ["restaurant"],
    "ristoranti": ["restaurant"],
    "pizzeria": ["pizzeria", "pizza restaurant"],
    "bar": ["bar", "cafe"],
    "hotel": ["hotel"],
    "b&b": ["bed and breakfast", "B&B"],
    "pasticceria": ["pastry shop", "bakery"],
    "gelateria": ["ice cream shop"],

    # Food & Hospitality - German
    "restaurant": ["restaurant"],
    "restaurants": ["restaurant"],
    "bäckerei": ["bakery", "bäcker"],
    "konditorei": ["pastry shop", "confectionery"],
    "café": ["cafe", "coffee shop"],
    "kaffee": ["cafe", "coffee shop"],
    "metzgerei": ["butcher", "metzger"],
    "gasthaus": ["restaurant", "inn"],
    "gasthof": ["restaurant", "inn"],

    # Services - Italian
    "idraulico": ["plumber"],
    "idraulici": ["plumber"],
    "elettricista": ["electrician"],
    "elettricisti": ["electrician"],
    "meccanico": ["mechanic", "auto repair"],
    "avvocato": ["lawyer", "law firm"],
    "avvocati": ["lawyer", "law firm"],
    "commercialista": ["accountant", "accounting firm"],
    "notaio": ["notary"],
    "architetto": ["architect"],
    "ingegnere": ["engineer"],

    # Services - German
    "klempner": ["plumber", "installateur"],
    "installateur": ["plumber", "installer"],
    "elektriker": ["electrician"],
    "mechaniker": ["mechanic", "auto repair"],
    "autowerkstatt": ["auto repair", "car mechanic"],
    "rechtsanwalt": ["lawyer", "law firm", "anwalt"],
    "anwalt": ["lawyer", "law firm"],
    "anwälte": ["lawyer", "law firm"],
    "steuerberater": ["tax advisor", "accountant"],
    "notar": ["notary"],
    "architekt": ["architect"],
    "ingenieur": ["engineer"],
    "handwerker": ["craftsman", "tradesman"],

    # Retail - Italian
    "negozio": ["shop", "store"],
    "abbigliamento": ["clothing store", "fashion"],
    "calzature": ["shoe store", "footwear"],
    "gioielleria": ["jewelry store"],
    "ferramenta": ["hardware store"],
    "libreria": ["bookstore"],

    # Retail - German
    "geschäft": ["shop", "store"],
    "laden": ["shop", "store"],
    "bekleidung": ["clothing store", "fashion"],
    "schuhgeschäft": ["shoe store"],
    "juwelier": ["jewelry store", "jeweler"],
    "baumarkt": ["hardware store", "DIY store"],
    "buchhandlung": ["bookstore"],

    # Beauty & Wellness - Italian
    "parrucchiere": ["hairdresser", "hair salon"],
    "estetista": ["beautician", "beauty salon"],
    "palestra": ["gym", "fitness center"],
    "spa": ["spa", "wellness center"],

    # Beauty & Wellness - German
    "friseur": ["hairdresser", "hair salon"],
    "frisör": ["hairdresser", "hair salon"],
    "kosmetik": ["beautician", "beauty salon", "kosmetikstudio"],
    "fitnessstudio": ["gym", "fitness center"],
    "wellness": ["spa", "wellness center"],

    # Tech & Business - multilingual
    "agenzia web": ["web agency", "digital agency"],
    "webagentur": ["web agency", "digital agency"],
    "software": ["software company", "IT company"],
    "marketing": ["marketing agency"],
    "consulenza": ["consulting"],
    "beratung": ["consulting", "consultant"],
    "unternehmensberatung": ["business consulting", "management consulting"],
}

# Exclusion keywords
EXCLUSION_PATTERNS = {
    "no corsi": ["corso", "formazione", "scuola", "academy", "training"],
    "no formazione": ["corso", "formazione", "scuola", "academy", "training"],
    "senza corsi": ["corso", "formazione", "scuola", "academy", "training"],
    "no franchising": ["franchising", "franchise"],
    "no online": ["online", "e-commerce", "ecommerce", "web"],
    "solo fisici": ["online", "e-commerce", "ecommerce", "virtuale"],
}

# Technology keywords for filtering
TECHNOLOGY_KEYWORDS = {
    # ERP Systems
    "sap": "SAP",
    "oracle": "Oracle",
    "microsoft dynamics": "Microsoft Dynamics",
    "dynamics 365": "Microsoft Dynamics 365",
    "netsuite": "NetSuite",
    "sage": "Sage",
    "odoo": "Odoo",
    # CRM Systems
    "salesforce": "Salesforce",
    "hubspot": "HubSpot",
    "zoho": "Zoho CRM",
    "pipedrive": "Pipedrive",
    # E-commerce
    "shopify": "Shopify",
    "magento": "Magento",
    "woocommerce": "WooCommerce",
    "prestashop": "PrestaShop",
    # Cloud/Infrastructure
    "aws": "AWS",
    "amazon web services": "AWS",
    "azure": "Microsoft Azure",
    "google cloud": "Google Cloud",
    "gcp": "Google Cloud",
    # Marketing/Analytics
    "google analytics": "Google Analytics",
    "mailchimp": "Mailchimp",
    "marketo": "Marketo",
    # Development
    "wordpress": "WordPress",
    "react": "React",
    "angular": "Angular",
    "node.js": "Node.js",
    "python": "Python",
    "java": "Java",
    ".net": ".NET",
    # Other
    "zendesk": "Zendesk",
    "jira": "Jira",
    "slack": "Slack",
    "teams": "Microsoft Teams",
}

# Company size keywords
COMPANY_SIZE_KEYWORDS = {
    # Small (1-50 employees)
    "kleine": "small",
    "piccole": "small",
    "small": "small",
    "petite": "small",
    "startup": "small",
    "startups": "small",
    "pmi": "small",  # Piccole e Medie Imprese
    "kmu": "small",  # Kleine und mittlere Unternehmen
    # Medium (51-250 employees)
    "mittelständisch": "medium",
    "mittelstand": "medium",
    "medie": "medium",
    "medium": "medium",
    "moyenne": "medium",
    "mittlere": "medium",
    # Large (251-1000 employees)
    "große": "large",
    "grandi": "large",
    "large": "large",
    "grande": "large",
    "groß": "large",
    # Enterprise (1000+ employees)
    "enterprise": "enterprise",
    "konzern": "enterprise",
    "multinazionali": "enterprise",
    "multinational": "enterprise",
    "dax": "enterprise",
    "fortune 500": "enterprise",
}


class QueryInterpreter:
    """Interprets natural language queries into structured search criteria.

    Supports both rule-based parsing and AI-powered interpretation.
    """

    def __init__(self, openai_api_key: str | None = None):
        """Initialize query interpreter.

        Args:
            openai_api_key: Optional OpenAI API key for AI interpretation
        """
        self.api_key = openai_api_key or getattr(settings, "openai_api_key", None)
        self.logger = get_logger(__name__)

    async def interpret(self, query: str, use_ai: bool = True) -> InterpretedQuery:
        """Interpret a natural language query.

        Args:
            query: Natural language search query
            use_ai: Whether to use AI for complex queries

        Returns:
            Structured search criteria
        """
        # First, try rule-based interpretation
        result = self._rule_based_interpret(query)

        # If confidence is low and AI is available, use AI
        if use_ai and self.api_key and result.confidence < 0.7:
            try:
                ai_result = await self._ai_interpret(query)
                if ai_result.confidence > result.confidence:
                    result = ai_result
            except Exception as e:
                self.logger.warning("ai_interpretation_failed", error=str(e))

        return result

    def _rule_based_interpret(self, query: str) -> InterpretedQuery:
        """Rule-based query interpretation.

        Args:
            query: Search query

        Returns:
            Interpreted query
        """
        query_lower = query.lower().strip()
        result = InterpretedQuery(original_query=query)

        confidence_factors = []

        # Extract countries (can be multiple for multi-country searches)
        detected_countries = []

        # Short country codes need word boundary matching (de, at, ch, etc.)
        short_codes = {"de", "at", "ch", "fr", "it", "es", "nl", "be", "pl", "cz", "pt", "gb"}

        for keyword, country_code in EUROPEAN_COUNTRIES.items():
            if keyword in short_codes:
                # Use word boundary matching for short codes to avoid false positives
                # (e.g., "de" in "dentist" or "it" in "italian")
                pattern = r'\b' + re.escape(keyword) + r'\b'
                if re.search(pattern, query_lower):
                    if country_code not in detected_countries:
                        detected_countries.append(country_code)
                        confidence_factors.append(0.9)
            elif keyword in query_lower:
                if country_code not in detected_countries:
                    detected_countries.append(country_code)
                    confidence_factors.append(0.9)

        # Check for "europa" / "europe" / "ganz europa" / "all europe"
        europe_keywords = ["europa", "europe", "ganz europa", "all europe", "tutta europa", "toute l'europe"]
        is_europe_wide = any(kw in query_lower for kw in europe_keywords)

        if is_europe_wide:
            # Add all major European countries
            all_european = ["DE", "AT", "CH", "IT", "FR", "ES", "NL", "BE", "PL"]
            for code in all_european:
                if code not in detected_countries:
                    detected_countries.append(code)
            confidence_factors.append(0.95)

        if detected_countries:
            # Use first one as primary but store ALL in countries list
            result.country = detected_countries[0]
            result.countries = detected_countries  # Store all countries
            # Also add to regions with prefix for backward compatibility
            for c in detected_countries[1:]:
                result.regions.append(f"country:{c}")
        else:
            result.country = "IT"  # Default to Italy
            result.countries = ["IT"]
            confidence_factors.append(0.5)

        # Extract regions and cities from all European countries
        for country_code, regions in EUROPEAN_REGIONS.items():
            for region, cities in regions.items():
                if region in query_lower:
                    result.regions.append(region.title())
                    # If we found a region, set the country if not already set
                    if not detected_countries:
                        result.country = country_code
                    confidence_factors.append(0.9)
                for city in cities:
                    if city.lower() in query_lower:
                        result.cities.append(city)
                        # If we found a city, set the country if not already set
                        if not detected_countries:
                            result.country = country_code
                        confidence_factors.append(0.9)

        # Extract categories (whole word matching)
        for term, en_terms in CATEGORY_MAPPINGS.items():
            # Use word boundary matching to avoid partial matches like "ärzte" in "zahnärzte"
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                result.categories.extend(en_terms[:2])  # Primary terms
                result.keywords.append(term)
                confidence_factors.append(0.9)

        # Extract exclusions
        for pattern, exclusions in EXCLUSION_PATTERNS.items():
            if pattern in query_lower:
                result.keywords_exclude.extend(exclusions)
                confidence_factors.append(0.8)

        # Extract technologies
        for keyword, tech_name in TECHNOLOGY_KEYWORDS.items():
            if keyword in query_lower:
                if tech_name not in result.technologies:
                    result.technologies.append(tech_name)
                confidence_factors.append(0.9)

        # Extract company size
        for keyword, size in COMPANY_SIZE_KEYWORDS.items():
            if keyword in query_lower:
                result.company_size = size
                confidence_factors.append(0.85)
                break  # Only take the first match

        # Extract employee count patterns like "50+ mitarbeiter", "über 100 angestellte"
        employee_patterns = [
            r'(\d+)\+?\s*(?:mitarbeiter|angestellte|employees|dipendenti|employés)',
            r'(?:über|more than|più di|plus de)\s*(\d+)\s*(?:mitarbeiter|angestellte|employees|dipendenti)',
            r'(\d+)\s*(?:bis|to|a|-)\s*(\d+)\s*(?:mitarbeiter|angestellte|employees|dipendenti)',
        ]
        for pattern in employee_patterns:
            match = re.search(pattern, query_lower)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    result.employee_count_min = int(groups[0])
                elif len(groups) == 2:
                    result.employee_count_min = int(groups[0])
                    result.employee_count_max = int(groups[1])
                confidence_factors.append(0.9)
                break

        # Extract other keywords
        # Remove already identified terms and extract remaining meaningful words
        remaining = query_lower
        for region in result.regions:
            remaining = remaining.replace(region.lower(), "")
        for city in result.cities:
            remaining = remaining.replace(city.lower(), "")
        for keyword in result.keywords:
            remaining = remaining.replace(keyword, "")

        # Find additional keywords
        words = re.findall(r'\b[a-zàèéìòù]{3,}\b', remaining)
        stop_words = {"cerco", "cerca", "trovare", "trova", "voglio", "vorrei",
                      "nella", "nella", "nel", "della", "del", "che", "con",
                      "per", "sono", "hanno", "hanno", "solo", "senza"}
        additional_keywords = [w for w in words if w not in stop_words]
        result.keywords.extend(additional_keywords[:3])  # Max 3 additional

        # Calculate confidence
        if confidence_factors:
            result.confidence = sum(confidence_factors) / len(confidence_factors)
        else:
            result.confidence = 0.3  # Low confidence if nothing matched

        # Add suggestions if confidence is low
        if result.confidence < 0.6:
            result.suggestions = [
                "Prova a specificare la categoria (es. 'dentisti', 'ristoranti')",
                "Aggiungi una città o regione (es. 'a Milano', 'in Lombardia')",
                "Usa esclusioni se necessario (es. 'no corsi', 'no franchising')",
            ]

        # Ensure we have at least one search term
        if not result.categories and not result.keywords:
            # Use the entire query as a keyword
            result.keywords = [query_lower]
            result.confidence = 0.3

        return result

    async def _ai_interpret(self, query: str) -> InterpretedQuery:
        """AI-powered query interpretation using OpenAI GPT.

        Args:
            query: Search query

        Returns:
            Interpreted query
        """
        system_prompt = """You are a B2B lead generation assistant that interprets natural language search queries.

Convert the user's search query into structured criteria for finding businesses.

Respond ONLY with valid JSON in this exact format:
{
    "categories": ["primary category in English", "secondary category"],
    "keywords": ["keyword1", "keyword2"],
    "country": "IT",
    "countries": ["IT", "DE", "FR"],
    "regions": ["Region Name"],
    "cities": ["City Name"],
    "keywords_include": ["must have keywords"],
    "keywords_exclude": ["exclude keywords"],
    "business_type": "B2B or B2C or null",
    "company_size": "small/medium/large/enterprise or null",
    "industry": "industry name or null",
    "technologies": ["SAP", "Salesforce"],
    "employee_count_min": null,
    "employee_count_max": null,
    "confidence": 0.0-1.0
}

Important:
- categories should be in English for API compatibility
- country is the primary country, countries is a list of ALL countries mentioned
- If user mentions "Europa" or "Europe" or multiple countries, include all in countries array
- European country codes: IT, DE, AT, CH, FR, ES, NL, BE, PL, CZ, PT, GB
- regions and cities should be properly capitalized
- keywords_exclude should include terms the user wants to avoid
- technologies: extract any mentioned software/platforms (SAP, Salesforce, Oracle, AWS, etc.)
- company_size: small (1-50), medium (51-250), large (251-1000), enterprise (1000+)
- employee_count_min/max: extract if user specifies employee ranges
- confidence should reflect how well you understood the query"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "max_tokens": 500,
                        "temperature": 0,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": f"Interpret this search query: {query}"}
                        ],
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                # Extract text content from OpenAI response
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")

                # Parse JSON
                parsed = json.loads(content)

                # Extract countries - ensure it's a list
                countries = parsed.get("countries", [])
                country = parsed.get("country", "IT")
                if not countries:
                    countries = [country]
                elif country not in countries:
                    countries.insert(0, country)

                return InterpretedQuery(
                    categories=parsed.get("categories", []),
                    keywords=parsed.get("keywords", []),
                    country=country,
                    countries=countries,
                    regions=parsed.get("regions", []),
                    cities=parsed.get("cities", []),
                    keywords_include=parsed.get("keywords_include", []),
                    keywords_exclude=parsed.get("keywords_exclude", []),
                    business_type=parsed.get("business_type"),
                    company_size=parsed.get("company_size"),
                    industry=parsed.get("industry"),
                    technologies=parsed.get("technologies", []),
                    employee_count_min=parsed.get("employee_count_min"),
                    employee_count_max=parsed.get("employee_count_max"),
                    confidence=parsed.get("confidence", 0.8),
                    original_query=query,
                )

        except Exception as e:
            self.logger.error("ai_interpret_error", error=str(e))
            raise

    def get_category_suggestions(self, partial: str) -> list[str]:
        """Get category suggestions for autocomplete.

        Args:
            partial: Partial category input

        Returns:
            List of matching categories
        """
        partial_lower = partial.lower()
        suggestions = []

        for it_term, en_terms in CATEGORY_MAPPINGS.items():
            if partial_lower in it_term or it_term.startswith(partial_lower):
                suggestions.append(it_term)

        return suggestions[:10]

    def get_city_suggestions(self, partial: str, region: str | None = None) -> list[str]:
        """Get city suggestions for autocomplete.

        Args:
            partial: Partial city input
            region: Optional region to filter by

        Returns:
            List of matching cities
        """
        partial_lower = partial.lower()
        suggestions = []

        if region:
            region_lower = region.lower()
            if region_lower in ITALIAN_REGIONS:
                cities = ITALIAN_REGIONS[region_lower]
                suggestions = [c for c in cities if partial_lower in c.lower()]
        else:
            for cities in ITALIAN_REGIONS.values():
                for city in cities:
                    if partial_lower in city.lower():
                        suggestions.append(city)

        return suggestions[:10]
