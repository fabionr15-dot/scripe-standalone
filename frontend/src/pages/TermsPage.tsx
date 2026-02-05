import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';

export function TermsPage() {
  const { t } = useTranslation('legal');

  return (
    <>
      <Helmet>
        <title>{t('terms.title')}</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>{t('terms.heading')}</h1>
        <p className="text-sm text-gray-500">{t('terms.lastUpdated')}</p>

        <h2>{t('terms.section1.title')}</h2>
        <p>{t('terms.section1.content')}</p>

        <h2>{t('terms.section2.title')}</h2>
        <p>{t('terms.section2.content')}</p>

        <h2>{t('terms.section3.title')}</h2>
        <ul>
          {(t('terms.section3.items', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('terms.section4.title')}</h2>
        <ul>
          {(t('terms.section4.items', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('terms.section5.title')}</h2>
        <p>{t('terms.section5.intro')}</p>
        <ul>
          {(t('terms.section5.allowed', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
        <p>{t('terms.section5.prohibitedIntro')}</p>
        <ul>
          {(t('terms.section5.prohibited', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('terms.section6.title')}</h2>
        <p>{t('terms.section6.content')}</p>

        <h2>{t('terms.section7.title')}</h2>
        <p>{t('terms.section7.content')}</p>

        <h2>{t('terms.section8.title')}</h2>
        <p>{t('terms.section8.content')}</p>

        <h2>{t('terms.section9.title')}</h2>
        <p>{t('terms.section9.content')}</p>

        <h2>{t('terms.section10.title')}</h2>
        <p>{t('terms.section10.content')}</p>

        <h2>{t('terms.section11.title')}</h2>
        <p>{t('terms.section11.content')}</p>
      </div>
    </>
  );
}
