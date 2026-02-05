import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';

// In development: leer lassen für Vite Proxy (/api → localhost:8010)
// In production: volle URL setzen (z.B. https://api.scripe.io)
const API_URL = import.meta.env.VITE_API_URL || '';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: `${API_URL}/api/v1`,
      headers: {
        'Content-Type': 'application/json',
        'X-Client-Type': 'public', // Mark as public frontend
      },
    });

    // Add auth token to requests
    this.client.interceptors.request.use((config) => {
      const token = localStorage.getItem('scripe_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    });

    // Handle auth errors
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('scripe_token');
          localStorage.removeItem('scripe_user');
          // Detect current language from URL path for localized redirect
          const pathLang = window.location.pathname.split('/')[1];
          const supportedLangs = ['en', 'de', 'it', 'fr'];
          const lang = supportedLangs.includes(pathLang) ? pathLang : 'en';
          window.location.href = `/${lang}/login`;
        }
        return Promise.reject(error);
      }
    );
  }

  // Auth
  async login(email: string, password: string) {
    const res = await this.client.post('/auth/login', { email, password });
    return res.data;
  }

  async register(email: string, password: string, name: string) {
    const res = await this.client.post('/auth/register', { email, password, name });
    return res.data;
  }

  async refreshToken(refreshToken: string) {
    const res = await this.client.post('/auth/refresh', { refresh_token: refreshToken });
    return res.data;
  }

  async getMe() {
    const res = await this.client.get('/auth/me');
    return res.data;
  }

  // Generic methods
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<{ data: T }> {
    const res = await this.client.get<T>(url, config);
    return { data: res.data };
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<{ data: T }> {
    const res = await this.client.post<T>(url, data, config);
    return { data: res.data };
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<{ data: T }> {
    const res = await this.client.put<T>(url, data, config);
    return { data: res.data };
  }

  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<{ data: T }> {
    const res = await this.client.patch<T>(url, data, config);
    return { data: res.data };
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<{ data: T }> {
    const res = await this.client.delete<T>(url, config);
    return { data: res.data };
  }

  // Searches
  async createSearch(data: {
    name: string;
    query: string;
    criteria: any;
    quality_tier: string;
  }) {
    const res = await this.client.post('/searches', data);
    return res.data;
  }

  async getSearches(params?: { limit?: number; offset?: number }) {
    const res = await this.client.get('/searches', { params });
    return res.data;
  }

  async getSearch(id: string) {
    const res = await this.client.get(`/searches/${id}`);
    return res.data;
  }

  async runSearch(id: string) {
    const res = await this.client.post(`/searches/${id}/run`);
    return res.data;
  }

  async getSearchResults(id: string, params?: { limit?: number; offset?: number; min_quality?: number }) {
    const res = await this.client.get(`/searches/${id}/companies`, { params });
    return res.data;
  }

  async exportSearch(id: string, format: 'csv' | 'excel', minQuality?: number) {
    const res = await this.client.post(
      `/searches/${id}/export`,
      { format, min_quality: minQuality },
      { responseType: 'blob' }
    );
    return res.data;
  }

  // AI
  async interpretQuery(query: string) {
    const res = await this.client.post('/searches/interpret', { query });
    return res.data;
  }

  async estimateSearch(criteria: any, qualityTier: string) {
    const res = await this.client.post('/searches/estimate', {
      criteria,
      quality_tier: qualityTier,
    });
    return res.data;
  }

  // Lists
  async getLists() {
    const res = await this.client.get('/lists');
    return res.data;
  }

  async createList(data: { name: string; description?: string }) {
    const res = await this.client.post('/lists', data);
    return res.data;
  }

  async getList(id: string) {
    const res = await this.client.get(`/lists/${id}`);
    return res.data;
  }

  async deleteList(id: string) {
    const res = await this.client.delete(`/lists/${id}`);
    return res.data;
  }

  async addToList(listId: string, leadIds: string[]) {
    const res = await this.client.post(`/lists/${listId}/leads`, { lead_ids: leadIds });
    return res.data;
  }

  async removeFromList(listId: string, leadIds: string[]) {
    const res = await this.client.delete(`/lists/${listId}/leads`, {
      data: { lead_ids: leadIds },
    });
    return res.data;
  }

  // Credits
  async getCredits() {
    const res = await this.client.get('/auth/credits');
    return res.data;
  }

  async getCreditPackages() {
    const res = await this.client.get('/auth/credits/packages');
    return res.data;
  }

  async purchaseCredits(packageId: string) {
    const res = await this.client.post('/auth/credits/purchase', {
      package_id: packageId,
    });
    return res.data;
  }

  async getCreditHistory(params?: { limit?: number; offset?: number }) {
    const res = await this.client.get('/auth/credits/history', { params });
    return res.data;
  }

  // SSE Stream helper
  createSearchStream(searchId: string, onMessage: (data: any) => void, onError?: (error: any) => void) {
    const token = localStorage.getItem('scripe_token');
    const url = `${API_URL}/api/v1/runs/${searchId}/stream`;

    const eventSource = new EventSource(url);

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        onMessage(data);
      } catch (e) {
        console.error('Failed to parse SSE message:', e);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      onError?.(error);
      eventSource.close();
    };

    return eventSource;
  }
}

export const api = new ApiClient();
