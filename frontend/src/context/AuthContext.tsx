import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

interface User {
  id: number;
  email: string;
  name: string | null;
  subscription_tier: string;
  credits_balance: number;
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  testLogin: () => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function getToken(): string | null {
  return localStorage.getItem('scripe_token');
}

function setToken(token: string | null) {
  if (token) {
    localStorage.setItem('scripe_token', token);
  } else {
    localStorage.removeItem('scripe_token');
  }
}

async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-Client-Type': 'public',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

// Auto-login nur in Development-Modus aktiviert
// In Production (npm run build) ist import.meta.env.DEV = false
const DEV_AUTO_LOGIN = import.meta.env.DEV;

const DEV_USER: User = {
  id: 1,
  email: 'test@scripe.dev',
  name: 'Test User',
  subscription_tier: 'pro',
  credits_balance: 1000,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEV_AUTO_LOGIN ? DEV_USER : null);
  const [isLoading, setIsLoading] = useState(!DEV_AUTO_LOGIN);

  useEffect(() => {
    if (!DEV_AUTO_LOGIN) {
      checkAuth();
    }
  }, []);

  async function checkAuth() {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      const userData = await apiRequest<User>('/api/v1/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Auth check failed:', error);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }

  async function login(email: string, password: string) {
    const response = await apiRequest<{ access_token: string; user: User }>(
      '/api/v1/auth/login',
      {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      }
    );
    setToken(response.access_token);
    setUser(response.user);
  }

  async function register(email: string, password: string, name?: string) {
    const response = await apiRequest<{ access_token: string; user: User }>(
      '/api/v1/auth/register',
      {
        method: 'POST',
        body: JSON.stringify({ email, password, name }),
      }
    );
    setToken(response.access_token);
    setUser(response.user);
  }

  async function testLogin() {
    const response = await apiRequest<{ access_token: string; user: User }>(
      '/api/v1/auth/test-login',
      {
        method: 'POST',
      }
    );
    setToken(response.access_token);
    setUser(response.user);
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  async function refreshUser() {
    try {
      const userData = await apiRequest<User>('/api/v1/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Failed to refresh user:', error);
    }
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        login,
        register,
        testLogin,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
