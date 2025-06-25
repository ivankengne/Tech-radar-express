"use client";

import React from 'react';
import { useDashboardStore, AxisType } from '@/store/dashboardStore';

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

const timePresets = [
  { value: '24h', label: '24h' },
  { value: '7d', label: '7j' },
  { value: '30d', label: '30j' },
  { value: '90d', label: '90j' },
] as const;

export function FilterBar() {
  const {
    selectedAxes,
    allAxes,
    timeRange,
    searchQuery,
    toggleAxis,
    selectAllAxes,
    setTimePreset,
    setSearchQuery,
    clearSearch,
    resetFilters,
  } = useDashboardStore();

  const getActiveFiltersCount = () => {
    let count = 0;
    if (!allAxes && selectedAxes.length > 0) count++;
    if (searchQuery.trim()) count++;
    if (timeRange.preset !== '7d') count++;
    return count;
  };

  const activeFiltersCount = getActiveFiltersCount();

  return (
    <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-4 mb-6">
      <div className="flex flex-col lg:flex-row gap-4 lg:items-center lg:justify-between">
        {/* Recherche */}
        <div className="flex-1 max-w-md">
          <div className="relative">
            <input
              type="text"
              placeholder="Rechercher insights, sources, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-10 py-2 text-sm border border-gray-300 dark:border-gray-600 
                         bg-white dark:bg-gray-700 rounded-lg focus:outline-none focus:ring-2 
                         focus:ring-blue-500 text-gray-900 dark:text-gray-100"
            />
            <svg className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            {searchQuery && (
              <button
                onClick={clearSearch}
                className="absolute right-3 top-2 p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
              >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Filtres par période */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Période :</span>
          <div className="flex gap-1">
            {timePresets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setTimePreset(preset.value)}
                className={`px-3 py-1 text-xs rounded-md transition-colors ${
                  timeRange.preset === preset.value
                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700'
                    : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        {/* Filtres par axes */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Axes :</span>
          <button
            onClick={selectAllAxes}
            className={`px-2 py-1 text-xs rounded-md transition-colors ${
              allAxes
                ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            Tous
          </button>
          <div className="flex gap-1">
            {(Object.keys(axisConfig) as AxisType[]).slice(0, 4).map((axis) => {
              const config = axisConfig[axis];
              const isSelected = allAxes || selectedAxes.includes(axis);
              return (
                <button
                  key={axis}
                  onClick={() => toggleAxis(axis)}
                  className={`px-2 py-1 text-xs rounded-md transition-colors flex items-center gap-1 ${
                    isSelected
                      ? 'bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 border border-blue-300 dark:border-blue-700'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                  title={config.label}
                >
                  <span>{config.icon}</span>
                  <span className="hidden sm:inline">{config.label}</span>
                </button>
              );
            })}
            {(Object.keys(axisConfig) as AxisType[]).length > 4 && (
              <button className="px-2 py-1 text-xs rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600">
                +{(Object.keys(axisConfig) as AxisType[]).length - 4}
              </button>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {activeFiltersCount > 0 && (
            <>
              <span className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs px-2 py-1 rounded-full">
                {activeFiltersCount} filtre{activeFiltersCount > 1 ? 's' : ''}
              </span>
              <button
                onClick={resetFilters}
                className="px-3 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-800 
                           dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md transition-colors"
              >
                Réinitialiser
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
} 