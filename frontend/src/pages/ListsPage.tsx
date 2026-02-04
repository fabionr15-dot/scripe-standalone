import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import {
  FolderOpen,
  Plus,
  Building2,
  Calendar,
  Download,
  Trash2,
  MoreVertical,
} from 'lucide-react';
import { api } from '@/lib/api';

interface SavedList {
  id: string;
  name: string;
  description: string | null;
  leads_count: number;
  created_at: string;
  updated_at: string;
}

export function ListsPage() {
  const [lists, setLists] = useState<SavedList[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newListName, setNewListName] = useState('');
  const [newListDescription, setNewListDescription] = useState('');

  useEffect(() => {
    loadLists();
  }, []);

  async function loadLists() {
    try {
      const res = await api.get('/lists');
      setLists(res.data.items || []);
    } catch (err) {
      console.error('Failed to load lists:', err);
      setLists([]);
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateList() {
    if (!newListName.trim()) return;

    try {
      await api.post('/lists', {
        name: newListName,
        description: newListDescription || null,
      });
      setShowCreateModal(false);
      setNewListName('');
      setNewListDescription('');
      loadLists();
    } catch (err) {
      console.error('Failed to create list:', err);
    }
  }

  async function handleDeleteList(id: string) {
    if (!confirm('Sei sicuro di voler eliminare questa lista?')) return;

    try {
      await api.delete(`/lists/${id}`);
      loadLists();
    } catch (err) {
      console.error('Failed to delete list:', err);
    }
  }

  async function handleExportList(id: string, format: 'csv' | 'excel') {
    try {
      const res = await api.get(`/lists/${id}/export?format=${format}`, {
        responseType: 'blob',
      });

      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `lista-${id}.${format === 'excel' ? 'xlsx' : 'csv'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Export failed:', err);
    }
  }

  return (
    <>
      <Helmet>
        <title>Le tue liste - Scripe</title>
      </Helmet>

      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Le tue liste</h1>
            <p className="text-gray-600">Organizza e gestisci i tuoi lead salvati</p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            Nuova lista
          </button>
        </div>

        {/* Lists */}
        {isLoading ? (
          <div className="bg-white rounded-xl border p-12 text-center text-gray-500">
            Caricamento...
          </div>
        ) : lists.length === 0 ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <FolderOpen className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="font-semibold text-gray-900">Nessuna lista</h3>
            <p className="text-gray-600 mt-1">
              Crea una lista per organizzare i tuoi lead
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="inline-flex items-center gap-2 mt-4 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Crea lista
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lists.map((list) => (
              <div
                key={list.id}
                className="bg-white rounded-xl border p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                      <FolderOpen className="h-5 w-5 text-blue-600" />
                    </div>
                    <div>
                      <h3 className="font-semibold">{list.name}</h3>
                      {list.description && (
                        <p className="text-sm text-gray-500 line-clamp-1">
                          {list.description}
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="relative group">
                    <button className="p-1 hover:bg-gray-100 rounded">
                      <MoreVertical className="h-5 w-5 text-gray-400" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 bg-white border rounded-lg shadow-lg py-1 hidden group-hover:block z-10 min-w-[150px]">
                      <button
                        onClick={() => handleExportList(list.id, 'csv')}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                      >
                        <Download className="h-4 w-4" />
                        Export CSV
                      </button>
                      <button
                        onClick={() => handleExportList(list.id, 'excel')}
                        className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center gap-2"
                      >
                        <Download className="h-4 w-4" />
                        Export Excel
                      </button>
                      <hr className="my-1" />
                      <button
                        onClick={() => handleDeleteList(list.id)}
                        className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                      >
                        <Trash2 className="h-4 w-4" />
                        Elimina
                      </button>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 mt-4 text-sm text-gray-500">
                  <div className="flex items-center gap-1">
                    <Building2 className="h-4 w-4" />
                    {list.leads_count} lead
                  </div>
                  <div className="flex items-center gap-1">
                    <Calendar className="h-4 w-4" />
                    {new Date(list.updated_at).toLocaleDateString('it-IT')}
                  </div>
                </div>

                <Link
                  to={`/lists/${list.id}`}
                  className="block mt-4 text-center py-2 border rounded-lg text-blue-600 hover:bg-blue-50 transition-colors"
                >
                  Visualizza
                </Link>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md mx-4">
            <h2 className="text-xl font-bold mb-4">Nuova lista</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Nome lista
                </label>
                <input
                  type="text"
                  value={newListName}
                  onChange={(e) => setNewListName(e.target.value)}
                  placeholder="Es: Lead Milano Q1"
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Descrizione (opzionale)
                </label>
                <textarea
                  value={newListDescription}
                  onChange={(e) => setNewListDescription(e.target.value)}
                  placeholder="Descrivi lo scopo di questa lista..."
                  className="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 min-h-[80px]"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-gray-50 transition-colors"
              >
                Annulla
              </button>
              <button
                onClick={handleCreateList}
                disabled={!newListName.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                Crea lista
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
