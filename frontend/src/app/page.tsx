"use client";

import { HeroKPI } from '@/components/ui/HeroKPI';
import { Timeline } from '@/components/dashboard/Timeline';
import { RadarChart } from '@/components/dashboard/RadarChart';
import { FilterBar } from '@/components/ui/FilterBar';
import { useMockData, useFilteredData } from '@/hooks/useFilteredData';
import { useDashboardStore } from '@/store/dashboardStore';

export default function Dashboard() {
  const mockData = useMockData();
  const { statistics, hasActiveFilters, filterCount, originalCount } = useFilteredData(mockData);
  const { activeView, setActiveView } = useDashboardStore();

  const views = [
         { id: 'overview', label: 'Vue d&apos;ensemble', icon: '📊' },
    { id: 'timeline', label: 'Timeline', icon: '📅' },
    { id: 'radar', label: 'Radar', icon: '🎯' },
    { id: 'sources', label: 'Sources', icon: '📚' },
  ] as const;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <div className="container mx-auto px-4 py-6 space-y-6">
        {/* En-tête du dashboard */}
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">
              Tech Radar Express
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Surveillance technologique intelligente et insights automatisés
            </p>
          </div>

          {/* Navigation des vues */}
          <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
            {views.map((view) => (
              <button
                key={view.id}
                onClick={() => setActiveView(view.id)}
                className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeView === view.id
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
                    : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
                }`}
              >
                <span>{view.icon}</span>
                <span className="hidden sm:inline">{view.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Barre de filtres */}
        <FilterBar />

        {/* Indicateur des filtres actifs */}
        {hasActiveFilters && (
          <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
            <div className="flex items-center gap-2">
              <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707v4.586a1 1 0 01-.707.707l-4 2A1 1 0 0110 21V13.414a1 1 0 00-.293-.707L3.293 6.293A1 1 0 013 5.586V4z" />
              </svg>
              <span className="text-sm text-blue-800 dark:text-blue-200">
                <strong>{filterCount}</strong> résultat{filterCount > 1 ? 's' : ''} affiché{filterCount > 1 ? 's' : ''} 
                sur <strong>{originalCount}</strong> au total
                {statistics.filteredPercentage < 100 && (
                  <span className="ml-2 text-xs bg-blue-200 dark:bg-blue-800 px-2 py-1 rounded">
                    {Math.round(statistics.filteredPercentage)}% des données
                  </span>
                )}
              </span>
            </div>
          </div>
        )}

        {/* Contenu principal basé sur la vue active */}
        {activeView === 'overview' && (
          <div className="space-y-6">
            {/* KPI Cards */}
            <HeroKPI />

            {/* Graphique Radar et Timeline côte à côte */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Vue radar par axe technologique
                </h3>
                <RadarChart />
              </div>
              
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
                  Timeline des insights récents
                </h3>
                <div className="max-h-96 overflow-y-auto">
                  <Timeline />
                </div>
              </div>
            </div>

            {/* Statistiques détaillées */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Sources actives</h4>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {statistics.uniqueSources}
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {Object.keys(statistics.bySource).length} sources avec données
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Période analysée</h4>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {statistics.timeSpan.days}j
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  {statistics.timeSpan.start.toLocaleDateString('fr-FR')} - {statistics.timeSpan.end.toLocaleDateString('fr-FR')}
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Confiance moyenne</h4>
                <div className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {Math.round(statistics.averageConfidence * 100)}%
                </div>
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  Niveau de confiance des insights
                </div>
              </div>

              <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4">
                <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Tendances</h4>
                <div className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-green-600 dark:text-green-400">📈 Croissance</span>
                    <span className="font-medium">{statistics.trends.rising}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">➡️ Stable</span>
                    <span className="font-medium">{statistics.trends.stable}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-red-600 dark:text-red-400">📉 Déclin</span>
                    <span className="font-medium">{statistics.trends.declining}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeView === 'timeline' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
              Timeline détaillée des insights
            </h2>
            <Timeline />
          </div>
        )}

        {activeView === 'radar' && (
          <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
              Vue radar complète
            </h2>
            <RadarChart />
          </div>
        )}

        {activeView === 'sources' && (
          <div className="space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">
                Analyse des sources de données
              </h2>
              
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Distribution par source */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                    Distribution par source
                  </h3>
                  <div className="space-y-3">
                    {Object.entries(statistics.bySource)
                      .sort(([, a], [, b]) => b - a)
                      .map(([source, count]) => (
                        <div key={source} className="flex items-center justify-between">
                          <span className="text-sm text-gray-700 dark:text-gray-300">{source}</span>
                          <div className="flex items-center gap-2">
                            <div className="bg-gray-200 dark:bg-gray-700 rounded-full h-2 w-20">
                              <div 
                                className="bg-blue-500 h-2 rounded-full" 
                                style={{ width: `${(count / Math.max(...Object.values(statistics.bySource))) * 100}%` }}
                              />
                            </div>
                            <span className="text-sm font-medium text-gray-900 dark:text-gray-100 w-8 text-right">
                              {count}
                            </span>
                          </div>
                        </div>
                      ))}
                  </div>
                </div>

                {/* Tags populaires */}
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
                    Tags les plus populaires
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {statistics.topTags.map(({ tag, count }) => (
                      <span 
                        key={tag}
                        className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium 
                                   bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
                      >
                        {tag}
                        <span className="bg-blue-200 dark:bg-blue-800 px-1.5 py-0.5 rounded-full text-xs">
                          {count}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
