import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { Database, Loader2, Zap } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/context/AuthContext';
import { LocalizedLink } from '@/i18n/LocalizedLink';
import { useLocalizedNavigate } from '@/i18n/useLocalizedNavigate';

export function LoginPage() {
  const navigate = useLocalizedNavigate();
  const location = useLocation();
  const { login, testLogin } = useAuth();
  const { t } = useTranslation('auth');

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isTestLoading] = useState(false);

  const from = location.state?.from?.pathname || '/dashboard';

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.message || t('login.invalidCredentials'));
    } finally {
      setIsLoading(false);
    }
  }

  function handleTestLogin() {
    navigate('/dashboard', { replace: true });
  }

  return (
    <>
      <Helmet>
        <title>{t('login.title')}</title>
      </Helmet>

      <div className="min-h-[80vh] flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <Database className="h-12 w-12 text-blue-600 mx-auto mb-4" />
            <h1 className="text-2xl font-bold">{t('login.heading')}</h1>
            <p className="text-gray-600">{t('login.subtitle')}</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="bg-red-50 text-red-600 p-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <div>
              <label htmlFor="email" className="block text-sm font-medium mb-1">
                {t('login.email')}
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={t('login.emailPlaceholder')}
                required
              />
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium mb-1">
                {t('login.password')}
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
                <span className="ml-2 text-sm text-gray-600">{t('login.rememberMe')}</span>
              </label>
              <LocalizedLink to="/forgot-password" className="text-sm text-blue-600 hover:underline">
                {t('login.forgotPassword')}
              </LocalizedLink>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('login.submit')}
            </button>
          </form>

          {/* Test Mode Button - only visible in development */}
          {import.meta.env.DEV && (
            <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800 mb-3 text-center font-medium">
                {t('login.testMode')}
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
                {t('login.testLogin')}
              </button>
            </div>
          )}

          <p className="mt-6 text-center text-gray-600">
            {t('login.noAccount')}{' '}
            <LocalizedLink to="/register" className="text-blue-600 hover:underline font-medium">
              {t('login.registerLink')}
            </LocalizedLink>
          </p>
        </div>
      </div>
    </>
  );
}
