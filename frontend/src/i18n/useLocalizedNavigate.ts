import { useNavigate, type NavigateOptions } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from './index';

export function useLocalizedNavigate() {
  const navigate = useNavigate();
  const { i18n } = useTranslation();

  return (to: string, options?: NavigateOptions) => {
    const lang = i18n.language?.slice(0, 2) || 'en';

    // Don't prefix if already has a language prefix
    const pathParts = to.split('/').filter(Boolean);
    if (pathParts.length > 0 && SUPPORTED_LANGUAGES.includes(pathParts[0] as SupportedLanguage)) {
      return navigate(to, options);
    }

    const localizedTo = `/${lang}${to.startsWith('/') ? to : `/${to}`}`;
    return navigate(localizedTo, options);
  };
}
