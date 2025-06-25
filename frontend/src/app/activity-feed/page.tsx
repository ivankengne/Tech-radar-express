'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import ActivityFeed from '@/components/dashboard/ActivityFeed'
import { 
  Activity, 
  Zap, 
  Clock,
  TrendingUp,
  BarChart3,
  Filter,
  Download,
  Share2,
  RefreshCw
} from 'lucide-react'

export default function ActivityFeedPage() {
  const [viewMode, setViewMode] = useState<'feed' | 'analytics'>('feed')

  const handleExportData = async () => {
    try {
      const response = await fetch('/api/activity-feed/activities?limit=1000&format=csv')
      if (response.ok) {
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.style.display = 'none'
        a.href = url
        a.download = `activity-feed-${new Date().toISOString().split('T')[0]}.csv`
        document.body.appendChild(a)
        a.click()
        window.URL.revokeObjectURL(url)
      }
    } catch (err) {
      console.error('Erreur export:', err)
    }
  }

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'Tech Radar Express - Flux d\'Activité',
          text: 'Découvrez le flux d\'activité temps réel de notre veille technologique',
          url: window.location.href,
        })
      } catch (err) {
        console.error('Erreur partage:', err)
      }
    } else {
      // Fallback: copier l'URL
      navigator.clipboard.writeText(window.location.href)
      alert('URL copiée dans le presse-papier')
    }
  }

  const populateDemoData = async () => {
    try {
      const response = await fetch('/api/activity-feed/demo/populate', {
        method: 'POST'
      })
      if (response.ok) {
        window.location.reload()
      }
    } catch (err) {
      console.error('Erreur population demo:', err)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Activity className="w-8 h-8 text-blue-600" />
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    Flux d'Activité Temps Réel
                  </h1>
                  <p className="text-sm text-gray-500">
                    Suivez toutes les activités de veille technologique en temps réel
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
                <span className="text-sm text-green-600 font-medium">En direct</span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex rounded-md shadow-sm">
                <Button
                  variant={viewMode === 'feed' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('feed')}
                  className="rounded-r-none"
                >
                  <Activity className="w-4 h-4 mr-2" />
                  Flux
                </Button>
                <Button
                  variant={viewMode === 'analytics' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setViewMode('analytics')}
                  className="rounded-l-none"
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Analytiques
                </Button>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={handleExportData}
              >
                <Download className="w-4 h-4 mr-2" />
                Exporter
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={handleShare}
              >
                <Share2 className="w-4 h-4 mr-2" />
                Partager
              </Button>

              <Button
                variant="outline"
                size="sm"
                onClick={populateDemoData}
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Demo
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-6">
        {viewMode === 'feed' ? (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Flux principal */}
            <div className="lg:col-span-3">
              <ActivityFeed 
                maxHeight="calc(100vh - 200px)"
                autoRefresh={true}
                showFilters={true}
                showStats={false}
                className="h-full"
              />
            </div>

            {/* Sidebar avec statistiques et raccourcis */}
            <div className="space-y-6">
              {/* Statistiques en temps réel */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Statistiques Live
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Dernière activité</span>
                    <Badge variant="secondary" className="text-xs">
                      <Clock className="w-3 h-3 mr-1" />
                      2m
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Niveau d'impact moyen</span>
                    <Badge className="bg-orange-500 text-white text-xs">
                      <Zap className="w-3 h-3 mr-1" />
                      78%
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Source la plus active</span>
                    <Badge variant="outline" className="text-xs">
                      MCP
                    </Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Types d'activités */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <Filter className="w-5 h-5" />
                    Types d'Activités
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>💡</span>
                      <span className="text-sm">Insights</span>
                    </div>
                    <Badge variant="secondary">42</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>🚨</span>
                      <span className="text-sm">Alertes Critiques</span>
                    </div>
                    <Badge className="bg-red-500 text-white">3</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>📄</span>
                      <span className="text-sm">Sources Crawlées</span>
                    </div>
                    <Badge variant="secondary">127</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>🔍</span>
                      <span className="text-sm">Recherches</span>
                    </div>
                    <Badge variant="secondary">18</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span>🤖</span>
                      <span className="text-sm">Analyses LLM</span>
                    </div>
                    <Badge variant="secondary">89</Badge>
                  </div>
                </CardContent>
              </Card>

              {/* Actions rapides */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">Actions Rapides</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full justify-start"
                    onClick={() => {
                      // Filtrer par alertes critiques
                      const filterBtn = document.querySelector('[title="Filtres"]') as HTMLButtonElement
                      filterBtn?.click()
                    }}
                  >
                    🚨 Alertes Critiques Seulement
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full justify-start"
                    onClick={() => {
                      // Filtrer par dernière heure
                    }}
                  >
                    ⏰ Dernière Heure
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full justify-start"
                    onClick={() => {
                      // Afficher seulement les non lues
                    }}
                  >
                    📧 Non Lues
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="w-full justify-start"
                    onClick={() => {
                      // Afficher seulement les favoris
                    }}
                  >
                    ⭐ Favoris
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Graphiques et analytiques */}
            <Card className="col-span-full">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5" />
                  Analytiques du Flux d'Activité
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-8 text-gray-500">
                  <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>Graphiques analytiques disponibles prochainement</p>
                  <p className="text-sm mt-2">
                    Visualisations des tendances, pics d'activité, et analyses temporelles
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  )
} 