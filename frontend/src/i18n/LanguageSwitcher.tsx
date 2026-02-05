import { useTranslation } from 'react-i18next';
import { useNavigate, useLocation } from 'react-router-dom';
import { Globe } from 'lucide-react';
import { SUPPORTED_LANGUAGES, LANGUAGE_NAMES, type SupportedLanguage } from './index';

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  function handleChange(newLang: SupportedLanguage) {
    const currentLang = i18n.language;
    const pathParts = location.pathname.split('/');

    // Replace the language prefix in the URL
    if (SUPPORTED_LANGUAGES.includes(pathParts[1] as SupportedLanguage)) {
      pathParts[1] = newLang;
    } else {
      pathParts.splice(1, 0, newLang);
    }

    const newPath = pathParts.join('/') || `/${newLang}`;
    i18n.changeLanguage(newLang);
    navigate(newPath + location.search, { replace: true });
  }

  return (
    <div className="relative group">
      <button className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-sm text-gray-600 dark:text-gray-300">
        <Globe className="h-4 w-4" />
        <span className="uppercase font-medium">{i18n.language?.slice(0, 2)}</span>
      </button>
      <div className="absolute right-0 top-full mt-1 bg-white dark:bg-gray-800 border dark:border-gray-700 rounded-lg shadow-lg py-1 hidden group-hover:block z-50 min-w-[140px]">
        {SUPPORTED_LANGUAGES.map((lang) => (
          <button
            key={lang}
            onClick={() => handleChange(lang)}
            className={`w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors ${
              i18n.language?.startsWith(lang) ? 'font-semibold text-blue-600' : 'text-gray-700 dark:text-gray-300'
            }`}
          >
            {LANGUAGE_NAMES[lang]}
          </button>
        ))}
      </div>
    </div>
  );
}
