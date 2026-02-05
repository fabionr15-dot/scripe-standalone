import { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  Search,
  Plus,
  Clock,
  CheckCircle,
  XCircle,
  ArrowRight,
  Filter,
  Calendar,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api } from '@/lib/api';
import { LocalizedLink } from '@/i18n/LocalizedLink';

interface SearchItem {
  id: string;
  name: string;
  query: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  quality_tier: string;
  results_count: number;
  created_at: string;
  completed_at: string | null;
}

export function SearchesPage() {
  const { t, i18n } = useTranslation('dashboard');
  const { t: tc } = useTranslation('common');
  const [searches, setSearches] = useState<SearchItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'completed' | 'running'>('all');

  useEffect(() => {
    loadSearches();
  }, []);

  async function loadSearches() {
    try {
      const res = await api.get('/searches');
      setSearches(res.data.items || []);
    } catch (err) {
      console.error('Failed to load searches:', err);
      setSearches([]);
    } finally {
      setIsLoading(false);
    }
  }

  const filteredSearches = searches.filter((s) => {
    if (filter === 'all') return true;
    if (filter === 'completed') return s.status === 'completed';
    if (filter === 'running') return s.status === 'running' || s.status === 'pending';
    return true;
  });

  const statusConfig = {
    pending: { label: tc('status.pending'), icon: Clock, color: 'text-gray-500 bg-gray-100' },
    running: { label: tc('status.running'), icon: Clock, color: 'text-blue-500 bg-blue-100' },
    completed: { label: tc('status.completed'), icon: CheckCircle, color: 'text-green-500 bg-green-100' },
    failed: { label: tc('status.failed'), icon: XCircle, color: 'text-red-500 bg-red-100' },
  };

  const tierLabels: Record<string, string> = {
    basic: 'Basic 40%',
    standard: 'Standard 60%',
    premium: 'Premium 80%',
  };

  return (
    <>
      <Helmet>
        <title>{t('searches.title')}</title>
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">{t('searches.heading')}</h1>
            <p className="text-gray-600">{t('searches.subtitle')}</p>
          </div>
          <LocalizedLink
            to="/searches/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t('searches.newSearch')}
          </LocalizedLink>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <div className="flex bg-gray-100 rounded-lg p-1">
            {[
              { value: 'all', label: t('searches.filters.all') },
              { value: 'running', label: t('searches.filters.running') },
              { value: 'completed', label: t('searches.filters.completed') },
            ].map((f) => (
              <button
                key={f.value}
                onClick={() => setFilter(f.value as any)}
                className={`px-4 py-1.5 rounded-md text-sm transition-colors ${
                  filter === f.value
                    ? 'bg-white shadow text-gray-900'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* List */}
        {isLoading ? (
          <div className="bg-white rounded-xl border p-12 text-center text-gray-500">
            {tc('actions.loading')}
          </div>
        ) : filteredSearches.length === 0 ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900">
              {filter === 'all' ? t('searches.noSearches') : t('searches.noResults')}
            </h3>
            <p className="text-gray-600 mt-1">
              {filter === 'all'
                ? t('searches.startFirst')
                : t('searches.changeFilters')}
            </p>
            {filter === 'all' && (
              <LocalizedLink
                to="/searches/new"
                className="inline-flex items-center gap-2 mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Plus className="h-4 w-4" />
                {t('searches.createSearch')}
              </LocalizedLink>
            )}
          </div>
        ) : (
          <div className="bg-white rounded-xl border divide-y">
            {filteredSearches.map((search) => {
              const status = statusConfig[search.status];
              const StatusIcon = status.icon;
              return (
                <LocalizedLink
                  key={search.id}
                  to={`/searches/${search.id}`}
                  className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                      <Search className="h-6 w-6 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{search.name}</h3>
                      <p className="text-sm text-gray-500 line-clamp-1">
                        {search.query}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="font-medium">{t('searches.leads', { count: search.results_count })}</p>
                      <p className="text-xs text-gray-500">
                        {tierLabels[search.quality_tier] || search.quality_tier}
                      </p>
                    </div>

                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Calendar className="h-4 w-4" />
                      {new Date(search.created_at).toLocaleDateString(i18n.language)}
                    </div>

                    <div
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-sm ${status.color}`}
                    >
                      <StatusIcon className="h-4 w-4" />
                      {status.label}
                    </div>

                    <ArrowRight className="h-5 w-5 text-gray-400" />
                  </div>
                </LocalizedLink>
              );
            })}
          </div>
        )}
      </div>
    </>
  );
}
