import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { PublicLayout } from './components/layout/PublicLayout';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { LandingPage } from './pages/LandingPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { SearchesPage } from './pages/SearchesPage';
import { NewSearchPage } from './pages/NewSearchPage';
import { SearchResultsPage } from './pages/SearchResultsPage';
import { PricingPage } from './pages/PricingPage';
import { ListsPage } from './pages/ListsPage';
import { ProtectedRoute } from './components/ProtectedRoute';

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        {/* Public pages */}
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="/pricing" element={<PricingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
        </Route>

        {/* Protected dashboard */}
        <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/searches" element={<SearchesPage />} />
          <Route path="/searches/new" element={<NewSearchPage />} />
          <Route path="/searches/:id" element={<SearchResultsPage />} />
          <Route path="/lists" element={<ListsPage />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  );
}
