import { useState, useEffect } from 'react';
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
  StopCircle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';
import { LocalizedLink } from '@/i18n/LocalizedLink';

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
  results_count: number;
  created_at: string;
}

export function DashboardPage() {
  const { user } = useAuth();
  const { t, i18n } = useTranslation('dashboard');
  const { t: tc } = useTranslation('common');
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
      title: t('dashboard.stats.totalSearches'),
      value: stats?.totalSearches ?? 0,
      icon: Search,
      color: 'blue',
    },
    {
      title: t('dashboard.stats.leadsFound'),
      value: stats?.totalLeads ?? 0,
      icon: Building2,
      color: 'green',
    },
    {
      title: t('dashboard.stats.creditsUsed'),
      value: stats?.creditsUsed ?? 0,
      icon: CreditCard,
      color: 'purple',
    },
    {
      title: t('dashboard.stats.avgQuality'),
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
    pending: { label: tc('status.pending'), icon: Clock, color: 'text-gray-500' },
    running: { label: tc('status.running'), icon: Clock, color: 'text-blue-500' },
    completed: { label: tc('status.completed'), icon: CheckCircle, color: 'text-green-500' },
    failed: { label: tc('status.failed'), icon: XCircle, color: 'text-red-500' },
    cancelled: { label: tc('status.cancelled'), icon: StopCircle, color: 'text-orange-500' },
  };

  return (
    <>
      <Helmet>
        <title>{t('dashboard.title')}</title>
      </Helmet>

      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              {t('dashboard.greeting', { name: user?.name?.split(' ')[0] || 'User' })}
            </h1>
            <p className="text-gray-600">
              {t('dashboard.creditsAvailable', { count: user?.credits_balance ?? 0 })}
            </p>
          </div>
          <LocalizedLink
            to="/searches/new"
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t('dashboard.quickActions.newSearch')}
          </LocalizedLink>
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
          <LocalizedLink
            to="/searches/new"
            className="bg-gradient-to-r from-blue-500 to-blue-600 text-white rounded-xl p-6 hover:from-blue-600 hover:to-blue-700 transition-all"
          >
            <Search className="h-8 w-8 mb-4" />
            <h3 className="text-lg font-semibold">{t('dashboard.quickActions.newSearch')}</h3>
            <p className="text-blue-100 text-sm mt-1">
              {t('dashboard.quickActions.findLeads')}
            </p>
          </LocalizedLink>

          <LocalizedLink
            to="/lists"
            className="bg-white border rounded-xl p-6 hover:shadow-md transition-all"
          >
            <Building2 className="h-8 w-8 mb-4 text-green-600" />
            <h3 className="text-lg font-semibold">{t('dashboard.quickActions.yourLists')}</h3>
            <p className="text-gray-600 text-sm mt-1">
              {t('dashboard.quickActions.manageLists')}
            </p>
          </LocalizedLink>

          <LocalizedLink
            to="/pricing"
            className="bg-white border rounded-xl p-6 hover:shadow-md transition-all"
          >
            <CreditCard className="h-8 w-8 mb-4 text-purple-600" />
            <h3 className="text-lg font-semibold">{t('dashboard.quickActions.buyCredits')}</h3>
            <p className="text-gray-600 text-sm mt-1">
              {t('dashboard.quickActions.rechargeAccount')}
            </p>
          </LocalizedLink>
        </div>

        {/* Recent Searches */}
        <div className="bg-white rounded-xl border">
          <div className="flex items-center justify-between p-6 border-b">
            <h2 className="text-lg font-semibold">{t('dashboard.recentSearches.title')}</h2>
            <LocalizedLink
              to="/searches"
              className="text-blue-600 hover:underline text-sm flex items-center gap-1"
            >
              {t('dashboard.recentSearches.viewAll')} <ArrowRight className="h-4 w-4" />
            </LocalizedLink>
          </div>

          {isLoading ? (
            <div className="p-6 text-center text-gray-500">{tc('actions.loading')}</div>
          ) : recentSearches.length === 0 ? (
            <div className="p-12 text-center">
              <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h3 className="font-semibold text-gray-900">{t('dashboard.recentSearches.noSearches')}</h3>
              <p className="text-gray-600 mt-1">
                {t('dashboard.recentSearches.startFirst')}
              </p>
              <LocalizedLink
                to="/searches/new"
                className="inline-flex items-center gap-2 mt-4 text-blue-600 hover:underline"
              >
                <Plus className="h-4 w-4" />
                {t('dashboard.recentSearches.createSearch')}
              </LocalizedLink>
            </div>
          ) : (
            <div className="divide-y">
              {recentSearches.map((search) => {
                const status = statusConfig[search.status] || { label: search.status, icon: Clock, color: 'text-gray-500' };
                const StatusIcon = status.icon;
                return (
                  <LocalizedLink
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
                          {new Date(search.created_at).toLocaleDateString(i18n.language)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-gray-600">
                        {t('dashboard.recentSearches.results', { count: search.results_count })}
                      </span>
                      <div className={`flex items-center gap-1 ${status.color}`}>
                        <StatusIcon className="h-4 w-4" />
                        <span className="text-sm">{status.label}</span>
                      </div>
                      <ArrowRight className="h-4 w-4 text-gray-400" />
                    </div>
                  </LocalizedLink>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
