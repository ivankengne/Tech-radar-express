"use client";

import React, { useState, useEffect } from 'react';
import { 
  RadarChart as RechartsRadarChart, 
  PolarGrid, 
  PolarAngleAxis, 
  PolarRadiusAxis, 
  Radar, 
  ResponsiveContainer, 
  Legend,
  Tooltip 
} from 'recharts';
import { useTheme } from '@/components/ui/ThemeProvider';

interface RadarDataPoint {
  axis: string;
  label: string;
  currentWeek: number;
  lastWeek: number;
  maxValue: number;
  icon: string;
  color: string;
}

interface RadarChartProps {
  data?: RadarDataPoint[];
  isLoading?: boolean;
  height?: number;
  showComparison?: boolean;
  animate?: boolean;
}

const defaultRadarData: RadarDataPoint[] = [
  {
    axis: 'frontend',
    label: 'Frontend',
    currentWeek: 85,
    lastWeek: 75,
    maxValue: 100,
    icon: '🎨',
    color: '#3b82f6', // blue
  },
  {
    axis: 'backend',
    label: 'Backend',
    currentWeek: 72,
    lastWeek: 68,
    maxValue: 100,
    icon: '⚙️',
    color: '#10b981', // green
  },
  {
    axis: 'ai-ml',
    label: 'IA/ML',
    currentWeek: 95,
    lastWeek: 82,
    maxValue: 100,
    icon: '🤖',
    color: '#8b5cf6', // purple
  },
  {
    axis: 'devops',
    label: 'DevOps',
    currentWeek: 64,
    lastWeek: 71,
    maxValue: 100,
    icon: '🚀',
    color: '#f97316', // orange
  },
  {
    axis: 'mobile',
    label: 'Mobile',
    currentWeek: 58,
    lastWeek: 52,
    maxValue: 100,
    icon: '📱',
    color: '#ec4899', // pink
  },
  {
    axis: 'data',
    label: 'Data',
    currentWeek: 77,
    lastWeek: 79,
    maxValue: 100,
    icon: '📊',
    color: '#eab308', // yellow
  },
  {
    axis: 'security',
    label: 'Sécurité',
    currentWeek: 41,
    lastWeek: 38,
    maxValue: 100,
    icon: '🔒',
    color: '#ef4444', // red
  },
  {
    axis: 'cloud',
    label: 'Cloud',
    currentWeek: 69,
    lastWeek: 73,
    maxValue: 100,
    icon: '☁️',
    color: '#6366f1', // indigo
  },
];

export function RadarChart({ 
  data = defaultRadarData, 
  isLoading = false, 
  height = 400,
  showComparison = true,
  animate = true 
}: RadarChartProps) {
  const themeContext = useTheme();
  const resolvedTheme = themeContext?.resolvedTheme || 'light';
  const [animatedData, setAnimatedData] = useState(data.map(item => ({ ...item, currentWeek: 0, lastWeek: 0 })));
  const [selectedMetric, setSelectedMetric] = useState<'volume' | 'growth'>('volume');

  // Animation des données au montage
  useEffect(() => {
    if (animate) {
      const timer = setTimeout(() => {
        setAnimatedData(data);
      }, 500);
      return () => clearTimeout(timer);
    } else {
      setAnimatedData(data);
    }
  }, [data, animate]);

  // Calculer les données à afficher selon la métrique sélectionnée
  const displayData = animatedData.map(item => {
    if (selectedMetric === 'growth') {
      const growth = item.lastWeek > 0 ? ((item.currentWeek - item.lastWeek) / item.lastWeek) * 100 : 0;
      return {
        ...item,
        value: Math.max(0, Math.min(100, growth + 50)), // Normaliser entre 0-100 avec 50 comme baseline
        displayValue: `${growth > 0 ? '+' : ''}${growth.toFixed(1)}%`,
      };
    }
    return {
      ...item,
      value: item.currentWeek,
      displayValue: `${item.currentWeek}%`,
    };
  });

  const isDark = resolvedTheme === 'dark';
  
  // Couleurs adaptées au thème
  const gridColor = isDark ? '#374151' : '#e5e7eb';
  const textColor = isDark ? '#d1d5db' : '#374151';
  const backgroundOpacity = isDark ? 0.1 : 0.05;

  // Tooltip personnalisé
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = data.find(item => item.label === label);
      return (
        <div className="bg-white dark:bg-gray-800 p-4 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{dataPoint?.icon}</span>
            <h3 className="font-semibold text-gray-900 dark:text-gray-100">{label}</h3>
          </div>
          
          {selectedMetric === 'volume' ? (
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">Cette semaine:</span>
                <span className="font-medium text-blue-600 dark:text-blue-400">
                  {dataPoint?.currentWeek}%
                </span>
              </div>
              {showComparison && (
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Semaine passée:</span>
                  <span className="font-medium text-gray-500">
                    {dataPoint?.lastWeek}%
                  </span>
                </div>
              )}
              {dataPoint && (
                <div className="flex justify-between items-center pt-1 border-t border-gray-200 dark:border-gray-600">
                  <span className="text-sm text-gray-600 dark:text-gray-400">Évolution:</span>
                  <span className={`font-medium ${
                    dataPoint.currentWeek > dataPoint.lastWeek 
                      ? 'text-green-600 dark:text-green-400' 
                      : dataPoint.currentWeek < dataPoint.lastWeek
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-gray-500'
                  }`}>
                    {dataPoint.currentWeek > dataPoint.lastWeek ? '↗' : 
                     dataPoint.currentWeek < dataPoint.lastWeek ? '↘' : '→'} 
                    {((dataPoint.currentWeek - dataPoint.lastWeek) / dataPoint.lastWeek * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600 dark:text-gray-400">Croissance:</span>
                <span className="font-medium text-purple-600 dark:text-purple-400">
                  {payload[0]?.payload?.displayValue}
                </span>
              </div>
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  // Calculer les stats globales
  const totalVolume = data.reduce((sum, item) => sum + item.currentWeek, 0);
  const averageVolume = totalVolume / data.length;
  const topPerformer = data.reduce((max, item) => 
    item.currentWeek > max.currentWeek ? item : max
  );
  const mostImproved = data.reduce((max, item) => {
    const growth = ((item.currentWeek - item.lastWeek) / item.lastWeek) * 100;
    const maxGrowth = ((max.currentWeek - max.lastWeek) / max.lastWeek) * 100;
    return growth > maxGrowth ? item : max;
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="h-8 bg-gray-300 dark:bg-gray-600 rounded animate-pulse w-48" />
        <div className={`h-${height/16} bg-gray-200 dark:bg-gray-700 rounded-lg animate-pulse`} />
        <div className="grid grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header avec contrôles */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
            Radar Technologique
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {selectedMetric === 'volume' 
              ? 'Volume d\'activité par axe technologique' 
              : 'Croissance relative par axe technologique'}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value as 'volume' | 'growth')}
            className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 
                       bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 
                       focus:ring-blue-500 text-gray-900 dark:text-gray-100"
          >
            <option value="volume">Volume d'activité</option>
            <option value="growth">Croissance</option>
          </select>
        </div>
      </div>

      {/* Graphique radar */}
      <div className="relative">
        <ResponsiveContainer width="100%" height={height}>
          <RechartsRadarChart data={displayData} margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
            <PolarGrid 
              stroke={gridColor}
              strokeWidth={1}
            />
            <PolarAngleAxis 
              dataKey="label" 
              tick={{ 
                fill: textColor, 
                fontSize: 12, 
                fontWeight: 500 
              }}
              className="text-sm"
            />
            <PolarRadiusAxis 
              angle={90} 
              domain={[0, selectedMetric === 'growth' ? 100 : 100]}
              tick={{ 
                fill: textColor, 
                fontSize: 10 
              }}
              tickCount={6}
            />
            
            <Radar
              name={selectedMetric === 'volume' ? 'Cette semaine' : 'Croissance'}
              dataKey="value"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={backgroundOpacity + 0.1}
              strokeWidth={2}
              dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            />
            
            {showComparison && selectedMetric === 'volume' && (
              <Radar
                name="Semaine passée"
                dataKey="lastWeek"
                stroke="#9ca3af"
                fill="#9ca3af"
                fillOpacity={backgroundOpacity}
                strokeWidth={1}
                strokeDasharray="5 5"
                dot={{ fill: '#9ca3af', strokeWidth: 1, r: 2 }}
              />
            )}
            
            <Tooltip content={<CustomTooltip />} />
            
            {showComparison && selectedMetric === 'volume' && (
              <Legend 
                wrapperStyle={{ 
                  color: textColor,
                  fontSize: '12px',
                  paddingTop: '10px'
                }}
              />
            )}
          </RechartsRadarChart>
        </ResponsiveContainer>
      </div>

      {/* Statistiques rapides */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">📊</span>
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Volume Moyen</span>
          </div>
          <div className="text-2xl font-bold text-blue-900 dark:text-blue-100">
            {averageVolume.toFixed(1)}%
          </div>
        </div>

        <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{topPerformer.icon}</span>
            <span className="text-sm font-medium text-green-700 dark:text-green-300">Top Performer</span>
          </div>
          <div className="text-lg font-bold text-green-900 dark:text-green-100">
            {topPerformer.label}
          </div>
          <div className="text-sm text-green-600 dark:text-green-400">
            {topPerformer.currentWeek}% d'activité
          </div>
        </div>

        <div className="p-4 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl">{mostImproved.icon}</span>
            <span className="text-sm font-medium text-purple-700 dark:text-purple-300">Plus Forte Croissance</span>
          </div>
          <div className="text-lg font-bold text-purple-900 dark:text-purple-100">
            {mostImproved.label}
          </div>
          <div className="text-sm text-purple-600 dark:text-purple-400">
            +{(((mostImproved.currentWeek - mostImproved.lastWeek) / mostImproved.lastWeek) * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Légende des axes */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {data.map((item) => (
          <div key={item.axis} className="flex items-center gap-2 p-2 rounded-lg bg-gray-50 dark:bg-gray-800/50">
            <div 
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: item.color }}
            />
            <span className="text-xl">{item.icon}</span>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {item.label}
            </span>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-auto">
              {item.currentWeek}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
} 