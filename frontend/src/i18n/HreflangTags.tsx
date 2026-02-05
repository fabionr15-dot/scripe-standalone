import { Helmet } from 'react-helmet-async';
import { useLocation } from 'react-router-dom';
import { SUPPORTED_LANGUAGES, type SupportedLanguage } from './index';

const BASE_URL = 'https://scripe.fabioprivato.org';

export function HreflangTags() {
  const location = useLocation();

  // Remove current language prefix from path
  const pathParts = location.pathname.split('/').filter(Boolean);
  let pathWithoutLang = location.pathname;
  if (pathParts.length > 0 && SUPPORTED_LANGUAGES.includes(pathParts[0] as SupportedLanguage)) {
    pathWithoutLang = '/' + pathParts.slice(1).join('/');
  }

  return (
    <Helmet>
      {SUPPORTED_LANGUAGES.map((lang) => (
        <link
          key={lang}
          rel="alternate"
          hrefLang={lang}
          href={`${BASE_URL}/${lang}${pathWithoutLang === '/' ? '' : pathWithoutLang}`}
        />
      ))}
      <link
        rel="alternate"
        hrefLang="x-default"
        href={`${BASE_URL}/en${pathWithoutLang === '/' ? '' : pathWithoutLang}`}
      />
    </Helmet>
  );
}
