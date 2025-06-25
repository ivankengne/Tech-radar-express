"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import SmartSourceForm from '@/components/admin/SmartSourceForm';
import { 
  Plus, 
  Edit, 
  Trash2, 
  Play, 
  Pause, 
  RefreshCw, 
  ExternalLink,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  BarChart3,
  Globe,
  Github,
  FileText,
  Rss,
  Settings,
  Activity
} from 'lucide-react';

// Types
interface Source {
  id: string;
  name: string;
  url: string;
  source_type: string;
  tech_axes: string[];
  enabled: boolean;
  crawl_frequency: number;
  max_depth: number;
  max_concurrent: number;
  chunk_size: number;
  description?: string;
  tags: string[];
  priority: number;
  created_at: string;
  last_crawled?: string;
  last_success?: string;
  crawl_count: number;
  error_count: number;
}

interface CrawlResult {
  source_id: string;
  success: boolean;
  pages_crawled: number;
  chunks_created: number;
  execution_time: number;
  error_message?: string;
  timestamp: string;
}

interface SourceStats {
  total_sources: number;
  active_sources: number;
  total_crawls: number;
  successful_crawls: number;
  failed_crawls: number;
  avg_crawl_time: number;
  sources_by_type: Record<string, number>;
  sources_by_axis: Record<string, number>;
  active_crawls: number;
  sources_with_errors: number;
}

// Constantes
const SOURCE_TYPES = [
  { value: 'website', label: 'Site Web', icon: Globe },
  { value: 'github_repo', label: 'Repository GitHub', icon: Github },
  { value: 'documentation', label: 'Documentation', icon: FileText },
  { value: 'blog', label: 'Blog', icon: FileText },
  { value: 'news', label: 'Actualités', icon: Rss },
  { value: 'rss_feed', label: 'Flux RSS', icon: Rss },
  { value: 'sitemap', label: 'Sitemap', icon: Globe }
];

const TECH_AXES = [
  { value: 'languages_frameworks', label: 'Langages & Frameworks' },
  { value: 'tools', label: 'Outils' },
  { value: 'platforms', label: 'Plateformes' },
  { value: 'techniques', label: 'Techniques' }
];

const PRIORITIES = [
  { value: 1, label: 'Très haute', color: 'bg-red-500' },
  { value: 2, label: 'Haute', color: 'bg-orange-500' },
  { value: 3, label: 'Moyenne', color: 'bg-yellow-500' },
  { value: 4, label: 'Basse', color: 'bg-blue-500' },
  { value: 5, label: 'Très basse', color: 'bg-gray-500' }
];

export default function SourcesAdminPage() {
  const [sources, setSources] = useState<Source[]>([]);
  const [stats, setStats] = useState<SourceStats | null>(null);
  const [selectedSource, setSelectedSource] = useState<Source | null>(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crawlResults, setCrawlResults] = useState<Record<string, CrawlResult[]>>({});

  // États pour le formulaire
  const [formData, setFormData] = useState({
    id: '',
    name: '',
    url: '',
    source_type: '',
    tech_axes: [] as string[],
    description: '',
    tags: [] as string[],
    priority: 1,
    crawl_frequency: 24,
    max_depth: 2,
    max_concurrent: 5,
    chunk_size: 5000
  });

  // Chargement initial
  useEffect(() => {
    loadSources();
    loadStats();
  }, []);

  const loadSources = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/sources/');
      if (!response.ok) throw new Error('Erreur chargement sources');
      
      const data = await response.json();
      setSources(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur inconnue');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/sources/stats/overview');
      if (!response.ok) throw new Error('Erreur chargement statistiques');
      
      const data = await response.json();
      setStats(data);
    } catch (err) {
      console.error('Erreur stats:', err);
    }
  };

  const loadCrawlHistory = async (sourceId: string) => {
    try {
      const response = await fetch(`/api/v1/sources/${sourceId}/crawl-history?limit=10`);
      if (!response.ok) throw new Error('Erreur chargement historique');
      
      const data = await response.json();
      setCrawlResults(prev => ({ ...prev, [sourceId]: data }));
    } catch (err) {
      console.error('Erreur historique:', err);
    }
  };

  const handleCreateSource = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/sources/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur création source');
      }

      await loadSources();
      await loadStats();
      setIsCreateMode(false);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur création');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateSource = async () => {
    if (!selectedSource) return;

    try {
      setLoading(true);
      const { id, ...updates } = formData; // Exclure l'ID des updates

      const response = await fetch(`/api/v1/sources/${selectedSource.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur mise à jour source');
      }

      await loadSources();
      await loadStats();
      setSelectedSource(null);
      resetForm();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur mise à jour');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteSource = async (sourceId: string) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette source ?')) return;

    try {
      setLoading(true);
      const response = await fetch(`/api/v1/sources/${sourceId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur suppression source');
      }

      await loadSources();
      await loadStats();
      if (selectedSource?.id === sourceId) {
        setSelectedSource(null);
        resetForm();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur suppression');
    } finally {
      setLoading(false);
    }
  };

  const handleToggleSource = async (sourceId: string) => {
    try {
      const response = await fetch(`/api/v1/sources/${sourceId}/toggle`, {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur toggle source');
      }

      await loadSources();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur toggle');
    }
  };

  const handleCrawlSource = async (sourceId: string, force = false) => {
    try {
      setLoading(true);
      const response = await fetch(`/api/v1/sources/${sourceId}/crawl?force=${force}`, {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur crawl source');
      }

      const result = await response.json();
      
      // Mise à jour de l'historique
      setCrawlResults(prev => ({
        ...prev,
        [sourceId]: [result, ...(prev[sourceId] || [])].slice(0, 10)
      }));

      await loadSources();
      await loadStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur crawl');
    } finally {
      setLoading(false);
    }
  };

  const handleCrawlAll = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/sources/crawl-all', {
        method: 'POST'
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Erreur crawl global');
      }

      // Rechargement après délai pour laisser le temps aux crawls
      setTimeout(() => {
        loadSources();
        loadStats();
      }, 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur crawl global');
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFormData({
      id: '',
      name: '',
      url: '',
      source_type: '',
      tech_axes: [],
      description: '',
      tags: [],
      priority: 1,
      crawl_frequency: 24,
      max_depth: 2,
      max_concurrent: 5,
      chunk_size: 5000
    });
  };

  const openEditMode = (source: Source) => {
    setSelectedSource(source);
    setFormData({
      id: source.id,
      name: source.name,
      url: source.url,
      source_type: source.source_type,
      tech_axes: source.tech_axes,
      description: source.description || '',
      tags: source.tags,
      priority: source.priority,
      crawl_frequency: source.crawl_frequency,
      max_depth: source.max_depth,
      max_concurrent: source.max_concurrent,
      chunk_size: source.chunk_size
    });
    setActiveTab('form');
    loadCrawlHistory(source.id);
  };

  const getSourceIcon = (type: string) => {
    const sourceType = SOURCE_TYPES.find(t => t.value === type);
    return sourceType?.icon || Globe;
  };

  const getStatusColor = (source: Source) => {
    if (!source.enabled) return 'text-gray-500';
    if (source.error_count > 0) return 'text-red-500';
    if (source.last_success) return 'text-green-500';
    return 'text-yellow-500';
  };

  const getStatusIcon = (source: Source) => {
    if (!source.enabled) return Pause;
    if (source.error_count > 0) return XCircle;
    if (source.last_success) return CheckCircle;
    return AlertTriangle;
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return 'Jamais';
    return new Date(dateString).toLocaleString('fr-FR');
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Administration des Sources</h1>
          <p className="text-muted-foreground">
            Gestion des sources de veille technologique et orchestration des crawls MCP
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={handleCrawlAll}
            disabled={loading}
            variant="outline"
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Crawler Tout
          </Button>
          <Button 
            onClick={() => {
              setIsCreateMode(true);
              setActiveTab('form');
              resetForm();
            }}
            className="flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Nouvelle Source
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => setError(null)}
            className="ml-auto"
          >
            ×
          </Button>
        </Alert>
      )}

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
          <TabsTrigger value="form">
            {isCreateMode ? 'Nouvelle Source' : selectedSource ? 'Modifier' : 'Formulaire'}
          </TabsTrigger>
          <TabsTrigger value="stats">Statistiques</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* Dashboard KPIs */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Total Sources</CardTitle>
                  <Globe className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.total_sources}</div>
                  <p className="text-xs text-muted-foreground">
                    {stats.active_sources} actives
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Crawls Total</CardTitle>
                  <Activity className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.total_crawls}</div>
                  <p className="text-xs text-muted-foreground">
                    {stats.successful_crawls} réussis
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Temps Moyen</CardTitle>
                  <Clock className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatDuration(stats.avg_crawl_time)}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Par crawl
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">Crawls Actifs</CardTitle>
                  <RefreshCw className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stats.active_crawls}</div>
                  <p className="text-xs text-muted-foreground">
                    En cours
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Aperçu des sources récentes */}
          <Card>
            <CardHeader>
              <CardTitle>Sources Récemment Crawlées</CardTitle>
              <CardDescription>
                Dernières activités de crawling
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {sources
                  .filter(s => s.last_crawled)
                  .sort((a, b) => new Date(b.last_crawled!).getTime() - new Date(a.last_crawled!).getTime())
                  .slice(0, 5)
                  .map(source => {
                    const Icon = getSourceIcon(source.source_type);
                    const StatusIcon = getStatusIcon(source);
                    
                    return (
                      <div key={source.id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          <Icon className="h-5 w-5 text-muted-foreground" />
                          <div>
                            <div className="font-medium">{source.name}</div>
                            <div className="text-sm text-muted-foreground">
                              Dernier crawl: {formatDate(source.last_crawled)}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <StatusIcon className={`h-4 w-4 ${getStatusColor(source)}`} />
                          <Badge variant="outline">
                            {source.crawl_count} crawls
                          </Badge>
                        </div>
                      </div>
                    );
                  })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sources" className="space-y-4">
          {/* Liste des sources */}
          <div className="grid gap-4">
            {sources.map(source => {
              const Icon = getSourceIcon(source.source_type);
              const StatusIcon = getStatusIcon(source);
              
              return (
                <Card key={source.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4 flex-1">
                        <Icon className="h-6 w-6 text-muted-foreground mt-1" />
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="font-semibold">{source.name}</h3>
                            <StatusIcon className={`h-4 w-4 ${getStatusColor(source)}`} />
                            <Switch
                              checked={source.enabled}
                              onCheckedChange={() => handleToggleSource(source.id)}
                            />
                          </div>
                          
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline">{source.source_type}</Badge>
                            {source.tech_axes.map(axis => (
                              <Badge key={axis} variant="secondary" className="text-xs">
                                {TECH_AXES.find(a => a.value === axis)?.label || axis}
                              </Badge>
                            ))}
                            <div className={`w-2 h-2 rounded-full ${PRIORITIES.find(p => p.value === source.priority)?.color}`} />
                          </div>
                          
                          <p className="text-sm text-muted-foreground mb-2">
                            {source.description || source.url}
                          </p>
                          
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-muted-foreground">Fréquence:</span>
                              <div>{source.crawl_frequency}h</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Crawls:</span>
                              <div>{source.crawl_count}</div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Erreurs:</span>
                              <div className={source.error_count > 0 ? 'text-red-500' : ''}>
                                {source.error_count}
                              </div>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Dernier succès:</span>
                              <div>{formatDate(source.last_success)}</div>
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex flex-col gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openEditMode(source)}
                          className="flex items-center gap-1"
                        >
                          <Edit className="h-3 w-3" />
                          Modifier
                        </Button>
                        
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCrawlSource(source.id)}
                          disabled={loading || !source.enabled}
                          className="flex items-center gap-1"
                        >
                          <Play className="h-3 w-3" />
                          Crawler
                        </Button>
                        
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => window.open(source.url, '_blank')}
                          className="flex items-center gap-1"
                        >
                          <ExternalLink className="h-3 w-3" />
                          Visiter
                        </Button>
                        
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDeleteSource(source.id)}
                          disabled={loading}
                          className="flex items-center gap-1"
                        >
                          <Trash2 className="h-3 w-3" />
                          Supprimer
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="form" className="space-y-6">
          <SmartSourceForm
            formData={formData}
            setFormData={setFormData}
            onSubmit={isCreateMode ? handleCreateSource : handleUpdateSource}
            onCancel={() => {
              setIsCreateMode(false);
              setSelectedSource(null);
              resetForm();
              setActiveTab('sources');
            }}
            loading={loading}
            isCreateMode={isCreateMode}
          />

          {/* Historique des crawls pour la source sélectionnée */}
          {selectedSource && crawlResults[selectedSource.id] && (
            <Card>
              <CardHeader>
                <CardTitle>Historique des Crawls</CardTitle>
                <CardDescription>
                  Derniers résultats de crawl pour {selectedSource.name}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {crawlResults[selectedSource.id].map((result, index) => (
                    <div key={index} className="flex items-center justify-between p-3 border rounded-lg">
                      <div className="flex items-center gap-3">
                        {result.success ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-500" />
                        )}
                        <div>
                          <div className="font-medium">
                            {formatDate(result.timestamp)}
                          </div>
                          {result.success ? (
                            <div className="text-sm text-muted-foreground">
                              {result.pages_crawled} pages, {result.chunks_created} chunks
                            </div>
                          ) : (
                            <div className="text-sm text-red-500">
                              {result.error_message}
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {formatDuration(result.execution_time)}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="stats" className="space-y-6">
          {stats && (
            <>
              {/* Statistiques par type */}
              <Card>
                <CardHeader>
                  <CardTitle>Répartition par Type</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.sources_by_type).map(([type, count]) => {
                      const typeInfo = SOURCE_TYPES.find(t => t.value === type);
                      const Icon = typeInfo?.icon || Globe;
                      
                      return (
                        <div key={type} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Icon className="h-4 w-4" />
                            <span>{typeInfo?.label || type}</span>
                          </div>
                          <Badge variant="outline">{count}</Badge>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Statistiques par axe */}
              <Card>
                <CardHeader>
                  <CardTitle>Répartition par Axe Technologique</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {Object.entries(stats.sources_by_axis).map(([axis, count]) => {
                      const axisInfo = TECH_AXES.find(a => a.value === axis);
                      
                      return (
                        <div key={axis} className="flex items-center justify-between">
                          <span>{axisInfo?.label || axis}</span>
                          <Badge variant="outline">{count}</Badge>
                        </div>
                      );
                    })}
                  </div>
                </CardContent>
              </Card>

              {/* Métriques de performance */}
              <Card>
                <CardHeader>
                  <CardTitle>Métriques de Performance</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-green-500">
                        {((stats.successful_crawls / Math.max(stats.total_crawls, 1)) * 100).toFixed(1)}%
                      </div>
                      <div className="text-sm text-muted-foreground">Taux de Succès</div>
                    </div>
                    
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold">
                        {formatDuration(stats.avg_crawl_time)}
                      </div>
                      <div className="text-sm text-muted-foreground">Temps Moyen</div>
                    </div>
                    
                    <div className="text-center p-4 border rounded-lg">
                      <div className="text-2xl font-bold text-red-500">
                        {stats.sources_with_errors}
                      </div>
                      <div className="text-sm text-muted-foreground">Sources avec Erreurs</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
} 