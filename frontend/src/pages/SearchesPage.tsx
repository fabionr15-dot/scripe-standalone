import { useState, useEffect, useCallback, useRef } from 'react';
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
  StopCircle,
  Loader2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { api } from '@/lib/api';
import { LocalizedLink } from '@/i18n/LocalizedLink';

interface SearchItem {
  id: string;
  name: string;
  query: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  quality_tier: string;
  results_count: number;
  target_count: number;
  created_at: string;
  completed_at: string | null;
  current_run_id?: number;
}

interface LiveProgress {
  results_found: number;
  target_count: number;
  progress_percent: number;
}

export function SearchesPage() {
  const { t, i18n } = useTranslation('dashboard');
  const { t: tc } = useTranslation('common');
  const [searches, setSearches] = useState<SearchItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'completed' | 'running'>('all');
  const [liveProgress, setLiveProgress] = useState<Record<string, LiveProgress>>({});
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  const loadSearches = useCallback(async () => {
    try {
      const res = await api.get('/searches');
      setSearches(res.data.items || []);
    } catch (err) {
      console.error('Failed to load searches:', err);
      setSearches([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Poll for live progress of running searches
  const pollRunningSearches = useCallback(async () => {
    const runningSearches = searches.filter(s => s.status === 'running' && s.current_run_id);

    if (runningSearches.length === 0) return;

    const progressUpdates: Record<string, LiveProgress> = {};

    for (const search of runningSearches) {
      try {
        const res = await api.get(`/searches/${search.id}/runs/${search.current_run_id}`);
        progressUpdates[search.id] = {
          results_found: res.data.results_found || 0,
          target_count: res.data.target_count || search.target_count,
          progress_percent: res.data.progress_percent || 0,
        };

        // If search completed, refresh the list
        if (res.data.status === 'completed' || res.data.status === 'cancelled' || res.data.status === 'failed') {
          loadSearches();
        }
      } catch (err) {
        console.error(`Failed to poll search ${search.id}:`, err);
      }
    }

    setLiveProgress(prev => ({ ...prev, ...progressUpdates }));
  }, [searches, loadSearches]);

  useEffect(() => {
    loadSearches();
  }, [loadSearches]);

  // Set up polling for running searches
  useEffect(() => {
    const hasRunning = searches.some(s => s.status === 'running');

    if (hasRunning) {
      // Initial poll
      pollRunningSearches();

      // Poll every 2 seconds
      pollingRef.current = setInterval(pollRunningSearches, 2000);
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current);
      }
    };
  }, [searches, pollRunningSearches]);

  // Cancel search handler
  const handleCancelSearch = async (e: React.MouseEvent, searchId: string, runId: number) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      await api.post(`/searches/${searchId}/runs/${runId}/cancel`);
      // Refresh the list
      loadSearches();
    } catch (err) {
      console.error('Failed to cancel search:', err);
    }
  };

  const filteredSearches = searches.filter((s) => {
    if (filter === 'all') return true;
    if (filter === 'completed') return s.status === 'completed';
    if (filter === 'running') return s.status === 'running' || s.status === 'pending';
    return true;
  });

  const statusConfig: Record<string, { label: string; icon: any; color: string }> = {
    pending: { label: tc('status.pending'), icon: Clock, color: 'text-gray-500 bg-gray-100' },
    running: { label: tc('status.running'), icon: Loader2, color: 'text-blue-500 bg-blue-100' },
    completed: { label: tc('status.completed'), icon: CheckCircle, color: 'text-green-500 bg-green-100' },
    failed: { label: tc('status.failed'), icon: XCircle, color: 'text-red-500 bg-red-100' },
    cancelled: { label: tc('status.cancelled'), icon: StopCircle, color: 'text-orange-500 bg-orange-100' },
  };

  // Helper to get lead count display
  const getLeadCountDisplay = (search: SearchItem) => {
    if (search.status === 'running') {
      const progress = liveProgress[search.id];
      if (progress) {
        return `${progress.results_found}/${progress.target_count}`;
      }
      return `0/${search.target_count || '?'}`;
    }
    return search.results_count.toString();
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
                      <p className="font-medium">
                        {getLeadCountDisplay(search)} Leads
                      </p>
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
                      <StatusIcon className={`h-4 w-4 ${search.status === 'running' ? 'animate-spin' : ''}`} />
                      {status.label}
                    </div>

                    {/* Stop button for running searches */}
                    {search.status === 'running' && search.current_run_id && (
                      <button
                        onClick={(e) => handleCancelSearch(e, search.id, search.current_run_id!)}
                        className="p-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                        title={tc('actions.stop')}
                      >
                        <StopCircle className="h-5 w-5" />
                      </button>
                    )}

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
