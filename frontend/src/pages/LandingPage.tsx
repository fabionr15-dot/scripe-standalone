import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Search,
  Globe,
  Phone,
  CheckCircle,
  ArrowRight,
  Zap,
  Shield,
  Target,
} from 'lucide-react';

export function LandingPage() {
  return (
    <>
      <Helmet>
        <title>Scripe - B2B Lead Generation Platform</title>
        <meta
          name="description"
          content="Trova contatti aziendali verificati in Italia e Europa. Genera lead B2B di qualità con validazione telefono ed email."
        />
      </Helmet>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center max-w-4xl">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
            Trova i tuoi prossimi clienti B2B
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
            Genera lead aziendali verificati in Italia e Europa. Telefoni validati, email funzionanti, dati sempre aggiornati.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              Inizia Gratis
              <ArrowRight className="h-5 w-5" />
            </Link>
            <Link
              to="/pricing"
              className="inline-flex items-center justify-center gap-2 border-2 border-gray-300 px-8 py-4 rounded-lg text-lg font-semibold hover:border-blue-600 hover:text-blue-600 transition-colors"
            >
              Vedi Prezzi
            </Link>
          </div>
          <p className="mt-4 text-sm text-gray-500">
            10 crediti gratis • Nessuna carta richiesta
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white dark:bg-gray-800">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            Tutto ciò che serve per trovare nuovi clienti
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={Search}
              title="Ricerca Intelligente"
              description="Usa il linguaggio naturale per cercare. 'Dentisti a Milano' - noi facciamo il resto."
            />
            <FeatureCard
              icon={Globe}
              title="Multi-Fonte"
              description="Cerchiamo su Google, Bing, Pagine Gialle e altre 10+ fonti per massimizzare i risultati."
            />
            <FeatureCard
              icon={Phone}
              title="Dati Verificati"
              description="Ogni telefono e email viene validato. Garantiamo almeno il 60% di dati funzionanti."
            />
            <FeatureCard
              icon={Target}
              title="Targeting Preciso"
              description="Filtra per regione, città, categoria. Escludi ciò che non vuoi con un click."
            />
            <FeatureCard
              icon={Zap}
              title="Risultati Rapidi"
              description="La maggior parte delle ricerche completa in meno di 5 minuti. Niente attese."
            />
            <FeatureCard
              icon={Shield}
              title="GDPR Compliant"
              description="Raccogliamo solo dati pubblici. Piena conformità alle normative privacy."
            />
          </div>
        </div>
      </section>

      {/* Quality Tiers */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">
            Scegli il livello di qualità
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            Più qualità significa più validazione, più fonti e dati più affidabili
          </p>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <TierCard
              name="Basic"
              minScore="40%"
              price="€0.02"
              features={[
                "2 fonti dati",
                "Validazione formato",
                "Export CSV",
                "Ideale per campagne di volume",
              ]}
            />
            <TierCard
              name="Standard"
              minScore="60%"
              price="€0.05"
              featured
              features={[
                "4 fonti dati",
                "Validazione MX email",
                "Arricchimento da sito web",
                "Export Excel/PDF",
                "Buon rapporto qualità/prezzo",
              ]}
            />
            <TierCard
              name="Premium"
              minScore="80%"
              price="€0.10"
              features={[
                "Tutte le fonti",
                "Validazione carrier telefono",
                "Verifica SMTP email",
                "Massima qualità",
                "Per campagne mirate",
              ]}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-blue-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Pronto a trovare nuovi clienti?
          </h2>
          <p className="text-blue-100 mb-8 max-w-xl mx-auto">
            Registrati ora e ricevi 10 crediti gratuiti per provare la piattaforma
          </p>
          <Link
            to="/register"
            className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-50 transition-colors"
          >
            Crea Account Gratuito
            <ArrowRight className="h-5 w-5" />
          </Link>
        </div>
      </section>
    </>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl bg-gray-50 dark:bg-gray-700">
      <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-4">
        <Icon className="h-6 w-6 text-blue-600" />
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
}

function TierCard({
  name,
  minScore,
  price,
  features,
  featured,
}: {
  name: string;
  minScore: string;
  price: string;
  features: string[];
  featured?: boolean;
}) {
  return (
    <div
      className={`p-6 rounded-xl border-2 ${
        featured
          ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      {featured && (
        <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          Più Popolare
        </span>
      )}
      <h3 className="text-2xl font-bold mt-4">{name}</h3>
      <p className="text-gray-500 mb-4">Min. qualità: {minScore}</p>
      <p className="text-4xl font-bold mb-6">
        {price}
        <span className="text-lg font-normal text-gray-500">/lead</span>
      </p>
      <ul className="space-y-3">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
            <span className="text-gray-600 dark:text-gray-400">{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
