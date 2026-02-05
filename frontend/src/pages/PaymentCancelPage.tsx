import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { XCircle, ArrowLeft } from 'lucide-react';

export function PaymentCancelPage() {
  return (
    <>
      <Helmet>
        <title>Pagamento annullato - Scripe</title>
      </Helmet>

      <div className="min-h-[60vh] flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="bg-white rounded-2xl border p-8 shadow-sm">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <XCircle className="h-8 w-8 text-gray-400" />
            </div>

            <h1 className="text-2xl font-bold mb-2">Pagamento annullato</h1>
            <p className="text-gray-600 mb-6">
              Il pagamento non è stato completato. Non è stato addebitato alcun importo.
              Puoi riprovare quando vuoi.
            </p>

            <div className="space-y-3">
              <Link
                to="/pricing"
                className="flex items-center justify-center gap-2 w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-semibold transition-colors"
              >
                <ArrowLeft className="h-5 w-5" />
                Torna ai prezzi
              </Link>
              <Link
                to="/dashboard"
                className="block w-full py-3 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg font-semibold transition-colors"
              >
                Vai alla dashboard
              </Link>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
