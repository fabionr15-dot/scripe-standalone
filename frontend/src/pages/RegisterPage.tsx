import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Database, Loader2, Check } from 'lucide-react';
import { useAuth } from '@/context/AuthContext';

export function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
    acceptTerms: false,
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const passwordRequirements = [
    { test: (p: string) => p.length >= 8, label: 'Almeno 8 caratteri' },
    { test: (p: string) => /[A-Z]/.test(p), label: 'Una lettera maiuscola' },
    { test: (p: string) => /[a-z]/.test(p), label: 'Una lettera minuscola' },
    { test: (p: string) => /[0-9]/.test(p), label: 'Un numero' },
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');

    // Validate
    if (formData.password !== formData.confirmPassword) {
      setError('Le password non corrispondono');
      return;
    }

    const failedRequirements = passwordRequirements.filter(
      (req) => !req.test(formData.password)
    );
    if (failedRequirements.length > 0) {
      setError('La password non soddisfa tutti i requisiti');
      return;
    }

    if (!formData.acceptTerms) {
      setError('Devi accettare i termini e condizioni');
      return;
    }

    setIsLoading(true);

    try {
      await register(formData.email, formData.password, formData.name);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Errore durante la registrazione');
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <>
      <Helmet>
        <title>Registrati - Scripe</title>
      </Helmet>

      <div className="min-h-[80vh] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Database className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold">Crea il tuo account</h1>
            <p className="text-gray-600">Inizia gratis con 10 crediti</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="name" className="block text-sm font-medium mb-1">
                Nome completo
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Mario Rossi"
                required
              />
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
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
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="••••••••"
                required
              />
              <div className="mt-2 space-y-1">
                {passwordRequirements.map((req, i) => (
                  <div
                    key={i}
                    className={`flex items-center gap-2 text-xs ${
                      req.test(formData.password) ? 'text-green-600' : 'text-gray-400'
                    }`}
                  >
                    <Check className="h-3 w-3" />
                    {req.label}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium mb-1">
                Conferma password
              </label>
              <input
                id="confirmPassword"
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="••••••••"
                required
              />
            </div>

            <div className="flex items-start">
              <input
                id="terms"
                type="checkbox"
                checked={formData.acceptTerms}
                onChange={(e) => setFormData({ ...formData, acceptTerms: e.target.checked })}
                className="rounded border-gray-300 mt-1"
              />
              <label htmlFor="terms" className="ml-2 text-sm text-gray-600">
                Accetto i{' '}
                <Link to="/terms" className="text-blue-600 hover:underline">
                  Termini di Servizio
                </Link>{' '}
                e la{' '}
                <Link to="/privacy" className="text-blue-600 hover:underline">
                  Privacy Policy
                </Link>
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              Crea account
            </button>
          </form>

          <p className="mt-6 text-center text-gray-600">
            Hai già un account?{' '}
            <Link to="/login" className="text-blue-600 hover:underline font-medium">
              Accedi
            </Link>
          </p>
        </div>
      </div>
    </>
  );
}
