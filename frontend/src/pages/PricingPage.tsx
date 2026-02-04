import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Check,
  CreditCard,
  Loader2,
  Sparkles,
  Zap,
  Crown,
  Building,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';

interface CreditPackage {
  id: string;
  name: string;
  credits: number;
  price: number;
  bonus: number;
  popular?: boolean;
  icon: typeof Sparkles;
  color: string;
}

const packages: CreditPackage[] = [
  {
    id: 'starter',
    name: 'Starter',
    credits: 100,
    price: 10,
    bonus: 0,
    icon: Sparkles,
    color: 'gray',
  },
  {
    id: 'growth',
    name: 'Growth',
    credits: 500,
    price: 40,
    bonus: 50,
    popular: true,
    icon: Zap,
    color: 'blue',
  },
  {
    id: 'scale',
    name: 'Scale',
    credits: 1000,
    price: 70,
    bonus: 150,
    icon: Crown,
    color: 'purple',
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    credits: 5000,
    price: 300,
    bonus: 1000,
    icon: Building,
    color: 'green',
  },
];

export function PricingPage() {
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const [selectedPackage, setSelectedPackage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handlePurchase(pkg: CreditPackage) {
    if (!isAuthenticated) {
      navigate('/login?redirect=/pricing');
      return;
    }

    setSelectedPackage(pkg.id);
    setIsLoading(true);

    try {
      const res = await api.post('/auth/credits/purchase', {
        package_id: pkg.id,
      });

      // Redirect to Stripe checkout or handle payment
      if (res.data.checkout_url) {
        window.location.href = res.data.checkout_url;
      }
    } catch (err) {
      console.error('Purchase failed:', err);
      alert('Errore durante l\'acquisto. Riprova.');
    } finally {
      setIsLoading(false);
      setSelectedPackage(null);
    }
  }

  const features = [
    'Ricerca AI illimitata',
    'Export Excel/CSV',
    'Validazione telefoni',
    'Verifica email MX',
    'Crawling siti web',
    'Multi-fonte: Google, Bing, Pagine Gialle',
  ];

  const colorClasses = {
    gray: {
      bg: 'bg-gray-100',
      text: 'text-gray-600',
      button: 'bg-gray-600 hover:bg-gray-700',
      border: 'border-gray-200',
    },
    blue: {
      bg: 'bg-blue-100',
      text: 'text-blue-600',
      button: 'bg-blue-600 hover:bg-blue-700',
      border: 'border-blue-500',
    },
    purple: {
      bg: 'bg-purple-100',
      text: 'text-purple-600',
      button: 'bg-purple-600 hover:bg-purple-700',
      border: 'border-purple-200',
    },
    green: {
      bg: 'bg-green-100',
      text: 'text-green-600',
      button: 'bg-green-600 hover:bg-green-700',
      border: 'border-green-200',
    },
  };

  return (
    <>
      <Helmet>
        <title>Prezzi - Scripe</title>
      </Helmet>

      <div className="py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            Semplice e trasparente
          </h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            Paga solo per quello che usi. Nessun abbonamento, nessun vincolo.
            Ogni credito = 1 lead verificato.
          </p>
          {user && (
            <p className="mt-4 text-lg">
              I tuoi crediti:{' '}
              <span className="font-bold text-blue-600">
                {user.credits_balance}
              </span>
            </p>
          )}
        </div>

        {/* Packages */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto px-4">
          {packages.map((pkg) => {
            const Icon = pkg.icon;
            const colors = colorClasses[pkg.color as keyof typeof colorClasses];
            const totalCredits = pkg.credits + pkg.bonus;
            const pricePerCredit = (pkg.price / totalCredits).toFixed(3);

            return (
              <div
                key={pkg.id}
                className={`relative bg-white rounded-2xl border-2 p-6 transition-all hover:shadow-lg ${
                  pkg.popular ? colors.border : 'border-gray-200'
                }`}
              >
                {pkg.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-3 py-1 rounded-full">
                    Più popolare
                  </div>
                )}

                <div className={`w-12 h-12 ${colors.bg} rounded-lg flex items-center justify-center mb-4`}>
                  <Icon className={`h-6 w-6 ${colors.text}`} />
                </div>

                <h3 className="text-xl font-bold">{pkg.name}</h3>

                <div className="mt-4">
                  <span className="text-4xl font-bold">€{pkg.price}</span>
                </div>

                <div className="mt-2 space-y-1">
                  <p className="text-2xl font-semibold">{pkg.credits} crediti</p>
                  {pkg.bonus > 0 && (
                    <p className="text-green-600 font-medium">
                      + {pkg.bonus} bonus gratuiti
                    </p>
                  )}
                  <p className="text-sm text-gray-500">
                    €{pricePerCredit} per credito
                  </p>
                </div>

                <button
                  onClick={() => handlePurchase(pkg)}
                  disabled={isLoading && selectedPackage === pkg.id}
                  className={`w-full mt-6 py-3 rounded-lg font-semibold text-white transition-colors flex items-center justify-center gap-2 ${colors.button} disabled:opacity-50`}
                >
                  {isLoading && selectedPackage === pkg.id ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      <CreditCard className="h-5 w-5" />
                      Acquista
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>

        {/* Features */}
        <div className="mt-16 max-w-3xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center mb-8">
            Cosa include ogni credito
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {features.map((feature, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-4 bg-gray-50 rounded-lg"
              >
                <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
                <span>{feature}</span>
              </div>
            ))}
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-16 max-w-2xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-center mb-8">
            Domande frequenti
          </h2>
          <div className="space-y-4">
            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold">Come funzionano i crediti?</h3>
              <p className="text-gray-600 mt-2">
                Ogni credito ti permette di ottenere 1 lead verificato. Il costo
                varia in base al livello di qualità scelto: Basic (1 credito),
                Standard (2 crediti), Premium (4 crediti).
              </p>
            </div>
            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold">I crediti scadono?</h3>
              <p className="text-gray-600 mt-2">
                No, i crediti non scadono mai. Puoi usarli quando vuoi.
              </p>
            </div>
            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold">Posso avere un rimborso?</h3>
              <p className="text-gray-600 mt-2">
                Se non sei soddisfatto, contattaci entro 14 giorni dall'acquisto
                per un rimborso completo dei crediti non utilizzati.
              </p>
            </div>
            <div className="bg-white rounded-lg border p-6">
              <h3 className="font-semibold">Accettate fatturazione aziendale?</h3>
              <p className="text-gray-600 mt-2">
                Sì, emettiamo fattura per tutti gli acquisti. Inserisci i dati
                della tua azienda durante il checkout.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
