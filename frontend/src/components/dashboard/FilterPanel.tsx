"use client";

import React, { useState } from 'react';
import { useDashboardStore, AxisType, PriorityType, ImpactType } from '@/store/dashboardStore';

const axisConfig = {
  frontend: { label: 'Frontend', icon: '🎨', color: 'blue' },
  backend: { label: 'Backend', icon: '⚙️', color: 'green' },
  'ai-ml': { label: 'IA/ML', icon: '🤖', color: 'purple' },
  devops: { label: 'DevOps', icon: '🚀', color: 'orange' },
  mobile: { label: 'Mobile', icon: '📱', color: 'pink' },
  data: { label: 'Data', icon: '📊', color: 'yellow' },
  security: { label: 'Sécurité', icon: '🔒', color: 'red' },
  cloud: { label: 'Cloud', icon: '☁️', color: 'indigo' },
} as const;

const priorityConfig = {
  low: { label: 'Faible', icon: '●', color: 'gray' },
  medium: { label: 'Moyen', icon: '●', color: 'yellow' },
  high: { label: 'Élevé', icon: '●', color: 'orange' },
  critical: { label: 'Critique', icon: '●', color: 'red' },
} as const;

const impactConfig = {
  disruptive: { label: 'Disruptif', icon: '🔥', color: 'red' },
  emerging: { label: 'Émergent', icon: '🌱', color: 'green' },
  incremental: { label: 'Incrémental', icon: '📈', color: 'blue' },
  declining: { label: 'Déclinant', icon: '📉', color: 'gray' },
} as const;

const timePresets = [
  { value: '24h', label: 'Dernières 24h' },
  { value: '7d', label: '7 derniers jours' },
  { value: '30d', label: '30 derniers jours' },
  { value: '90d', label: '90 derniers jours' },
  { value: 'custom', label: 'Période personnalisée' },
] as const;

interface FilterPanelProps {
  isCollapsed?: boolean;
  onToggle?: () => void;
  availableSources?: string[];
}

export function FilterPanel({ 
  isCollapsed = false, 
  onToggle,
  availableSources = ['Vercel Blog', 'OpenAI Research', 'CNCF', 'FastAPI Docs', 'Meta Engineering', 'GitHub', 'Stack Overflow', 'Reddit'] 
}: FilterPanelProps) {
  const {
    // State
    selectedAxes,
    allAxes,
    timeRange,
    selectedSources,
    allSources,
    selectedPriorities,
    allPriorities,
    selectedImpacts,
    allImpacts,
    searchQuery,
    itemsPerPage,
    sortBy,
    sortOrder,
    
    // Actions
    toggleAxis,
    selectAllAxes,
    deselectAllAxes,
    toggleSource,
    selectAllSources,
    deselectAllSources,
    togglePriority,
    selectAllPriorities,
    deselectAllPriorities,
    toggleImpact,
    selectAllImpacts,
    deselectAllImpacts,
    setTimePreset,
    setSearchQuery,
    clearSearch,
    setItemsPerPage,
    setSorting,
    resetFilters,
    resetToDefaults,
  } = useDashboardStore();

  const [activeSection, setActiveSection] = useState<string>('axes');

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('fr-FR', { 
      day: '2-digit', 
      month: '2-digit', 
      year: 'numeric' 
    });
  };

  const getActiveFiltersCount = () => {
    let count = 0;
    if (!allAxes && selectedAxes.length > 0) count++;
    if (!allSources && selectedSources.length > 0) count++;
    if (!allPriorities && selectedPriorities.length > 0) count++;
    if (!allImpacts && selectedImpacts.length > 0) count++;
    if (searchQuery.trim()) count++;
    if (timeRange.preset !== '7d') count++;
    return count;
  };

  const activeFiltersCount = getActiveFiltersCount();

  if (isCollapsed) {
    return (
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={onToggle}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              title="Ouvrir les filtres"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707v4.586a1 1 0 01-.707.707l-4 2A1 1 0 0110 21V13.414a1 1 0 00-.293-.707L3.293 6.293A1 1 0 013 5.586V4z" />
              </svg>
            </button>
            
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Filtres
              </span>
              {activeFiltersCount > 0 && (
                <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs px-2 py-1 rounded-full">
                  {activeFiltersCount}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <input
                type="text"
                placeholder="Rechercher..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-4 py-2 text-sm border border-gray-300 dark:border-gray-600 
                           bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 
                           focus:ring-blue-500 text-gray-900 dark:text-gray-100 w-64"
              />
              <svg className="absolute left-2.5 top-2.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              {searchQuery && (
                <button
                  onClick={clearSearch}
                  className="absolute right-2 top-2 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>

            {activeFiltersCount > 0 && (
              <button
                onClick={resetFilters}
                className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 
                           dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Réinitialiser
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          {onToggle && (
            <button
              onClick={onToggle}
              className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              title="Réduire les filtres"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">
            Filtres & Recherche
          </h3>
          {activeFiltersCount > 0 && (
            <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs px-2 py-1 rounded-full">
              {activeFiltersCount} actif{activeFiltersCount > 1 ? 's' : ''}
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={resetFilters}
            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 
                       dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            Réinitialiser
          </button>
          <button
            onClick={resetToDefaults}
            className="px-3 py-1 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 
                       dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
          >
            Défaut
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="relative">
          <input
            type="text"
            placeholder="Rechercher dans les insights, sources, tags..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-3 text-sm border border-gray-300 dark:border-gray-600 
                       bg-white dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 
                       focus:ring-blue-500 text-gray-900 dark:text-gray-100"
          />
          <svg className="absolute left-3 top-3.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-3 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* Filter Sections */}
      <div className="p-4 space-y-6">
        {/* Time Range */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Période temporelle
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {timePresets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setTimePreset(preset.value)}
                className={`px-3 py-2 text-xs rounded-md transition-colors ${
                  timeRange.preset === preset.value
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
          <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Du {formatDate(timeRange.start)} au {formatDate(timeRange.end)}
          </div>
        </div>

        {/* Navigation des sections */}
        <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-700 pb-2">
          {[
            { id: 'axes', label: 'Axes Tech', count: !allAxes ? selectedAxes.length : 0 },
            { id: 'priorities', label: 'Priorités', count: !allPriorities ? selectedPriorities.length : 0 },
            { id: 'impacts', label: 'Impacts', count: !allImpacts ? selectedImpacts.length : 0 },
            { id: 'sources', label: 'Sources', count: !allSources ? selectedSources.length : 0 },
          ].map((section) => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`px-3 py-1 text-sm rounded-md transition-colors flex items-center gap-1 ${
                activeSection === section.id
                  ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200'
                  : 'text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700'
              }`}
            >
              {section.label}
              {section.count > 0 && (
                <span className="bg-blue-500 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {section.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Section content */}
        <div className="min-h-[200px]">
          {activeSection === 'axes' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Axes technologiques
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllAxes}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Tout
                  </button>
                  <button
                    onClick={deselectAllAxes}
                    className="text-xs text-gray-600 dark:text-gray-400 hover:underline"
                  >
                    Aucun
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(axisConfig) as AxisType[]).map((axis) => {
                  const config = axisConfig[axis];
                  const isSelected = allAxes || selectedAxes.includes(axis);
                  return (
                    <button
                      key={axis}
                      onClick={() => toggleAxis(axis)}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isSelected
                          ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
                          : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
                      }`}
                    >
                      <span className="text-lg">{config.icon}</span>
                      <span className="text-sm">{config.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeSection === 'priorities' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Niveaux de priorité
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllPriorities}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Tout
                  </button>
                  <button
                    onClick={deselectAllPriorities}
                    className="text-xs text-gray-600 dark:text-gray-400 hover:underline"
                  >
                    Aucun
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(priorityConfig) as PriorityType[]).map((priority) => {
                  const config = priorityConfig[priority];
                  const isSelected = allPriorities || selectedPriorities.includes(priority);
                  return (
                    <button
                      key={priority}
                      onClick={() => togglePriority(priority)}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isSelected
                          ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
                          : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
                      }`}
                    >
                      <span className={`text-${config.color}-500`}>{config.icon}</span>
                      <span className="text-sm">{config.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeSection === 'impacts' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Types d'impact
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllImpacts}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Tout
                  </button>
                  <button
                    onClick={deselectAllImpacts}
                    className="text-xs text-gray-600 dark:text-gray-400 hover:underline"
                  >
                    Aucun
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {(Object.keys(impactConfig) as ImpactType[]).map((impact) => {
                  const config = impactConfig[impact];
                  const isSelected = allImpacts || selectedImpacts.includes(impact);
                  return (
                    <button
                      key={impact}
                      onClick={() => toggleImpact(impact)}
                      className={`flex items-center gap-2 p-2 rounded-lg border transition-all ${
                        isSelected
                          ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
                          : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
                      }`}
                    >
                      <span className="text-lg">{config.icon}</span>
                      <span className="text-sm">{config.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {activeSection === 'sources' && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">
                  Sources de données
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllSources}
                    className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                  >
                    Toutes
                  </button>
                  <button
                    onClick={deselectAllSources}
                    className="text-xs text-gray-600 dark:text-gray-400 hover:underline"
                  >
                    Aucune
                  </button>
                </div>
              </div>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {availableSources.map((source) => {
                  const isSelected = allSources || selectedSources.includes(source);
                  return (
                    <button
                      key={source}
                      onClick={() => toggleSource(source)}
                      className={`flex items-center justify-between w-full p-2 rounded-lg border transition-all text-left ${
                        isSelected
                          ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20 text-blue-800 dark:text-blue-200'
                          : 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:border-gray-300 dark:hover:border-gray-500'
                      }`}
                    >
                      <span className="text-sm">{source}</span>
                      {isSelected && (
                        <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Settings */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-3">
            Paramètres d'affichage
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Éléments par page
              </label>
              <select
                value={itemsPerPage}
                onChange={(e) => setItemsPerPage(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 
                           bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 
                           focus:ring-blue-500 text-gray-900 dark:text-gray-100"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-600 dark:text-gray-400 mb-1">
                Trier par
              </label>
              <div className="flex gap-1">
                <select
                  value={sortBy}
                  onChange={(e) => setSorting(e.target.value as any, sortOrder)}
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 
                             bg-white dark:bg-gray-700 rounded-l-md focus:outline-none focus:ring-2 
                             focus:ring-blue-500 text-gray-900 dark:text-gray-100"
                >
                  <option value="timestamp">Date</option>
                  <option value="priority">Priorité</option>
                  <option value="impact">Impact</option>
                  <option value="source">Source</option>
                </select>
                <button
                  onClick={() => setSorting(sortBy, sortOrder === 'asc' ? 'desc' : 'asc')}
                  className="px-3 py-2 border border-l-0 border-gray-300 dark:border-gray-600 
                             bg-white dark:bg-gray-700 rounded-r-md hover:bg-gray-50 dark:hover:bg-gray-600 
                             transition-colors"
                  title={`Tri ${sortOrder === 'asc' ? 'croissant' : 'décroissant'}`}
                >
                  <svg 
                    className={`w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform ${
                      sortOrder === 'desc' ? 'rotate-180' : ''
                    }`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 