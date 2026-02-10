# Scripe Platform - Vollstaendige Dokumentation

> **Stand:** 5. Februar 2026
> **Version:** 1.0.0
> **Repository:** `https://github.com/fabionr15-dot/scripe-standalone.git`
> **Production:** `https://scripe.fabioprivato.org`
> **API:** `https://api.scripe.fabioprivato.org`

---

## Inhaltsverzeichnis

1. [Projekt-Uebersicht](#1-projekt-uebersicht)
2. [Was bereits implementiert ist](#2-was-bereits-implementiert-ist)
3. [Was noch offen ist](#3-was-noch-offen-ist)
4. [Architektur-Uebersicht](#4-architektur-uebersicht)
5. [Verzeichnisstruktur](#5-verzeichnisstruktur)
6. [Backend (FastAPI)](#6-backend-fastapi)
7. [Frontend (React + Vite)](#7-frontend-react--vite)
8. [Datenbank (PostgreSQL)](#8-datenbank-postgresql)
9. [Authentifizierung & Autorisierung](#9-authentifizierung--autorisierung)
10. [Credit-System & Preise](#10-credit-system--preise)
11. [Zahlungssystem (Stripe)](#11-zahlungssystem-stripe)
12. [Such-System & Data Pipeline](#12-such-system--data-pipeline)
13. [Internationalisierung (i18n)](#13-internationalisierung-i18n)
14. [Infrastruktur & Deployment](#14-infrastruktur--deployment)
15. [Sicherheit (Cyber Security)](#15-sicherheit-cyber-security)
16. [API-Referenz](#16-api-referenz)
17. [Umgebungsvariablen](#17-umgebungsvariablen)
18. [Deployment-Anleitung](#18-deployment-anleitung)
19. [Abgeschlossene Arbeiten (Changelog)](#19-abgeschlossene-arbeiten-changelog)

---

## 1. Projekt-Uebersicht

**Scripe** ist eine B2B-Leadgenerierungsplattform fuer den europaeischen Markt. Nutzer suchen nach Unternehmen (z.B. "Friseure in Wien"), die Plattform aggregiert Daten aus mehreren Quellen, validiert Telefonnummern und E-Mails, und liefert qualitaetsgesicherte Kontaktdaten.

### Tech-Stack

| Schicht | Technologie |
|---------|------------|
| **Frontend** | React 18, TypeScript, Vite 5, Tailwind CSS 4, shadcn/ui (Radix), React Router 7 |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic 2 |
| **Datenbank** | PostgreSQL 15 (Alpine) |
| **Auth** | JWT (HS256, python-jose), bcrypt Passwort-Hashing |
| **Zahlungen** | Stripe Checkout + Webhooks |
| **i18n** | react-i18next (EN, DE, IT, FR) |
| **Deployment** | Docker Compose, Nginx Reverse Proxy, Hetzner VPS |
| **CDN/SSL** | Cloudflare (Proxy + SSL Termination) |
| **Scraping** | httpx, selectolax, BeautifulSoup4 |
| **AI** | OpenAI API (Suchinterpretation) |

---

## 2. Was bereits implementiert ist

### Kernfunktionen
- [x] Vollstaendige Benutzerregistrierung & Login (E-Mail/Passwort)
- [x] JWT-basierte Authentifizierung (2h Token-Ablauf)
- [x] Credit-System mit 4 Paketen (Starter, Growth, Scale, Enterprise)
- [x] Stripe Checkout Integration (Zahlung + Webhook)
- [x] AI-gestuetzte Suchinterpretation (natuerliche Sprache)
- [x] Manuelle Suche mit Filtern (Kategorie, Stadt, Region, Land)
- [x] Multi-Source Scraping (Google Places, Bing Maps, Google SERP, Pagine Gialle)
- [x] Website-Enrichment (Kontaktseiten crawlen)
- [x] Echtzeit-Fortschritt via Server-Sent Events (SSE)
- [x] 3-stufiges Qualitaetssystem (Basic 40%, Standard 60%, Premium 80%)
- [x] Telefon-, E-Mail- und Website-Validierung
- [x] Deduplizierung mit alternativen Telefonnummern
- [x] Export: CSV, Excel (formatiert mit Styles), PDF
- [x] Listen-Management (erstellen, Leads hinzufuegen/entfernen, exportieren)
- [x] Dashboard mit Statistiken
- [x] Preisseite mit Paketvergleich

### i18n (4 Sprachen)
- [x] Englisch (EN) - vollstaendig
- [x] Deutsch (DE) - vollstaendig
- [x] Italienisch (IT) - vollstaendig
- [x] Franzoesisch (FR) - vollstaendig
- [x] Spracherkennung ueber URL-Pfad (`/:lang/...`)
- [x] Hreflang SEO-Tags
- [x] Sprachumschalter in Header & Sidebar

### Rechtliche Seiten
- [x] Datenschutzerklaerung (Privacy Policy)
- [x] Nutzungsbedingungen (Terms of Service)
- [x] Cookie-Richtlinie (Cookie Policy)
- [x] DSGVO-konform (nur oeffentliche Geschaeftsdaten)

### Sicherheit (Cyber-Hardening)
- [x] JWT-Secret Startup-Validierung (kein Default in Produktion)
- [x] Zitadel Auth-Bypass geschlossen
- [x] IDOR-Fix in Listen (Company-Ownership-Check)
- [x] Atomare Credit-Deduktion (SELECT FOR UPDATE)
- [x] Stripe Webhook Idempotenz
- [x] Content-Security-Policy Header
- [x] Rate-Limiting auf kritische Endpoints
- [x] CORS nur explizite Origins (kein Wildcard)
- [x] DB-Port nicht extern exponiert
- [x] Passwort min. 10 Zeichen

### Infrastruktur
- [x] Docker Compose (Dev + Prod)
- [x] Nginx Reverse Proxy mit Security Headers
- [x] Cloudflare SSL + CDN
- [x] Hot-Reload in Development
- [x] Produktions-Deployment auf Hetzner VPS

---

## 3. Was noch offen ist

### Hoch (Sicherheit)
- [ ] **httpOnly Cookie Migration** - JWT aus localStorage in httpOnly Secure Cookies verschieben (XSS-Schutz)
- [ ] **Account-Lockout Persistenz** - Von In-Memory auf DB/Redis umstellen (ueberlebt Server-Neustart nicht)
- [ ] **SSE Authentifizierung** - EventSource sendet kein Auth-Token (kurzlebige Tokens oder WebSocket)

### Mittel (Features)
- [ ] **E-Mail-Versand** - Passwort-Reset und Verifikation brauchen SMTP (z.B. Resend, SendGrid)
- [ ] **Search-Timeout** - asyncio.wait_for fuer langlaufende Suchen
- [ ] **Credit-Refund bei Fehler** - Automatische Rueckbuchung bei fehlgeschlagener Suche
- [ ] **Forgot-Password Frontend-Seite** - Link existiert, Seite fehlt
- [ ] **User Settings/Profil Seite** - Backend existiert (`PATCH /auth/me`), Frontend fehlt
- [ ] **Listen-Detail-Seite** - `/lists/:id` verlinkt aber nicht implementiert

### Niedrig (Nice-to-have)
- [ ] **Dark Mode** - CSS-Infrastruktur vorhanden, nicht aktiviert
- [ ] **Sitemap.xml** - SEO-Verbesserung
- [ ] **CI/CD Pipeline** - GitHub Actions fuer automatisches Testing/Deployment
- [ ] **Refresh Token** - Separater langlebiger Token + kurzer Access Token
- [ ] **Advanced Search Filters** - Auf Searches-Seite (Datum, Status, etc.)
- [ ] **Webhook Notifications** - Echtzeit-Benachrichtigungen
- [ ] **SQL-Echo in Dev** - Sensible Daten in Logs moeglich

### Zahlungssystem (Stripe) - Offene Punkte
- [ ] **Stripe Publishable Key** - Im Frontend einbinden fuer clientseitige Stripe-Integration
- [ ] **Webhook Production Setup** - `STRIPE_WEBHOOK_SECRET` in .env auf Server setzen
- [ ] **Payment History Seite** - Frontend-Seite fuer Zahlungsverlauf
- [ ] **Rechnungsgenerierung** - PDF-Rechnungen nach Kauf
- [ ] **Subscription-Modell** - Monatliches Abo als Alternative zu Credits (optional)

---

## 4. Architektur-Uebersicht

```
                    +------------------+
                    |   Cloudflare     |
                    |   (SSL + CDN)    |
                    +--------+---------+
                             |
                    +--------v---------+
                    |   Nginx          |
                    |   (Reverse Proxy)|
                    |   Port 80        |
                    +--+----------+----+
                       |          |
          +------------+    +-----+--------+
          |                 |              |
+---------v---+    +--------v--+    +------v------+
|  Frontend   |    |  Backend  |    |  Backend    |
|  (React)    |    |  (FastAPI)|    |  /api/...   |
|  Port 80    |    |  Port 8010|    |  Port 8010  |
+-------------+    +-----+-----+    +------+------+
                         |                 |
                    +----v-----------------v----+
                    |      PostgreSQL 15         |
                    |      Port 5432 (intern)    |
                    +----------------------------+
```

### Anfrage-Routing (Nginx)

| Domain | Routing |
|--------|---------|
| `scripe.fabioprivato.org/*` | Frontend (React SPA) |
| `scripe.fabioprivato.org/api/*` | Backend (FastAPI) |
| `scripe.fabioprivato.org/health` | Backend Health Check |
| `api.scripe.fabioprivato.org/*` | Backend (direkt, alle Pfade) |

---

## 5. Verzeichnisstruktur

```
scripe-standalone/
|-- docker-compose.yml              # Development Setup
|-- docker-compose.prod.yml         # Production Setup
|-- SCRIPE_COMPLETE_DOCUMENTATION.md
|
|-- backend/
|   |-- pyproject.toml               # Python Dependencies & Config
|   |-- README.md
|   |-- Dockerfile
|   |-- allowlist_sources.yaml       # Erlaubte Datenquellen (DSGVO)
|   |-- src/
|       |-- app/
|       |   |-- __init__.py
|       |   |-- settings.py           # Konfiguration + JWT-Validierung
|       |   |-- logging_config.py     # Strukturiertes Logging (structlog)
|       |   |-- cli.py                # CLI-Befehle (Typer)
|       |   |
|       |   |-- api/
|       |   |   |-- main.py           # FastAPI App Factory + CORS + Rate Limiting
|       |   |   |-- routes.py         # Erweiterte Routen (Clients, Campaigns)
|       |   |   |-- rate_limit.py     # Limiter-Konfiguration (slowapi)
|       |   |   |-- v1/
|       |   |       |-- auth.py       # Auth-Endpoints (Register, Login, Credits)
|       |   |       |-- searches.py   # Such-Endpoints + SSE Streaming
|       |   |       |-- export.py     # CSV/Excel/PDF Export
|       |   |       |-- ai.py         # AI Query Interpretation
|       |   |       |-- sources.py    # Datenquellen-Management
|       |   |       |-- dashboard.py  # Dashboard-Statistiken
|       |   |       |-- lists.py      # Listen-Management
|       |   |       |-- webhooks.py   # Stripe Webhook Handler
|       |   |
|       |   |-- auth/
|       |   |   |-- models.py         # User, Subscription, Credit Models
|       |   |   |-- local.py          # JWT Auth Service (Erstellen, Validieren)
|       |   |   |-- middleware.py      # Auth Middleware (require_auth)
|       |   |   |-- credits.py        # Credit-Service (Kaufen, Ausgeben, Refund)
|       |   |
|       |   |-- storage/
|       |   |   |-- db.py             # Database Connection Manager
|       |   |   |-- models.py         # Core Models (Search, Company, Run, Source)
|       |   |   |-- models_v2.py      # Extended Models (Client, Campaign)
|       |   |   |-- repo.py           # Repository/DAO Layer
|       |   |   |-- export.py         # Export-Funktionalitaet
|       |   |
|       |   |-- sources/
|       |   |   |-- base.py           # BaseConnector Abstract Class
|       |   |   |-- manager.py        # Source Orchestration
|       |   |   |-- setup.py          # Source Initialisierung
|       |   |   |-- google_serp.py    # Google SERP Scraper
|       |   |   |-- bing_places.py    # Bing Maps API
|       |   |   |-- pagine_gialle.py  # Pagine Gialle (IT)
|       |   |   |-- places.py         # Google Places API
|       |   |   |-- official_site.py  # Website Crawler (Enrichment)
|       |   |
|       |   |-- quality/
|       |   |   |-- scorer.py         # Qualitaetsbewertung
|       |   |   |-- validators.py     # Telefon/E-Mail/Website Validierung
|       |   |   |-- enrichment.py     # Daten-Anreicherung
|       |   |   |-- tiers.py          # Basic/Standard/Premium Tiers
|       |   |
|       |   |-- extractors/
|       |   |   |-- phone.py          # Telefonnummer-Extraktion (phonenumbers)
|       |   |   |-- email.py          # E-Mail-Extraktion + MX-Check
|       |   |   |-- normalizers.py    # Daten-Normalisierung
|       |   |
|       |   |-- dedupe/
|       |   |   |-- deduper.py        # Deduplizierung (Website, Telefon, Name+Stadt)
|       |   |
|       |   |-- pipeline/
|       |   |   |-- runner.py         # Pipeline-Ausfuehrung
|       |   |
|       |   |-- payments/
|       |   |   |-- stripe_service.py # Stripe Checkout + Webhook-Verarbeitung
|       |   |
|       |   |-- ai/
|       |   |   |-- query_interpreter.py  # NLP Abfrage-Interpretation (OpenAI)
|       |   |
|       |   |-- infra/
|       |   |   |-- proxy_manager.py  # Proxy-Rotation fuer Scraping
|       |   |
|       |   |-- matcher/
|       |   |   |-- quality_scorer.py # Quality Matching
|       |   |   |-- scoring.py       # Scoring Utilities
|       |   |
|       |   |-- validators/
|       |       |-- validators.py     # Custom Validators
|       |
|       |-- scripe/                    # Standalone SDK Package
|           |-- core/http_client.py
|           |-- extractors/ (phone, website, address, normalizers)
|           |-- storage/ (models, exporter, repository)
|
|-- frontend/
|   |-- package.json                  # Dependencies
|   |-- vite.config.ts                # Vite Config (Proxy, Alias)
|   |-- tsconfig.json                 # TypeScript Config
|   |-- index.html                    # HTML Entry Point
|   |-- Dockerfile
|   |-- nginx.conf                    # Frontend Nginx Config
|   |-- .env.development              # VITE_API_URL= (leer = Proxy)
|   |-- .env.production               # VITE_API_URL= (leer = gleicher Server)
|   |
|   |-- public/
|   |   |-- locales/
|   |       |-- en/ (common, landing, auth, dashboard, search, pricing, legal).json
|   |       |-- de/ (common, landing, auth, dashboard, search, pricing, legal).json
|   |       |-- it/ (common, landing, auth, dashboard, search, pricing, legal).json
|   |       |-- fr/ (common, landing, auth, dashboard, search, pricing, legal).json
|   |
|   |-- src/
|       |-- main.tsx                   # Entry Point (Provider-Setup)
|       |-- App.tsx                    # Router-Konfiguration
|       |-- index.css                  # Globale Styles (Tailwind)
|       |
|       |-- context/
|       |   |-- AuthContext.tsx         # Auth State Management
|       |
|       |-- i18n/
|       |   |-- index.ts               # i18next Initialisierung
|       |   |-- HreflangTags.tsx        # SEO Hreflang Tags
|       |   |-- LanguageSwitcher.tsx    # Sprachumschalter
|       |   |-- LocalizedLink.tsx       # Sprachbewusste Links
|       |   |-- useLocalizedNavigate.ts # Navigation Hook
|       |
|       |-- lib/
|       |   |-- api.ts                 # Axios API Client (alle Endpunkte)
|       |   |-- utils.ts               # Utility (cn = clsx + tailwind-merge)
|       |
|       |-- components/
|       |   |-- ProtectedRoute.tsx     # Auth-Guard
|       |   |-- layout/
|       |       |-- PublicLayout.tsx    # Header + Footer (oeffentlich)
|       |       |-- DashboardLayout.tsx # Sidebar + Main (eingeloggt)
|       |
|       |-- pages/
|           |-- LandingPage.tsx        # Startseite (Hero, Features, Tiers, CTA)
|           |-- PricingPage.tsx        # Preise + Pakete + FAQ
|           |-- LoginPage.tsx          # Login-Formular
|           |-- RegisterPage.tsx       # Registrierung + Validierung
|           |-- DashboardPage.tsx      # Dashboard (Stats, Aktionen, Letzte Suchen)
|           |-- SearchesPage.tsx       # Alle Suchen (Liste)
|           |-- NewSearchPage.tsx      # Neue Suche (AI + Manuell)
|           |-- SearchResultsPage.tsx  # Suchergebnisse + Echtzeit-Fortschritt
|           |-- ListsPage.tsx          # Listen-Verwaltung
|           |-- PrivacyPage.tsx        # Datenschutz
|           |-- TermsPage.tsx          # Nutzungsbedingungen
|           |-- CookiePolicyPage.tsx   # Cookie-Richtlinie
|           |-- PaymentSuccessPage.tsx # Zahlung erfolgreich
|           |-- PaymentCancelPage.tsx  # Zahlung abgebrochen
|
|-- nginx/
    |-- nginx.prod.conf               # Nginx Production Config (2 Server-Bloecke)
```

---

## 6. Backend (FastAPI)

### 6.1 App Factory (`api/main.py`)

```python
# Erstellt FastAPI App mit:
# - CORS (explizite Origins, kein Wildcard)
# - Rate Limiting (slowapi, nur in Production aktiv)
# - API Docs nur in Development (/api/docs, /api/redoc)
# - Health Check Endpoint (/health)
# - Lifespan: DB-Tabellen erstellen + Sources initialisieren
```

### 6.2 Rate Limiting

| Endpoint | Limit |
|----------|-------|
| Global (default) | 200/Minute |
| `POST /auth/register` | 5/Minute |
| `POST /auth/login` | 10/Minute + Account Lockout |
| `POST /auth/forgot-password` | 3/Minute |
| `POST /auth/credits/purchase` | 10/Minute |
| `POST /searches` | 20/Minute |
| `POST /searches/{id}/export` | 10/Minute |

### 6.3 Account Lockout

- **Schwelle:** 5 fehlgeschlagene Versuche
- **Fenster:** 15 Minuten
- **Sperrzeit:** 15 Minuten
- **Tracking:** Nach E-Mail + IP-Adresse
- **Achtung:** Aktuell nur In-Memory (geht bei Neustart verloren)

### 6.4 Dependencies (pyproject.toml)

**Core:**
- `fastapi>=0.109.0`, `uvicorn[standard]>=0.27.0`
- `sqlalchemy>=2.0.25`, `psycopg2-binary>=2.9.9`
- `pydantic[email]>=2.6.0`, `pydantic-settings>=2.1.0`

**Auth & Security:**
- `passlib[bcrypt]>=1.7.4`, `bcrypt>=4.0,<5.0`
- `python-jose[cryptography]>=3.3.0`

**Scraping:**
- `httpx>=0.27.0`, `selectolax>=0.3.21`, `beautifulsoup4>=4.12.3`

**Validation:**
- `phonenumbers>=8.13.27`, `dnspython>=2.4.2`

**Export:**
- `openpyxl>=3.1.2` (Excel), `reportlab>=4.0.8` (PDF)

**Zahlungen:**
- `stripe>=7.0.0`

**Sonstiges:**
- `structlog>=24.1.0`, `slowapi>=0.1.9`, `tenacity>=8.2.3`

---

## 7. Frontend (React + Vite)

### 7.1 Routing (React Router v7)

Alle Routen haben das Praefix `/:lang` (en, de, it, fr).

| Route | Komponente | Typ | Beschreibung |
|-------|-----------|-----|-------------|
| `/` | LanguageRedirect | Redirect | Erkennt Sprache, leitet zu `/:lang` |
| `/:lang` | LandingPage | Public | Startseite mit Hero, Features, Tiers, CTA |
| `/:lang/login` | LoginPage | Public | Login-Formular |
| `/:lang/register` | RegisterPage | Public | Registrierung mit Passwort-Validierung |
| `/:lang/pricing` | PricingPage | Public | Credit-Pakete, Features, FAQ |
| `/:lang/privacy` | PrivacyPage | Public | Datenschutzerklaerung |
| `/:lang/terms` | TermsPage | Public | Nutzungsbedingungen |
| `/:lang/cookies` | CookiePolicyPage | Public | Cookie-Richtlinie |
| `/:lang/dashboard` | DashboardPage | Protected | Uebersicht, Stats, Schnellaktionen |
| `/:lang/searches` | SearchesPage | Protected | Alle Suchen (Tabelle) |
| `/:lang/searches/new` | NewSearchPage | Protected | Neue Suche (AI/Manuell) |
| `/:lang/searches/:id` | SearchResultsPage | Protected | Ergebnisse + Live-Fortschritt |
| `/:lang/lists` | ListsPage | Protected | Listen-Verwaltung |
| `/:lang/payment/success` | PaymentSuccessPage | Protected | Zahlung erfolgreich |
| `/:lang/payment/cancel` | PaymentCancelPage | Protected | Zahlung abgebrochen |

**Legacy-Routen** (ohne `:lang`) leiten automatisch mit Spracherkennung weiter.

### 7.2 Layouts

**PublicLayout** - Header (Logo, Nav, Sprache, Login/Register) + Footer + Outlet
**DashboardLayout** - Sidebar (Navigation, Credits, User) + Main Content + Outlet

### 7.3 Auth Context

```typescript
interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string, name?: string): Promise<void>;
  testLogin(): Promise<void>;  // Nur Development
  logout(): void;
  refreshUser(): Promise<void>;
}
```

- Token in `localStorage` als `scripe_token`
- Automatisch als `Authorization: Bearer {token}` gesendet
- 401-Response loescht Token und leitet zu Login weiter

### 7.4 API Client (`lib/api.ts`)

- **Basis-URL:** `{VITE_API_URL}/api/v1` (leer = Vite Proxy in Dev)
- **Header:** `Content-Type: application/json`, `X-Client-Type: public`
- **Interceptor:** Fuegt Token hinzu, 401 = Logout

### 7.5 Seiten im Detail

#### LandingPage
- Hero-Sektion mit CTA ("Start Free" + "View Pricing")
- 6 Feature-Karten (Smart Search, Multi-Source, Verified Data, Targeting, Fast, GDPR)
- 3 Qualitaetsstufen (Basic, Standard, Premium) mit Preisen
- Abschluss-CTA ("Create Free Account")

#### PricingPage
- 4 Credit-Pakete (Starter, Growth, Scale, Enterprise)
- Feature-Vergleich
- FAQ-Sektion (Accordion)
- "Jetzt kaufen"-Buttons (leiten zu Stripe Checkout)

#### NewSearchPage (Dual-Mode)
- **AI-Modus:** Natuerliche Sprache eingeben, KI interpretiert
- **Manueller Modus:** Kategorie, Stadt, Region auswaehlen
- Quality-Tier-Auswahl (Basic/Standard/Premium)
- Lead-Anzahl Slider (0-10.000)
- Kostenschaetzung vor Start
- Credit-Check (verhindert Start bei zu wenig Credits)

#### SearchResultsPage
- Echtzeit-Fortschritt via SSE (Fortschrittsbalken, aktuelle Quelle)
- Ergebnistabelle mit Qualitaets-Badge
- Qualitaetsfilter-Dropdown (Alle, 40%+, 60%+, 80%+)
- Export-Buttons (CSV, Excel)
- "Zur Liste hinzufuegen"-Funktion

### 7.6 Dependencies (package.json)

```json
{
  "react": "^18.3.1",
  "react-router-dom": "^7.9.6",
  "react-i18next": "^16.5.4",
  "i18next": "^25.8.4",
  "axios": "^1.7.9",
  "react-hook-form": "^7.66.1",
  "react-helmet-async": "^2.0.5",
  "sonner": "^2.0.7",
  "lucide-react": "^0.554.0",
  "tailwindcss": "^4.1.17",
  "@tanstack/react-table": "^8.21.3",
  "motion": "^12.23.24",
  "@radix-ui/react-*": "diverse"
}
```

---

## 8. Datenbank (PostgreSQL)

### 8.1 Core Models

#### UserAccount
```
id              SERIAL PRIMARY KEY
email           VARCHAR UNIQUE NOT NULL (indexed)
name            VARCHAR
auth_provider   ENUM(local, zitadel, google, github)
password_hash   VARCHAR (fuer local auth)
email_verified  BOOLEAN DEFAULT false
subscription_tier ENUM(free, pro, enterprise)
credits_balance FLOAT DEFAULT 0
credits_used_total FLOAT DEFAULT 0
default_country VARCHAR(2) DEFAULT 'IT'
default_language VARCHAR(5) DEFAULT 'it'
settings_json   TEXT
is_active       BOOLEAN DEFAULT true
is_admin        BOOLEAN DEFAULT false
created_at      TIMESTAMP
updated_at      TIMESTAMP
last_login_at   TIMESTAMP
```

#### Search
```
id              SERIAL PRIMARY KEY
name            VARCHAR NOT NULL
criteria_json   TEXT (JSON: query, country, regions, cities, keywords, tier)
target_count    INTEGER
campaign_id     INTEGER FK -> Campaign (nullable)
require_phone   BOOLEAN DEFAULT true
require_email   BOOLEAN DEFAULT true
require_website BOOLEAN DEFAULT true
validate_phone  BOOLEAN DEFAULT false
validate_email  BOOLEAN DEFAULT false
validate_website BOOLEAN DEFAULT true
created_at      TIMESTAMP
```

#### Company (Lead)
```
id              SERIAL PRIMARY KEY
search_id       INTEGER FK -> Search (indexed)
company_name    VARCHAR NOT NULL (indexed)
website         VARCHAR (indexed)
phone           VARCHAR (indexed)
email           VARCHAR (indexed)
alternative_phones TEXT (JSON Array)
sources_count   INTEGER DEFAULT 1
address_line    VARCHAR
postal_code     VARCHAR (indexed)
city            VARCHAR (indexed)
region          VARCHAR (indexed)
country         VARCHAR (indexed)
category        VARCHAR
keywords_matched VARCHAR
company_size    VARCHAR (small/medium/large)
employee_count  INTEGER
match_score     FLOAT (indexed, 0-1)
confidence_score FLOAT (0-1)
quality_score   INTEGER (indexed, 0-100)
phone_validated BOOLEAN
email_validated BOOLEAN
website_validated BOOLEAN
source_url      VARCHAR
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

#### Run (Ausfuehrung)
```
id              SERIAL PRIMARY KEY
search_id       INTEGER FK -> Search (indexed)
status          VARCHAR (indexed: running/completed/failed/cancelled)
progress_percent INTEGER (0-100)
current_step    VARCHAR
estimated_time_remaining INTEGER (Sekunden)
started_at      TIMESTAMP
ended_at        TIMESTAMP
found_count     INTEGER
discarded_count INTEGER
notes_json      TEXT
```

#### Source (Nachweis)
```
id              SERIAL PRIMARY KEY
company_id      INTEGER FK -> Company (indexed)
source_name     VARCHAR (indexed)
source_url      VARCHAR
field_name      VARCHAR (phone, email, website, address)
evidence_snippet VARCHAR
retrieved_at    TIMESTAMP
```

#### CreditTransaction
```
id              SERIAL PRIMARY KEY
user_id         INTEGER FK -> UserAccount
amount          FLOAT (positiv=Gutschrift, negativ=Ausgabe)
balance_after   FLOAT
operation       VARCHAR (purchase, search, refund, bonus)
search_id       INTEGER FK -> Search (nullable)
description     VARCHAR
metadata_json   TEXT
created_at      TIMESTAMP
```

#### UserSearch (Junction)
```
id              SERIAL PRIMARY KEY
user_id         INTEGER FK -> UserAccount
search_id       INTEGER FK -> Search
credits_spent   FLOAT
created_at      TIMESTAMP
```

#### SavedList
```
id              SERIAL PRIMARY KEY
user_id         INTEGER FK -> UserAccount
name            VARCHAR NOT NULL
description     VARCHAR
companies_json  TEXT (JSON Array von Company-IDs)
company_count   INTEGER DEFAULT 0
is_archived     BOOLEAN DEFAULT false
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

### 8.2 Extended Models (v2)

#### Client
```
id, name (unique), email, company, notes, settings_json, is_active, timestamps
```

#### Campaign
```
id, client_id FK, name, description, config_json, status (draft/active/paused/completed/archived), timestamps
```

---

## 9. Authentifizierung & Autorisierung

### 9.1 Ablauf

```
1. User registriert sich (POST /auth/register)
   -> Passwort wird mit bcrypt gehasht
   -> UserAccount wird erstellt
   -> 10 Welcome-Bonus-Credits
   -> JWT Token zurueckgegeben

2. User loggt sich ein (POST /auth/login)
   -> Account-Lockout-Check (E-Mail + IP)
   -> Passwort verifizieren (bcrypt)
   -> Bei Fehler: Failed Attempts tracken
   -> Bei Erfolg: JWT Token zurueckgeben

3. Authentifizierte Anfragen
   -> Frontend sendet: Authorization: Bearer {token}
   -> Middleware dekodiert JWT (HS256)
   -> UserAccount aus DB laden
   -> In request.state.user speichern
   -> Endpoint-Funktion erhaelt User via Depends(require_auth)
```

### 9.2 JWT Token Payload

```json
{
  "sub": 42,                    // User ID
  "email": "user@example.com",
  "provider": "local",
  "tier": "pro",
  "exp": 1738771200,            // 2 Stunden ab Erstellung
  "iat": 1738764000
}
```

### 9.3 Passwort-Regeln

- Minimum: 10 Zeichen
- Maximum: 128 Zeichen
- Hashing: bcrypt (passlib)

---

## 10. Credit-System & Preise

### 10.1 Credit-Pakete

| Paket | Credits | Bonus | Gesamt | Preis | Pro Credit |
|-------|---------|-------|--------|-------|------------|
| **Starter** | 100 | 0 | 100 | 19,00 EUR | 0,19 EUR |
| **Growth** | 500 | 50 (10%) | 550 | 79,00 EUR | 0,14 EUR |
| **Scale** | 1.000 | 150 (15%) | 1.150 | 129,00 EUR | 0,11 EUR |
| **Enterprise** | 5.000 | 1.000 (20%) | 6.000 | 519,00 EUR | 0,09 EUR |

### 10.2 Kosten pro Lead (nach Qualitaetsstufe)

| Tier | Min. Qualitaet | Quellen | Validierung | Kosten/Lead |
|------|---------------|---------|-------------|-------------|
| **Basic** | 40% | 2 | Format-Check | 0,07 Credits |
| **Standard** | 60% | 4 | MX + Format | 0,16 Credits |
| **Premium** | 80% | Alle | Carrier + SMTP | 0,33 Credits |

### 10.3 Welcome Bonus

Neue Benutzer erhalten **10 kostenlose Credits** bei Registrierung.

### 10.4 Credit-Operationen

| Operation | Beschreibung | Betrag |
|-----------|-------------|--------|
| `purchase` | Paket gekauft | +Positiv |
| `bonus` | Welcome Bonus | +10 |
| `search` | Suche ausgefuehrt | -Negativ |
| `refund` | Rueckerstattung | +Positiv |

### 10.5 Atomare Deduktion

Credits werden mit `SELECT FOR UPDATE` (Row-Level Lock) abgezogen, um Race Conditions bei gleichzeitigen Requests zu verhindern.

---

## 11. Zahlungssystem (Stripe)

### 11.1 Aktueller Stand

Das Zahlungssystem ist im Backend vollstaendig implementiert:

- **Stripe Checkout Session** erstellen
- **Webhook** empfangen und verifizieren
- **Credits** nach erfolgreicher Zahlung gutschreiben
- **Idempotenz** (keine doppelte Gutschrift bei Webhook-Retry)

### 11.2 Zahlungsablauf

```
1. User klickt "Kaufen" auf PricingPage
   -> POST /api/v1/auth/credits/purchase { package_id: "growth" }

2. Backend erstellt Stripe Checkout Session
   -> stripe.checkout.Session.create({
        payment_method_types: ["card"],
        line_items: [{ price: ..., quantity: 1 }],
        mode: "payment",
        success_url: "https://scripe.../payment/success?session_id={SESSION_ID}",
        cancel_url: "https://scripe.../payment/cancel",
        metadata: { user_id, package_id, credits, bonus }
      })
   -> Gibt checkout_url zurueck

3. Frontend leitet zu Stripe Checkout weiter
   -> window.location.href = checkout_url

4. User bezahlt bei Stripe

5. Stripe sendet Webhook (checkout.session.completed)
   -> POST /api/v1/webhooks/stripe
   -> Signatur wird verifiziert (STRIPE_WEBHOOK_SECRET)
   -> Event-ID wird gegen Duplikat-Set geprueft
   -> Credits werden gutgeschrieben (purchase + bonus)
   -> Transaction Record erstellt

6. User wird zu /payment/success weitergeleitet
   -> Zeigt Bestaetigung + neues Guthaben
```

### 11.3 Backend-Code (stripe_service.py)

```python
# Funktionen:
create_checkout_session(user_id, user_email, package_id, success_url, cancel_url)
  -> Erstellt Stripe Checkout Session mit Metadata
  -> Gibt checkout_url zurueck

verify_webhook_signature(payload, sig_header)
  -> Verifiziert Stripe-Signatur
  -> Gibt Event-Objekt zurueck

handle_checkout_completed(session)
  -> Liest user_id + package_id aus Metadata
  -> Ruft credit_service.purchase_credits() auf
  -> Loggt Transaktion
```

### 11.4 Webhook Handler (webhooks.py)

```python
@router.post("/stripe")
async def stripe_webhook(request: Request):
    # 1. Signatur verifizieren
    # 2. Idempotenz-Check (event_id in _processed_events?)
    # 3. checkout.session.completed -> Credits gutschreiben
    # 4. Event-ID speichern (max 10.000, dann Reset)
```

### 11.5 Frontend-Integration

**PaymentSuccessPage:**
- Zeigt Bestaetigung
- Aktualisiert Credit-Balance (refreshUser)
- Links zu Dashboard und Neue Suche

**PaymentCancelPage:**
- Zeigt Abbruch-Nachricht
- Link zurueck zu Pricing

**PricingPage:**
- 4 Paket-Karten mit Preis, Credits, Bonus
- "Kaufen"-Button ruft `purchaseCredits(packageId)` auf
- Leitet zu Stripe Checkout weiter

### 11.6 Stripe Setup (was noch konfiguriert werden muss)

**Umgebungsvariablen auf dem Server:**
```bash
STRIPE_SECRET_KEY=sk_live_...       # Stripe Dashboard > API Keys
STRIPE_PUBLISHABLE_KEY=pk_live_...  # Fuer Frontend (optional)
STRIPE_WEBHOOK_SECRET=whsec_...     # Stripe Dashboard > Webhooks
```

**Stripe Dashboard Konfiguration:**
1. Account erstellen auf stripe.com
2. Produkte anlegen (4 Pakete mit EUR-Preisen)
3. Webhook Endpoint hinzufuegen:
   - URL: `https://api.scripe.fabioprivato.org/api/v1/webhooks/stripe`
   - Events: `checkout.session.completed`
4. Webhook Secret kopieren -> STRIPE_WEBHOOK_SECRET

**Test-Modus (Development):**
- Wenn kein STRIPE_SECRET_KEY gesetzt und `ENV=development`:
  - Credits werden direkt ohne Zahlung gutgeschrieben
  - Nur von localhost erreichbar

---

## 12. Such-System & Data Pipeline

### 12.1 Datenquellen

| Quelle | Typ | Laender | API Key noetig |
|--------|-----|---------|---------------|
| **Google Places** | API | Alle | Ja |
| **Bing Maps** | API | Alle | Ja |
| **Google SERP** | Scraping | Alle | Nein |
| **Pagine Gialle** | Scraping | Italien | Nein |
| **Official Website** | Crawling | Alle | Nein |

### 12.2 Such-Ablauf

```
1. User erstellt Suche (Kriterien: Query, Land, Stadte, Keywords, Tier)
2. Kostenschaetzung: target_count * cost_per_lead = Credits
3. Credits werden abgezogen (atomar mit Row-Lock)
4. Run wird erstellt (status: running)
5. Source Manager startet Cascade:
   a. Google Places (wenn API Key vorhanden)
   b. Bing Maps (wenn API Key vorhanden)
   c. Google SERP (immer)
   d. Pagine Gialle (nur IT)
6. Ergebnisse werden validiert:
   - Telefon: Format + Carrier (je nach Tier)
   - E-Mail: Format + MX-Check (je nach Tier)
   - Website: DNS-Resolution
7. Enrichment: Website crawlen fuer Kontaktdaten
8. Deduplizierung:
   - Match auf Website-Domain
   - Match auf Telefonnummer
   - Match auf normalisierter Name + Stadt
   - Alternative Telefonnummern sammeln
9. Qualitaetsbewertung:
   - Completeness (35%): Wie viele Felder ausgefuellt?
   - Validation (30%): Sind Daten validiert?
   - Sources (20%): Wie viele Quellen bestaetigen?
   - Match (15%): Wie gut passt der Lead zur Suche?
10. Ergebnisse in DB speichern
11. SSE-Stream sendet Updates zum Frontend
12. Run wird auf "completed" gesetzt
```

### 12.3 Qualitaetsbewertung

```
quality_score = (
  completeness_score * 0.35 +
  validation_score   * 0.30 +
  source_score       * 0.20 +
  match_score        * 0.15
)
```

**Feld-Gewichte:**
- company_name: 0.15
- phone: 0.20
- email: 0.15
- website: 0.15
- address: 0.10
- city: 0.10
- category: 0.10
- description: 0.05

### 12.4 Export-Formate

| Format | Beschreibung | Max Zeilen |
|--------|-------------|-----------|
| **CSV** | Streaming, kommasepariert | Unbegrenzt |
| **Excel** | Formatiert mit Styles, Summary-Sheet | Unbegrenzt |
| **PDF** | Tabellen-Format, Landscape | 100 |

---

## 13. Internationalisierung (i18n)

### 13.1 Setup

- **Library:** react-i18next + i18next-http-backend
- **Sprachen:** EN, DE, IT, FR
- **Erkennung:** URL-Pfad > Browser > HTML-Tag
- **Fallback:** Englisch (en)
- **Namespaces:** common, landing, auth, dashboard, search, pricing, legal

### 13.2 Uebersetzungsdateien

```
public/locales/
|-- en/
|   |-- common.json      # Navigation, Footer, Sidebar, Status, Actions, Laender
|   |-- landing.json      # Hero, Features, Tiers, CTA
|   |-- auth.json         # Login, Register, Passwort-Anforderungen
|   |-- dashboard.json    # Dashboard Stats, Suchen, Listen
|   |-- search.json       # Neue Suche, Ergebnisse, Quellen
|   |-- pricing.json      # Pakete, Features, FAQ, Payment
|   |-- legal.json        # Privacy, Terms, Cookies (vollstaendige Texte)
|-- de/ (identische Struktur)
|-- it/ (identische Struktur)
|-- fr/ (identische Struktur)
```

### 13.3 URL-Schema

```
https://scripe.fabioprivato.org/en/dashboard
https://scripe.fabioprivato.org/de/dashboard
https://scripe.fabioprivato.org/it/dashboard
https://scripe.fabioprivato.org/fr/dashboard
```

### 13.4 Komponenten

- **LanguageSwitcher:** Dropdown in Header und Sidebar
- **LocalizedLink:** `<Link>` mit automatischem Sprach-Praefix
- **useLocalizedNavigate:** Hook fuer programmatische Navigation
- **HreflangTags:** SEO `<link rel="alternate">` fuer alle Sprachen
- **LanguageWrapper:** Synchronisiert URL-Param mit i18n-Instanz

---

## 14. Infrastruktur & Deployment

### 14.1 Docker Compose (Production)

```yaml
services:
  backend:
    build: ./backend
    environment:
      - ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - GOOGLE_PLACES_API_KEY=${GOOGLE_PLACES_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ALLOWED_ORIGINS=${ALLOWED_ORIGINS}
      - STRIPE_SECRET_KEY=${STRIPE_SECRET_KEY}
      - STRIPE_WEBHOOK_SECRET=${STRIPE_WEBHOOK_SECRET}
    networks: [scripe-network]

  frontend:
    build:
      context: ./frontend
      args:
        VITE_API_URL: ""  # Leer = gleicher Server via Nginx
    networks: [scripe-network]

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./nginx/nginx.prod.conf:/etc/nginx/nginx.conf:ro
    networks: [scripe-network]

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    volumes: [postgres_data:/var/lib/postgresql/data]
    networks: [scripe-network]
    # Port NICHT extern exponiert
```

### 14.2 Nginx Konfiguration

**2 Server-Bloecke:**

1. **API Server** (`api.scripe.fabioprivato.org`)
   - Alle Anfragen -> Backend (Port 8010)
   - SSE-Support (proxy_buffering off, timeout 86400s)

2. **Frontend Server** (`scripe.fabioprivato.org`)
   - `/api/*` -> Backend
   - `/health` -> Backend
   - `/*` -> Frontend (React SPA)
   - Blockiert `.`-Dateien und wp-admin/phpmyadmin

**Security Headers (beide Server):**
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'; script-src 'self'; ...`

**Cloudflare Real IP:** Alle Cloudflare IP-Ranges konfiguriert.

### 14.3 Server

| Detail | Wert |
|--------|------|
| **Provider** | Hetzner VPS |
| **IP** | 46.225.68.31 |
| **OS** | Linux |
| **SSL** | Cloudflare (Full Strict) |
| **Domain** | fabioprivato.org (Cloudflare DNS) |
| **SSH** | `ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31` |

---

## 15. Sicherheit (Cyber Security)

### 15.1 Implementierte Massnahmen

| Kategorie | Massnahme | Status |
|-----------|----------|--------|
| **Auth** | JWT-Secret Validierung (min 32 Zeichen, kein Default) | Aktiv |
| **Auth** | Zitadel Auth-Bypass blockiert | Aktiv |
| **Auth** | Account Lockout (5 Versuche / 15 Min) | Aktiv (In-Memory) |
| **Auth** | Passwort min 10 Zeichen, bcrypt Hashing | Aktiv |
| **Auth** | JWT Ablauf 2 Stunden | Aktiv |
| **Auth** | E-Mail Enumeration Prevention | Aktiv |
| **IDOR** | Company-Ownership-Check in Listen | Aktiv |
| **Payment** | Atomare Credit-Deduktion (SELECT FOR UPDATE) | Aktiv |
| **Payment** | Webhook Idempotenz (Event-ID Tracking) | Aktiv |
| **Payment** | Stripe Signatur-Verifizierung | Aktiv |
| **Infra** | Content-Security-Policy Header | Aktiv |
| **Infra** | Security Headers (HSTS, X-Frame, etc.) | Aktiv |
| **Infra** | CORS nur explizite Origins | Aktiv |
| **Infra** | DB-Port nicht extern exponiert | Aktiv |
| **Infra** | Rate Limiting auf kritische Endpoints | Aktiv |
| **Infra** | API-Docs in Production deaktiviert | Aktiv |
| **Scraping** | Source Allowlist (DSGVO-konform) | Aktiv |
| **Scraping** | robots.txt Respektierung | Aktiv |

### 15.2 Noch offene Sicherheits-Punkte

| Prioritaet | Problem | Empfohlener Fix |
|-----------|---------|----------------|
| **Hoch** | JWT in localStorage (XSS-Risiko) | httpOnly Secure Cookies |
| **Hoch** | Account Lockout nur In-Memory | Redis oder DB persistent |
| **Hoch** | SSE ohne Authentifizierung | Kurzlebige Tokens oder WebSocket |
| **Mittel** | Kein Search-Timeout | asyncio.wait_for |
| **Mittel** | Kein Credit-Refund bei Fehler | Automatische Rueckbuchung |
| **Niedrig** | SQL-Echo in Development | Sensible Daten in Logs |

---

## 16. API-Referenz

### Auth Endpoints

```
POST   /api/v1/auth/register           # Registrierung
POST   /api/v1/auth/login              # Login
POST   /api/v1/auth/refresh            # Token erneuern
GET    /api/v1/auth/me                 # User-Profil
PATCH  /api/v1/auth/me                 # Profil aktualisieren
POST   /api/v1/auth/change-password    # Passwort aendern
POST   /api/v1/auth/forgot-password    # Passwort-Reset anfordern
POST   /api/v1/auth/reset-password     # Passwort zuruecksetzen
POST   /api/v1/auth/verify-email       # E-Mail verifizieren
POST   /api/v1/auth/resend-verification # Verifikation erneut senden
```

### Credit Endpoints

```
GET    /api/v1/auth/credits            # Guthaben + Zusammenfassung
GET    /api/v1/auth/credits/packages   # Verfuegbare Pakete
GET    /api/v1/auth/credits/history    # Transaktionsverlauf
POST   /api/v1/auth/credits/purchase   # Credits kaufen (Stripe)
```

### Search Endpoints

```
GET    /api/v1/searches                # Alle Suchen (Pagination)
POST   /api/v1/searches                # Neue Suche erstellen
POST   /api/v1/searches/estimate       # Kostenschaetzung
GET    /api/v1/searches/{id}           # Suche Details
POST   /api/v1/searches/{id}/run       # Suche starten
GET    /api/v1/searches/{id}/runs/{rid}/stream  # SSE Fortschritt
GET    /api/v1/searches/{id}/runs/{rid}         # Run-Status
GET    /api/v1/searches/{id}/companies          # Ergebnisse (Pagination)
```

### Export Endpoints

```
POST   /api/v1/searches/{id}/export    # Export mit Optionen
GET    /api/v1/searches/{id}/export/csv    # Schnell-CSV
GET    /api/v1/searches/{id}/export/excel  # Schnell-Excel
GET    /api/v1/searches/{id}/export/pdf    # Schnell-PDF
```

### AI Endpoints

```
POST   /api/v1/ai/interpret            # Natuerliche Sprache interpretieren
GET    /api/v1/ai/tiers                 # Qualitaetsstufen-Info
POST   /api/v1/ai/estimate             # Kostenschaetzung
```

### List Endpoints

```
GET    /api/v1/lists                    # Alle Listen
POST   /api/v1/lists                    # Liste erstellen
GET    /api/v1/lists/{id}              # Liste Details
POST   /api/v1/lists/{id}/add          # Leads hinzufuegen
POST   /api/v1/lists/{id}/remove       # Leads entfernen
GET    /api/v1/lists/{id}/export        # Liste exportieren
```

### Source Endpoints

```
GET    /api/v1/sources                  # Alle Quellen
GET    /api/v1/sources/{name}           # Quellen-Details
POST   /api/v1/sources/{name}/health-check  # Health Check
```

### Dashboard Endpoints

```
GET    /api/v1/dashboard/stats          # User-Statistiken
```

### Webhook Endpoints

```
POST   /api/v1/webhooks/stripe          # Stripe Webhook
```

### Health Check

```
GET    /health                          # Backend-Status
```

---

## 17. Umgebungsvariablen

### Backend (.env auf dem Server)

```bash
# App
ENV=production
DATABASE_URL=postgresql://scripe:{PASSWORD}@db:5432/scripe

# Auth
JWT_SECRET_KEY=<min 32 Zeichen, zufaellig: openssl rand -hex 32>

# CORS
ALLOWED_ORIGINS=https://scripe.fabioprivato.org

# API Keys
GOOGLE_PLACES_API_KEY=<Google Cloud Console>
OPENAI_API_KEY=<OpenAI Dashboard>

# Stripe
STRIPE_SECRET_KEY=sk_live_<...>
STRIPE_PUBLISHABLE_KEY=pk_live_<...>
STRIPE_WEBHOOK_SECRET=whsec_<...>
```

### Datenbank (.env auf dem Server)

```bash
POSTGRES_USER=scripe
POSTGRES_PASSWORD=<starkes Passwort>
POSTGRES_DB=scripe
```

### Frontend (.env.production)

```bash
VITE_API_URL=
# Leer = nutzt gleichen Server (Nginx routet /api -> Backend)
```

### Frontend (.env.development)

```bash
VITE_API_URL=
# Leer = nutzt Vite Proxy (/api -> localhost:8010)
```

---

## 18. Deployment-Anleitung

### 18.1 Erstmaliges Setup

```bash
# 1. Auf Server verbinden
ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31

# 2. Repository klonen
git clone https://github.com/fabionr15-dot/scripe-standalone.git
cd scripe-standalone

# 3. .env erstellen
cat > .env << 'EOF'
ENV=production
DATABASE_URL=postgresql://scripe:SICHERES_PASSWORT@db:5432/scripe
JWT_SECRET_KEY=$(openssl rand -hex 32)
ALLOWED_ORIGINS=https://scripe.fabioprivato.org
GOOGLE_PLACES_API_KEY=...
OPENAI_API_KEY=...
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
POSTGRES_USER=scripe
POSTGRES_PASSWORD=SICHERES_PASSWORT
POSTGRES_DB=scripe
EOF

# 4. Starten
docker compose -f docker-compose.prod.yml up -d --build

# 5. Pruefen
curl -s http://localhost:80/health -H 'Host: api.scripe.fabioprivato.org'
# Sollte {"status":"ok"} zurueckgeben
```

### 18.2 Update/Deployment

```bash
ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31 \
  "cd /root/scripe-standalone && \
   git pull origin main && \
   docker compose -f docker-compose.prod.yml up -d --build"
```

### 18.3 Nginx Reload (nach Config-Aenderung)

```bash
ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31 \
  "docker restart scripe-standalone-nginx-1"
```

### 18.4 Logs pruefen

```bash
# Backend Logs
ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31 \
  "docker logs scripe-standalone-backend-1 --tail 50"

# Nginx Logs
ssh -i ~/.ssh/jarvis_deploy_key root@46.225.68.31 \
  "docker logs scripe-standalone-nginx-1 --tail 50"
```

### 18.5 Lokale Entwicklung

```bash
# Backend + DB starten
cd scripe-standalone
docker compose up -d

# Frontend separat starten (Hot Reload)
cd frontend
npm install
npm run dev
# -> http://localhost:3005

# Backend laeuft auf http://localhost:8010
# Vite Proxy: /api -> localhost:8010
```

---

## 19. Abgeschlossene Arbeiten (Changelog)

### Session 1-2 (Vorherige Conversations)
- Preiserhoehung +30% auf alle Credit-Pakete
- Vollstaendige i18n-Implementation (EN, DE, IT, FR)
  - 7 Namespace-Dateien pro Sprache
  - URL-basierte Spracherkennung mit `/:lang` Prefix
  - LanguageSwitcher, LocalizedLink, HreflangTags
  - Alle Seiten uebersetzt (inkl. Legal Pages)

### Session 3 (Aktuelle Conversation)

**Bug-Fix:**
- "Invalid Date" im Dashboard behoben (snake_case Mapping)

**Produktion-Test (Browser):**
- Alle Seiten getestet (Landing, Pricing, Login, Dashboard, Searches, Privacy, Terms, Cookies)
- Alle 4 Sprachen verifiziert
- Legacy-Redirects funktionieren
- Console: 0 Fehler

**Cyber Security Analyse & Haertung (24 Schwachstellen gefunden):**

| Commit | Beschreibung |
|--------|-------------|
| `d69802f` | Harden security: fix auth bypass, IDOR, payment race conditions, add CSP |

**Behobene Schwachstellen:**
1. Zitadel Auth-Bypass via `X-Client-Type: internal` blockiert
2. JWT Secret Startup-Validierung (kein Default in Production)
3. JWT Ablauf von 24h auf 2h reduziert
4. IDOR in Listen: Company-Ownership-Check ueber UserSearch
5. Atomare Credit-Deduktion mit `SELECT FOR UPDATE`
6. Stripe Webhook Idempotenz (Event-ID Tracking)
7. Content-Security-Policy Header in Nginx
8. DB-Port nicht mehr extern exponiert
9. CORS nur konfigurierte Origins (kein Wildcard)
10. Rate-Limiting auf Export und Search-Erstellung
11. Passwort-Minimum auf 10 Zeichen erhoeht
12. Axios Update auf ^1.7.9
13. Interne Error-Details durch generische Meldung ersetzt

---

> **Letzte Aktualisierung:** 5. Februar 2026, 15:30 Uhr
> **Letzter Commit:** `d69802f` - Security Hardening
> **Produktionsstatus:** Live und verifiziert
