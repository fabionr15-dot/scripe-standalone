import { useState } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  Search,
  Sparkles,
  Loader2,
  MapPin,
  Building2,
  Filter,
  AlertCircle,
  CreditCard,
  Clock,
  ChevronRight,
  Users,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/context/AuthContext';
import { useLocalizedNavigate } from '@/i18n/useLocalizedNavigate';
import { api } from '@/lib/api';

interface SearchEstimate {
  estimated_results: number;
  estimated_available: number;
  estimated_time_seconds: number;
  estimated_credits: number;
  sources: string[];
  quality_tier: string;
}

interface InterpretedQuery {
  categories: string[];
  locations: {
    cities: string[];
    regions: string[];
    country: string;
    countries: string[];  // All countries for multi-country search
  };
  keywords_include: string[];
  keywords_exclude: string[];
  confidence: number;
  // Advanced filters
  technologies: string[];
  company_size: string | null;
  employee_count_min: number | null;
  employee_count_max: number | null;
}

type SearchMode = 'ai' | 'manual';
type QualityTier = 'basic' | 'standard' | 'premium';

// Helper function to format location display
function formatLocationDisplay(
  locations: InterpretedQuery['locations'],
  t: (key: string) => string,
): string {
  const parts: string[] = [];

  // Use the countries array directly
  const countries: string[] = [...(locations.countries || [])];

  // Fallback: if countries array is empty, use the country field
  if (countries.length === 0 && locations.country) {
    countries.push(locations.country);
  }

  // Extract additional countries from regions (backward compatibility)
  const realRegions: string[] = [];
  for (const region of locations.regions || []) {
    if (region.startsWith('country:')) {
      const code = region.replace('country:', '');
      if (!countries.includes(code)) {
        countries.push(code);
      }
    } else {
      realRegions.push(region);
    }
  }

  if (locations.cities && locations.cities.length > 0) {
    parts.push(locations.cities.join(', '));
  }

  if (realRegions.length > 0) {
    parts.push(realRegions.join(', '));
  }

  if (countries.length > 0) {
    const countryNames = countries.map(code => t(`common:countries.${code}`) || code);
    if (parts.length > 0) {
      parts.push(`(${countryNames.join(', ')})`);
    } else {
      parts.push(countryNames.join(', '));
    }
  }

  return parts.join(' ') || t('common:notSpecified');
}

export function NewSearchPage() {
  const navigate = useLocalizedNavigate();
  const { user } = useAuth();
  const { t, i18n } = useTranslation('search');

  const [mode, setMode] = useState<SearchMode>('ai');
  const [query, setQuery] = useState('');
  const [interpretation, setInterpretation] = useState<InterpretedQuery | null>(null);
  const [estimate, setEstimate] = useState<SearchEstimate | null>(null);
  const [qualityTier, setQualityTier] = useState<QualityTier>('standard');

  const [targetCount, setTargetCount] = useState(100);
  const [isInterpreting, setIsInterpreting] = useState(false);
  const [isEstimating, setIsEstimating] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  const [manualData, setManualData] = useState({
    categories: '',
    city: '',
    region: '',
    country: 'IT',
    // Advanced filters
    technologies: '',
    companySize: '',
    employeeCountMin: '',
    employeeCountMax: '',
  });

  const qualityTiers = [
    {
      id: 'basic',
      name: t('newSearch.quality.basic'),
      description: t('newSearch.quality.basicDesc'),
      costMultiplier: 1,
      color: 'gray',
    },
    {
      id: 'standard',
      name: t('newSearch.quality.standard'),
      description: t('newSearch.quality.standardDesc'),
      costMultiplier: 2.4,
      color: 'blue',
    },
    {
      id: 'premium',
      name: t('newSearch.quality.premium'),
      description: t('newSearch.quality.premiumDesc'),
      costMultiplier: 5,
      color: 'purple',
    },
  ];

  async function handleInterpret() {
    if (!query.trim()) return;

    setIsInterpreting(true);
    setError('');

    try {
      const res = await api.post('/ai/interpret', { query });

      // Parse countries array - ensure it's always an array
      let countries = res.data.countries || [];
      if (!Array.isArray(countries)) {
        countries = countries ? [countries] : [];
      }
      // Fallback: if countries is empty, use country field
      if (countries.length === 0 && res.data.country) {
        countries = [res.data.country];
      }

      const mappedInterpretation: InterpretedQuery = {
        categories: res.data.categories || [],
        locations: {
          cities: res.data.cities || [],
          regions: res.data.regions || [],
          country: res.data.country || 'IT',
          countries: countries,
        },
        keywords_include: res.data.keywords_include || [],
        keywords_exclude: res.data.keywords_exclude || [],
        confidence: res.data.confidence || 0,
        // Advanced filters
        technologies: res.data.technologies || [],
        company_size: res.data.company_size || null,
        employee_count_min: res.data.employee_count_min || null,
        employee_count_max: res.data.employee_count_max || null,
      };
      setInterpretation(mappedInterpretation);
      await handleEstimate(mappedInterpretation);
    } catch (err: any) {
      setError(err.message || t('newSearch.errors.interpretFailed'));
    } finally {
      setIsInterpreting(false);
    }
  }

  async function handleEstimate(interpreted?: InterpretedQuery, overrideTier?: QualityTier) {
    setIsEstimating(true);

    try {
      const criteria = mode === 'ai' && interpreted
        ? {
            categories: interpreted.categories,
            city: interpreted.locations.cities[0],
            region: interpreted.locations.regions[0],
            country: interpreted.locations.country,
          }
        : {
            categories: manualData.categories.split(',').map((c) => c.trim()),
            city: manualData.city,
            region: manualData.region,
            country: manualData.country,
          };

      const allRegions: string[] = [];
      if (mode === 'ai' && interpreted) {
        allRegions.push(...(interpreted.locations.regions || []));
      } else if (criteria.region) {
        allRegions.push(criteria.region);
      }

      const tierToUse = overrideTier || qualityTier;

      const res = await api.post('/ai/estimate', {
        query: criteria.categories?.join(' ') || '',
        country: criteria.country || 'IT',
        regions: allRegions,
        cities: criteria.city ? [criteria.city] : [],
        target_count: targetCount,
        quality_tier: tierToUse,
      });
      setEstimate({
        estimated_results: res.data.estimated_results,
        estimated_available: res.data.estimated_available || res.data.estimated_results,
        estimated_time_seconds: res.data.estimated_time_seconds,
        estimated_credits: res.data.estimated_cost_credits,
        sources: [],
        quality_tier: res.data.tier,
      });
    } catch (err: any) {
      setError(err.message || t('newSearch.errors.estimateFailed'));
    } finally {
      setIsEstimating(false);
    }
  }

  async function handleCreate() {
    if (!estimate) return;

    const credits = user?.credits_balance ?? 0;
    if (credits < estimate.estimated_credits) {
      setError(t('newSearch.errors.insufficientCredits'));
      return;
    }

    setIsCreating(true);
    setError('');

    try {
      const criteria = mode === 'ai' && interpretation
        ? {
            categories: interpretation.categories,
            city: interpretation.locations.cities[0],
            region: interpretation.locations.regions[0],
            country: interpretation.locations.country,
            keywords_exclude: interpretation.keywords_exclude,
          }
        : {
            categories: manualData.categories.split(',').map((c) => c.trim()),
            city: manualData.city,
            region: manualData.region,
            country: manualData.country,
          };

      // Get all countries for multi-country search
      const countries = mode === 'ai' && interpretation?.locations.countries
        ? interpretation.locations.countries
        : [criteria.country || 'IT'];

      // Parse manual technologies into array
      const manualTechnologies = manualData.technologies
        ? manualData.technologies.split(',').map((t) => t.trim()).filter(Boolean)
        : undefined;

      const res = await api.post('/searches', {
        name: query || t('newSearch.defaultName', { date: new Date().toLocaleDateString(i18n.language) }),
        query: query || criteria.categories?.join(' ') || manualData.categories,
        country: criteria.country || 'IT',
        countries: countries,  // Pass all countries for multi-country search
        regions: criteria.region ? [criteria.region] : undefined,
        cities: criteria.city ? [criteria.city] : undefined,
        keywords_exclude: criteria.keywords_exclude || undefined,
        target_count: targetCount,
        quality_tier: qualityTier,
        // Advanced filters - support both AI and manual mode
        technologies: mode === 'ai'
          ? (interpretation?.technologies?.length ? interpretation.technologies : undefined)
          : (manualTechnologies?.length ? manualTechnologies : undefined),
        company_size: mode === 'ai'
          ? (interpretation?.company_size || undefined)
          : (manualData.companySize || undefined),
        employee_count_min: mode === 'ai'
          ? (interpretation?.employee_count_min || undefined)
          : (manualData.employeeCountMin ? parseInt(manualData.employeeCountMin) : undefined),
        employee_count_max: mode === 'ai'
          ? (interpretation?.employee_count_max || undefined)
          : (manualData.employeeCountMax ? parseInt(manualData.employeeCountMax) : undefined),
      });

      await api.post(`/searches/${res.data.id}/run`);
      navigate(`/searches/${res.data.id}`);
    } catch (err: any) {
      setError(err.message || t('newSearch.errors.createFailed'));
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <>
      <Helmet>
        <title>{t('newSearch.title')}</title>
      </Helmet>

      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">{t('newSearch.heading')}</h1>
          <p className="text-gray-600">
            {t('newSearch.subtitle')}
          </p>
        </div>

        {/* Mode Toggle */}
        <div className="flex bg-gray-100 rounded-lg p-1 w-fit">
          <button
            onClick={() => setMode('ai')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              mode === 'ai'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Sparkles className="h-4 w-4" />
            {t('newSearch.aiMode')}
          </button>
          <button
            onClick={() => setMode('manual')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
              mode === 'manual'
                ? 'bg-white shadow text-gray-900'
                : 'text-gray-600 hover:text-gray-900'
            }`}
          >
            <Filter className="h-4 w-4" />
            {t('newSearch.manualMode')}
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2 bg-red-50 text-red-600 p-4 rounded-lg">
            <AlertCircle className="h-5 w-5" />
            {error}
          </div>
        )}

        {/* AI Mode */}
        {mode === 'ai' && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                {t('newSearch.ai.label')}
              </label>
              <div className="relative">
                <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('newSearch.ai.placeholder')}
                  className="w-full pl-12 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 min-h-[100px]"
                />
              </div>
            </div>

            <button
              onClick={handleInterpret}
              disabled={!query.trim() || isInterpreting}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isInterpreting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              {t('newSearch.ai.interpret')}
            </button>

            {/* Interpretation Result */}
            {interpretation && (
              <div className="bg-blue-50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-blue-900">{t('newSearch.ai.interpreted')}</h3>
                  <span className="text-xs bg-blue-200 text-blue-800 px-2 py-1 rounded">
                    {t('newSearch.ai.confidence', { score: Math.round(interpretation.confidence * 100) })}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-blue-700 font-medium">{t('newSearch.ai.categories')}</p>
                    <p className="text-blue-900">{interpretation.categories.join(', ')}</p>
                  </div>
                  <div>
                    <p className="text-blue-700 font-medium">{t('newSearch.ai.location')}</p>
                    <p className="text-blue-900">
                      {formatLocationDisplay(interpretation.locations, t)}
                    </p>
                  </div>
                  {interpretation.keywords_exclude.length > 0 && (
                    <div className="col-span-2">
                      <p className="text-blue-700 font-medium">{t('newSearch.ai.exclude')}</p>
                      <p className="text-blue-900">{interpretation.keywords_exclude.join(', ')}</p>
                    </div>
                  )}
                  {/* Advanced filters */}
                  {interpretation.technologies && interpretation.technologies.length > 0 && (
                    <div>
                      <p className="text-blue-700 font-medium">{t('newSearch.ai.technologies')}</p>
                      <p className="text-blue-900">{interpretation.technologies.join(', ')}</p>
                    </div>
                  )}
                  {interpretation.company_size && (
                    <div>
                      <p className="text-blue-700 font-medium">{t('newSearch.ai.companySize')}</p>
                      <p className="text-blue-900">{t(`newSearch.ai.size.${interpretation.company_size}`)}</p>
                    </div>
                  )}
                  {(interpretation.employee_count_min || interpretation.employee_count_max) && (
                    <div className="col-span-2">
                      <p className="text-blue-700 font-medium">{t('newSearch.ai.employees')}</p>
                      <p className="text-blue-900">
                        {interpretation.employee_count_min && !interpretation.employee_count_max
                          ? `${interpretation.employee_count_min}+`
                          : interpretation.employee_count_min && interpretation.employee_count_max
                          ? `${interpretation.employee_count_min} - ${interpretation.employee_count_max}`
                          : `≤ ${interpretation.employee_count_max}`}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Manual Mode */}
        {mode === 'manual' && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-sm font-medium mb-1">
                  {t('newSearch.manual.categories')}
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={manualData.categories}
                    onChange={(e) => setManualData({ ...manualData, categories: e.target.value })}
                    placeholder={t('newSearch.manual.categoriesPlaceholder')}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.city')}</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={manualData.city}
                    onChange={(e) => setManualData({ ...manualData, city: e.target.value })}
                    placeholder={t('newSearch.manual.cityPlaceholder')}
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.region')}</label>
                <input
                  type="text"
                  value={manualData.region}
                  onChange={(e) => setManualData({ ...manualData, region: e.target.value })}
                  placeholder={t('newSearch.manual.regionPlaceholder')}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Country Selection */}
              <div>
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.country')}</label>
                <select
                  value={manualData.country}
                  onChange={(e) => setManualData({ ...manualData, country: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="IT">{t('common:countries.IT')}</option>
                  <option value="DE">{t('common:countries.DE')}</option>
                  <option value="AT">{t('common:countries.AT')}</option>
                  <option value="CH">{t('common:countries.CH')}</option>
                  <option value="FR">{t('common:countries.FR')}</option>
                  <option value="ES">{t('common:countries.ES')}</option>
                  <option value="NL">{t('common:countries.NL')}</option>
                  <option value="BE">{t('common:countries.BE')}</option>
                  <option value="PL">{t('common:countries.PL')}</option>
                </select>
              </div>

              {/* Technologies */}
              <div className="col-span-2">
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.technologies')}</label>
                <input
                  type="text"
                  value={manualData.technologies}
                  onChange={(e) => setManualData({ ...manualData, technologies: e.target.value })}
                  placeholder={t('newSearch.manual.technologiesPlaceholder')}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Company Size */}
              <div>
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.companySize')}</label>
                <select
                  value={manualData.companySize}
                  onChange={(e) => setManualData({ ...manualData, companySize: e.target.value })}
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">{t('newSearch.manual.anySize')}</option>
                  <option value="small">{t('newSearch.ai.size.small')}</option>
                  <option value="medium">{t('newSearch.ai.size.medium')}</option>
                  <option value="large">{t('newSearch.ai.size.large')}</option>
                  <option value="enterprise">{t('newSearch.ai.size.enterprise')}</option>
                </select>
              </div>

              {/* Employee Count */}
              <div>
                <label className="block text-sm font-medium mb-1">{t('newSearch.manual.employees')}</label>
                <div className="flex gap-2 items-center">
                  <input
                    type="number"
                    value={manualData.employeeCountMin}
                    onChange={(e) => setManualData({ ...manualData, employeeCountMin: e.target.value })}
                    placeholder={t('newSearch.manual.min')}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="0"
                  />
                  <span className="text-gray-400">-</span>
                  <input
                    type="number"
                    value={manualData.employeeCountMax}
                    onChange={(e) => setManualData({ ...manualData, employeeCountMax: e.target.value })}
                    placeholder={t('newSearch.manual.max')}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                    min="0"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={() => handleEstimate()}
              disabled={!manualData.categories || isEstimating}
              className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isEstimating ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Search className="h-4 w-4" />
              )}
              {t('newSearch.manual.estimate')}
            </button>
          </div>
        )}

        {/* Quality Tier Selection */}
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h3 className="font-medium">{t('newSearch.quality.title')}</h3>
          <div className="grid grid-cols-3 gap-3">
            {qualityTiers.map((tier) => (
              <button
                key={tier.id}
                onClick={() => {
                  const newTier = tier.id as QualityTier;
                  setQualityTier(newTier);
                  if (interpretation || manualData.categories) {
                    handleEstimate(interpretation || undefined, newTier);
                  }
                }}
                className={`p-4 rounded-lg border-2 text-left transition-all ${
                  qualityTier === tier.id
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <p className="font-medium">{tier.name}</p>
                <p className="text-xs text-gray-500 mt-1">{tier.description}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Target Count Selection */}
        {(interpretation || manualData.categories) && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium flex items-center gap-2">
                <Users className="h-5 w-5 text-gray-600" />
                {t('newSearch.leads.title')}
              </h3>
              <span className="text-2xl font-bold text-blue-600">
                {targetCount.toLocaleString(i18n.language)}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={10000}
              step={50}
              value={targetCount}
              onChange={(e) => {
                const val = parseInt(e.target.value);
                setTargetCount(val);
              }}
              onMouseUp={() => {
                if (interpretation || manualData.categories) {
                  handleEstimate(interpretation || undefined);
                }
              }}
              onTouchEnd={() => {
                if (interpretation || manualData.categories) {
                  handleEstimate(interpretation || undefined);
                }
              }}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400">
              <span>0</span>
              <span>2,500</span>
              <span>5,000</span>
              <span>7,500</span>
              <span>10,000</span>
            </div>
          </div>
        )}

        {/* Estimate & Create */}
        {estimate && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{t('newSearch.estimate.title')}</h3>
              <span className="text-sm text-gray-500">
                {t('newSearch.estimate.available', { count: estimate.estimated_available.toLocaleString(i18n.language) })}
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <Building2 className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">{estimate.estimated_results.toLocaleString(i18n.language)}</p>
                <p className="text-sm text-gray-500">{t('newSearch.estimate.leadsToCollect')}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <Clock className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">
                  {Math.ceil(estimate.estimated_time_seconds / 60)}
                </p>
                <p className="text-sm text-gray-500">{t('newSearch.estimate.minutes')}</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <CreditCard className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">{estimate.estimated_credits.toLocaleString(i18n.language)}</p>
                <p className="text-sm text-gray-500">{t('newSearch.estimate.credits')}</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <div>
                <p className="text-sm text-gray-600">
                  {t('newSearch.estimate.yourCredits', { count: user?.credits_balance ?? 0 })}
                </p>
                {(user?.credits_balance ?? 0) < estimate.estimated_credits && (
                  <p className="text-sm text-red-500">{t('newSearch.estimate.insufficientCredits')}</p>
                )}
              </div>
              <button
                onClick={handleCreate}
                disabled={isCreating || (user?.credits_balance ?? 0) < estimate.estimated_credits}
                className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreating ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <>
                    {t('newSearch.estimate.startSearch')}
                    <ChevronRight className="h-5 w-5" />
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
