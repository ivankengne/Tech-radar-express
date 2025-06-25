import { useMemo } from 'react';
import { useDashboardStore, AxisType, PriorityType, ImpactType } from '@/store/dashboardStore';

// Types pour les données d'insight
export interface TechInsight {
  id: string;
  title: string;
  description: string;
  axis: AxisType;
  priority: PriorityType;
  impact: ImpactType;
  source: string;
  tags: string[];
  timestamp: Date;
  url?: string;
  confidence: number;
  trend: 'rising' | 'stable' | 'declining';
  readingTime: number;
  category: string;
}

// Types pour les données du radar chart
export interface RadarData {
  axis: AxisType;
  volume: number;
  growth: number;
  timestamp: Date;
}

// Types pour les métriques
export interface KPIData {
  activeSources: number;
  generatedInsights: number;
  criticalAlerts: number;
  techCoverage: number;
  totalInsights: number;
  weeklyGrowth: number;
  sourceHealth: number;
  trendingTopics: string[];
}

interface UseFilteredDataOptions {
  insights?: TechInsight[];
  radarData?: RadarData[];
  kpiData?: KPIData;
}

export function useFilteredData(options: UseFilteredDataOptions = {}) {
  const {
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
    sortBy,
    sortOrder,
  } = useDashboardStore();

  // Fonction de filtrage principal
  const filteredInsights = useMemo(() => {
    if (!options.insights) return [];

    const filtered = options.insights.filter(insight => {
      // Filtre par axe
      if (!allAxes && selectedAxes.length > 0) {
        if (!selectedAxes.includes(insight.axis)) {
          return false;
        }
      }

      // Filtre par source
      if (!allSources && selectedSources.length > 0) {
        if (!selectedSources.includes(insight.source)) {
          return false;
        }
      }

      // Filtre par priorité
      if (!allPriorities && selectedPriorities.length > 0) {
        if (!selectedPriorities.includes(insight.priority)) {
          return false;
        }
      }

      // Filtre par impact
      if (!allImpacts && selectedImpacts.length > 0) {
        if (!selectedImpacts.includes(insight.impact)) {
          return false;
        }
      }

      // Filtre temporel
      if (insight.timestamp < timeRange.start || insight.timestamp > timeRange.end) {
        return false;
      }

      // Recherche textuelle
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const searchableText = [
          insight.title,
          insight.description,
          insight.source,
          insight.category,
          ...insight.tags,
        ].join(' ').toLowerCase();

        if (!searchableText.includes(query)) {
          return false;
        }
      }

      return true;
    });

    // Tri des résultats
    filtered.sort((a, b) => {
      let comparison = 0;

      switch (sortBy) {
        case 'timestamp':
          comparison = a.timestamp.getTime() - b.timestamp.getTime();
          break;
        case 'priority':
          const priorityOrder = { low: 1, medium: 2, high: 3, critical: 4 };
          comparison = priorityOrder[a.priority] - priorityOrder[b.priority];
          break;
        case 'impact':
          const impactOrder = { declining: 1, incremental: 2, emerging: 3, disruptive: 4 };
          comparison = impactOrder[a.impact] - impactOrder[b.impact];
          break;
        case 'source':
          comparison = a.source.localeCompare(b.source);
          break;
        default:
          comparison = 0;
      }

      return sortOrder === 'desc' ? -comparison : comparison;
    });

    return filtered;
  }, [
    options.insights,
    selectedAxes,
    allAxes,
    selectedSources,
    allSources,
    selectedPriorities,
    allPriorities,
    selectedImpacts,
    allImpacts,
    timeRange,
    searchQuery,
    sortBy,
    sortOrder,
  ]);

  // Données filtrées pour le radar chart
  const filteredRadarData = useMemo(() => {
    if (!options.radarData) return [];

    return options.radarData.filter(data => {
      // Filtre par axe
      if (!allAxes && selectedAxes.length > 0) {
        if (!selectedAxes.includes(data.axis)) {
          return false;
        }
      }

      // Filtre temporel
      if (data.timestamp < timeRange.start || data.timestamp > timeRange.end) {
        return false;
      }

      return true;
    });
  }, [options.radarData, selectedAxes, allAxes, timeRange]);

  // Statistiques calculées
  const statistics = useMemo(() => {
    const total = filteredInsights.length;
    const originalTotal = options.insights?.length || 0;

    // Groupement par axe
    const byAxis = filteredInsights.reduce((acc, insight) => {
      acc[insight.axis] = (acc[insight.axis] || 0) + 1;
      return acc;
    }, {} as Record<AxisType, number>);

    // Groupement par priorité
    const byPriority = filteredInsights.reduce((acc, insight) => {
      acc[insight.priority] = (acc[insight.priority] || 0) + 1;
      return acc;
    }, {} as Record<PriorityType, number>);

    // Groupement par impact
    const byImpact = filteredInsights.reduce((acc, insight) => {
      acc[insight.impact] = (acc[insight.impact] || 0) + 1;
      return acc;
    }, {} as Record<ImpactType, number>);

    // Groupement par source
    const bySource = filteredInsights.reduce((acc, insight) => {
      acc[insight.source] = (acc[insight.source] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    // Sources uniques
    const uniqueSources = Array.from(new Set(filteredInsights.map(i => i.source)));

    // Tags les plus fréquents
    const tagFrequency = filteredInsights
      .flatMap(i => i.tags)
      .reduce((acc, tag) => {
        acc[tag] = (acc[tag] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);

    const topTags = Object.entries(tagFrequency)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10)
      .map(([tag, count]) => ({ tag, count }));

    // Tendances
    const trends = {
      rising: filteredInsights.filter(i => i.trend === 'rising').length,
      stable: filteredInsights.filter(i => i.trend === 'stable').length,
      declining: filteredInsights.filter(i => i.trend === 'declining').length,
    };

    // Moyennes
    const averageConfidence = filteredInsights.length > 0 
      ? filteredInsights.reduce((sum, i) => sum + i.confidence, 0) / filteredInsights.length 
      : 0;

    const averageReadingTime = filteredInsights.length > 0
      ? filteredInsights.reduce((sum, i) => sum + i.readingTime, 0) / filteredInsights.length
      : 0;

    return {
      total,
      originalTotal,
      filteredPercentage: originalTotal > 0 ? (total / originalTotal) * 100 : 0,
      byAxis,
      byPriority,
      byImpact,
      bySource,
      uniqueSources: uniqueSources.length,
      topTags,
      trends,
      averageConfidence,
      averageReadingTime,
      timeSpan: {
        start: timeRange.start,
        end: timeRange.end,
        days: Math.ceil((timeRange.end.getTime() - timeRange.start.getTime()) / (1000 * 60 * 60 * 24)),
      },
    };
  }, [filteredInsights, options.insights, timeRange]);

  // Helpers pour la pagination
  const getPaginatedData = (page: number, itemsPerPage: number) => {
    const start = page * itemsPerPage;
    const end = start + itemsPerPage;
    return {
      data: filteredInsights.slice(start, end),
      totalPages: Math.ceil(filteredInsights.length / itemsPerPage),
      currentPage: page,
      hasNextPage: end < filteredInsights.length,
      hasPrevPage: page > 0,
    };
  };

  // Helpers pour l'export
  const getExportData = () => {
    return {
      insights: filteredInsights,
      statistics,
      filters: {
        axes: allAxes ? 'all' : selectedAxes,
        sources: allSources ? 'all' : selectedSources,
        priorities: allPriorities ? 'all' : selectedPriorities,
        impacts: allImpacts ? 'all' : selectedImpacts,
        timeRange,
        searchQuery,
        sortBy,
        sortOrder,
      },
      exportDate: new Date(),
    };
  };

  return {
    // Données filtrées
    insights: filteredInsights,
    radarData: filteredRadarData,
    
    // Statistiques et métriques
    statistics,
    
    // Helpers
    getPaginatedData,
    getExportData,
    
    // État des filtres
    hasActiveFilters: !allAxes || !allSources || !allPriorities || !allImpacts || searchQuery.trim() !== '',
    filterCount: statistics.total,
    originalCount: statistics.originalTotal,
  };
}

// Hook spécialisé pour les données de démonstration
export function useMockData(): UseFilteredDataOptions {
  return useMemo(() => {
    // Données d'exemple pour le développement
    const mockInsights: TechInsight[] = [
      {
        id: '1',
        title: 'Next.js 15 App Router Performance Improvements',
        description: 'Nouvelle architecture App Router avec amélioration des performances de 40%',
        axis: 'frontend',
        priority: 'high',
        impact: 'emerging',
        source: 'Vercel Blog',
        tags: ['Next.js', 'Performance', 'React', 'SSR'],
        timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
        url: 'https://nextjs.org/blog/next-15',
        confidence: 0.92,
        trend: 'rising',
        readingTime: 8,
        category: 'Framework',
      },
      {
        id: '2',
        title: 'FastAPI + Pydantic v2 Migration Guide',
        description: 'Guide complet pour migrer vers Pydantic v2 avec FastAPI',
        axis: 'backend',
        priority: 'medium',
        impact: 'incremental',
        source: 'FastAPI Docs',
        tags: ['FastAPI', 'Pydantic', 'Python', 'API'],
        timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
        url: 'https://fastapi.tiangolo.com/pydantic-v2',
        confidence: 0.87,
        trend: 'stable',
        readingTime: 12,
        category: 'Backend Framework',
      },
      {
        id: '3',
        title: 'OpenAI GPT-4 Turbo avec Vision multimodale',
        description: 'Nouvelle capacité de traitement d\'images et texte simultané',
        axis: 'ai-ml',
        priority: 'critical',
        impact: 'disruptive',
        source: 'OpenAI Research',
        tags: ['OpenAI', 'GPT-4', 'Vision', 'Multimodal', 'AI'],
        timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
        url: 'https://openai.com/research/gpt-4-vision',
        confidence: 0.95,
        trend: 'rising',
        readingTime: 6,
        category: 'AI Model',
      },
    ];

    const mockRadarData: RadarData[] = [
      { axis: 'frontend', volume: 85, growth: 12, timestamp: new Date() },
      { axis: 'backend', volume: 78, growth: 8, timestamp: new Date() },
      { axis: 'ai-ml', volume: 92, growth: 25, timestamp: new Date() },
      { axis: 'devops', volume: 73, growth: 15, timestamp: new Date() },
      { axis: 'mobile', volume: 65, growth: 5, timestamp: new Date() },
      { axis: 'data', volume: 82, growth: 18, timestamp: new Date() },
      { axis: 'security', volume: 70, growth: 10, timestamp: new Date() },
      { axis: 'cloud', volume: 88, growth: 20, timestamp: new Date() },
    ];

    const mockKpiData: KPIData = {
      activeSources: 8,
      generatedInsights: 156,
      criticalAlerts: 3,
      techCoverage: 92,
      totalInsights: 1247,
      weeklyGrowth: 15.2,
      sourceHealth: 96,
      trendingTopics: ['Next.js 15', 'GPT-4 Vision', 'Kubernetes', 'TypeScript 5.5'],
    };

    return {
      insights: mockInsights,
      radarData: mockRadarData,
      kpiData: mockKpiData,
    };
  }, []);
} 