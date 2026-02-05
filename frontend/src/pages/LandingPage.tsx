import { Helmet } from 'react-helmet-async';
import {
  Search,
  Globe,
  Phone,
  CheckCircle,
  ArrowRight,
  Zap,
  Shield,
  Target,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { LocalizedLink } from '@/i18n/LocalizedLink';

export function LandingPage() {
  const { t } = useTranslation('landing');

  return (
    <>
      <Helmet>
        <title>{t('meta.title')}</title>
        <meta name="description" content={t('meta.description')} />
      </Helmet>

      {/* Hero Section */}
      <section className="py-20 px-4">
        <div className="container mx-auto text-center max-w-4xl">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">
            {t('hero.title')}
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-8 max-w-2xl mx-auto">
            {t('hero.subtitle')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <LocalizedLink
              to="/register"
              className="inline-flex items-center justify-center gap-2 bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
            >
              {t('hero.cta')}
              <ArrowRight className="h-5 w-5" />
            </LocalizedLink>
            <LocalizedLink
              to="/pricing"
              className="inline-flex items-center justify-center gap-2 border-2 border-gray-300 px-8 py-4 rounded-lg text-lg font-semibold hover:border-blue-600 hover:text-blue-600 transition-colors"
            >
              {t('hero.viewPricing')}
            </LocalizedLink>
          </div>
          <p className="mt-4 text-sm text-gray-500">
            {t('hero.freeCredits')}
          </p>
        </div>
      </section>

      {/* Features Grid */}
      <section className="py-20 bg-white dark:bg-gray-800">
        <div className="container mx-auto px-4">
          <h2 className="text-3xl font-bold text-center mb-12">
            {t('features.title')}
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={Search}
              title={t('features.aiSearch.title')}
              description={t('features.aiSearch.description')}
            />
            <FeatureCard
              icon={Globe}
              title={t('features.multiSource.title')}
              description={t('features.multiSource.description')}
            />
            <FeatureCard
              icon={Phone}
              title={t('features.verifiedData.title')}
              description={t('features.verifiedData.description')}
            />
            <FeatureCard
              icon={Target}
              title={t('features.targeting.title')}
              description={t('features.targeting.description')}
            />
            <FeatureCard
              icon={Zap}
              title={t('features.fastResults.title')}
              description={t('features.fastResults.description')}
            />
            <FeatureCard
              icon={Shield}
              title={t('features.gdpr.title')}
              description={t('features.gdpr.description')}
            />
          </div>
        </div>
      </section>

      {/* Quality Tiers */}
      <section className="py-20 px-4">
        <div className="container mx-auto">
          <h2 className="text-3xl font-bold text-center mb-4">
            {t('tiers.title')}
          </h2>
          <p className="text-center text-gray-600 mb-12 max-w-2xl mx-auto">
            {t('tiers.subtitle')}
          </p>
          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            <TierCard
              t={t}
              name="Basic"
              minScore="40%"
              price="€0.07"
              features={t('tiers.basic.features', { returnObjects: true }) as string[]}
            />
            <TierCard
              t={t}
              name="Standard"
              minScore="60%"
              price="€0.16"
              featured
              features={t('tiers.standard.features', { returnObjects: true }) as string[]}
            />
            <TierCard
              t={t}
              name="Premium"
              minScore="80%"
              price="€0.33"
              features={t('tiers.premium.features', { returnObjects: true }) as string[]}
            />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-blue-600">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            {t('cta.title')}
          </h2>
          <p className="text-blue-100 mb-8 max-w-xl mx-auto">
            {t('cta.subtitle')}
          </p>
          <LocalizedLink
            to="/register"
            className="inline-flex items-center justify-center gap-2 bg-white text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-50 transition-colors"
          >
            {t('cta.button')}
            <ArrowRight className="h-5 w-5" />
          </LocalizedLink>
        </div>
      </section>
    </>
  );
}

function FeatureCard({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <div className="p-6 rounded-xl bg-gray-50 dark:bg-gray-700">
      <div className="h-12 w-12 rounded-lg bg-blue-100 dark:bg-blue-900 flex items-center justify-center mb-4">
        <Icon className="h-6 w-6 text-blue-600" />
      </div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-gray-600 dark:text-gray-400">{description}</p>
    </div>
  );
}

function TierCard({
  t,
  name,
  minScore,
  price,
  features,
  featured,
}: {
  t: (key: string, options?: any) => string;
  name: string;
  minScore: string;
  price: string;
  features: string[];
  featured?: boolean;
}) {
  return (
    <div
      className={`p-6 rounded-xl border-2 ${
        featured
          ? 'border-blue-600 bg-blue-50 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-700'
      }`}
    >
      {featured && (
        <span className="bg-blue-600 text-white text-xs font-semibold px-3 py-1 rounded-full">
          {t('tiers.mostPopular')}
        </span>
      )}
      <h3 className="text-2xl font-bold mt-4">{name}</h3>
      <p className="text-gray-500 mb-4">{t('tiers.minQuality', { score: minScore })}</p>
      <p className="text-4xl font-bold mb-6">
        {price}
        <span className="text-lg font-normal text-gray-500">{t('tiers.perLead')}</span>
      </p>
      <ul className="space-y-3">
        {features.map((feature, i) => (
          <li key={i} className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500 flex-shrink-0" />
            <span className="text-gray-600 dark:text-gray-400">{feature}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
