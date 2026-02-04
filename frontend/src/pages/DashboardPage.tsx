import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  Search,
  TrendingUp,
  CreditCard,
  Clock,
  ArrowRight,
  Plus,
  Building2,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';

interface DashboardStats {
  totalSearches: number;
  totalLeads: number;
  creditsUsed: number;
  avgQuality: number;
}

interface RecentSearch {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  resultsCount: number;
  createdAt: string;
}

export function DashboardPage() {
  const { user } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    loadDashboard();
  }, []);

  async function loadDashboard() {
    try {
      const [statsRes, searchesRes] = await Promise.all([
        api.get('/dashboard/stats'),
        api.get('/searches?limit=5'),
      ]);
      setStats(statsRes.data);
      setRecentSearches(searchesRes.data.items || []);
    } catch (err) {
      console.error('Failed to load dashboard:', err);
      // Use mock data for demo
      setStats({
        totalSearches: 0,
        totalLeads: 0,
        creditsUsed: 0,
        avgQuality: 0,
      });
      setRecentSearches([]);
    } finally {
      setIsLoading(false);
    }
  }

  const statCards = [
    {
      title: 'Ricerche totali',
      value: stats?.totalSearches ?? 0,
      icon: Search,
      color: 'blue',
    },
    {
      title: 'Lead trovati',
      value: stats?.totalLeads ?? 0,
      icon: Building2,
      color: 'green',
    },
    {
      title: 'Crediti utilizzati',
      value: stats?.creditsUsed ?? 0,
      icon: CreditCard,
      color: 'purple',
    },
    {
      title: 'Qualità media',
      value: stats?.avgQuality ? `${Math.round(stats.avgQuality * 100)}%` : '-',
      icon: TrendingUp,
      color: 'orange',
    },
  ];

  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600',
  };

  const statusConfig = {
    pending: { label: 'In attesa', icon: Clock, color: 'text-gray-500' },
    running: { label: 'In corso', icon: Clock, color: 'text-blue-500' },
    completed: { label: 'Completata', icon: CheckCircle, color: 'text-green-500' },
    failed: { label: 'Fallita', icon: XCircle, color: 'text-red-500' },
  };

  return (
    <>
      <Helmet>
        <title>Dashboard - Scripe</title>
      </Helmet>

      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              Ciao, {user?.name?.split(' ')[0] || 'Utente'}!
            </h1>
            <p className="text-gray-600">
              Hai {user?.credits_balance ?? 0} crediti disponibili
            </p>
          </div>
          <Link
            to="/searches/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuova ricerca
          </Link>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => {
            const Icon = stat.icon;
            return (
              <div
                key={stat.title}
                className="bg-white rounded-xl border p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">{stat.title}</p>
                    <p className="text-2xl font-bold mt-1">
                      {isLoading ? '-' : stat.value}
                    </p>
                  </div>
                  <div
                    className={`p-3 rounded-lg ${
                      colorClasses[stat.color as keyof typeof colorClasses]
                    }`}
                  >
                    <Icon className="h-6 w-6" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/searches/new"
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl p-6 hover:from-blue-600 hover:to-blue-700 transition-all"
          >
            <Search className="h-8 w-8 mb-4" />
            <h3 className="text-lg font-semibold">Nuova ricerca</h3>
            <p className="text-blue-100 text-sm mt-1">
              Trova nuovi lead con l'AI
            </p>
          </Link>

          <Link
            to="/lists"
            className="bg-white border rounded-xl p-6 hover:shadow-md transition-all"
          >
            <Building2 className="h-8 w-8 mb-4 text-green-600" />
            <h3 className="text-lg font-semibold">Le tue liste</h3>
            <p className="text-gray-600 text-sm mt-1">
              Gestisci i lead salvati
            </p>
          </Link>

          <Link
            to="/pricing"
            className="bg-white border rounded-xl p-6 hover:shadow-md transition-all"
          >
            <CreditCard className="h-8 w-8 mb-4 text-purple-600" />
            <h3 className="text-lg font-semibold">Acquista crediti</h3>
            <p className="text-gray-600 text-sm mt-1">
              Ricarica il tuo account
            </p>
          </Link>
        </div>

        {/* Recent Searches */}
        <div className="bg-white rounded-xl border">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-lg font-semibold">Ricerche recenti</h2>
            <Link
              to="/searches"
              className="text-blue-600 hover:underline text-sm flex items-center gap-1"
            >
              Vedi tutte <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {isLoading ? (
            <div className="p-6 text-center text-gray-500">Caricamento...</div>
          ) : recentSearches.length === 0 ? (
            <div className="p-12 text-center">
              <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="font-semibold text-gray-900">Nessuna ricerca</h3>
              <p className="text-gray-600 mt-1">
                Inizia creando la tua prima ricerca
              </p>
              <Link
                to="/searches/new"
                className="inline-flex items-center gap-2 mt-4 text-blue-600 hover:underline"
              >
                <Plus className="h-4 w-4" />
                Crea ricerca
              </Link>
            </div>
          ) : (
            <div className="divide-y">
              {recentSearches.map((search) => {
                const status = statusConfig[search.status];
                const StatusIcon = status.icon;
                return (
                  <Link
                    key={search.id}
                    to={`/searches/${search.id}`}
                    className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                        <Search className="h-5 w-5 text-blue-600" />
                      </div>
                      <div>
                        <h4 className="font-medium">{search.name}</h4>
                        <p className="text-sm text-gray-500">
                          {new Date(search.createdAt).toLocaleDateString('it-IT')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-600">
                        {search.resultsCount} risultati
                      </span>
                      <div className={`flex items-center gap-1 ${status.color}`}>
                        <StatusIcon className="h-4 w-4" />
                        <span className="text-sm">{status.label}</span>
                      </div>
                      <ArrowRight className="h-4 w-4 text-gray-400" />
                    </div>
                  </Link>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
