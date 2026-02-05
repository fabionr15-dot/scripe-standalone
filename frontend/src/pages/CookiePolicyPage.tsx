import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';

export function CookiePolicyPage() {
  const { t } = useTranslation('legal');

  return (
    <>
      <Helmet>
        <title>{t('cookies.title')}</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>{t('cookies.heading')}</h1>
        <p className="text-sm text-gray-500">{t('cookies.lastUpdated')}</p>

        <h2>{t('cookies.section1.title')}</h2>
        <p>{t('cookies.section1.content')}</p>

        <h2>{t('cookies.section2.title')}</h2>

        <h3>{t('cookies.section2.technicalTitle')}</h3>
        <p>{t('cookies.section2.technicalContent')}</p>
        <ul>
          {(t('cookies.section2.technicalItems', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h3>{t('cookies.section2.cloudflareTitle')}</h3>
        <p>{t('cookies.section2.cloudflareContent')}</p>

        <h2>{t('cookies.section3.title')}</h2>
        <p>{t('cookies.section3.content')}</p>

        <h2>{t('cookies.section4.title')}</h2>
        <p>{t('cookies.section4.content')}</p>

        <h2>{t('cookies.section5.title')}</h2>
        <p>{t('cookies.section5.content')}</p>
      </div>
    </>
  );
}
