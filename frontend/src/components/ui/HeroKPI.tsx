"use client";

import React, { useState, useEffect } from 'react';

interface KPIData {
  id: string;
  title: string;
  value: string | number;
  change: number;
  changeType: 'increase' | 'decrease' | 'neutral';
  icon: string;
  description: string;
  trend: number[];
  color: 'blue' | 'green' | 'purple' | 'orange' | 'red';
}

interface HeroKPIProps {
  data?: KPIData[];
  isLoading?: boolean;
}

const defaultKPIData: KPIData[] = [
  {
    id: 'sources',
    title: 'Sources Actives',
    value: 24,
    change: 12.5,
    changeType: 'increase',
    icon: '📡',
    description: 'Sources de veille configurées et opérationnelles',
    trend: [45, 52, 48, 61, 70, 65, 72],
    color: 'blue',
  },
  {
    id: 'insights',
    title: 'Insights Générés',
    value: 156,
    change: 8.3,
    changeType: 'increase',
    icon: '💡',
    description: 'Insights IA générés cette semaine',
    trend: [12, 19, 15, 25, 32, 28, 35],
    color: 'green',
  },
  {
    id: 'alerts',
    title: 'Alertes Critiques',
    value: 3,
    change: -25.0,
    changeType: 'decrease',
    icon: '🚨',
    description: 'Alertes nécessitant une attention immédiate',
    trend: [8, 6, 7, 5, 4, 5, 3],
    color: 'red',
  },
  {
    id: 'coverage',
    title: 'Couverture Tech',
    value: '94%',
    change: 5.2,
    changeType: 'increase',
    icon: '🎯',
    description: 'Pourcentage de couverture des technologies cibles',
    trend: [78, 82, 85, 88, 90, 92, 94],
    color: 'purple',
  },
];

export function HeroKPI({ data = defaultKPIData, isLoading = false }: HeroKPIProps) {
  const [flippedCards, setFlippedCards] = useState<Set<string>>(new Set());
  const [animatedValues, setAnimatedValues] = useState<Record<string, number>>({});

  // Animation des valeurs au montage
  useEffect(() => {
    const timer = setTimeout(() => {
      const newAnimatedValues: Record<string, number> = {};
      data.forEach((kpi) => {
        if (typeof kpi.value === 'number') {
          newAnimatedValues[kpi.id] = kpi.value;
        }
      });
      setAnimatedValues(newAnimatedValues);
    }, 500);

    return () => clearTimeout(timer);
  }, [data]);

  const toggleFlip = (cardId: string) => {
    setFlippedCards(prev => {
      const newSet = new Set(prev);
      if (newSet.has(cardId)) {
        newSet.delete(cardId);
      } else {
        newSet.add(cardId);
      }
      return newSet;
    });
  };

  const getColorClasses = (color: KPIData['color']) => {
    const colorMap = {
      blue: {
        bg: 'bg-blue-50 dark:bg-blue-900/20',
        border: 'border-blue-200 dark:border-blue-800',
        icon: 'text-blue-600 dark:text-blue-400',
        value: 'text-blue-900 dark:text-blue-100',
        accent: 'bg-blue-500',
      },
      green: {
        bg: 'bg-green-50 dark:bg-green-900/20',
        border: 'border-green-200 dark:border-green-800',
        icon: 'text-green-600 dark:text-green-400',
        value: 'text-green-900 dark:text-green-100',
        accent: 'bg-green-500',
      },
      purple: {
        bg: 'bg-purple-50 dark:bg-purple-900/20',
        border: 'border-purple-200 dark:border-purple-800',
        icon: 'text-purple-600 dark:text-purple-400',
        value: 'text-purple-900 dark:text-purple-100',
        accent: 'bg-purple-500',
      },
      orange: {
        bg: 'bg-orange-50 dark:bg-orange-900/20',
        border: 'border-orange-200 dark:border-orange-800',
        icon: 'text-orange-600 dark:text-orange-400',
        value: 'text-orange-900 dark:text-orange-100',
        accent: 'bg-orange-500',
      },
      red: {
        bg: 'bg-red-50 dark:bg-red-900/20',
        border: 'border-red-200 dark:border-red-800',
        icon: 'text-red-600 dark:text-red-400',
        value: 'text-red-900 dark:text-red-100',
        accent: 'bg-red-500',
      },
    };
    return colorMap[color];
  };

  const getChangeIcon = (changeType: KPIData['changeType']) => {
    switch (changeType) {
      case 'increase':
        return <span className="text-green-500">↗</span>;
      case 'decrease':
        return <span className="text-red-500">↘</span>;
      default:
        return <span className="text-gray-500">→</span>;
    }
  };

  const renderMiniChart = (trend: number[], color: string) => {
    const max = Math.max(...trend);
    const min = Math.min(...trend);
    const range = max - min;

    return (
      <div className="flex items-end h-8 gap-1">
        {trend.map((value, index) => {
          const height = range === 0 ? 50 : ((value - min) / range) * 100;
          return (
            <div
              key={index}
              className={`w-1 bg-current opacity-60 rounded-full transition-all duration-300`}
              style={{ height: `${Math.max(height, 10)}%` }}
            />
          );
        })}
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-48 bg-gray-200 dark:bg-gray-800 rounded-xl animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      {data.map((kpi) => {
        const isFlipped = flippedCards.has(kpi.id);
        const colors = getColorClasses(kpi.color);

        return (
          <div
            key={kpi.id}
            className="group h-48 cursor-pointer"
            onClick={() => toggleFlip(kpi.id)}
          >
            <div
              className={`relative w-full h-full transition-transform duration-700 
                         ${isFlipped ? 'scale-105' : ''}`}
            >
              {!isFlipped ? (
                // Face avant
                <div
                  className={`w-full h-full rounded-xl p-6 border-2 ${colors.bg} ${colors.border} 
                             hover:shadow-lg transition-all duration-300 group-hover:scale-105`}
                >
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">
                        {kpi.title}
                      </h3>
                      <div className={`text-3xl font-bold ${colors.value} mb-2`}>
                        {typeof kpi.value === 'number' ? (
                          <CountUpAnimation target={kpi.value} />
                        ) : (
                          kpi.value
                        )}
                      </div>
                    </div>
                    <div className={`text-3xl ${colors.icon}`}>
                      {kpi.icon}
                    </div>
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1 text-sm">
                      {getChangeIcon(kpi.changeType)}
                      <span
                        className={`font-medium ${
                          kpi.changeType === 'increase'
                            ? 'text-green-600 dark:text-green-400'
                            : kpi.changeType === 'decrease'
                            ? 'text-red-600 dark:text-red-400'
                            : 'text-gray-600 dark:text-gray-400'
                        }`}
                      >
                        {Math.abs(kpi.change)}%
                      </span>
                      <span className="text-gray-500 text-xs">vs semaine passée</span>
                    </div>
                    <button className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                  </div>
                </div>
              ) : (
                // Face arrière
                <div
                  className={`w-full h-full rounded-xl p-6 border-2 ${colors.bg} ${colors.border} 
                             hover:shadow-lg transition-all duration-300`}
                >
                  <div className="h-full flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                      <span className={`text-2xl ${colors.icon}`}>{kpi.icon}</span>
                      <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">
                        Tendance 7 jours
                      </h3>
                    </div>

                    <div className="flex-1 flex flex-col justify-center">
                      <div className={colors.icon}>
                        {renderMiniChart(kpi.trend, kpi.color)}
                      </div>
                    </div>

                    <div className="mt-4">
                      <p className="text-xs text-gray-600 dark:text-gray-400 leading-relaxed">
                        {kpi.description}
                      </p>
                    </div>

                    <button className="mt-3 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-left">
                      Cliquer pour retourner ↶
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Composant d'animation pour les nombres
function CountUpAnimation({ target }: { target: number }) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    if (target === 0) return;

    const increment = target / 30;
    let currentValue = 0;

    const timer = setInterval(() => {
      currentValue += increment;
      if (currentValue >= target) {
        setCurrent(target);
        clearInterval(timer);
      } else {
        setCurrent(Math.floor(currentValue));
      }
    }, 50);

    return () => clearInterval(timer);
  }, [target]);

  return <span>{current}</span>;
} 