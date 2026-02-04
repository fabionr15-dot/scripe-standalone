import { Outlet, Link } from 'react-router-dom';
import { Database } from 'lucide-react';

export function PublicLayout() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Database className="h-8 w-8 text-blue-600" />
            <span className="text-2xl font-bold text-blue-600">Scripe</span>
          </Link>

          <nav className="hidden md:flex items-center gap-6">
            <Link to="/pricing" className="text-gray-600 hover:text-gray-900 dark:text-gray-300">
              Prezzi
            </Link>
            <Link to="/login" className="text-gray-600 hover:text-gray-900 dark:text-gray-300">
              Accedi
            </Link>
            <Link
              to="/register"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Inizia Gratis
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main>
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t bg-white dark:bg-gray-900 py-12">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-4 gap-8">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Database className="h-6 w-6 text-blue-600" />
                <span className="text-xl font-bold">Scripe</span>
              </div>
              <p className="text-gray-600 dark:text-gray-400 text-sm">
                Piattaforma di lead generation B2B. Trova contatti aziendali verificati in Italia e Europa.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Prodotto</h4>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><Link to="/pricing">Prezzi</Link></li>
                <li><a href="#">Documentazione</a></li>
                <li><a href="#">API</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Azienda</h4>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><a href="#">Chi siamo</a></li>
                <li><a href="#">Contatti</a></li>
                <li><a href="#">Blog</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legale</h4>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li><a href="#">Privacy Policy</a></li>
                <li><a href="#">Termini di Servizio</a></li>
                <li><a href="#">Cookie Policy</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t mt-8 pt-8 text-center text-sm text-gray-600 dark:text-gray-400">
            © {new Date().getFullYear()} Scripe. Tutti i diritti riservati.
          </div>
        </div>
      </footer>
    </div>
  );
}
