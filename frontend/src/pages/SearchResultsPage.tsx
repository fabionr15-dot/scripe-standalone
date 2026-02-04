import { useState, useEffect, useRef } from 'react';
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
} from 'lucide-react';
import { api } from '@/lib/api';

interface Lead {
  id: string;
  company_name: string;
  phone: string | null;
  email: string | null;
  website: string | null;
  address: string | null;
  city: string | null;
  category: string | null;
  quality_score: number;
  source: string;
  validated: boolean;
}

interface SearchDetails {
  id: string;
  name: string;
  query: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  quality_tier: string;
  results_count: number;
  created_at: string;
  completed_at: string | null;
  progress?: {
    current: number;
    total: number;
    stage: string;
  };
}

export function SearchResultsPage() {
  const { id } = useParams<{ id: string }>();
  const [search, setSearch] = useState<SearchDetails | null>(null);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [minQuality, setMinQuality] = useState(0);

  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    loadSearch();
    return () => {
      eventSourceRef.current?.close();
    };
  }, [id]);

  async function loadSearch() {
    try {
      const res = await api.get(`/searches/${id}`);
      setSearch(res.data);

      if (res.data.status === 'running') {
        subscribeToProgress();
      } else if (res.data.status === 'completed') {
        loadLeads();
      }
    } catch (err) {
      console.error('Failed to load search:', err);
    } finally {
      setIsLoading(false);
    }
  }

  async function loadLeads() {
    try {
      const res = await api.get(`/searches/${id}/companies`);
      setLeads(res.data.items || []);
    } catch (err) {
      console.error('Failed to load leads:', err);
    }
  }

  function subscribeToProgress() {
    const token = localStorage.getItem('scripe_token');
    const url = `${import.meta.env.VITE_API_URL || ''}/api/v1/runs/${id}/stream`;

    eventSourceRef.current = new EventSource(url);

    eventSourceRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === 'progress') {
        setSearch((prev) =>
          prev
            ? {
                ...prev,
                progress: {
                  current: data.current,
                  total: data.total,
                  stage: data.stage,
                },
              }
            : null
        );
      } else if (data.type === 'completed') {
        setSearch((prev) => (prev ? { ...prev, status: 'completed' } : null));
        loadLeads();
        eventSourceRef.current?.close();
      } else if (data.type === 'error') {
        setSearch((prev) => (prev ? { ...prev, status: 'failed' } : null));
        eventSourceRef.current?.close();
      }
    };

    eventSourceRef.current.onerror = () => {
      eventSourceRef.current?.close();
    };
  }

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

  const filteredLeads = leads.filter((l) => l.quality_score * 100 >= minQuality);

  const statusConfig = {
    pending: { label: 'In attesa', icon: Clock, color: 'text-gray-500' },
    running: { label: 'In corso', icon: RefreshCw, color: 'text-blue-500' },
    completed: { label: 'Completata', icon: CheckCircle, color: 'text-green-500' },
    failed: { label: 'Fallita', icon: XCircle, color: 'text-red-500' },
  };

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

  const status = statusConfig[search.status];
  const StatusIcon = status.icon;

  return (
    <>
      <Helmet>
        <title>{search.name} - Scripe</title>
      </Helmet>

      <div className="space-y-6">
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

          <div className={`flex items-center gap-2 ${status.color}`}>
            <StatusIcon
              className={`h-5 w-5 ${search.status === 'running' ? 'animate-spin' : ''}`}
            />
            <span className="font-medium">{status.label}</span>
          </div>
        </div>

        {/* Progress (if running) */}
        {search.status === 'running' && search.progress && (
          <div className="bg-blue-50 rounded-xl p-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-blue-700 font-medium">{search.progress.stage}</span>
              <span className="text-blue-600 text-sm">
                {search.progress.current} / {search.progress.total}
              </span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{
                  width: `${(search.progress.current / search.progress.total) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Results */}
        {search.status === 'completed' && (
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
                              <a
                                href={`tel:${lead.phone}`}
                                className="flex items-center gap-1 text-gray-600 hover:text-blue-600"
                              >
                                <Phone className="h-4 w-4" />
                                {lead.phone}
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
                            {(lead.address || lead.city) && (
                              <span className="flex items-center gap-1 text-gray-600">
                                <MapPin className="h-4 w-4" />
                                {[lead.address, lead.city].filter(Boolean).join(', ')}
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
                                lead.quality_score >= 0.8
                                  ? 'text-yellow-500 fill-yellow-500'
                                  : lead.quality_score >= 0.6
                                  ? 'text-yellow-500'
                                  : 'text-gray-300'
                              }`}
                            />
                            <span className="font-medium">
                              {Math.round(lead.quality_score * 100)}%
                            </span>
                          </div>
                          <p className="text-xs text-gray-500">{lead.source}</p>
                        </div>
                        {lead.validated && (
                          <div className="p-1 bg-green-100 rounded">
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {/* Failed state */}
        {search.status === 'failed' && (
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
