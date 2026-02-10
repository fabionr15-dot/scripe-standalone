import { Routes, Route, Navigate, useParams, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { AuthProvider } from './context/AuthContext';
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { SearchesPage } from './pages/SearchesPage';
import { NewSearchPage } from './pages/NewSearchPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { PricingPage } from './pages/PricingPage';
import { ListsPage } from './pages/ListsPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { TermsPage } from './pages/TermsPage';
import { CookiePolicyPage } from './pages/CookiePolicyPage';
import { PaymentSuccessPage } from './pages/PaymentSuccessPage';
import { PaymentCancelPage } from './pages/PaymentCancelPage';
import { ProtectedRoute } from './components/ProtectedRoute';
import { HreflangTags } from './i18n/HreflangTags';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from './i18n';

/**
 * Wrapper that reads :lang from URL and syncs it with i18next.
 */
function LanguageWrapper({ children }: { children: React.ReactNode }) {
  const { lang } = useParams<{ lang: string }>();
  const { i18n } = useTranslation();

  useEffect(() => {
    if (lang && SUPPORTED_LANGUAGES.includes(lang as SupportedLanguage)) {
      if (i18n.language !== lang) {
        i18n.changeLanguage(lang);
      }
      document.documentElement.lang = lang;
    }
  }, [lang, i18n]);

  return <>{children}</>;
}

/**
 * Detects user language and redirects to /:lang/ preserving the path.
 * Fixed: Prevents redirect loop when path already has a language prefix.
 */
function LanguageRedirect() {
  const { i18n } = useTranslation();
  const location = useLocation();

  let detectedLang = i18n.language?.slice(0, 2) || 'en';
  if (!SUPPORTED_LANGUAGES.includes(detectedLang as SupportedLanguage)) {
    detectedLang = 'en';
  }

  let path = location.pathname;

  // Check if path already starts with a language code to prevent /de/de/de... loops
  const langPrefixMatch = path.match(/^\/([a-z]{2})(\/|$)/);
  if (langPrefixMatch && SUPPORTED_LANGUAGES.includes(langPrefixMatch[1] as SupportedLanguage)) {
    // Already has a valid language prefix - strip it and use detected language
    const pathWithoutLang = path.slice(3) || ''; // Remove /de or /en etc.
    return <Navigate to={`/${detectedLang}${pathWithoutLang}`} replace />;
  }

  // No language prefix - add one
  if (path === '/') {
    path = '';
  }
  return <Navigate to={`/${detectedLang}${path}`} replace />;
}

export default function App() {
  return (
    <AuthProvider>
      <HreflangTags />
      <Routes>
        {/* Language-prefixed public pages */}
        <Route path="/:lang" element={<LanguageWrapper><PublicLayout /></LanguageWrapper>}>
          <Route index element={<LandingPage />} />
          <Route path="pricing" element={<PricingPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
          <Route path="privacy" element={<PrivacyPage />} />
          <Route path="terms" element={<TermsPage />} />
          <Route path="cookies" element={<CookiePolicyPage />} />
        </Route>

        {/* Language-prefixed protected dashboard */}
        <Route path="/:lang" element={<LanguageWrapper><ProtectedRoute><DashboardLayout /></ProtectedRoute></LanguageWrapper>}>
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="searches" element={<SearchesPage />} />
          <Route path="searches/new" element={<NewSearchPage />} />
          <Route path="searches/:id" element={<SearchResultsPage />} />
          <Route path="lists" element={<ListsPage />} />
          <Route path="payment/success" element={<PaymentSuccessPage />} />
          <Route path="payment/cancel" element={<PaymentCancelPage />} />
        </Route>

        {/* Root redirect to detected language */}
        <Route path="/" element={<LanguageRedirect />} />

        {/* Legacy routes without language prefix — redirect preserving path */}
        <Route path="/pricing" element={<LanguageRedirect />} />
        <Route path="/login" element={<LanguageRedirect />} />
        <Route path="/register" element={<LanguageRedirect />} />
        <Route path="/dashboard" element={<LanguageRedirect />} />
        <Route path="/searches" element={<LanguageRedirect />} />
        <Route path="/searches/*" element={<LanguageRedirect />} />
        <Route path="/lists" element={<LanguageRedirect />} />
        <Route path="/privacy" element={<LanguageRedirect />} />
        <Route path="/terms" element={<LanguageRedirect />} />
        <Route path="/cookies" element={<LanguageRedirect />} />
        <Route path="/payment/*" element={<LanguageRedirect />} />

        {/* Catch all */}
        <Route path="*" element={<LanguageRedirect />} />
      </Routes>
    </AuthProvider>
  );
}
