import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { CheckCircle, Loader2, ArrowRight } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export function PaymentSuccessPage() {
  const [searchParams] = useSearchParams();
  const sessionId = searchParams.get('session_id');
  const { refreshUser } = useAuth();
  const [refreshed, setRefreshed] = useState(false);

  useEffect(() => {
    // Refresh user data to get updated credit balance
    async function updateBalance() {
      try {
        await refreshUser();
      } catch {
        // Ignore errors - user can refresh manually
      } finally {
        setRefreshed(true);
      }
    }
    updateBalance();
  }, [refreshUser]);

  return (
    <>
      <Helmet>
        <title>Pagamento completato - Scripe</title>
      </Helmet>

      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="bg-white rounded-2xl border p-8 shadow-sm">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <CheckCircle className="h-8 w-8 text-green-600" />
            </div>

            <h1 className="text-2xl font-bold mb-2">Pagamento completato!</h1>
            <p className="text-gray-600 mb-6">
              I tuoi crediti sono stati aggiunti al tuo account.
              Puoi iniziare a usarli subito.
            </p>

            {!refreshed && (
              <div className="flex items-center justify-center gap-2 text-gray-500 mb-6">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm">Aggiornamento saldo...</span>
              </div>
            )}

            <div className="space-y-3">
              <Link
                to="/searches/new"
                className="flex items-center justify-center gap-2 w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
              >
                Inizia una ricerca
                <ArrowRight className="h-5 w-5" />
              </Link>
              <Link
                to="/dashboard"
                className="block w-full py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-semibold transition-colors"
              >
                Vai alla dashboard
              </Link>
            </div>

            {sessionId && (
              <p className="mt-6 text-xs text-gray-400">
                Riferimento: {sessionId.slice(0, 20)}...
              </p>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
