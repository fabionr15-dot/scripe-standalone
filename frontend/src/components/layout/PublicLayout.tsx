import { Outlet } from 'react-router-dom';
import { Database } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { LocalizedLink } from '@/i18n/LocalizedLink';
import { LanguageSwitcher } from '@/i18n/LanguageSwitcher';

export function PublicLayout() {
  const { t } = useTranslation('common');

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <LocalizedLink to="/" className="flex items-center gap-2">
            <Database className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-blue-600">Scripe</span>
          </LocalizedLink>

          <nav className="hidden md:flex items-center gap-6">
            <LocalizedLink to="/pricing" className="text-gray-600 hover:text-gray-900 dark:text-gray-300">
              {t('nav.pricing')}
            </LocalizedLink>
            <LocalizedLink to="/login" className="text-gray-600 hover:text-gray-900 dark:text-gray-300">
              {t('nav.login')}
            </LocalizedLink>
            <LocalizedLink
              to="/register"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              {t('nav.register')}
            </LocalizedLink>
            <LanguageSwitcher />
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t bg-white dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Database className="h-6 w-6 text-blue-600" />
                <span className="text-xl font-bold">Scripe</span>
              </div>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                {t('footer.description')}
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">{t('footer.product')}</h4>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><LocalizedLink to="/pricing">{t('footer.pricing')}</LocalizedLink></li>
                <li><LocalizedLink to="/register">{t('footer.startFree')}</LocalizedLink></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">{t('footer.legal')}</h4>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><LocalizedLink to="/privacy">{t('footer.privacy')}</LocalizedLink></li>
                <li><LocalizedLink to="/terms">{t('footer.terms')}</LocalizedLink></li>
                <li><LocalizedLink to="/cookies">{t('footer.cookies')}</LocalizedLink></li>
              </ul>
            </div>
          </div>
          <div className="border-t mt-8 pt-8 text-center text-sm text-gray-600 dark:text-gray-400">
            {t('footer.copyright', { year: new Date().getFullYear() })}
          </div>
        </div>
      </footer>
    </div>
  );
}
