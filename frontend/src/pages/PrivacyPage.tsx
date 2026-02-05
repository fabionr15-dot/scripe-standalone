import { Helmet } from 'react-helmet-async';
import { useTranslation } from 'react-i18next';

export function PrivacyPage() {
  const { t } = useTranslation('legal');

  return (
    <>
      <Helmet>
        <title>{t('privacy.title')}</title>
      </Helmet>

      <div className="py-12 px-4 max-w-3xl mx-auto prose prose-gray">
        <h1>{t('privacy.heading')}</h1>
        <p className="text-sm text-gray-500">{t('privacy.lastUpdated')}</p>

        <h2>{t('privacy.section1.title')}</h2>
        <p>{t('privacy.section1.content')}</p>

        <h2>{t('privacy.section2.title')}</h2>
        <h3>{t('privacy.section2.userDataTitle')}</h3>
        <ul>
          {(t('privacy.section2.userData', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
        <h3>{t('privacy.section2.autoDataTitle')}</h3>
        <ul>
          {(t('privacy.section2.autoData', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('privacy.section3.title')}</h2>
        <ul>
          {(t('privacy.section3.purposes', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('privacy.section4.title')}</h2>
        <p>{t('privacy.section4.content')}</p>

        <h2>{t('privacy.section5.title')}</h2>
        <p>{t('privacy.section5.content')}</p>

        <h2>{t('privacy.section6.title')}</h2>
        <p>{t('privacy.section6.intro')}</p>
        <ul>
          {(t('privacy.section6.parties', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>

        <h2>{t('privacy.section7.title')}</h2>
        <p>{t('privacy.section7.content')}</p>

        <h2>{t('privacy.section8.title')}</h2>
        <p>{t('privacy.section8.intro')}</p>
        <ul>
          {(t('privacy.section8.rights', { returnObjects: true }) as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
        <p>{t('privacy.section8.exercise')}</p>

        <h2>{t('privacy.section9.title')}</h2>
        <p>{t('privacy.section9.content')}</p>

        <h2>{t('privacy.section10.title')}</h2>
        <p>{t('privacy.section10.content')}</p>
      </div>
    </>
  );
}
