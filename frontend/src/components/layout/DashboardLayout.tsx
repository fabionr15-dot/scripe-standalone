import { Outlet, useLocation } from 'react-router-dom';
import {
  Database,
  LayoutDashboard,
  Search,
  PlusCircle,
  CreditCard,
  FolderOpen,
  LogOut,
  User,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/context/AuthContext';
import { cn } from '@/lib/utils';
import { LocalizedLink } from '@/i18n/LocalizedLink';
import { LanguageSwitcher } from '@/i18n/LanguageSwitcher';

export function DashboardLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t, i18n } = useTranslation('common');
  const lang = i18n.language?.slice(0, 2) || 'en';

  const navItems = [
    { href: '/dashboard', label: t('sidebar.dashboard'), icon: LayoutDashboard },
    { href: '/searches', label: t('sidebar.searches'), icon: Search },
    { href: '/searches/new', label: t('sidebar.newSearch'), icon: PlusCircle },
    { href: '/lists', label: t('sidebar.lists'), icon: FolderOpen },
  ];

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 w-64 bg-white dark:bg-gray-800 border-r">
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b">
          <LocalizedLink to="/dashboard" className="flex items-center gap-2">
            <Database className="h-8 w-8 text-blue-600" />
            <span className="text-xl font-bold">Scripe</span>
          </LocalizedLink>
        </div>

        {/* Navigation */}
        <nav className="p-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === `/${lang}${item.href}`;
            return (
              <LocalizedLink
                key={item.href}
                to={item.href}
                className={cn(
                  'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors',
                  isActive
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300'
                    : 'text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700'
                )}
              >
                <Icon className="h-5 w-5" />
                {item.label}
              </LocalizedLink>
            );
          })}
        </nav>

        {/* Credits */}
        <div className="absolute bottom-20 left-0 right-0 px-4">
          <div className="bg-blue-50 dark:bg-blue-900/30 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-600 dark:text-gray-400">{t('sidebar.credits')}</span>
              <CreditCard className="h-4 w-4 text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-blue-600">
              {user?.credits_balance.toFixed(2)}
            </p>
            <LocalizedLink
              to="/pricing"
              className="text-sm text-blue-600 hover:underline mt-2 block"
            >
              {t('sidebar.buyCredits')}
            </LocalizedLink>
          </div>
        </div>

        {/* User menu */}
        <div className="absolute bottom-0 left-0 right-0 border-t">
          <div className="px-4 py-4 flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
              <User className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.name || user?.email}</p>
              <p className="text-xs text-gray-500 truncate">{user?.email}</p>
            </div>
            <button
              onClick={logout}
              className="p-2 text-gray-400 hover:text-gray-600"
              title={t('sidebar.logout')}
            >
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="ml-64 min-h-screen">
        {/* Top header bar with language switcher */}
        <div className="h-16 border-b bg-white dark:bg-gray-800 flex items-center justify-end px-8">
          <LanguageSwitcher />
        </div>
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
