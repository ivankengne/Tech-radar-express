"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { 
  Filter, 
  RefreshCw, 
  Bookmark, 
  BookmarkCheck, 
  ExternalLink, 
  Clock,
  TrendingUp,
  Activity,
  Zap,
  Settings,
  Eye,
  AlertTriangle
} from 'lucide-react';
import { useWebSocket, WebSocketMessage } from '@/hooks/useWebSocket';

interface ActivityItem {
  id: string;
  type: string;
  priority: string;
  source: string;
  title: string;
  description: string;
  details: Record<string, any>;
  timestamp: string;
  user_id?: string;
  source_name?: string;
  url?: string;
  tags: string[];
  tech_areas: string[];
  impact_score: number;
  read: boolean;
  bookmarked: boolean;
}

interface ActivityStats {
  period_hours: number;
  total_activities: number;
  activities_24h: number;
  activities_by_type: Record<string, number>;
  activities_by_priority: Record<string, number>;
  avg_impact_score: number;
  most_active_source: string;
  last_activity?: string;
}

interface ActivityFeedProps {
  className?: string;
  maxHeight?: string;
  autoRefresh?: boolean;
  showFilters?: boolean;
  showStats?: boolean;
}

const PRIORITY_COLORS = {
  low: 'bg-gray-500',
  normal: 'bg-blue-500',
  high: 'bg-orange-500',
  urgent: 'bg-red-500',
  critical: 'bg-red-700'
};

const PRIORITY_LABELS = {
  low: 'Faible',
  normal: 'Normale',
  high: 'Élevée',
  urgent: 'Urgente',
  critical: 'Critique'
};

const TYPE_ICONS = {
  insight_discovered: '💡',
  critical_alert: '🚨',
  custom_alert: '⚠️',
  source_crawled: '📄',
  daily_summary: '📋',
  focus_mode: '🎯',
  source_added: '📂',
  user_search: '🔍',
  system_update: '⚙️',
  crawl_started: '🔄',
  crawl_completed: '✅',
  llm_analysis: '🤖'
};

export default function ActivityFeed({ 
  className = "", 
  maxHeight = "600px",
  autoRefresh = true,
  showFilters = true,
  showStats = true
}: ActivityFeedProps): React.ReactElement {
  // État principal
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [stats, setStats] = useState<ActivityStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(true);
  const [offset, setOffset] = useState(0);
  
  // État des filtres
  const [filters, setFilters] = useState({
    types: '',
    priorities: '',
    sources: '',
    tech_areas: '',
    since_hours: 24,
    include_system: true
  });
  
  // État UI
  const [showFiltersPanel, setShowFiltersPanel] = useState(false);
  const [newActivitiesCount, setNewActivitiesCount] = useState(0);
  
  // Références
  const containerRef = useRef<HTMLDivElement>(null);
  const loadingRef = useRef<HTMLDivElement>(null);

  // WebSocket temps réel
  const handleWsMessage = useCallback((message: WebSocketMessage) => {
    // On s'intéresse uniquement aux nouveaux éléments d'activité
    if (message.data?.event === 'new_activity' && message.data?.activity) {
      const activity: ActivityItem = {
        // On merge les propriétés avec des valeurs par défaut
        ...message.data.activity,
        details: message.data.activity.details || {},
        tags: message.data.activity.tags || [],
        tech_areas: message.data.activity.tech_areas || [],
        read: false,
        bookmarked: false
      }

      setActivities(prev => [activity, ...prev])

      // Si l'utilisateur n'est pas tout en haut du flux, afficher le badge "Nouveau"
      if (containerRef.current && containerRef.current.scrollTop > 100) {
        setNewActivitiesCount(prev => prev + 1)
      }
    }
  }, [])

  const { isConnected: wsConnected, send: wsSend } = useWebSocket({
    url: process.env.NEXT_PUBLIC_WS_DASHBOARD_URL || `ws://${typeof window !== 'undefined' ? window.location.hostname : 'localhost'}:8000/ws/dashboard`,
    onMessage: handleWsMessage
  })

  // Abonnement au topic "activity_feed" lorsque la connexion est établie
  useEffect(() => {
    if (wsConnected) {
      wsSend({ type: 'subscribe', topics: ['activity_feed'] })
    }
  }, [wsConnected, wsSend])

  // Chargement initial
  useEffect(() => {
    loadActivities(true);
    if (showStats) {
      loadStats();
    }
  }, [filters, showStats]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      loadActivities(true);
    }, 30000); // 30 secondes
    
    return () => clearInterval(interval);
  }, [autoRefresh, filters]);

  // Intersection Observer pour défilement infini
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loading) {
          loadMoreActivities();
        }
      },
      { threshold: 0.1 }
    );

    if (loadingRef.current) {
      observer.observe(loadingRef.current);
    }

    return () => observer.disconnect();
  }, [hasMore, loading]);

  const loadActivities = async (reset = false) => {
    if (loading && !reset) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams({
        limit: '20',
        offset: reset ? '0' : offset.toString(),
        include_system: filters.include_system.toString(),
        since_hours: filters.since_hours.toString()
      });
      
      if (filters.types) params.append('types', filters.types);
      if (filters.priorities) params.append('priorities', filters.priorities);
      if (filters.sources) params.append('sources', filters.sources);
      if (filters.tech_areas) params.append('tech_areas', filters.tech_areas);
      
      const response = await fetch(`/api/activity-feed/activities?${params}`);
      
      if (!response.ok) {
        throw new Error('Erreur lors du chargement des activités');
      }
      
      const data = await response.json();
      
      if (reset) {
        setActivities(data.activities);
        setOffset(data.activities.length);
      } else {
        setActivities(prev => [...prev, ...data.activities]);
        setOffset(prev => prev + data.activities.length);
      }
      
      setHasMore(data.has_more);
      
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const loadMoreActivities = () => {
    if (!loading && hasMore) {
      loadActivities(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch(`/api/activity-feed/stats?since_hours=${filters.since_hours}`);
      if (response.ok) {
        const data = await response.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Erreur chargement stats:', err);
    }
  };

  const handleMarkAsRead = async (activityId: string) => {
    try {
      const response = await fetch(`/api/activity-feed/activities/${activityId}/read`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setActivities(prev => 
          prev.map(activity => 
            activity.id === activityId 
              ? { ...activity, read: true }
              : activity
          )
        );
      }
    } catch (err) {
      console.error('Erreur marquage lu:', err);
    }
  };

  const handleToggleBookmark = async (activityId: string) => {
    try {
      const response = await fetch(`/api/activity-feed/activities/${activityId}/bookmark`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const data = await response.json();
        setActivities(prev => 
          prev.map(activity => 
            activity.id === activityId 
              ? { ...activity, bookmarked: data.bookmarked }
              : activity
          )
        );
      }
    } catch (err) {
      console.error('Erreur bookmark:', err);
    }
  };

  const handleScrollToTop = () => {
    containerRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
    setNewActivitiesCount(0);
    loadActivities(true);
  };

  const formatTimeAgo = (timestamp: string) => {
    const now = new Date();
    const time = new Date(timestamp);
    const diffInSeconds = Math.floor((now.getTime() - time.getTime()) / 1000);
    
    if (diffInSeconds < 60) return 'À l\'instant';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
    return `${Math.floor(diffInSeconds / 86400)}j`;
  };

  const getImpactColor = (score: number) => {
    if (score >= 0.8) return 'text-red-600';
    if (score >= 0.6) return 'text-orange-600';
    if (score >= 0.4) return 'text-yellow-600';
    return 'text-green-600';
  };

  return (
    <Card className={`relative ${className}`}>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Activity className="w-5 h-5" />
            Flux d'Activité Temps Réel
          </CardTitle>
          <div className="flex items-center gap-2">
            {showFilters && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowFiltersPanel(!showFiltersPanel)}
                className={showFiltersPanel ? 'bg-blue-50' : ''}
              >
                <Filter className="w-4 h-4" />
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadActivities(true)}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
        
        {/* Statistiques */}
        {showStats && stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{stats.total_activities}</div>
              <div className="text-sm text-blue-600">Total activités</div>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{stats.activities_24h}</div>
              <div className="text-sm text-green-600">Dernières 24h</div>
            </div>
            <div className="bg-orange-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{stats.avg_impact_score.toFixed(1)}</div>
              <div className="text-sm text-orange-600">Impact moyen</div>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{stats.most_active_source}</div>
              <div className="text-sm text-purple-600">Source active</div>
            </div>
          </div>
        )}
        
        {/* Panneau de filtres */}
        {showFiltersPanel && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Types</label>
                <Select
                  value={filters.types}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, types: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tous les types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Tous les types</SelectItem>
                    <SelectItem value="insight_discovered">Insights</SelectItem>
                    <SelectItem value="critical_alert">Alertes critiques</SelectItem>
                    <SelectItem value="source_crawled">Sources crawlées</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Priorité</label>
                <Select
                  value={filters.priorities}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, priorities: value }))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Toutes priorités" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Toutes priorités</SelectItem>
                    <SelectItem value="critical">Critique</SelectItem>
                    <SelectItem value="high">Élevée</SelectItem>
                    <SelectItem value="normal">Normale</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Période</label>
                <Select
                  value={filters.since_hours.toString()}
                  onValueChange={(value) => setFilters(prev => ({ ...prev, since_hours: parseInt(value) }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Dernière heure</SelectItem>
                    <SelectItem value="6">6 dernières heures</SelectItem>
                    <SelectItem value="24">24 dernières heures</SelectItem>
                    <SelectItem value="168">Dernière semaine</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>
        )}
      </CardHeader>

      <CardContent className="p-0">
        {/* Nouveau contenu disponible */}
        {newActivitiesCount > 0 && (
          <div className="mx-4 mb-4">
            <Button
              onClick={handleScrollToTop}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white"
            >
              <TrendingUp className="w-4 h-4 mr-2" />
              {newActivitiesCount} nouvelle{newActivitiesCount > 1 ? 's' : ''} activité{newActivitiesCount > 1 ? 's' : ''}
            </Button>
          </div>
        )}

        {/* Liste des activités */}
        <div 
          ref={containerRef}
          className="overflow-y-auto px-4"
          style={{ maxHeight }}
        >
          {error && (
            <div className="bg-red-50 border border-red-200 p-4 rounded-lg mb-4">
              <div className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-4 h-4" />
                {error}
              </div>
            </div>
          )}

          <div className="space-y-3">
            {activities.map((activity) => (
              <div
                key={activity.id}
                className={`border rounded-lg p-4 transition-all duration-200 hover:shadow-md ${
                  !activity.read ? 'bg-blue-50 border-blue-200' : 'bg-white'
                } ${activity.bookmarked ? 'ring-2 ring-yellow-200' : ''}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-lg">
                        {TYPE_ICONS[activity.type as keyof typeof TYPE_ICONS] || '📌'}
                      </span>
                      <h4 className="font-medium text-gray-900 line-clamp-1">
                        {activity.title}
                      </h4>
                      <Badge 
                        className={`text-white text-xs ${
                          PRIORITY_COLORS[activity.priority as keyof typeof PRIORITY_COLORS]
                        }`}
                      >
                        {PRIORITY_LABELS[activity.priority as keyof typeof PRIORITY_LABELS]}
                      </Badge>
                      {activity.impact_score > 0 && (
                        <Badge 
                          variant="outline"
                          className={getImpactColor(activity.impact_score)}
                        >
                          <Zap className="w-3 h-3 mr-1" />
                          {(activity.impact_score * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>
                    
                    <p className="text-gray-600 text-sm mb-2 line-clamp-2">
                      {activity.description}
                    </p>
                    
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatTimeAgo(activity.timestamp)}
                      </div>
                      {activity.source_name && (
                        <div className="flex items-center gap-1">
                          <Settings className="w-3 h-3" />
                          {activity.source_name}
                        </div>
                      )}
                      {activity.tech_areas.length > 0 && (
                        <div className="flex gap-1">
                          {activity.tech_areas.slice(0, 2).map((area) => (
                            <Badge key={area} variant="secondary" className="text-xs">
                              {area}
                            </Badge>
                          ))}
                          {activity.tech_areas.length > 2 && (
                            <span className="text-gray-400">+{activity.tech_areas.length - 2}</span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-1 ml-4">
                    {!activity.read && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleMarkAsRead(activity.id)}
                        title="Marquer comme lu"
                      >
                        <Eye className="w-4 h-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleToggleBookmark(activity.id)}
                      title={activity.bookmarked ? "Retirer des favoris" : "Ajouter aux favoris"}
                    >
                      {activity.bookmarked ? (
                        <BookmarkCheck className="w-4 h-4 text-yellow-500" />
                      ) : (
                        <Bookmark className="w-4 h-4" />
                      )}
                    </Button>
                    {activity.url && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(activity.url, '_blank')}
                        title="Ouvrir le lien"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Loading indicator pour le défilement infini */}
          {hasMore && (
            <div ref={loadingRef} className="py-4 text-center">
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span className="text-sm text-gray-500">Chargement...</span>
                </div>
              ) : (
                <span className="text-sm text-gray-400">Faites défiler pour charger plus</span>
              )}
            </div>
          )}

          {!hasMore && activities.length > 0 && (
            <div className="py-4 text-center text-sm text-gray-400">
              Toutes les activités ont été chargées
            </div>
          )}

          {activities.length === 0 && !loading && (
            <div className="py-8 text-center text-gray-500">
              <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Aucune activité trouvée</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
