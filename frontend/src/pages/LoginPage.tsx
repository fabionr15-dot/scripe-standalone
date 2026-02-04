import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Database, Loader2, Zap } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, testLogin } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTestLoading] = useState(false); // Nicht mehr genutzt, aber für Button

  const from = location.state?.from?.pathname || '/dashboard';

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || 'Credenziali non valide');
    } finally {
      setIsLoading(false);
    }
  }

  function handleTestLogin() {
    // Bypass direkt zum Dashboard - kein Backend nötig
    navigate('/dashboard', { replace: true });
  }

  return (
    <>
      <Helmet>
        <title>Accedi - Scripe</title>
      </Helmet>

      <div className="min-h-[80vh] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Database className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold">Bentornato</h1>
            <p className="text-gray-600">Accedi al tuo account Scripe</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="nome@azienda.it"
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-1">
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="••••••••"
                required
              />
            </div>

            <div className="flex items-center justify-between">
              <label className="flex items-center">
                <input type="checkbox" className="rounded border-gray-300" />
                <span className="ml-2 text-sm text-gray-600">Ricordami</span>
              </label>
              <Link to="/forgot-password" className="text-sm text-blue-600 hover:underline">
                Password dimenticata?
              </Link>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Accedi
            </button>
          </form>

                    {/* Test Mode Button */}
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800 mb-3 text-center font-medium">
              🧪 Modalità Test
            </p>
            <button
              type="button"
              onClick={handleTestLogin}
              disabled={isTestLoading}
              className="w-full bg-yellow-500 text-white py-2 rounded-lg font-semibold hover:bg-yellow-600 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isTestLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Zap className="h-4 w-4" />
              )}
              Accedi come Test User (1000 crediti)
            </button>
          </div>

          <p className="mt-6 text-center text-gray-600">
            Non hai un account?{' '}
            <Link to="/register" className="text-blue-600 hover:underline font-medium">
              Registrati gratis
            </Link>
          </p>
        </div>
      </div>
    </>
  );
}
