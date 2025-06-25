"use client";

import React, { useState, useEffect } from 'react';
import { RefreshCw, AlertTriangle, Clock, CheckCircle, XCircle, Eye, Play, BarChart3 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

interface CriticalAnalysis {
  source: string;
  criticality_level: string;
  confidence_score: number;
  categories: string[];
  key_factors: string[];
  impact_assessment: string;
  time_sensitivity: string;
  llm_reasoning?: string;
}

interface CriticalAlert {
  id: string;
  priority_score: number;
  created_at: string;
  analysis: CriticalAnalysis;
}

interface DetectionStats {
  total_alerts: number;
  false_positives: number;
  accuracy_rate: number;
  categories_distribution: Record<string, number>;
  last_analysis: string | null;
}

const CriticalAlertsMonitor: React.FC = () => {
  const [alerts, setAlerts] = useState<CriticalAlert[]>([]);
  const [stats, setStats] = useState<DetectionStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedAlert, setSelectedAlert] = useState<CriticalAlert | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const getCriticalityColor = (level: string): string => {
    switch (level) {
      case 'emergency': return 'bg-red-500';
      case 'critical': return 'bg-orange-500';
      case 'high': return 'bg-yellow-500';
      case 'medium': return 'bg-blue-500';
      case 'low': return 'bg-gray-500';
      default: return 'bg-gray-400';
    }
  };

  const getCriticalityLabel = (level: string): string => {
    const labels: Record<string, string> = {
      emergency: '🚨 URGENCE',
      critical: '⚠️ CRITIQUE',
      high: '🔴 ÉLEVÉ',
      medium: '🟡 MOYEN',
      low: '⚪ FAIBLE'
    };
    return labels[level] || level.toUpperCase();
  };

  const loadActiveAlerts = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/v1/critical-alerts/active');
      const data = await response.json();

      if (data.success && data.data?.alerts) {
        setAlerts(data.data.alerts);
      } else {
        setError(data.error || 'Erreur chargement alertes');
      }
    } catch (err) {
      setError('Erreur réseau lors du chargement');
    } finally {
      setIsLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/critical-alerts/stats');
      const data = await response.json();

      if (data.success && data.data?.stats) {
        setStats(data.data.stats);
      }
    } catch (err) {
      console.error('Erreur chargement stats:', err);
    }
  };

  const startAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const response = await fetch('/api/v1/critical-alerts/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hours_back: 2 })
      });

      const data = await response.json();
      if (data.success) {
        setTimeout(() => {
          loadActiveAlerts();
          loadStats();
        }, 5000);
      }
    } catch (err) {
      setError('Erreur réseau');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const markFalsePositive = async (alertId: string) => {
    try {
      await fetch(`/api/v1/critical-alerts/alert/${alertId}/mark-false-positive`, {
        method: 'POST'
      });
      setAlerts(prev => prev.filter(a => a.id !== alertId));
      setSelectedAlert(null);
      loadStats();
    } catch (err) {
      setError('Erreur réseau');
    }
  };

  useEffect(() => {
    loadActiveAlerts();
    loadStats();

    if (autoRefresh) {
      const interval = setInterval(() => {
        loadActiveAlerts();
        loadStats();
      }, 60000);
      
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Alertes Critiques Automatiques</h2>
          <p className="text-gray-600">Détection d'alertes via analyse LLM du contenu MCP</p>
        </div>
        
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-spin' : ''}`} />
            Auto: {autoRefresh ? 'ON' : 'OFF'}
          </Button>
          
          <Button onClick={startAnalysis} disabled={isAnalyzing} size="sm">
            <Play className="h-4 w-4 mr-2" />
            {isAnalyzing ? 'Analyse...' : 'Analyser Maintenant'}
          </Button>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-500" />
                <div>
                  <p className="text-sm text-gray-600">Total Alertes</p>
                  <p className="text-2xl font-bold">{stats.total_alerts}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-green-500" />
                <div>
                  <p className="text-sm text-gray-600">Précision</p>
                  <p className="text-2xl font-bold">{(stats.accuracy_rate * 100).toFixed(1)}%</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <XCircle className="h-5 w-5 text-orange-500" />
                <div>
                  <p className="text-sm text-gray-600">Faux Positifs</p>
                  <p className="text-2xl font-bold">{stats.false_positives}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-600">Dernière Analyse</p>
                  <p className="text-sm font-medium">
                    {stats.last_analysis 
                      ? new Date(stats.last_analysis).toLocaleTimeString('fr-FR')
                      : 'Aucune'
                    }
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="text-red-800">{error}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Alertes Actives ({alerts.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex justify-center py-8">
                <RefreshCw className="h-6 w-6 animate-spin" />
              </div>
            ) : alerts.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                <p>Aucune alerte critique détectée</p>
              </div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {alerts
                  .sort((a, b) => b.priority_score - a.priority_score)
                  .map((alert) => (
                    <div
                      key={alert.id}
                      className={`p-3 border rounded-lg cursor-pointer hover:bg-gray-50 ${
                        selectedAlert?.id === alert.id ? 'ring-2 ring-blue-500' : ''
                      }`}
                      onClick={() => setSelectedAlert(alert)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-1 text-xs font-medium text-white rounded ${getCriticalityColor(alert.analysis.criticality_level)}`}>
                              {getCriticalityLabel(alert.analysis.criticality_level)}
                            </span>
                            <span className="text-sm text-gray-600">
                              Score: {(alert.priority_score * 100).toFixed(0)}%
                            </span>
                          </div>
                          
                          <p className="text-sm font-medium mb-1">
                            {alert.analysis.source}
                          </p>
                          
                          <p className="text-xs text-gray-600 mb-2">
                            {alert.analysis.impact_assessment.length > 100
                              ? alert.analysis.impact_assessment.substring(0, 100) + '...'
                              : alert.analysis.impact_assessment
                            }
                          </p>
                          
                          <div className="flex flex-wrap gap-1">
                            {alert.analysis.categories.slice(0, 2).map((cat) => (
                              <Badge key={cat} variant="secondary" className="text-xs">
                                {cat}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        
                        <div className="text-xs text-gray-500">
                          {new Date(alert.created_at).toLocaleTimeString('fr-FR')}
                        </div>
                      </div>
                    </div>
                  ))
                }
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Détails de l'Alerte
            </CardTitle>
          </CardHeader>
          <CardContent>
            {selectedAlert ? (
              <div className="space-y-4">
                <div>
                  <h4 className="font-medium mb-2">Analyse LLM</h4>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Niveau de criticité</p>
                      <p className="font-medium">{getCriticalityLabel(selectedAlert.analysis.criticality_level)}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Confiance</p>
                      <p className="font-medium">{(selectedAlert.analysis.confidence_score * 100).toFixed(1)}%</p>
                    </div>
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Facteurs Clés</h4>
                  <div className="space-y-1">
                    {selectedAlert.analysis.key_factors.map((factor, idx) => (
                      <div key={idx} className="flex items-center gap-2 text-sm">
                        <div className="w-2 h-2 bg-red-500 rounded-full" />
                        {factor}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <h4 className="font-medium mb-2">Évaluation d'Impact</h4>
                  <p className="text-sm text-gray-700 bg-gray-50 p-3 rounded">
                    {selectedAlert.analysis.impact_assessment}
                  </p>
                </div>

                <div className="pt-4 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => markFalsePositive(selectedAlert.id)}
                    className="w-full"
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    Marquer comme Faux Positif
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500">
                <Eye className="h-12 w-12 mx-auto mb-4" />
                <p>Sélectionnez une alerte pour voir les détails</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CriticalAlertsMonitor;
