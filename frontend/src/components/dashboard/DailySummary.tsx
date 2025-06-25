"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Calendar, 
  Clock, 
  Download, 
  RefreshCw, 
  TrendingUp, 
  FileText,
  AlertTriangle,
  Loader2
} from 'lucide-react';

interface SummarySection {
  title: string;
  content: string;
  priority: number;
  source_count: number;
}

interface SummaryStats {
  sections_count: number;
  total_sources: number;
  generation_time: number;
  generated_at: string;
}

interface DailySummaryData {
  date: string;
  sections: SummarySection[];
  stats: SummaryStats;
}

interface DailySummaryResponse {
  success: boolean;
  data?: {
    summary: DailySummaryData;
  };
  error?: string;
  metadata?: {
    request_timestamp: string;
    generation_time: number;
  };
}

const DailySummary: React.FC = () => {
  const [summary, setSummary] = useState<DailySummaryData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>('');

  // Fonction pour récupérer le dernier résumé
  const fetchLatestSummary = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/summary/latest');
      const data: DailySummaryResponse = await response.json();
      
      if (data.success && data.data) {
        setSummary(data.data.summary);
      } else {
        setError(data.error || 'Erreur lors du chargement du résumé');
      }
    } catch (err) {
      setError('Erreur de connexion à l\'API');
      console.error('Erreur fetch résumé:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fonction pour générer un nouveau résumé
  const generateNewSummary = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const requestBody = selectedDate ? { date: selectedDate } : {};
      
      const response = await fetch('/api/v1/summary/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });
      
      const data: DailySummaryResponse = await response.json();
      
      if (data.success && data.data) {
        setSummary(data.data.summary);
      } else {
        setError(data.error || 'Erreur lors de la génération du résumé');
      }
    } catch (err) {
      setError('Erreur de connexion à l\'API');
      console.error('Erreur génération résumé:', err);
    } finally {
      setLoading(false);
    }
  };

  // Fonction pour télécharger le résumé en Markdown
  const downloadMarkdown = async () => {
    try {
      const url = selectedDate 
        ? `/api/v1/summary/markdown?date=${selectedDate}`
        : '/api/v1/summary/markdown';
      
      const response = await fetch(url);
      
      if (response.ok) {
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = downloadUrl;
        
        const filename = response.headers.get('content-disposition')
          ?.split('filename=')[1]
          ?.replace(/"/g, '') || `resume-${summary?.date || 'latest'}.md`;
        
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(downloadUrl);
      } else {
        setError('Erreur lors du téléchargement');
      }
    } catch (err) {
      setError('Erreur de téléchargement');
      console.error('Erreur download:', err);
    }
  };

  // Fonction pour obtenir l'icône d'une section selon son titre
  const getSectionIcon = (title: string) => {
    if (title.includes('Tendances')) return <TrendingUp className="w-5 h-5" />;
    if (title.includes('Alertes')) return <AlertTriangle className="w-5 h-5" />;
    return <FileText className="w-5 h-5" />;
  };

  // Fonction pour obtenir la couleur d'une section selon sa priorité
  const getSectionBadgeColor = (priority: number) => {
    if (priority >= 90) return "destructive";
    if (priority >= 70) return "default";
    return "secondary";
  };

  // Formatage du contenu d'une section
  const formatSectionContent = (content: string) => {
    return content.split('\n').map((line, index) => (
      <p key={index} className="mb-2 text-sm text-gray-700 dark:text-gray-300">
        {line}
      </p>
    ));
  };

  // Chargement initial
  useEffect(() => {
    fetchLatestSummary();
  }, []);

  return (
    <div className="space-y-6">
      {/* En-tête avec contrôles */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Calendar className="w-6 h-6 text-blue-600" />
              <CardTitle className="text-xl">Résumé Quotidien</CardTitle>
            </div>
            <div className="flex items-center space-x-2">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="px-3 py-2 border rounded-md text-sm"
                max={new Date().toISOString().split('T')[0]}
              />
              <Button
                onClick={generateNewSummary}
                disabled={loading}
                size="sm"
                variant="outline"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                Générer
              </Button>
              <Button
                onClick={downloadMarkdown}
                disabled={!summary}
                size="sm"
                variant="outline"
              >
                <Download className="w-4 h-4" />
                MD
              </Button>
            </div>
          </div>
        </CardHeader>
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

      {/* Indicateur de chargement */}
      {loading && !summary && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-center space-x-2 text-gray-500">
              <Loader2 className="w-6 h-6 animate-spin" />
              <span>Génération du résumé en cours...</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Résumé principal */}
      {summary && (
        <>
          {/* Statistiques du résumé */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {summary.stats.sections_count}
                  </div>
                  <div className="text-sm text-gray-500">Sections</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {summary.stats.total_sources}
                  </div>
                  <div className="text-sm text-gray-500">Sources</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">
                    {summary.stats.generation_time.toFixed(1)}s
                  </div>
                  <div className="text-sm text-gray-500">Génération</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-orange-600">
                    {new Date(summary.date).toLocaleDateString('fr-FR')}
                  </div>
                  <div className="text-sm text-gray-500">Date</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Sections du résumé */}
          <div className="space-y-4">
            {summary.sections
              .sort((a, b) => b.priority - a.priority)
              .map((section, index) => (
                <Card key={index} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getSectionIcon(section.title)}
                        <CardTitle className="text-lg">
                          {section.title}
                        </CardTitle>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Badge variant={getSectionBadgeColor(section.priority)}>
                          Priorité {section.priority}
                        </Badge>
                        <Badge variant="outline">
                          {section.source_count} sources
                        </Badge>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="prose prose-sm max-w-none dark:prose-invert">
                      {formatSectionContent(section.content)}
                    </div>
                  </CardContent>
                </Card>
              ))}
          </div>

          {/* Métadonnées */}
          <Card className="bg-gray-50 dark:bg-gray-800/50">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center space-x-2">
                  <Clock className="w-4 h-4" />
                  <span>
                    Généré le {new Date(summary.stats.generated_at).toLocaleString('fr-FR')}
                  </span>
                </div>
                <span>
                  Tech Radar Express v1.0
                </span>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
};

export default DailySummary; 