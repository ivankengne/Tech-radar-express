"use client";

import React, { useState, useEffect } from 'react';

interface TimelineItem {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  axis: 'frontend' | 'backend' | 'ai-ml' | 'devops' | 'mobile' | 'data' | 'security' | 'cloud';
  priority: 'low' | 'medium' | 'high' | 'critical';
  source: string;
  tags: string[];
  impact: 'disruptive' | 'emerging' | 'incremental' | 'declining';
  readTime?: number;
}

interface TimelineProps {
  items?: TimelineItem[];
  isLoading?: boolean;
  showFilters?: boolean;
  maxItems?: number;
}

const defaultTimelineData: TimelineItem[] = [
  {
    id: '1',
    title: 'Next.js 15 introduit les Server Actions améliorées',
    description: 'Les nouvelles Server Actions permettent une meilleure gestion des formulaires avec validation côté serveur intégrée et cache optimisé.',
    timestamp: '2025-01-15T14:30:00Z',
    axis: 'frontend',
    priority: 'high',
    source: 'Vercel Blog',
    tags: ['Next.js', 'React', 'Server Actions'],
    impact: 'emerging',
    readTime: 5,
  },
  {
    id: '2',
    title: 'OpenAI lance GPT-5 avec capacités multimodales avancées',
    description: 'GPT-5 intègre vision, audio et génération de code avec une précision accrue de 40% sur les benchmarks techniques.',
    timestamp: '2025-01-15T11:15:00Z',
    axis: 'ai-ml',
    priority: 'critical',
    source: 'OpenAI Research',
    tags: ['GPT-5', 'Multimodal', 'Code Generation'],
    impact: 'disruptive',
    readTime: 8,
  },
  {
    id: '3',
    title: 'Kubernetes 1.32 améliore la sécurité des pods',
    description: 'Nouvelle politique de sécurité par défaut et isolation renforcée des workloads dans les environnements multi-tenant.',
    timestamp: '2025-01-15T09:45:00Z',
    axis: 'devops',
    priority: 'medium',
    source: 'CNCF',
    tags: ['Kubernetes', 'Security', 'Containers'],
    impact: 'incremental',
    readTime: 6,
  },
  {
    id: '4',
    title: 'FastAPI 0.120 avec support natif WebAssembly',
    description: 'Intégration WASM permettant d\'exécuter du code Python dans le navigateur pour des applications hybrides.',
    timestamp: '2025-01-14T16:20:00Z',
    axis: 'backend',
    priority: 'medium',
    source: 'FastAPI Docs',
    tags: ['FastAPI', 'WebAssembly', 'Python'],
    impact: 'emerging',
    readTime: 4,
  },
  {
    id: '5',
    title: 'React Native 0.76 unifie le développement cross-platform',
    description: 'New Architecture par défaut et meilleure performance sur iOS et Android avec Fabric et TurboModules.',
    timestamp: '2025-01-14T13:10:00Z',
    axis: 'mobile',
    priority: 'high',
    source: 'Meta Engineering',
    tags: ['React Native', 'Mobile', 'Cross-platform'],
    impact: 'emerging',
    readTime: 7,
  },
];

const axisConfig = {
  frontend: {
    label: 'Frontend',
    color: 'bg-blue-500',
    lightBg: 'bg-blue-50 dark:bg-blue-900/20',
    textColor: 'text-blue-700 dark:text-blue-300',
    icon: '🎨',
  },
  backend: {
    label: 'Backend',
    color: 'bg-green-500',
    lightBg: 'bg-green-50 dark:bg-green-900/20',
    textColor: 'text-green-700 dark:text-green-300',
    icon: '⚙️',
  },
  'ai-ml': {
    label: 'IA/ML',
    color: 'bg-purple-500',
    lightBg: 'bg-purple-50 dark:bg-purple-900/20',
    textColor: 'text-purple-700 dark:text-purple-300',
    icon: '🤖',
  },
  devops: {
    label: 'DevOps',
    color: 'bg-orange-500',
    lightBg: 'bg-orange-50 dark:bg-orange-900/20',
    textColor: 'text-orange-700 dark:text-orange-300',
    icon: '🚀',
  },
  mobile: {
    label: 'Mobile',
    color: 'bg-pink-500',
    lightBg: 'bg-pink-50 dark:bg-pink-900/20',
    textColor: 'text-pink-700 dark:text-pink-300',
    icon: '📱',
  },
  data: {
    label: 'Data',
    color: 'bg-yellow-500',
    lightBg: 'bg-yellow-50 dark:bg-yellow-900/20',
    textColor: 'text-yellow-700 dark:text-yellow-300',
    icon: '📊',
  },
  security: {
    label: 'Sécurité',
    color: 'bg-red-500',
    lightBg: 'bg-red-50 dark:bg-red-900/20',
    textColor: 'text-red-700 dark:text-red-300',
    icon: '🔒',
  },
  cloud: {
    label: 'Cloud',
    color: 'bg-indigo-500',
    lightBg: 'bg-indigo-50 dark:bg-indigo-900/20',
    textColor: 'text-indigo-700 dark:text-indigo-300',
    icon: '☁️',
  },
};

const priorityConfig = {
  low: { label: 'Faible', color: 'text-gray-500', icon: '●' },
  medium: { label: 'Moyen', color: 'text-yellow-500', icon: '●' },
  high: { label: 'Élevé', color: 'text-orange-500', icon: '●' },
  critical: { label: 'Critique', color: 'text-red-500', icon: '●' },
};

const impactConfig = {
  disruptive: { label: 'Disruptif', color: 'text-red-600 dark:text-red-400', icon: '🔥' },
  emerging: { label: 'Émergent', color: 'text-green-600 dark:text-green-400', icon: '🌱' },
  incremental: { label: 'Incrémental', color: 'text-blue-600 dark:text-blue-400', icon: '📈' },
  declining: { label: 'Déclinant', color: 'text-gray-600 dark:text-gray-400', icon: '📉' },
};

export function Timeline({ 
  items = defaultTimelineData, 
  isLoading = false, 
  showFilters = true,
  maxItems = 10 
}: TimelineProps) {
  const [filteredItems, setFilteredItems] = useState<TimelineItem[]>(items);
  const [selectedAxis, setSelectedAxis] = useState<string>('all');
  const [selectedPriority, setSelectedPriority] = useState<string>('all');
  const [visibleItems, setVisibleItems] = useState(5);

  useEffect(() => {
    let filtered = items;

    if (selectedAxis !== 'all') {
      filtered = filtered.filter(item => item.axis === selectedAxis);
    }

    if (selectedPriority !== 'all') {
      filtered = filtered.filter(item => item.priority === selectedPriority);
    }

    // Trier par timestamp décroissant
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    setFilteredItems(filtered.slice(0, maxItems));
  }, [items, selectedAxis, selectedPriority, maxItems]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60);

    if (diffInHours < 1) {
      return `Il y a ${Math.floor(diffInHours * 60)} min`;
    } else if (diffInHours < 24) {
      return `Il y a ${Math.floor(diffInHours)}h`;
    } else {
      const diffInDays = Math.floor(diffInHours / 24);
      return `Il y a ${diffInDays}j`;
    }
  };

  const loadMoreItems = () => {
    setVisibleItems(prev => Math.min(prev + 5, filteredItems.length));
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="w-4 h-4 bg-gray-300 dark:bg-gray-600 rounded-full animate-pulse mt-2" />
            <div className="flex-1 space-y-2">
              <div className="h-4 bg-gray-300 dark:bg-gray-600 rounded animate-pulse w-3/4" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-full" />
              <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded animate-pulse w-5/6" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {showFilters && (
        <div className="flex flex-wrap gap-4 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Axe :
            </label>
            <select
              value={selectedAxis}
              onChange={(e) => setSelectedAxis(e.target.value)}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 
                         bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 
                         focus:ring-blue-500 text-gray-900 dark:text-gray-100"
            >
              <option value="all">Tous</option>
              {Object.entries(axisConfig).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.icon} {config.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Priorité :
            </label>
            <select
              value={selectedPriority}
              onChange={(e) => setSelectedPriority(e.target.value)}
              className="px-3 py-1 text-sm border border-gray-300 dark:border-gray-600 
                         bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-2 
                         focus:ring-blue-500 text-gray-900 dark:text-gray-100"
            >
              <option value="all">Toutes</option>
              {Object.entries(priorityConfig).map(([key, config]) => (
                <option key={key} value={key}>
                  {config.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="relative">
        {/* Ligne verticale de la timeline */}
        <div className="absolute left-6 top-0 bottom-0 w-0.5 bg-gray-200 dark:bg-gray-700" />

        <div className="space-y-6">
          {filteredItems.slice(0, visibleItems).map((item, index) => {
            const axisStyle = axisConfig[item.axis];
            const priorityStyle = priorityConfig[item.priority];
            const impactStyle = impactConfig[item.impact];

            return (
              <div key={item.id} className="relative flex gap-6 group">
                {/* Pastille de couleur */}
                <div className="relative z-10">
                  <div 
                    className={`w-4 h-4 ${axisStyle.color} rounded-full border-4 border-white 
                               dark:border-gray-900 shadow-md group-hover:scale-125 transition-transform duration-200`}
                    title={`${axisStyle.label} - ${priorityStyle.label}`}
                  />
                </div>

                {/* Contenu */}
                <div className="flex-1 pb-6">
                  <div className={`p-4 rounded-lg border border-gray-200 dark:border-gray-700 
                                 bg-white dark:bg-gray-800 hover:shadow-md transition-all duration-200
                                 group-hover:border-gray-300 dark:group-hover:border-gray-600`}>
                    
                    {/* Header */}
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                                        ${axisStyle.lightBg} ${axisStyle.textColor}`}>
                          {axisStyle.icon} {axisStyle.label}
                        </span>
                        <span className={`inline-flex items-center gap-1 text-xs ${priorityStyle.color}`}>
                          {priorityStyle.icon} {priorityStyle.label}
                        </span>
                        <span className={`inline-flex items-center gap-1 text-xs ${impactStyle.color}`}>
                          {impactStyle.icon} {impactStyle.label}
                        </span>
                      </div>
                      
                      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                        {item.readTime && (
                          <span className="flex items-center gap-1">
                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            {item.readTime} min
                          </span>
                        )}
                        <span>{formatTimestamp(item.timestamp)}</span>
                      </div>
                    </div>

                    {/* Titre et description */}
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2 
                                   group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {item.title}
                    </h3>
                    <p className="text-gray-600 dark:text-gray-300 text-sm leading-relaxed mb-3">
                      {item.description}
                    </p>

                    {/* Tags et source */}
                    <div className="flex items-center justify-between">
                      <div className="flex flex-wrap gap-1">
                        {item.tags.slice(0, 3).map((tag) => (
                          <span key={tag} className="px-2 py-1 bg-gray-100 dark:bg-gray-700 
                                                   text-gray-600 dark:text-gray-300 text-xs rounded">
                            #{tag}
                          </span>
                        ))}
                        {item.tags.length > 3 && (
                          <span className="px-2 py-1 bg-gray-100 dark:bg-gray-700 
                                         text-gray-500 dark:text-gray-400 text-xs rounded">
                            +{item.tags.length - 3}
                          </span>
                        )}
                      </div>
                      
                      <span className="text-xs text-gray-500 dark:text-gray-400 font-medium">
                        {item.source}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bouton "Voir plus" */}
        {visibleItems < filteredItems.length && (
          <div className="flex justify-center mt-6">
            <button
              onClick={loadMoreItems}
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg 
                         transition-colors duration-200 text-sm font-medium"
            >
              Voir plus d'insights ({filteredItems.length - visibleItems} restants)
            </button>
          </div>
        )}

        {filteredItems.length === 0 && (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400">
            <div className="text-4xl mb-2">🔍</div>
            <p>Aucun insight trouvé avec ces filtres</p>
          </div>
        )}
      </div>
    </div>
  );
} 