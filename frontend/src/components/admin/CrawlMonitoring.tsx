"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  XCircle, 
  Loader2, 
  Zap,
  TrendingUp,
  AlertCircle,
  RefreshCw,
  Pause,
  Play,
  Eye
} from 'lucide-react'
import { useWebSocket } from '@/hooks/useWebSocket'

// Types pour le monitoring
interface CrawlProgress {
  source_id: string
  status: 'pending' | 'starting' | 'connecting' | 'crawling' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'timeout' | 'rate_limited'
  current_step: string
  start_time: string
  pages_discovered: number
  pages_crawled: number
  pages_processed: number
  chunks_created: number
  errors_count: number
  last_error?: string
  estimated_completion?: string
  duration_seconds: number
  progress_percentage: number
  metadata: Record<string, any>
}

interface CrawlError {
  source_id: string
  error_type: string
  error_message: string
  error_details: Record<string, any>
  timestamp: string
  url?: string
  retry_count: number
  resolved: boolean
}

interface CrawlAlert {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  title: string
  message: string
  source_id?: string
  timestamp: string
  acknowledged: boolean
  metadata: Record<string, any>
}

interface MonitoringMetrics {
  total_crawls: number
  active_crawls: number
  successful_crawls: number
  failed_crawls: number
  success_rate: number
  error_rate: number
  avg_crawl_time: number
  avg_pages_per_crawl: number
  avg_chunks_per_crawl: number
  throughput_per_hour: number
  last_updated: string
}

const CrawlMonitoring: React.FC = () => {
  // États
  const [activeCrawls, setActiveCrawls] = useState<CrawlProgress[]>([])
  const [errors, setErrors] = useState<CrawlError[]>([])
  const [alerts, setAlerts] = useState<CrawlAlert[]>([])
  const [metrics, setMetrics] = useState<MonitoringMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [selectedTab, setSelectedTab] = useState("overview")

  // WebSocket pour les mises à jour temps réel
  const { lastMessage, isConnected } = useWebSocket({
    url: `ws://localhost:8000/api/v1/crawl-monitoring/ws`,
    reconnectAttempts: 5,
    reconnectInterval: 3000,
    autoConnect: true
  })

  // Fonction pour récupérer les données
  const fetchMonitoringData = useCallback(async () => {
    try {
      const [crawlsRes, errorsRes, alertsRes, metricsRes] = await Promise.all([
        fetch('/api/v1/crawl-monitoring/crawls/active'),
        fetch('/api/v1/crawl-monitoring/errors?limit=50'),
        fetch('/api/v1/crawl-monitoring/alerts?acknowledged=false&limit=20'),
        fetch('/api/v1/crawl-monitoring/metrics')
      ])

      if (crawlsRes.ok) {
        const crawlsData = await crawlsRes.json()
        setActiveCrawls(crawlsData.active_crawls || [])
      }

      if (errorsRes.ok) {
        const errorsData = await errorsRes.json()
        setErrors(errorsData.errors || [])
      }

      if (alertsRes.ok) {
        const alertsData = await alertsRes.json()
        setAlerts(alertsData.alerts || [])
      }

      if (metricsRes.ok) {
        const metricsData = await metricsRes.json()
        setMetrics(metricsData.metrics)
      }

    } catch (error) {
      console.error('Erreur récupération données monitoring:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Gestion des messages WebSocket
  useEffect(() => {
    if (lastMessage) {
      try {
        const data = JSON.parse(lastMessage.data)
        
        if (data.type === 'status_update') {
          setActiveCrawls(data.active_crawls || [])
        } else if (data.type === 'crawl_cancelled') {
          setActiveCrawls(prev => prev.filter(crawl => crawl.source_id !== data.source_id))
        } else if (data.type === 'alert_acknowledged') {
          setAlerts(prev => prev.map(alert => 
            alert.id === data.alert_id ? { ...alert, acknowledged: true } : alert
          ))
        }
      } catch (error) {
        console.error('Erreur traitement message WebSocket:', error)
      }
    }
  }, [lastMessage])

  // Chargement initial et auto-refresh
  useEffect(() => {
    fetchMonitoringData()
    
    if (autoRefresh) {
      const interval = setInterval(fetchMonitoringData, 30000) // Refresh toutes les 30s
      return () => clearInterval(interval)
    }
  }, [fetchMonitoringData, autoRefresh])

  // Fonction pour annuler un crawl
  const cancelCrawl = async (sourceId: string) => {
    try {
      const response = await fetch(`/api/v1/crawl-monitoring/crawls/${sourceId}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Annulé par l\'utilisateur' })
      })

      if (response.ok) {
        await fetchMonitoringData()
      }
    } catch (error) {
      console.error('Erreur annulation crawl:', error)
    }
  }

  // Fonction pour acquitter une alerte
  const acknowledgeAlert = async (alertId: string) => {
    try {
      const response = await fetch(`/api/v1/crawl-monitoring/alerts/${alertId}/acknowledge`, {
        method: 'POST'
      })

      if (response.ok) {
        setAlerts(prev => prev.map(alert => 
          alert.id === alertId ? { ...alert, acknowledged: true } : alert
        ))
      }
    } catch (error) {
      console.error('Erreur acquittement alerte:', error)
    }
  }

  // Fonction pour obtenir la couleur du statut
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'crawling': case 'processing': return 'bg-blue-500'
      case 'failed': case 'timeout': return 'bg-red-500'
      case 'cancelled': return 'bg-gray-500'
      case 'rate_limited': return 'bg-yellow-500'
      default: return 'bg-gray-400'
    }
  }

  // Fonction pour obtenir l'icône du statut
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4" />
      case 'crawling': case 'processing': return <Loader2 className="w-4 h-4 animate-spin" />
      case 'failed': case 'timeout': return <XCircle className="w-4 h-4" />
      case 'cancelled': return <Pause className="w-4 h-4" />
      case 'rate_limited': return <Clock className="w-4 h-4" />
      default: return <Activity className="w-4 h-4" />
    }
  }

  // Fonction pour obtenir la couleur de l'alerte
  const getAlertColor = (level: string) => {
    switch (level) {
      case 'critical': return 'border-red-500 bg-red-50'
      case 'error': return 'border-red-400 bg-red-25'
      case 'warning': return 'border-yellow-500 bg-yellow-50'
      default: return 'border-blue-500 bg-blue-50'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin" />
        <span className="ml-2">Chargement du monitoring...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* En-tête avec statut de connexion */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Monitoring des Crawls</h2>
          <p className="text-gray-600">Surveillance temps réel des crawls MCP</p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Statut WebSocket */}
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connecté' : 'Déconnecté'}
            </span>
          </div>

          {/* Contrôles */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {autoRefresh ? 'Pause' : 'Auto'}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchMonitoringData}
          >
            <RefreshCw className="w-4 h-4" />
            Actualiser
          </Button>
        </div>
      </div>

      {/* Métriques globales */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Crawls Actifs</CardTitle>
              <Activity className="h-4 w-4 text-blue-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.active_crawls}</div>
              <p className="text-xs text-gray-600">En cours d'exécution</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Taux de Succès</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.success_rate.toFixed(1)}%</div>
              <p className="text-xs text-gray-600">
                {metrics.successful_crawls}/{metrics.total_crawls} réussis
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Temps Moyen</CardTitle>
              <Clock className="h-4 w-4 text-orange-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.avg_crawl_time.toFixed(1)}s</div>
              <p className="text-xs text-gray-600">Par crawl</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Débit</CardTitle>
              <Zap className="h-4 w-4 text-purple-500" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.throughput_per_hour}</div>
              <p className="text-xs text-gray-600">Crawls/heure</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Alertes critiques */}
      {alerts.filter(a => !a.acknowledged && ['critical', 'error'].includes(a.level)).length > 0 && (
        <Alert className="border-red-500 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {alerts.filter(a => !a.acknowledged && ['critical', 'error'].includes(a.level)).length} alerte(s) critique(s) nécessitent votre attention
          </AlertDescription>
        </Alert>
      )}

      {/* Onglets principaux */}
      <Tabs value={selectedTab} onValueChange={setSelectedTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
          <TabsTrigger value="active">Crawls Actifs</TabsTrigger>
          <TabsTrigger value="errors">Erreurs</TabsTrigger>
          <TabsTrigger value="alerts">Alertes</TabsTrigger>
        </TabsList>

        {/* Vue d'ensemble */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Crawls actifs résumé */}
            <Card>
              <CardHeader>
                <CardTitle>Crawls en Cours</CardTitle>
                <CardDescription>
                  {activeCrawls.length} crawl(s) actif(s)
                </CardDescription>
              </CardHeader>
              <CardContent>
                {activeCrawls.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">Aucun crawl en cours</p>
                ) : (
                  <div className="space-y-3">
                    {activeCrawls.slice(0, 5).map((crawl) => (
                      <div key={crawl.source_id} className="flex items-center justify-between p-3 border rounded-lg">
                        <div className="flex items-center gap-3">
                          {getStatusIcon(crawl.status)}
                          <div>
                            <p className="font-medium">{crawl.source_id}</p>
                            <p className="text-sm text-gray-600">{crawl.current_step}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge className={getStatusColor(crawl.status)}>
                            {crawl.status}
                          </Badge>
                          <p className="text-xs text-gray-500 mt-1">
                            {crawl.progress_percentage}%
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Erreurs récentes */}
            <Card>
              <CardHeader>
                <CardTitle>Erreurs Récentes</CardTitle>
                <CardDescription>
                  {errors.length} erreur(s) dans les dernières 24h
                </CardDescription>
              </CardHeader>
              <CardContent>
                {errors.length === 0 ? (
                  <p className="text-gray-500 text-center py-4">Aucune erreur récente</p>
                ) : (
                  <div className="space-y-3">
                    {errors.slice(0, 5).map((error, index) => (
                      <div key={index} className="p-3 border rounded-lg bg-red-50 border-red-200">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <p className="font-medium text-red-800">{error.source_id}</p>
                            <p className="text-sm text-red-700">{error.error_message}</p>
                            <p className="text-xs text-red-600 mt-1">
                              {error.error_type} • {new Date(error.timestamp).toLocaleString()}
                            </p>
                          </div>
                          {error.retry_count > 0 && (
                            <Badge variant="outline" className="text-xs">
                              Retry {error.retry_count}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Crawls actifs détaillés */}
        <TabsContent value="active" className="space-y-4">
          {activeCrawls.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500">Aucun crawl en cours d'exécution</p>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {activeCrawls.map((crawl) => (
                <Card key={crawl.source_id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{crawl.source_id}</CardTitle>
                      <Badge className={getStatusColor(crawl.status)}>
                        {crawl.status}
                      </Badge>
                    </div>
                    <CardDescription>{crawl.current_step}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Barre de progression */}
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span>Progression</span>
                        <span>{crawl.progress_percentage}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-2">
                        <div 
                          className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${crawl.progress_percentage}%` }}
                        />
                      </div>
                    </div>

                    {/* Statistiques */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <p className="text-gray-600">Pages crawlées</p>
                        <p className="font-medium">{crawl.pages_crawled}/{crawl.pages_discovered}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Chunks créés</p>
                        <p className="font-medium">{crawl.chunks_created}</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Durée</p>
                        <p className="font-medium">{Math.floor(crawl.duration_seconds)}s</p>
                      </div>
                      <div>
                        <p className="text-gray-600">Erreurs</p>
                        <p className="font-medium text-red-600">{crawl.errors_count}</p>
                      </div>
                    </div>

                    {/* Erreur récente */}
                    {crawl.last_error && (
                      <Alert className="border-red-200 bg-red-50">
                        <AlertTriangle className="h-4 w-4" />
                        <AlertDescription className="text-sm">
                          {crawl.last_error}
                        </AlertDescription>
                      </Alert>
                    )}

                    {/* Actions */}
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => cancelCrawl(crawl.source_id)}
                      >
                        <Pause className="w-4 h-4 mr-1" />
                        Annuler
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Erreurs */}
        <TabsContent value="errors" className="space-y-4">
          {errors.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                <p className="text-gray-500">Aucune erreur récente</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {errors.map((error, index) => (
                <Card key={index}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <XCircle className="w-5 h-5 text-red-500" />
                        {error.source_id}
                      </CardTitle>
                      <Badge variant="outline" className="text-red-600 border-red-300">
                        {error.error_type}
                      </Badge>
                    </div>
                    <CardDescription>
                      {new Date(error.timestamp).toLocaleString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-800 mb-2">{error.error_message}</p>
                    {error.url && (
                      <p className="text-sm text-gray-600 mb-2">URL: {error.url}</p>
                    )}
                    {error.retry_count > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {error.retry_count} tentative(s) de retry
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Alertes */}
        <TabsContent value="alerts" className="space-y-4">
          {alerts.length === 0 ? (
            <Card>
              <CardContent className="text-center py-8">
                <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                <p className="text-gray-500">Aucune alerte active</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {alerts.map((alert) => (
                <Card key={alert.id} className={getAlertColor(alert.level)}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg flex items-center gap-2">
                        <AlertCircle className={`w-5 h-5 ${
                          alert.level === 'critical' ? 'text-red-500' :
                          alert.level === 'error' ? 'text-red-400' :
                          alert.level === 'warning' ? 'text-yellow-500' :
                          'text-blue-500'
                        }`} />
                        {alert.title}
                      </CardTitle>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={
                          alert.level === 'critical' ? 'text-red-600 border-red-300' :
                          alert.level === 'error' ? 'text-red-500 border-red-200' :
                          alert.level === 'warning' ? 'text-yellow-600 border-yellow-300' :
                          'text-blue-600 border-blue-300'
                        }>
                          {alert.level}
                        </Badge>
                        {!alert.acknowledged && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => acknowledgeAlert(alert.id)}
                          >
                            <Eye className="w-4 h-4 mr-1" />
                            Acquitter
                          </Button>
                        )}
                      </div>
                    </div>
                    <CardDescription>
                      {alert.source_id && `Source: ${alert.source_id} • `}
                      {new Date(alert.timestamp).toLocaleString()}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-800">{alert.message}</p>
                    {alert.acknowledged && (
                      <Badge variant="outline" className="mt-2 text-green-600 border-green-300">
                        Acquittée
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default CrawlMonitoring 