import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';

interface SearchEstimate {
  estimated_results: number;
  estimated_available: number;  // Total in market
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
    countries?: string[]; // Per ricerca multi-paese
  };
  keywords_include: string[];
  keywords_exclude: string[];
  confidence: number;
}

type SearchMode = 'ai' | 'manual';
type QualityTier = 'basic' | 'standard' | 'premium';

// Country code to name mapping
const COUNTRY_NAMES: Record<string, string> = {
  DE: 'Germania',
  AT: 'Austria',
  CH: 'Svizzera',
  IT: 'Italia',
  FR: 'Francia',
  ES: 'Spagna',
  NL: 'Paesi Bassi',
  BE: 'Belgio',
  PL: 'Polonia',
  CZ: 'Repubblica Ceca',
  PT: 'Portogallo',
  GB: 'Regno Unito',
};

// Helper function to format location display
function formatLocationDisplay(locations: InterpretedQuery['locations']): string {
  const parts: string[] = [];

  // Extract all countries (primary + additional from regions)
  const countries: string[] = [];
  if (locations.country) {
    countries.push(locations.country);
  }

  // Extract additional countries from regions (format: "country:XX")
  const realRegions: string[] = [];
  for (const region of locations.regions) {
    if (region.startsWith('country:')) {
      const code = region.replace('country:', '');
      if (!countries.includes(code)) {
        countries.push(code);
      }
    } else {
      realRegions.push(region);
    }
  }

  // Add cities if any
  if (locations.cities.length > 0) {
    parts.push(locations.cities.join(', '));
  }

  // Add regions if any
  if (realRegions.length > 0) {
    parts.push(realRegions.join(', '));
  }

  // Add countries
  if (countries.length > 0) {
    const countryNames = countries.map(code => COUNTRY_NAMES[code] || code);
    if (parts.length > 0) {
      parts.push(`(${countryNames.join(', ')})`);
    } else {
      parts.push(countryNames.join(', '));
    }
  }

  return parts.join(' ') || 'Non specificato';
}

export function NewSearchPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [mode, setMode] = useState<SearchMode>('ai');
  const [query, setQuery] = useState('');
  const [interpretation, setInterpretation] = useState<InterpretedQuery | null>(null);
  const [estimate, setEstimate] = useState<SearchEstimate | null>(null);
  const [qualityTier, setQualityTier] = useState<QualityTier>('standard');

  const [isInterpreting, setIsInterpreting] = useState(false);
  const [isEstimating, setIsEstimating] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  // Manual mode fields
  const [manualData, setManualData] = useState({
    categories: '',
    city: '',
    region: '',
    country: 'IT',
  });

  const qualityTiers = [
    {
      id: 'basic',
      name: 'Basic 40%',
      description: 'Verifica formato, 2 fonti',
      costMultiplier: 1,
      color: 'gray',
    },
    {
      id: 'standard',
      name: 'Standard 60%',
      description: 'Verifica MX, enrichment sito, 4 fonti',
      costMultiplier: 2,
      color: 'blue',
    },
    {
      id: 'premium',
      name: 'Premium 80%',
      description: 'Verifica carrier, SMTP, tutte le fonti',
      costMultiplier: 4,
      color: 'purple',
    },
  ];

  async function handleInterpret() {
    if (!query.trim()) return;

    setIsInterpreting(true);
    setError('');

    try {
      const res = await api.post('/ai/interpret', { query });
      // Map response to expected format
      const mappedInterpretation = {
        categories: res.data.categories || [],
        locations: {
          cities: res.data.cities || [],
          regions: res.data.regions || [],
          country: res.data.country || 'IT',
        },
        keywords_include: res.data.keywords_include || [],
        keywords_exclude: res.data.keywords_exclude || [],
        confidence: res.data.confidence || 0,
      };
      setInterpretation(mappedInterpretation);

      // Auto-estimate
      await handleEstimate(mappedInterpretation);
    } catch (err: any) {
      setError(err.message || "Errore nell'interpretazione della query");
    } finally {
      setIsInterpreting(false);
    }
  }

  async function handleEstimate(interpreted?: InterpretedQuery) {
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

      const res = await api.post('/ai/estimate', {
        query: criteria.categories?.join(' ') || '',
        country: criteria.country || 'IT',
        regions: criteria.region ? [criteria.region] : [],
        cities: criteria.city ? [criteria.city] : [],
        target_count: 100,
        quality_tier: qualityTier,
      });
      // Map response to expected format
      setEstimate({
        estimated_results: res.data.estimated_results,
        estimated_available: res.data.estimated_available || res.data.estimated_results,
        estimated_time_seconds: res.data.estimated_time_seconds,
        estimated_credits: res.data.estimated_cost_credits,
        sources: [],
        quality_tier: res.data.tier,
      });
    } catch (err: any) {
      setError(err.message || 'Errore nella stima');
    } finally {
      setIsEstimating(false);
    }
  }

  async function handleCreate() {
    if (!estimate) return;

    const credits = user?.credits_balance ?? 0;
    if (credits < estimate.estimated_credits) {
      setError('Crediti insufficienti');
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

      const res = await api.post('/searches', {
        name: query || `Ricerca ${new Date().toLocaleDateString('it-IT')}`,
        query: query || manualData.categories,
        criteria,
        quality_tier: qualityTier,
      });

      // Start the search
      await api.post(`/searches/${res.data.id}/run`);

      navigate(`/searches/${res.data.id}`);
    } catch (err: any) {
      setError(err.message || 'Errore nella creazione della ricerca');
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <>
      <Helmet>
        <title>Nuova ricerca - Scripe</title>
      </Helmet>

      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Nuova ricerca</h1>
          <p className="text-gray-600">
            Trova lead B2B di qualità con l'intelligenza artificiale
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
            Ricerca AI
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
            Ricerca manuale
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
                Descrivi cosa stai cercando
              </label>
              <div className="relative">
                <Sparkles className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                <textarea
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder='Es: "Cerco ristoranti a Milano, no fast food"'
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
              Interpreta con AI
            </button>

            {/* Interpretation Result */}
            {interpretation && (
              <div className="bg-blue-50 rounded-lg p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-blue-900">Query interpretata</h3>
                  <span className="text-xs bg-blue-200 text-blue-800 px-2 py-1 rounded">
                    Confidenza: {Math.round(interpretation.confidence * 100)}%
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-blue-700 font-medium">Categorie</p>
                    <p className="text-blue-900">{interpretation.categories.join(', ')}</p>
                  </div>
                  <div>
                    <p className="text-blue-700 font-medium">Località</p>
                    <p className="text-blue-900">
                      {formatLocationDisplay(interpretation.locations)}
                    </p>
                  </div>
                  {interpretation.keywords_exclude.length > 0 && (
                    <div className="col-span-2">
                      <p className="text-blue-700 font-medium">Escludi</p>
                      <p className="text-blue-900">{interpretation.keywords_exclude.join(', ')}</p>
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
                  Categorie (separate da virgola)
                </label>
                <div className="relative">
                  <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={manualData.categories}
                    onChange={(e) => setManualData({ ...manualData, categories: e.target.value })}
                    placeholder="Es: ristorante, pizzeria, trattoria"
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Città</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={manualData.city}
                    onChange={(e) => setManualData({ ...manualData, city: e.target.value })}
                    placeholder="Es: Milano"
                    className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Regione</label>
                <input
                  type="text"
                  value={manualData.region}
                  onChange={(e) => setManualData({ ...manualData, region: e.target.value })}
                  placeholder="Es: Lombardia"
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
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
              Calcola stima
            </button>
          </div>
        )}

        {/* Quality Tier Selection */}
        <div className="bg-white rounded-xl border p-6 space-y-4">
          <h3 className="font-medium">Livello di qualità</h3>
          <div className="grid grid-cols-3 gap-3">
            {qualityTiers.map((tier) => (
              <button
                key={tier.id}
                onClick={() => {
                  setQualityTier(tier.id as QualityTier);
                  if (interpretation || manualData.categories) {
                    handleEstimate(interpretation || undefined);
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

        {/* Estimate & Create */}
        {estimate && (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">Stima della ricerca</h3>
              <span className="text-sm text-gray-500">
                ~{estimate.estimated_available.toLocaleString('it-IT')} disponibili sul mercato
              </span>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <Building2 className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">{estimate.estimated_results.toLocaleString('it-IT')}</p>
                <p className="text-sm text-gray-500">Lead da raccogliere</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <Clock className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">
                  {Math.ceil(estimate.estimated_time_seconds / 60)}
                </p>
                <p className="text-sm text-gray-500">Minuti</p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 text-center">
                <CreditCard className="h-6 w-6 mx-auto text-gray-600 mb-2" />
                <p className="text-2xl font-bold">{estimate.estimated_credits.toLocaleString('it-IT')}</p>
                <p className="text-sm text-gray-500">Crediti</p>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t">
              <div>
                <p className="text-sm text-gray-600">
                  I tuoi crediti: <span className="font-medium">{user?.credits_balance ?? 0}</span>
                </p>
                {(user?.credits_balance ?? 0) < estimate.estimated_credits && (
                  <p className="text-sm text-red-500">Crediti insufficienti</p>
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
                    Avvia ricerca
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
