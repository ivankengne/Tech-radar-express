import { Metadata } from 'next';
import { SearchInterface } from '@/components/chat/SearchInterface';

export const metadata: Metadata = {
  title: 'Recherche IA | Tech Radar Express',
  description: 'Interface de recherche conversationnelle avec IA pour la veille technologique. Posez vos questions et obtenez des réponses avec citations.',
  keywords: ['IA', 'recherche', 'chat', 'assistant', 'technologie', 'veille'],
};

export default function SearchPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* En-tête de la page */}
      <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                🔍 Recherche Conversationnelle
              </h1>
              <p className="mt-1 text-gray-600 dark:text-gray-400">
                Posez vos questions techniques à notre assistant IA spécialisé
              </p>
            </div>
            
            <div className="hidden sm:flex items-center gap-4 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span>Alimenté par MCP crawl4ai-rag</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <span>Citations en temps réel</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Container principal pour l'interface chat */}
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="max-w-5xl mx-auto">
          {/* Carte avec l'interface de chat */}
          <div className="bg-white dark:bg-gray-900 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
            {/* Interface de recherche - hauteur fixe pour un comportement type application */}
            <div className="h-[calc(100vh-12rem)]">
              <SearchInterface className="h-full" />
            </div>
          </div>
          
          {/* Footer informatif */}
          <div className="mt-6 text-center">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600 dark:text-gray-400">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <span className="text-lg">🤖</span>
                  <span className="font-medium">Assistant IA</span>
                </div>
                <p>Optimisé pour les questions techniques et la veille technologique</p>
              </div>
              
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <span className="text-lg">📚</span>
                  <span className="font-medium">Sources Citées</span>
                </div>
                <p>Toutes les réponses incluent des références vers les sources originales</p>
              </div>
              
              <div className="bg-white dark:bg-gray-800 rounded-lg p-4 border border-gray-200 dark:border-gray-700">
                <div className="flex items-center justify-center gap-2 mb-2">
                  <span className="text-lg">⚡</span>
                  <span className="font-medium">Temps Réel</span>
                </div>
                <p>Données mises à jour en continu depuis les sources de veille</p>
              </div>
            </div>
            
            {/* Tips d'utilisation */}
            <div className="mt-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
              <h3 className="font-medium text-blue-900 dark:text-blue-300 mb-2">
                💡 Conseils pour de meilleures recherches :
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-blue-800 dark:text-blue-300">
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>
                  <span>Utilisez des termes techniques précis (ex: "React Server Components")</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>
                  <span>Demandez des comparaisons entre technologies</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>
                  <span>Cliquez sur le bouton 💡 pour une analyse approfondie</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-blue-500 mt-0.5">•</span>
                  <span>Explorez les citations pour approfondir vos recherches</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 