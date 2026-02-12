import { useState, useEffect } from 'react';
import { Helmet } from 'react-helmet-async';
import {
  User,
  Building2,
  MapPin,
  FileText,
  Save,
  Download,
  AlertCircle,
  CheckCircle,
  Loader2,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '@/context/AuthContext';
import { api } from '@/lib/api';

// Types
interface BillingAddress {
  id?: number;
  street_address: string;
  street_address_2?: string;
  city: string;
  state_province?: string;
  postal_code: string;
  country: string;
}

interface Invoice {
  id: number;
  invoice_number: string;
  invoice_date: string;
  total: number;
  currency: string;
  status: string;
}

type TabType = 'profile' | 'company' | 'address' | 'invoices';

export function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const { t, i18n } = useTranslation('profile');
  const { t: tc } = useTranslation('common');

  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Profile form state
  const [name, setName] = useState(user?.name || '');
  const [defaultCountry, setDefaultCountry] = useState(user?.default_country || 'DE');
  const [defaultLanguage, setDefaultLanguage] = useState(user?.default_language || 'de');

  // Company form state
  const [companyName, setCompanyName] = useState(user?.company_name || '');
  const [vatId, setVatId] = useState(user?.vat_id || '');
  const [billingEmail, setBillingEmail] = useState(user?.billing_email || '');

  // Billing address state
  const [address, setAddress] = useState<BillingAddress>({
    street_address: '',
    street_address_2: '',
    city: '',
    state_province: '',
    postal_code: '',
    country: 'DE',
  });

  // Invoices state
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);

  // Load billing address on mount
  useEffect(() => {
    loadBillingAddress();
  }, []);

  // Load invoices when tab changes
  useEffect(() => {
    if (activeTab === 'invoices') {
      loadInvoices();
    }
  }, [activeTab]);

  // Sync user data when user changes
  useEffect(() => {
    if (user) {
      setName(user.name || '');
      setDefaultCountry(user.default_country || 'DE');
      setDefaultLanguage(user.default_language || 'de');
      setCompanyName(user.company_name || '');
      setVatId(user.vat_id || '');
      setBillingEmail(user.billing_email || '');
    }
  }, [user]);

  async function loadBillingAddress() {
    try {
      const res = await api.get('/billing/address');
      if (res.data) {
        setAddress(res.data);
      }
    } catch (err) {
      console.error('Failed to load billing address:', err);
    }
  }

  async function loadInvoices() {
    setInvoicesLoading(true);
    try {
      const res = await api.get('/billing/invoices');
      setInvoices(res.data.items || []);
    } catch (err) {
      console.error('Failed to load invoices:', err);
    } finally {
      setInvoicesLoading(false);
    }
  }

  async function saveProfile() {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.patch('/auth/me', {
        name,
        default_country: defaultCountry,
        default_language: defaultLanguage,
      });
      await refreshUser();
      setMessage({ type: 'success', text: t('messages.profileSaved') });
    } catch (err) {
      setMessage({ type: 'error', text: t('messages.saveFailed') });
    } finally {
      setIsSaving(false);
    }
  }

  async function saveCompany() {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.patch('/auth/me', {
        company_name: companyName,
        vat_id: vatId,
        billing_email: billingEmail,
      });
      await refreshUser();
      setMessage({ type: 'success', text: t('messages.companySaved') });
    } catch (err) {
      setMessage({ type: 'error', text: t('messages.saveFailed') });
    } finally {
      setIsSaving(false);
    }
  }

  async function saveAddress() {
    setIsSaving(true);
    setMessage(null);
    try {
      await api.post('/billing/address', address);
      setMessage({ type: 'success', text: t('messages.addressSaved') });
    } catch (err) {
      setMessage({ type: 'error', text: t('messages.saveFailed') });
    } finally {
      setIsSaving(false);
    }
  }

  async function downloadInvoice(invoiceId: number, invoiceNumber: string) {
    try {
      const response = await api.get(`/billing/invoices/${invoiceId}/pdf`, {
        responseType: 'blob',
      });
      const blob = new Blob([response.data], { type: 'text/plain' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `invoice_${invoiceNumber}.txt`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Failed to download invoice:', err);
      setMessage({ type: 'error', text: t('messages.downloadFailed') });
    }
  }

  const tabs: { id: TabType; label: string; icon: typeof User }[] = [
    { id: 'profile', label: t('tabs.profile'), icon: User },
    { id: 'company', label: t('tabs.company'), icon: Building2 },
    { id: 'address', label: t('tabs.address'), icon: MapPin },
    { id: 'invoices', label: t('tabs.invoices'), icon: FileText },
  ];

  const countries = [
    { code: 'DE', name: tc('countries.DE') },
    { code: 'AT', name: tc('countries.AT') },
    { code: 'CH', name: tc('countries.CH') },
    { code: 'IT', name: tc('countries.IT') },
    { code: 'FR', name: tc('countries.FR') },
    { code: 'ES', name: tc('countries.ES') },
    { code: 'NL', name: tc('countries.NL') },
    { code: 'BE', name: tc('countries.BE') },
    { code: 'PL', name: tc('countries.PL') },
    { code: 'CZ', name: tc('countries.CZ') },
    { code: 'PT', name: tc('countries.PT') },
    { code: 'GB', name: tc('countries.GB') },
  ];

  const languages = [
    { code: 'de', name: 'Deutsch' },
    { code: 'en', name: 'English' },
    { code: 'fr', name: 'Francais' },
    { code: 'it', name: 'Italiano' },
  ];

  return (
    <>
      <Helmet>
        <title>{t('title')}</title>
      </Helmet>

      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold">{t('title')}</h1>
          <p className="text-gray-600">{t('subtitle')}</p>
        </div>

        {/* Message */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${
              message.type === 'success'
                ? 'bg-green-50 text-green-700 border border-green-200'
                : 'bg-red-50 text-red-700 border border-red-200'
            }`}
          >
            {message.type === 'success' ? (
              <CheckCircle className="h-5 w-5" />
            ) : (
              <AlertCircle className="h-5 w-5" />
            )}
            {message.text}
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-xl border">
          <div className="border-b">
            <nav className="flex">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-blue-600 text-blue-600'
                        : 'border-transparent text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <Icon className="h-4 w-4" />
                    {tab.label}
                  </button>
                );
              })}
            </nav>
          </div>

          <div className="p-6">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.email')}
                  </label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="w-full px-4 py-2 border rounded-lg bg-gray-50 text-gray-500"
                  />
                  <p className="text-sm text-gray-500 mt-1">{t('fields.emailHint')}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.name')}
                  </label>
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.namePlaceholder')}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.defaultCountry')}
                    </label>
                    <select
                      value={defaultCountry}
                      onChange={(e) => setDefaultCountry(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {countries.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.defaultLanguage')}
                    </label>
                    <select
                      value={defaultLanguage}
                      onChange={(e) => setDefaultLanguage(e.target.value)}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {languages.map((l) => (
                        <option key={l.code} value={l.code}>
                          {l.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="pt-4">
                  <button
                    onClick={saveProfile}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {tc('actions.save')}
                  </button>
                </div>
              </div>
            )}

            {/* Company Tab */}
            {activeTab === 'company' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.companyName')}
                  </label>
                  <input
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.companyNamePlaceholder')}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.vatId')}
                  </label>
                  <input
                    type="text"
                    value={vatId}
                    onChange={(e) => setVatId(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.vatIdPlaceholder')}
                  />
                  <p className="text-sm text-gray-500 mt-1">{t('fields.vatIdHint')}</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.billingEmail')}
                  </label>
                  <input
                    type="email"
                    value={billingEmail}
                    onChange={(e) => setBillingEmail(e.target.value)}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.billingEmailPlaceholder')}
                  />
                  <p className="text-sm text-gray-500 mt-1">{t('fields.billingEmailHint')}</p>
                </div>

                <div className="pt-4">
                  <button
                    onClick={saveCompany}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {tc('actions.save')}
                  </button>
                </div>
              </div>
            )}

            {/* Address Tab */}
            {activeTab === 'address' && (
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.streetAddress')}
                  </label>
                  <input
                    type="text"
                    value={address.street_address}
                    onChange={(e) => setAddress({ ...address, street_address: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.streetAddressPlaceholder')}
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('fields.streetAddress2')}
                  </label>
                  <input
                    type="text"
                    value={address.street_address_2 || ''}
                    onChange={(e) => setAddress({ ...address, street_address_2: e.target.value })}
                    className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder={t('fields.streetAddress2Placeholder')}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.postalCode')}
                    </label>
                    <input
                      type="text"
                      value={address.postal_code}
                      onChange={(e) => setAddress({ ...address, postal_code: e.target.value })}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder={t('fields.postalCodePlaceholder')}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.city')}
                    </label>
                    <input
                      type="text"
                      value={address.city}
                      onChange={(e) => setAddress({ ...address, city: e.target.value })}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder={t('fields.cityPlaceholder')}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.stateProvince')}
                    </label>
                    <input
                      type="text"
                      value={address.state_province || ''}
                      onChange={(e) => setAddress({ ...address, state_province: e.target.value })}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      placeholder={t('fields.stateProvincePlaceholder')}
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      {t('fields.country')}
                    </label>
                    <select
                      value={address.country}
                      onChange={(e) => setAddress({ ...address, country: e.target.value })}
                      className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      {countries.map((c) => (
                        <option key={c.code} value={c.code}>
                          {c.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="pt-4">
                  <button
                    onClick={saveAddress}
                    disabled={isSaving}
                    className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                  >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    {tc('actions.save')}
                  </button>
                </div>
              </div>
            )}

            {/* Invoices Tab */}
            {activeTab === 'invoices' && (
              <div>
                {invoicesLoading ? (
                  <div className="text-center py-12">
                    <Loader2 className="h-8 w-8 animate-spin mx-auto text-gray-400" />
                    <p className="text-gray-500 mt-2">{tc('actions.loading')}</p>
                  </div>
                ) : invoices.length === 0 ? (
                  <div className="text-center py-12">
                    <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="font-semibold text-gray-900">{t('invoices.noInvoices')}</h3>
                    <p className="text-gray-600 mt-1">{t('invoices.noInvoicesHint')}</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b">
                          <th className="text-left py-3 px-4 font-medium text-gray-600">
                            {t('invoices.number')}
                          </th>
                          <th className="text-left py-3 px-4 font-medium text-gray-600">
                            {t('invoices.date')}
                          </th>
                          <th className="text-left py-3 px-4 font-medium text-gray-600">
                            {t('invoices.amount')}
                          </th>
                          <th className="text-left py-3 px-4 font-medium text-gray-600">
                            {t('invoices.status')}
                          </th>
                          <th className="text-right py-3 px-4 font-medium text-gray-600">
                            {t('invoices.actions')}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {invoices.map((invoice) => (
                          <tr key={invoice.id} className="border-b hover:bg-gray-50">
                            <td className="py-3 px-4 font-medium">{invoice.invoice_number}</td>
                            <td className="py-3 px-4">
                              {new Date(invoice.invoice_date).toLocaleDateString(i18n.language)}
                            </td>
                            <td className="py-3 px-4">
                              {new Intl.NumberFormat(i18n.language, {
                                style: 'currency',
                                currency: invoice.currency,
                              }).format(invoice.total)}
                            </td>
                            <td className="py-3 px-4">
                              <span
                                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                  invoice.status === 'paid'
                                    ? 'bg-green-100 text-green-700'
                                    : 'bg-gray-100 text-gray-700'
                                }`}
                              >
                                {t(`invoices.statusValues.${invoice.status}`)}
                              </span>
                            </td>
                            <td className="py-3 px-4 text-right">
                              <button
                                onClick={() => downloadInvoice(invoice.id, invoice.invoice_number)}
                                className="text-blue-600 hover:text-blue-700 flex items-center gap-1 ml-auto"
                              >
                                <Download className="h-4 w-4" />
                                {t('invoices.download')}
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
