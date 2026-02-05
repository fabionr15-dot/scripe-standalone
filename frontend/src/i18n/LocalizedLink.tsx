import { Link, type LinkProps } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from './index';

interface LocalizedLinkProps extends Omit<LinkProps, 'to'> {
  to: string;
}

export function LocalizedLink({ to, ...props }: LocalizedLinkProps) {
  const { i18n } = useTranslation();
  const lang = i18n.language?.slice(0, 2) || 'en';

  // Don't prefix if already has a language prefix
  const pathParts = to.split('/').filter(Boolean);
  if (pathParts.length > 0 && SUPPORTED_LANGUAGES.includes(pathParts[0] as SupportedLanguage)) {
    return <Link to={to} {...props} />;
  }

  // Prefix with current language
  const localizedTo = `/${lang}${to.startsWith('/') ? to : `/${to}`}`;
  return <Link to={localizedTo} {...props} />;
}
