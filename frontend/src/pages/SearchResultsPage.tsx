import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  ArrowLeft,
  Building2,
  Phone,
  Mail,
  Globe,
  MapPin,
  Download,
  CheckCircle,
  Clock,
  XCircle,
  RefreshCw,
  Star,
  Filter,
  Search,
  Database,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api';

interface Lead {
  id: string;
  company_name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address_line: string | null;
  city: string | null;
  region: string | null;
  country: string | null;
  category: string | null;
  quality_score: number;
  confidence_score: number;
  phone_validated: boolean | null;
  email_validated: boolean | null;
  website_validated: boolean | null;
  alternative_phones: string[];
  sources_count: number;
}

interface RunStatus {
  id: number;
  status: string;
  progress_percent: number;
  current_source: string | null;
  results_found: number;
  target_count: number;
  is_active: boolean;
  started_at: string;
  ended_at: string | null;
}

interface SearchDetails {
  id: string;
  name: string;
  query: string;
  status: string;
  quality_tier: string;
  results_count: number;
  target_count: number;
  created_at: string;
  completed_at: string | null;
  company_count: number;
  latest_run: {
    id: number;
    status: string;
    progress_percent: number;
    found_count: number;
    started_at: string;
    ended_at: string | null;
  } | null;
}

// Source display names
const SOURCE_NAMES: Record<string, string> = {
  google_places: 'Google Places',
  google_serp: 'Google Search',
  pagine_gialle: 'Pagine Gialle',
  official_website: 'Siti Web',
  bing_places: 'Bing Places',
  validation: 'Validazione dati',
  enrichment: 'Arricchimento dati',
};

// Animated dots for loading text
function LoadingDots() {
  const [dots, setDots] = useState('');
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(d => d.length >= 3 ? '' : d + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);
  return <span className="inline-block w-6 text-left">{dots}</span>;
}

export function SearchResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [search, setSearch] = useState<SearchDetails | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [minQuality, setMinQuality] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Load search details
  const loadSearch = useCallback(async () => {
    try {
      const res = await api.get(`/searches/${id}`);
      setSearch(res.data);
      return res.data;
    } catch (err) {
      console.error('Failed to load search:', err);
      return null;
    }
  }, [id]);

  // Load leads
  const loadLeads = useCallback(async () => {
    try {
      const res = await api.get(`/searches/${id}/companies`);
      setLeads(res.data.items || []);
    } catch (err) {
      console.error('Failed to load leads:', err);
    }
  }, [id]);

  // Poll run status
  const pollRunStatus = useCallback(async (searchId: string, runId: number) => {
    try {
      const res = await api.get(`/searches/${searchId}/runs/${runId}`);
      setRunStatus(res.data);

      // Also load partial leads if any found
      if (res.data.results_found > 0) {
        loadLeads();
      }

      // If completed or failed, stop polling
      if (res.data.status === 'completed' || res.data.status === 'failed') {
        if (pollingRef.current) {
          clearInterval(pollingRef.current);
          pollingRef.current = null;
        }
        if (timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
        }
        // Reload search data and leads
        loadSearch();
        loadLeads();
      }
    } catch (err) {
      console.error('Failed to poll run status:', err);
    }
  }, [loadSearch, loadLeads]);

  // Initial load
  useEffect(() => {
    async function init() {
      const data = await loadSearch();
      if (!data) {
        setIsLoading(false);
        return;
      }

      if (data.latest_run && (data.latest_run.status === 'running' || data.status === 'running')) {
        // Start polling — append Z if no timezone info (backend sends UTC without Z)
        const startedAt = data.latest_run.started_at.endsWith('Z') || data.latest_run.started_at.includes('+')
          ? data.latest_run.started_at
          : data.latest_run.started_at + 'Z';
        startTimeRef.current = new Date(startedAt).getTime();
        setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));

        // Poll every 2 seconds
        pollingRef.current = setInterval(() => {
          pollRunStatus(data.id, data.latest_run!.id);
        }, 2000);

        // Timer every second
        timerRef.current = setInterval(() => {
          setElapsedSeconds(Math.floor((Date.now() - startTimeRef.current) / 1000));
        }, 1000);

        // Initial poll
        pollRunStatus(data.id, data.latest_run.id);
      } else if (data.status === 'completed') {
        loadLeads();
      }

      setIsLoading(false);
    }

    init();

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [id]);

  async function handleExport(format: 'csv' | 'excel') {
    try {
      const res = await api.post(
        `/searches/${id}/export`,
        { format, min_quality: minQuality / 100 },
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `leads-${id}.${format === 'excel' ? 'xlsx' : 'csv'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Export failed:', err);
    }
  }

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${seconds}s`;
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  }

  const filteredLeads = leads.filter((l) => (l.quality_score || 0) >= minQuality);
  const isRunning = search?.status === 'running' || runStatus?.is_active;
  const isCompleted = search?.status === 'completed' && !runStatus?.is_active;
  const isFailed = search?.status === 'failed';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!search) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Ricerca non trovata</h2>
        <Link to="/searches" className="text-blue-600 hover:underline mt-2 inline-block">
          Torna alle ricerche
        </Link>
      </div>
    );
  }

  const progressPercent = runStatus?.progress_percent ?? search.latest_run?.progress_percent ?? 0;
  const resultsFound = runStatus?.results_found ?? search.company_count ?? 0;
  const targetCount = runStatus?.target_count ?? search.target_count ?? 0;

  return (
    <>
      <Helmet>
        <title>{search.name} - Scripe</title>
      </Helmet>

      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              to="/searches"
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="h-5 w-5" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold">{search.name}</h1>
              <p className="text-gray-600">{search.query}</p>
            </div>
          </div>

          <div className={`flex items-center gap-2 ${
            isRunning ? 'text-blue-500' :
            isCompleted ? 'text-green-500' :
            isFailed ? 'text-red-500' : 'text-gray-500'
          }`}>
            {isRunning && <RefreshCw className="h-5 w-5 animate-spin" />}
            {isCompleted && <CheckCircle className="h-5 w-5" />}
            {isFailed && <XCircle className="h-5 w-5" />}
            <span className="font-medium">
              {isRunning ? 'In corso' :
               isCompleted ? 'Completata' :
               isFailed ? 'Fallita' : 'In attesa'}
            </span>
          </div>
        </div>

        {/* === RUNNING STATE === */}
        {isRunning && (
          <div className="bg-white rounded-xl border overflow-hidden">
            {/* Progress Header */}
            <div className="p-6 space-y-5">
              {/* Main progress bar */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Search className="h-5 w-5 text-blue-600" />
                    <span className="font-medium text-gray-900">Ricerca in corso</span>
                  </div>
                  <span className="text-sm font-medium text-blue-600">
                    {progressPercent}%
                  </span>
                </div>
                <div className="w-full bg-gray-100 rounded-full h-3">
                  <div
                    className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-500 relative overflow-hidden"
                    style={{ width: `${Math.max(progressPercent, 3)}%` }}
                  >
                    <div className="absolute inset-0 bg-white/20 animate-pulse" />
                  </div>
                </div>
              </div>

              {/* Status cards */}
              <div className="grid grid-cols-3 gap-4">
                {/* Found */}
                <div className="bg-blue-50 rounded-lg p-4 text-center">
                  <Building2 className="h-5 w-5 mx-auto text-blue-600 mb-1" />
                  <p className="text-2xl font-bold text-blue-700">{resultsFound}</p>
                  <p className="text-xs text-blue-600">Lead trovati</p>
                </div>

                {/* Target */}
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <Database className="h-5 w-5 mx-auto text-gray-500 mb-1" />
                  <p className="text-2xl font-bold text-gray-700">{targetCount}</p>
                  <p className="text-xs text-gray-500">Obiettivo</p>
                </div>

                {/* Time */}
                <div className="bg-gray-50 rounded-lg p-4 text-center">
                  <Clock className="h-5 w-5 mx-auto text-gray-500 mb-1" />
                  <p className="text-2xl font-bold text-gray-700">
                    {formatDuration(elapsedSeconds)}
                  </p>
                  <p className="text-xs text-gray-500">Tempo trascorso</p>
                </div>
              </div>

              {/* Current source */}
              {runStatus?.current_source && (
                <div className="flex items-center gap-2 text-sm text-gray-600 bg-gray-50 rounded-lg px-4 py-3">
                  <Zap className="h-4 w-4 text-yellow-500 animate-pulse" />
                  <span>
                    Interrogando <strong>{SOURCE_NAMES[runStatus.current_source] || runStatus.current_source}</strong>
                    <LoadingDots />
                  </span>
                </div>
              )}
            </div>

            {/* Live results preview */}
            {leads.length > 0 && (
              <div className="border-t">
                <div className="px-6 py-3 bg-gray-50 flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    Risultati parziali ({leads.length})
                  </span>
                  <span className="text-xs text-gray-500">Aggiornamento in tempo reale</span>
                </div>
                <div className="divide-y max-h-[300px] overflow-y-auto">
                  {leads.slice(0, 10).map((lead) => (
                    <div key={lead.id} className="px-6 py-3 flex items-center gap-3">
                      <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                        <Building2 className="h-4 w-4 text-blue-600" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="font-medium text-sm truncate">{lead.company_name}</p>
                        <p className="text-xs text-gray-500 truncate">
                          {[lead.city, lead.region].filter(Boolean).join(', ')}
                        </p>
                      </div>
                      {lead.phone && (
                        <span className="text-xs text-gray-400 hidden sm:inline">
                          {lead.phone}
                        </span>
                      )}
                    </div>
                  ))}
                  {leads.length > 10 && (
                    <div className="px-6 py-2 text-center text-xs text-gray-400">
                      + {leads.length - 10} altri risultati...
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* === COMPLETED STATE === */}
        {isCompleted && (
          <>
            {/* Filters & Export */}
            <div className="flex items-center justify-between bg-white rounded-xl border p-4">
              <div className="flex items-center gap-4">
                <Filter className="h-5 w-5 text-gray-500" />
                <div className="flex items-center gap-2">
                  <label className="text-sm text-gray-600">Qualità minima:</label>
                  <select
                    value={minQuality}
                    onChange={(e) => setMinQuality(Number(e.target.value))}
                    className="border rounded px-2 py-1 text-sm"
                  >
                    <option value={0}>Tutti</option>
                    <option value={40}>40%+</option>
                    <option value={60}>60%+</option>
                    <option value={80}>80%+</option>
                  </select>
                </div>
                <span className="text-sm text-gray-500">
                  {filteredLeads.length} di {leads.length} lead
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleExport('csv')}
                  className="flex items-center gap-2 px-3 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  CSV
                </button>
                <button
                  onClick={() => handleExport('excel')}
                  className="flex items-center gap-2 px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  Excel
                </button>
              </div>
            </div>

            {/* Lead List */}
            {filteredLeads.length === 0 ? (
              <div className="bg-white rounded-xl border p-12 text-center">
                <Building2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="font-semibold">Nessun lead trovato</h3>
                <p className="text-gray-600 mt-1">
                  Prova ad abbassare il filtro qualità
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-xl border divide-y">
                {filteredLeads.map((lead) => (
                  <div key={lead.id} className="p-4 hover:bg-gray-50">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0">
                          <Building2 className="h-6 w-6 text-blue-600" />
                        </div>
                        <div>
                          <h3 className="font-semibold">{lead.company_name}</h3>
                          {lead.category && (
                            <p className="text-sm text-gray-500">{lead.category}</p>
                          )}
                          <div className="flex flex-wrap gap-3 mt-2 text-sm">
                            {lead.phone && (
                              <div className="flex items-center gap-1">
                                <a
                                  href={`tel:${lead.phone}`}
                                  className="flex items-center gap-1 text-gray-600 hover:text-blue-600"
                                >
                                  <Phone className="h-4 w-4" />
                                  {lead.phone}
                                </a>
                                {lead.alternative_phones && lead.alternative_phones.length > 0 && (
                                  <span
                                    className="text-[10px] bg-orange-100 text-orange-700 px-1.5 py-0.5 rounded-full font-medium cursor-help"
                                    title={`Numeri alternativi:\n${lead.alternative_phones.join('\n')}`}
                                  >
                                    +{lead.alternative_phones.length}
                                  </span>
                                )}
                              </div>
                            )}
                            {/* Show alternative phones if no primary phone */}
                            {!lead.phone && lead.alternative_phones && lead.alternative_phones.length > 0 && (
                              <a
                                href={`tel:${lead.alternative_phones[0]}`}
                                className="flex items-center gap-1 text-gray-600 hover:text-blue-600"
                              >
                                <Phone className="h-4 w-4" />
                                {lead.alternative_phones[0]}
                              </a>
                            )}
                            {lead.email && (
                              <a
                                href={`mailto:${lead.email}`}
                                className="flex items-center gap-1 text-gray-600 hover:text-blue-600"
                              >
                                <Mail className="h-4 w-4" />
                                {lead.email}
                              </a>
                            )}
                            {lead.website && (
                              <a
                                href={lead.website}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-gray-600 hover:text-blue-600"
                              >
                                <Globe className="h-4 w-4" />
                                Sito web
                              </a>
                            )}
                            {(lead.address_line || lead.city) && (
                              <span className="flex items-center gap-1 text-gray-600">
                                <MapPin className="h-4 w-4" />
                                {[lead.city, lead.region, lead.country].filter(Boolean).join(', ')}
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3">
                        <div className="text-right">
                          <div className="flex items-center gap-1">
                            <Star
                              className={`h-4 w-4 ${
                                (lead.quality_score || 0) >= 80
                                  ? 'text-yellow-500 fill-yellow-500'
                                  : (lead.quality_score || 0) >= 60
                                  ? 'text-yellow-500'
                                  : 'text-gray-300'
                              }`}
                            />
                            <span className="font-medium">
                              {lead.quality_score || 0}%
                            </span>
                          </div>
                          {lead.phone_validated && (
                            <span className="text-[10px] text-green-600">Tel. verificato</span>
                          )}
                          {lead.sources_count > 1 && (
                            <span className="text-[10px] text-blue-600">{lead.sources_count} fonti</span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* === FAILED STATE === */}
        {isFailed && (
          <div className="bg-red-50 rounded-xl p-6 text-center">
            <XCircle className="h-12 w-12 text-red-400 mx-auto mb-4" />
            <h3 className="font-semibold text-red-800">Ricerca fallita</h3>
            <p className="text-red-600 mt-1">
              Si è verificato un errore durante l'elaborazione
            </p>
            <Link
              to="/searches/new"
              className="inline-block mt-4 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Riprova
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
