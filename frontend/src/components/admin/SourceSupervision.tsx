"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Database, 
  Globe, 
  TrendingUp, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  XCircle, 
  Loader2, 
  BarChart3,
  RefreshCw,
  Search,
  Filter,
  Plus,
  Eye,
  Zap,
  Target,
  Activity,
  Link,
  Lightbulb
} from 'lucide-react'
import { Input } from "@/components/ui/input"

// Types pour la supervision
interface SourceOverview {
  total_local_sources: number
  active_local_sources: number
  total_mcp_sources: number
  active_crawls: number
  success_rate: number
  error_rate: number
  avg_crawl_time: number
  last_updated: string
}

interface SourceDistribution {
  by_axis: Record<string, number>
  by_type: Record<string, number>
}

interface RecentCrawl {
  source_id: string
  name: string
  last_crawled: string
  success: boolean
  crawl_count: number
  error_count: number
}

interface ProblematicSource {
  source_id: string
  name: string
  error_count: number
  crawl_count: number
  error_rate: number
  last_crawled?: string
  enabled: boolean
}

interface MCPSource {
  source_id: string
  summary: string
  total_words?: number
  created_at: string
  updated_at: string
  domain: string
  content_size: string
  freshness: string
}

interface LocalSource {
  id: string
  name: string
  url: string
  source_type: string
  tech_axes: string[]
  enabled: boolean
  crawl_frequency: number
  priority: number
  description?: string
  tags: string[]
  created_at: string
  last_crawled?: string
  last_success?: string
  crawl_count: number
  error_count: number
  health_status: string
}

interface Recommendation {
  type: string
  title: string
  description: string
  priority: 'high' | 'medium' | 'low'
  action: string
  source_id?: string
  reason?: string
  url?: string
}

interface SupervisionDashboard {
  overview: SourceOverview
  distribution: SourceDistribution
  recent_activity: {
    recent_crawls: RecentCrawl[]
    problematic_sources: ProblematicSource[]
    popular_mcp_sources: MCPSource[]
  }
  recommendations: Recommendation[]
  health_status: {
    overall: string
    active_sources_percentage: number
    problematic_sources_count: number
    mcp_integration: string
  }
}

const SourceSupervision: React.FC = () => {
  // États
  const [dashboard, setDashboard] = useState<SupervisionDashboard | null>(null)
  const [localSources, setLocalSources] = useState<LocalSource[]>([])
  const [mcpSources, setMCPSources] = useState<MCPSource[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTab, setSelectedTab] = useState("overview")
  const [searchTerm, setSearchTerm] = useState("")
  const [filterAxis, setFilterAxis] = useState("")
  const [filterType, setFilterType] = useState("")

  // Chargement des données
  const fetchDashboardData = useCallback(async () => {
    try {
      const [dashboardRes, localRes, mcpRes] = await Promise.all([
        fetch('/api/v1/source-supervision/dashboard'),
        fetch('/api/v1/source-supervision/sources/local'),
        fetch('/api/v1/source-supervision/sources/mcp?limit=100')
      ])

      if (dashboardRes.ok) {
        const dashboardData = await dashboardRes.json()
        setDashboard(dashboardData.dashboard)
      }

      if (localRes.ok) {
        const localData = await localRes.json()
        setLocalSources(localData.sources)
      }

      if (mcpRes.ok) {
        const mcpData = await mcpRes.json()
        setMCPSources(mcpData.sources)
      }

    } catch (error) {
      console.error('Erreur récupération données supervision:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDashboardData()
    
    // Auto-refresh toutes les 60 secondes
    const interval = setInterval(fetchDashboardData, 60000)
    return () => clearInterval(interval)
  }, [fetchDashboardData])

  // Fonctions utilitaires
  const getHealthColor = (status: string) => {
    switch (status) {
      case 'healthy': return 'bg-green-500'
      case 'warning': return 'bg-yellow-500'
      case 'critical': return 'bg-red-500'
      case 'disabled': return 'bg-gray-500'
      case 'new': return 'bg-blue-500'
      case 'stale': return 'bg-orange-500'
      default: return 'bg-gray-400'
    }
  }

  const getHealthIcon = (status: string) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4" />
      case 'warning': return <AlertTriangle className="w-4 h-4" />
      case 'critical': return <XCircle className="w-4 h-4" />
      case 'disabled': return <Clock className="w-4 h-4" />
      case 'new': return <Plus className="w-4 h-4" />
      case 'stale': return <Clock className="w-4 h-4" />
      default: return <Activity className="w-4 h-4" />
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'border-red-500 bg-red-50'
      case 'medium': return 'border-yellow-500 bg-yellow-50'
      case 'low': return 'border-blue-500 bg-blue-50'
      default: return 'border-gray-500 bg-gray-50'
    }
  }

  const getContentSizeBadge = (size: string) => {
    switch (size) {
      case 'xlarge': return <Badge className="bg-purple-500">XL</Badge>
      case 'large': return <Badge className="bg-blue-500">L</Badge>
      case 'medium': return <Badge className="bg-green-500">M</Badge>
      case 'small': return <Badge className="bg-yellow-500">S</Badge>
      default: return <Badge variant="outline">?</Badge>
    }
  }

  // Filtrage des sources
  const filteredLocalSources = localSources.filter(source => {
    const matchesSearch = !searchTerm || 
      source.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      source.url.toLowerCase().includes(searchTerm.toLowerCase())
    
    const matchesAxis = !filterAxis || source.tech_axes.includes(filterAxis)
    const matchesType = !filterType || source.source_type === filterType
    
    return matchesSearch && matchesAxis && matchesType
  })

  const filteredMCPSources = mcpSources.filter(source => {
    return !searchTerm || 
      source.source_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      source.summary.toLowerCase().includes(searchTerm.toLowerCase())
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin" />
        <span className="ml-2">Chargement de la supervision...</span>
      </div>
    )
  }

  if (!dashboard) {
    return (
      <Alert className="border-red-500 bg-red-50">
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          Impossible de charger les données de supervision
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Supervision des Sources</h2>
          <p className="text-gray-600">Dashboard de supervision avec intégration MCP</p>
        </div>
        
        <Button
          variant="outline"
          size="sm"
          onClick={fetchDashboardData}
        >
          <RefreshCw className="w-4 h-4 mr-1" />
          Actualiser
        </Button>
      </div>

      {/* Statut global */}
      <Alert className={dashboard.health_status.overall === 'healthy' ? 'border-green-500 bg-green-50' : 
                       dashboard.health_status.overall === 'warning' ? 'border-yellow-500 bg-yellow-50' : 
                       'border-red-500 bg-red-50'}>
        <Activity className="h-4 w-4" />
        <AlertDescription>
          Statut global: <strong>{dashboard.health_status.overall}</strong> • 
          {dashboard.health_status.active_sources_percentage}% sources actives • 
          {dashboard.health_status.problematic_sources_count} sources problématiques • 
          MCP: {dashboard.health_status.mcp_integration}
        </AlertDescription>
      </Alert>

      {/* Métriques principales */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sources Locales</CardTitle>
            <Database className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.overview.active_local_sources}/{dashboard.overview.total_local_sources}</div>
            <p className="text-xs text-gray-600">Actives/Total</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sources MCP</CardTitle>
            <Globe className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.overview.total_mcp_sources}</div>
            <p className="text-xs text-gray-600">Disponibles</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Taux de Succès</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.overview.success_rate}%</div>
            <p className="text-xs text-gray-600">Crawls réussis</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Crawls Actifs</CardTitle>
            <Zap className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard.overview.active_crawls}</div>
            <p className="text-xs text-gray-600">En cours</p>
          </CardContent>
        </Card>
      </div>

      {/* Recommandations */}
      {dashboard.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Lightbulb className="w-5 h-5 text-yellow-500" />
              Recommandations
            </CardTitle>
            <CardDescription>
              Suggestions d'amélioration basées sur l'analyse des sources
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dashboard.recommendations.slice(0, 3).map((rec, index) => (
                <div key={index} className={`p-3 border rounded-lg ${getPriorityColor(rec.priority)}`}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium">{rec.title}</h4>
                      <p className="text-sm text-gray-700 mt-1">{rec.description}</p>
                      <p className="text-xs text-gray-600 mt-2">{rec.action}</p>
                    </div>
                    <Badge variant="outline" className={
                      rec.priority === 'high' ? 'text-red-600 border-red-300' :
                      rec.priority === 'medium' ? 'text-yellow-600 border-yellow-300' :
                      'text-blue-600 border-blue-300'
                    }>
                      {rec.priority}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Onglets principaux */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
          <TabsTrigger value="local">Sources Locales</TabsTrigger>
          <TabsTrigger value="mcp">Sources MCP</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        {/* Vue d'ensemble */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Distribution par axe */}
            <Card>
              <CardHeader>
                <CardTitle>Distribution par Axe Technologique</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(dashboard.distribution.by_axis).map(([axis, count]) => (
                    <div key={axis} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{axis.replace('_', ' ')}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-blue-500 h-2 rounded-full"
                            style={{ width: `${(count / Math.max(...Object.values(dashboard.distribution.by_axis))) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium w-8">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Distribution par type */}
            <Card>
              <CardHeader>
                <CardTitle>Distribution par Type</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(dashboard.distribution.by_type).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between">
                      <span className="text-sm capitalize">{type.replace('_', ' ')}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-20 bg-gray-200 rounded-full h-2">
                          <div 
                            className="bg-green-500 h-2 rounded-full"
                            style={{ width: `${(count / Math.max(...Object.values(dashboard.distribution.by_type))) * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-medium w-8">{count}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Crawls récents */}
            <Card>
              <CardHeader>
                <CardTitle>Activité Récente</CardTitle>
                <CardDescription>Derniers crawls effectués</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {dashboard.recent_activity.recent_crawls.slice(0, 5).map((crawl, index) => (
                    <div key={index} className="flex items-center justify-between p-2 border rounded">
                      <div className="flex items-center gap-3">
                        {crawl.success ? 
                          <CheckCircle className="w-4 h-4 text-green-500" /> : 
                          <XCircle className="w-4 h-4 text-red-500" />
                        }
                        <div>
                          <p className="font-medium text-sm">{crawl.name}</p>
                          <p className="text-xs text-gray-600">
                            {new Date(crawl.last_crawled).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <div className="text-right text-xs">
                        <p>{crawl.crawl_count} crawls</p>
                        {crawl.error_count > 0 && (
                          <p className="text-red-600">{crawl.error_count} erreurs</p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Sources problématiques */}
            <Card>
              <CardHeader>
                <CardTitle>Sources Problématiques</CardTitle>
                <CardDescription>Sources avec taux d'erreur élevé</CardDescription>
              </CardHeader>
              <CardContent>
                {dashboard.recent_activity.problematic_sources.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">Aucune source problématique</p>
                ) : (
                  <div className="space-y-3">
                    {dashboard.recent_activity.problematic_sources.map((source, index) => (
                      <div key={index} className="p-3 border rounded-lg bg-red-50 border-red-200">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-red-800">{source.name}</p>
                            <p className="text-sm text-red-700">
                              {source.error_count}/{source.crawl_count} erreurs ({source.error_rate}%)
                            </p>
                            {source.last_crawled && (
                              <p className="text-xs text-red-600">
                                Dernier crawl: {new Date(source.last_crawled).toLocaleString()}
                              </p>
                            )}
                          </div>
                          <Badge variant="outline" className={source.enabled ? 'text-green-600' : 'text-gray-600'}>
                            {source.enabled ? 'Actif' : 'Inactif'}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Sources locales */}
        <TabsContent value="local" className="space-y-4">
          {/* Filtres */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-64">
                  <Input
                    placeholder="Rechercher par nom ou URL..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full"
                  />
                </div>
                <select 
                  value={filterAxis} 
                  onChange={(e) => setFilterAxis(e.target.value)}
                  className="px-3 py-2 border rounded-md"
                >
                  <option value="">Tous les axes</option>
                  <option value="languages_frameworks">Languages & Frameworks</option>
                  <option value="tools">Tools</option>
                  <option value="platforms">Platforms</option>
                  <option value="techniques">Techniques</option>
                </select>
                <select 
                  value={filterType} 
                  onChange={(e) => setFilterType(e.target.value)}
                  className="px-3 py-2 border rounded-md"
                >
                  <option value="">Tous les types</option>
                  <option value="website">Website</option>
                  <option value="blog">Blog</option>
                  <option value="documentation">Documentation</option>
                  <option value="github_repo">GitHub Repo</option>
                  <option value="news">News</option>
                </select>
              </div>
            </CardContent>
          </Card>

          {/* Liste des sources locales */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {filteredLocalSources.map((source) => (
              <Card key={source.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{source.name}</CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge className={getHealthColor(source.health_status)}>
                        {getHealthIcon(source.health_status)}
                        {source.health_status}
                      </Badge>
                      <Badge variant="outline">
                        {source.source_type}
                      </Badge>
                    </div>
                  </div>
                  <CardDescription className="flex items-center gap-1">
                    <Link className="w-3 h-3" />
                    {source.url}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {/* Axes technologiques */}
                  <div>
                    <p className="text-sm font-medium mb-1">Axes technologiques:</p>
                    <div className="flex flex-wrap gap-1">
                      {source.tech_axes.map((axis) => (
                        <Badge key={axis} variant="outline" className="text-xs">
                          {axis.replace('_', ' ')}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  {/* Statistiques */}
                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Crawls</p>
                      <p className="font-medium">{source.crawl_count}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Erreurs</p>
                      <p className="font-medium text-red-600">{source.error_count}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Fréquence</p>
                      <p className="font-medium">{source.crawl_frequency}h</p>
                    </div>
                  </div>

                  {/* Dernier crawl */}
                  {source.last_crawled && (
                    <div className="text-xs text-gray-600">
                      Dernier crawl: {new Date(source.last_crawled).toLocaleString()}
                    </div>
                  )}

                  {/* Tags */}
                  {source.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {source.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs bg-gray-50">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Sources MCP */}
        <TabsContent value="mcp" className="space-y-4">
          {/* Recherche */}
          <Card>
            <CardContent className="pt-6">
              <Input
                placeholder="Rechercher dans les sources MCP..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full"
              />
            </CardContent>
          </Card>

          {/* Liste des sources MCP */}
          <div className="space-y-4">
            {filteredMCPSources.map((source) => (
              <Card key={source.source_id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{source.source_id}</CardTitle>
                    <div className="flex items-center gap-2">
                      {getContentSizeBadge(source.content_size)}
                      <Badge variant="outline" className={
                        source.freshness === 'today' || source.freshness === 'yesterday' ? 'text-green-600 border-green-300' :
                        source.freshness === 'this_week' ? 'text-blue-600 border-blue-300' :
                        'text-gray-600 border-gray-300'
                      }>
                        {source.freshness.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                  <CardDescription>
                    Domaine: {source.domain} • 
                    {source.total_words ? ` ${source.total_words.toLocaleString()} mots` : ' Taille inconnue'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-gray-700 mb-3">{source.summary}</p>
                  <div className="flex justify-between text-xs text-gray-500">
                    <span>Créé: {new Date(source.created_at).toLocaleDateString()}</span>
                    <span>Mis à jour: {new Date(source.updated_at).toLocaleDateString()}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Analytics */}
        <TabsContent value="analytics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Analytics de Supervision</CardTitle>
              <CardDescription>
                Métriques détaillées et tendances des sources
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8">
                <BarChart3 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Analytics détaillées à venir</p>
                <p className="text-sm text-gray-400">
                  Graphiques de tendances, comparaisons temporelles et insights
                </p>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default SourceSupervision