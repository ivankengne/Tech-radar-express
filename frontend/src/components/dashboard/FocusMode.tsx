"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Target, 
  Timer, 
  Zap, 
  Brain, 
  AlertTriangle,
  Rocket,
  Play,
  Download,
  Loader2,
  Clock,
  TrendingUp
} from 'lucide-react';

interface FocusInsight {
  title: string;
  summary: string;
  impact_level: number;
  tech_area: string;
  keywords: string[];
}

interface FocusSynthesis {
  mode: string;
  insights: FocusInsight[];
  key_trends: string[];
  critical_alerts: string[];
  innovation_highlights: string[];
  stats: {
    generation_time: number;
    sources_analyzed: number;
    confidence_score: number;
    timestamp: string;
  };
}

const FocusMode: React.FC = () => {
  const [selectedMode, setSelectedMode] = useState<string>('tech_pulse');
  const [customQuery, setCustomQuery] = useState<string>('');
  const [synthesis, setSynthesis] = useState<FocusSynthesis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timer, setTimer] = useState<number>(0);

  // Modes disponibles (static pour simplifier)
  const modes = {
    quick_scan: {
      name: "Scan Rapide",
      description: "Analyse express des dernières tendances",
      target_time: 30,
      emoji: "⚡"
    },
    tech_pulse: {
      name: "Pouls Technologique", 
      description: "Vue d'ensemble équilibrée de l'écosystème tech",
      target_time: 60,
      emoji: "💓"
    },
    critical_alerts: {
      name: "Alertes Critiques",
      description: "Focus sur les points critiques et urgences",
      target_time: 45,
      emoji: "🚨"
    },
    innovation_radar: {
      name: "Radar Innovation",
      description: "Exploration des technologies émergentes",
      target_time: 90,
      emoji: "🚀"
    }
  };

  // Timer en temps réel
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (loading) {
      interval = setInterval(() => {
        setTimer((prev) => prev + 0.1);
      }, 100);
    } else {
      setTimer(0);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading]);

  // Génération de la synthèse
  const generateFocus = async () => {
    setLoading(true);
    setError(null);
    setTimer(0);
    
    try {
      const response = await fetch('/api/v1/focus/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: selectedMode,
          custom_query: customQuery || null,
        }),
      });
      
      const data = await response.json();
      
      if (data.success && data.data) {
        setSynthesis(data.data.synthesis);
      } else {
        setError(data.error || 'Erreur lors de la génération');
      }
    } catch (err) {
      setError('Erreur de connexion à l\'API');
      console.error('Erreur génération focus:', err);
    } finally {
      setLoading(false);
    }
  };

  // Téléchargement texte
  const downloadText = async () => {
    try {
      const url = `/api/v1/focus/text?mode=${selectedMode}${customQuery ? `&query=${encodeURIComponent(customQuery)}` : ''}`;
      
      const response = await fetch(url);
      
      if (response.ok) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.download = `focus-${selectedMode}-${Date.now()}.txt`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      }
    } catch (err) {
      setError('Erreur de téléchargement');
    }
  };

  // Icône selon le mode
  const getModeIcon = (modeKey: string) => {
    const icons: Record<string, React.ReactElement> = {
      quick_scan: <Zap className="w-5 h-5" />,
      tech_pulse: <Brain className="w-5 h-5" />,
      critical_alerts: <AlertTriangle className="w-5 h-5" />,
      innovation_radar: <Rocket className="w-5 h-5" />
    };
    return icons[modeKey] || <Target className="w-5 h-5" />;
  };

  // Couleur selon l'impact
  const getImpactColor = (level: number) => {
    if (level >= 4) return "text-red-600";
    if (level >= 3) return "text-orange-600";
    return "text-blue-600";
  };

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Target className="w-6 h-6 text-blue-600" />
              <CardTitle className="text-xl">Mode Focus</CardTitle>
              <Badge variant="outline">Synthèse rapide</Badge>
            </div>
            {loading && (
              <div className="flex items-center space-x-2 text-blue-600">
                <Timer className="w-4 h-4" />
                <span className="font-mono">{timer.toFixed(1)}s</span>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Sélection du mode */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            {Object.entries(modes).map(([key, mode]) => (
              <Card
                key={key}
                className={`cursor-pointer transition-all hover:shadow-md ${
                  selectedMode === key ? 'ring-2 ring-blue-500' : ''
                }`}
                onClick={() => setSelectedMode(key)}
              >
                <CardContent className="pt-4">
                  <div className="text-center">
                    <div className="text-2xl mb-2">{mode.emoji}</div>
                    <h3 className="font-semibold text-sm">{mode.name}</h3>
                    <p className="text-xs text-gray-500 mt-1">{mode.description}</p>
                    <Badge variant="secondary" className="mt-2 text-xs">
                      {mode.target_time}s max
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Requête personnalisée */}
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">
              Requête personnalisée (optionnel)
            </label>
            <input
              type="text"
              value={customQuery}
              onChange={(e) => setCustomQuery(e.target.value)}
              placeholder="Ex: React 19, sécurité cloud, AI coding..."
              className="w-full px-3 py-2 border rounded-md text-sm"
            />
          </div>

          {/* Boutons */}
          <div className="flex items-center space-x-2">
            <Button
              onClick={generateFocus}
              disabled={loading}
              className="flex items-center space-x-2"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Play className="w-4 h-4" />
              )}
              <span>Générer Focus</span>
            </Button>
            <Button
              onClick={downloadText}
              disabled={!synthesis}
              variant="outline"
              size="sm"
            >
              <Download className="w-4 h-4" />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Message d'erreur */}
      {error && (
        <Card className="border-red-200 bg-red-50 dark:bg-red-900/20">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-600 dark:text-red-400">
              <AlertTriangle className="w-5 h-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Chargement */}
      {loading && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center space-x-4">
              <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
              <div className="text-center">
                <div className="font-medium">Génération focus en cours...</div>
                <div className="text-sm text-gray-500">
                  Mode: {modes[selectedMode as keyof typeof modes]?.name}
                </div>
                <div className="text-sm text-gray-500">
                  Objectif: {modes[selectedMode as keyof typeof modes]?.target_time}s max
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Synthèse générée */}
      {synthesis && (
        <>
          {/* Stats */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {synthesis.insights.length}
                  </div>
                  <div className="text-sm text-gray-500">Insights</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {synthesis.stats.generation_time.toFixed(1)}s
                  </div>
                  <div className="text-sm text-gray-500">Génération</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {Math.round(synthesis.stats.confidence_score * 100)}%
                  </div>
                  <div className="text-sm text-gray-500">Confiance</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {synthesis.stats.sources_analyzed}
                  </div>
                  <div className="text-sm text-gray-500">Sources</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Insights */}
          {synthesis.insights.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <Brain className="w-5 h-5" />
                  <span>Insights Clés</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {synthesis.insights.map((insight, index) => (
                    <div key={index} className="border-l-4 border-blue-500 pl-4">
                      <div className="flex items-center space-x-2 mb-2">
                        <Badge variant="outline">{insight.tech_area}</Badge>
                        <div className={`text-sm font-medium ${getImpactColor(insight.impact_level)}`}>
                          Impact: {insight.impact_level}/5
                        </div>
                      </div>
                      <h4 className="font-semibold text-sm mb-1">{insight.title}</h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {insight.summary}
                      </p>
                      {insight.keywords.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-1">
                          {insight.keywords.map((keyword, i) => (
                            <Badge key={i} variant="secondary" className="text-xs">
                              {keyword}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Tendances */}
          {synthesis.key_trends.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <TrendingUp className="w-5 h-5" />
                  <span>Tendances Clés</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {synthesis.key_trends.map((trend, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-green-500 mt-1">•</span>
                      <span className="text-sm">{trend}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Alertes */}
          {synthesis.critical_alerts.length > 0 && (
            <Card className="border-red-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-red-600">
                  <AlertTriangle className="w-5 h-5" />
                  <span>Alertes Critiques</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {synthesis.critical_alerts.map((alert, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-red-500 mt-1">⚠️</span>
                      <span className="text-sm">{alert}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Innovations */}
          {synthesis.innovation_highlights.length > 0 && (
            <Card className="border-purple-200">
              <CardHeader>
                <CardTitle className="flex items-center space-x-2 text-purple-600">
                  <Rocket className="w-5 h-5" />
                  <span>Innovations</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {synthesis.innovation_highlights.map((innovation, index) => (
                    <li key={index} className="flex items-start space-x-2">
                      <span className="text-purple-500 mt-1">🚀</span>
                      <span className="text-sm">{innovation}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {/* Footer */}
          <Card className="bg-gray-50 dark:bg-gray-800/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4" />
                  <span>
                    Généré le {new Date(synthesis.stats.timestamp).toLocaleString('fr-FR')}
                  </span>
                </div>
                <span>
                  Mode: {modes[synthesis.mode as keyof typeof modes]?.name || synthesis.mode}
                </span>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default FocusMode; 