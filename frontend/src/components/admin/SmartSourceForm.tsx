"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Textarea } from '@/components/ui/textarea';
import { 
  Loader2, 
  CheckCircle, 
  AlertTriangle, 
  Lightbulb,
  Globe,
  Github,
  FileText,
  Rss,
  Sparkles,
  Brain,
  Wand2
} from 'lucide-react';

// Types
interface SourceFormData {
  id: string;
  name: string;
  url: string;
  source_type: string;
  tech_axes: string[];
  description: string;
  tags: string[];
  priority: number;
  crawl_frequency: number;
  max_depth: number;
  max_concurrent: number;
  chunk_size: number;
}

interface URLAnalysis {
  suggested_name: string;
  suggested_type: string;
  suggested_axes: string[];
  suggested_description: string;
  suggested_tags: string[];
  suggested_priority: number;
  confidence: number;
  reasoning: string;
  warnings: string[];
}

interface SmartSourceFormProps {
  formData: SourceFormData;
  setFormData: (data: SourceFormData | ((prev: SourceFormData) => SourceFormData)) => void;
  onSubmit: () => void;
  onCancel: () => void;
  loading: boolean;
  isCreateMode: boolean;
}

// Constantes
const SOURCE_TYPES = [
  { value: 'website', label: 'Site Web', icon: Globe, keywords: ['www', 'blog', 'site', 'portal'] },
  { value: 'github_repo', label: 'Repository GitHub', icon: Github, keywords: ['github.com', 'git', 'repository', 'repo'] },
  { value: 'documentation', label: 'Documentation', icon: FileText, keywords: ['docs', 'documentation', 'guide', 'manual', 'api'] },
  { value: 'blog', label: 'Blog', icon: FileText, keywords: ['blog', 'medium.com', 'dev.to', 'hashnode'] },
  { value: 'news', label: 'Actualités', icon: Rss, keywords: ['news', 'techcrunch', 'hacker', 'ycombinator'] },
  { value: 'rss_feed', label: 'Flux RSS', icon: Rss, keywords: ['rss', 'feed', 'xml'] },
  { value: 'sitemap', label: 'Sitemap', icon: Globe, keywords: ['sitemap', 'xml'] }
];

const TECH_AXES = [
  { 
    value: 'languages_frameworks', 
    label: 'Langages & Frameworks',
    keywords: ['javascript', 'python', 'react', 'vue', 'angular', 'node', 'django', 'spring', 'laravel', 'rails', 'golang', 'rust', 'kotlin', 'swift', 'typescript', 'php', 'java', 'c#', 'ruby', 'scala', 'flutter', 'nextjs', 'nuxt', 'svelte']
  },
  { 
    value: 'tools', 
    label: 'Outils',
    keywords: ['docker', 'kubernetes', 'jenkins', 'github', 'gitlab', 'vscode', 'intellij', 'webpack', 'vite', 'eslint', 'prettier', 'jest', 'cypress', 'postman', 'figma', 'sketch', 'jira', 'confluence', 'slack', 'notion', 'terraform', 'ansible']
  },
  { 
    value: 'platforms', 
    label: 'Plateformes',
    keywords: ['aws', 'azure', 'gcp', 'vercel', 'netlify', 'heroku', 'digitalocean', 'linode', 'cloudflare', 'firebase', 'supabase', 'mongodb', 'postgresql', 'redis', 'elasticsearch', 'kafka', 'rabbitmq', 'nginx', 'apache']
  },
  { 
    value: 'techniques', 
    label: 'Techniques',
    keywords: ['microservices', 'devops', 'ci/cd', 'testing', 'security', 'performance', 'scalability', 'architecture', 'design patterns', 'agile', 'scrum', 'tdd', 'bdd', 'ddd', 'api', 'rest', 'graphql', 'grpc', 'websocket', 'oauth', 'jwt', 'machine learning', 'ai', 'blockchain', 'iot']
  }
];

const PRIORITIES = [
  { value: 1, label: 'Très haute', color: 'bg-red-500', keywords: ['trending', 'breaking', 'urgent', 'critical'] },
  { value: 2, label: 'Haute', color: 'bg-orange-500', keywords: ['important', 'major', 'significant'] },
  { value: 3, label: 'Moyenne', color: 'bg-yellow-500', keywords: ['regular', 'standard', 'normal'] },
  { value: 4, label: 'Basse', color: 'bg-blue-500', keywords: ['minor', 'low', 'secondary'] },
  { value: 5, label: 'Très basse', color: 'bg-gray-500', keywords: ['archive', 'old', 'deprecated'] }
];

export default function SmartSourceForm({ 
  formData, 
  setFormData, 
  onSubmit, 
  onCancel, 
  loading, 
  isCreateMode 
}: SmartSourceFormProps) {
  const [urlAnalysis, setUrlAnalysis] = useState<URLAnalysis | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [autoApplied, setAutoApplied] = useState<Set<string>>(new Set());

  // Analyse automatique de l'URL
  const analyzeURL = useCallback(async (url: string) => {
    if (!url || !url.startsWith('http')) return;

    setAnalyzing(true);
    try {
      const response = await fetch('/api/v1/sources/analyze-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      });

      if (!response.ok) {
        throw new Error('Erreur analyse URL');
      }

      const analysis = await response.json();
      setUrlAnalysis(analysis);
      setShowSuggestions(true);
    } catch (error) {
      console.error('Erreur analyse URL:', error);
      // Fallback vers analyse locale
      const analysis = performURLAnalysis(url);
      setUrlAnalysis(analysis);
      setShowSuggestions(true);
    } finally {
      setAnalyzing(false);
    }
  }, []);

  // Analyse intelligente de l'URL
  const performURLAnalysis = (url: string): URLAnalysis => {
    const domain = new URL(url).hostname.toLowerCase();
    const path = new URL(url).pathname.toLowerCase();
    const fullUrl = url.toLowerCase();

    // Détection du type de source
    let suggestedType = 'website';
    let confidence = 0.5;

    for (const type of SOURCE_TYPES) {
      const matches = type.keywords.filter(keyword => 
        domain.includes(keyword) || path.includes(keyword)
      );
      if (matches.length > 0) {
        suggestedType = type.value;
        confidence = Math.min(0.9, 0.6 + (matches.length * 0.1));
        break;
      }
    }

    // Détection des axes technologiques
    const suggestedAxes: string[] = [];
    for (const axis of TECH_AXES) {
      const matches = axis.keywords.filter(keyword => 
        fullUrl.includes(keyword) || domain.includes(keyword)
      );
      if (matches.length > 0) {
        suggestedAxes.push(axis.value);
      }
    }

    // Si aucun axe détecté, suggérer selon le type
    if (suggestedAxes.length === 0) {
      switch (suggestedType) {
        case 'github_repo':
          suggestedAxes.push('languages_frameworks', 'tools');
          break;
        case 'documentation':
          suggestedAxes.push('techniques');
          break;
        case 'blog':
        case 'news':
          suggestedAxes.push('techniques', 'tools');
          break;
        default:
          suggestedAxes.push('techniques');
      }
    }

    // Détection de la priorité
    let suggestedPriority = 3;
    for (const priority of PRIORITIES) {
      const matches = priority.keywords.filter(keyword => 
        fullUrl.includes(keyword) || domain.includes(keyword)
      );
      if (matches.length > 0) {
        suggestedPriority = priority.value;
        break;
      }
    }

    // Génération du nom suggéré
    let suggestedName = domain.replace('www.', '').split('.')[0];
    suggestedName = suggestedName.charAt(0).toUpperCase() + suggestedName.slice(1);

    // Spécialisations par domaine
    if (domain.includes('github.com')) {
      const pathParts = path.split('/').filter(p => p);
      if (pathParts.length >= 2) {
        suggestedName = `${pathParts[0]}/${pathParts[1]}`;
      }
    }

    // Description suggérée
    const suggestedDescription = generateDescription(domain, suggestedType, suggestedAxes);

    // Tags suggérés
    const suggestedTags = generateTags(domain, suggestedType, suggestedAxes);

    // Génération du raisonnement
    const reasoning = generateReasoning(domain, suggestedType, suggestedAxes, confidence);

    // Avertissements
    const warnings = generateWarnings(url, suggestedType, confidence);

    return {
      suggested_name: suggestedName,
      suggested_type: suggestedType,
      suggested_axes: suggestedAxes,
      suggested_description: suggestedDescription,
      suggested_tags: suggestedTags,
      suggested_priority: suggestedPriority,
      confidence,
      reasoning,
      warnings
    };
  };

  const generateDescription = (domain: string, type: string, axes: string[]): string => {
    const axesLabels = axes.map(axis => 
      TECH_AXES.find(a => a.value === axis)?.label
    ).filter(Boolean);

    const typeLabel = SOURCE_TYPES.find(t => t.value === type)?.label || type;

    return `${typeLabel} spécialisé en ${axesLabels.join(', ')} - ${domain}`;
  };

  const generateTags = (domain: string, type: string, axes: string[]): string[] => {
    const tags = [type];
    
    if (domain.includes('github')) tags.push('open-source', 'git');
    if (domain.includes('dev.to')) tags.push('community', 'tutorials');
    if (domain.includes('medium')) tags.push('articles', 'blog');
    if (domain.includes('stackoverflow')) tags.push('q&a', 'community');
    if (domain.includes('docs')) tags.push('documentation', 'official');
    
    return [...new Set(tags)];
  };

  const generateReasoning = (domain: string, type: string, axes: string[], confidence: number): string => {
    let reasoning = `Analyse du domaine "${domain}": `;
    
    reasoning += `Type "${type}" détecté avec ${Math.round(confidence * 100)}% de confiance. `;
    
    if (axes.length > 0) {
      reasoning += `Axes technologiques suggérés: ${axes.join(', ')} basés sur les mots-clés trouvés.`;
    } else {
      reasoning += `Aucun axe spécifique détecté, suggestion par défaut selon le type.`;
    }

    return reasoning;
  };

  const generateWarnings = (url: string, type: string, confidence: number): string[] => {
    const warnings: string[] = [];

    if (confidence < 0.7) {
      warnings.push('Confiance faible dans la détection automatique, vérifiez les suggestions');
    }

    if (!url.includes('https://')) {
      warnings.push('URL non sécurisée (HTTP), considérez une source HTTPS');
    }

    if (type === 'github_repo' && !url.includes('github.com')) {
      warnings.push('Type GitHub détecté mais URL ne contient pas github.com');
    }

    return warnings;
  };

  // Application automatique des suggestions
  const applySuggestion = (field: keyof URLAnalysis, value: any) => {
    switch (field) {
      case 'suggested_name':
        setFormData(prev => ({ ...prev, name: value }));
        break;
      case 'suggested_type':
        setFormData(prev => ({ ...prev, source_type: value }));
        break;
      case 'suggested_axes':
        setFormData(prev => ({ ...prev, tech_axes: value }));
        break;
      case 'suggested_description':
        setFormData(prev => ({ ...prev, description: value }));
        break;
      case 'suggested_tags':
        setFormData(prev => ({ ...prev, tags: value }));
        break;
      case 'suggested_priority':
        setFormData(prev => ({ ...prev, priority: value }));
        break;
    }
    setAutoApplied(prev => new Set(prev).add(field));
  };

  const applyAllSuggestions = () => {
    if (!urlAnalysis) return;

    setFormData(prev => ({
      ...prev,
      name: urlAnalysis.suggested_name,
      source_type: urlAnalysis.suggested_type,
      tech_axes: urlAnalysis.suggested_axes,
      description: urlAnalysis.suggested_description,
      tags: urlAnalysis.suggested_tags,
      priority: urlAnalysis.suggested_priority
    }));

    setAutoApplied(new Set([
      'suggested_name',
      'suggested_type', 
      'suggested_axes',
      'suggested_description',
      'suggested_tags',
      'suggested_priority'
    ]));
  };

  // Analyse automatique quand l'URL change
  useEffect(() => {
    if (formData.url && isCreateMode) {
      const timeoutId = setTimeout(() => {
        analyzeURL(formData.url);
      }, 1000); // Debounce de 1 seconde

      return () => clearTimeout(timeoutId);
    }
  }, [formData.url, isCreateMode, analyzeURL]);

  // Génération automatique de l'ID
  useEffect(() => {
    if (isCreateMode && formData.name && !formData.id) {
      const suggestedId = formData.name
        .toLowerCase()
        .replace(/[^a-z0-9]/g, '-')
        .replace(/-+/g, '-')
        .replace(/^-|-$/g, '');
      
      setFormData(prev => ({ ...prev, id: suggestedId }));
    }
  }, [formData.name, isCreateMode, setFormData]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {isCreateMode ? (
              <>
                <Sparkles className="h-5 w-5 text-blue-500" />
                Assistant Intelligent - Nouvelle Source
              </>
            ) : (
              'Modifier la Source'
            )}
          </CardTitle>
          <CardDescription>
            {isCreateMode 
              ? "L'assistant analyse automatiquement l'URL pour suggérer la configuration optimale"
              : "Modification de la configuration de la source"
            }
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* URL avec analyse en temps réel */}
          <div className="space-y-2">
            <Label htmlFor="url">URL de la Source *</Label>
            <div className="relative">
              <Input
                id="url"
                value={formData.url}
                onChange={(e) => {
                  setFormData(prev => ({ ...prev, url: e.target.value }));
                  setUrlAnalysis(null);
                  setShowSuggestions(false);
                  setAutoApplied(new Set());
                }}
                placeholder="https://github.com/trending"
                className="pr-10"
              />
              {analyzing && (
                <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-blue-500" />
              )}
            </div>
          </div>

          {/* Suggestions intelligentes */}
          {urlAnalysis && showSuggestions && (
            <Card className="border-blue-200 bg-blue-50 dark:bg-blue-950 dark:border-blue-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Brain className="h-4 w-4 text-blue-500" />
                  Suggestions Intelligentes
                  <Badge variant="secondary" className="ml-auto">
                    {Math.round(urlAnalysis.confidence * 100)}% confiance
                  </Badge>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Raisonnement */}
                <div className="text-sm text-muted-foreground bg-white dark:bg-gray-900 p-3 rounded border-l-4 border-blue-500">
                  <div className="flex items-start gap-2">
                    <Lightbulb className="h-4 w-4 text-blue-500 mt-0.5 flex-shrink-0" />
                    <span>{urlAnalysis.reasoning}</span>
                  </div>
                </div>

                {/* Avertissements */}
                {urlAnalysis.warnings.length > 0 && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>
                      <ul className="list-disc list-inside space-y-1">
                        {urlAnalysis.warnings.map((warning, index) => (
                          <li key={index}>{warning}</li>
                        ))}
                      </ul>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Suggestions par champ */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Nom suggéré */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-medium">Nom suggéré</Label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => applySuggestion('suggested_name', urlAnalysis.suggested_name)}
                        disabled={autoApplied.has('suggested_name')}
                        className="h-6 px-2 text-xs"
                      >
                        {autoApplied.has('suggested_name') ? (
                          <CheckCircle className="h-3 w-3 text-green-500" />
                        ) : (
                          <Wand2 className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <div className="text-sm bg-white dark:bg-gray-900 p-2 rounded border">
                      {urlAnalysis.suggested_name}
                    </div>
                  </div>

                  {/* Type suggéré */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-medium">Type suggéré</Label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => applySuggestion('suggested_type', urlAnalysis.suggested_type)}
                        disabled={autoApplied.has('suggested_type')}
                        className="h-6 px-2 text-xs"
                      >
                        {autoApplied.has('suggested_type') ? (
                          <CheckCircle className="h-3 w-3 text-green-500" />
                        ) : (
                          <Wand2 className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <div className="text-sm bg-white dark:bg-gray-900 p-2 rounded border">
                      {SOURCE_TYPES.find(t => t.value === urlAnalysis.suggested_type)?.label}
                    </div>
                  </div>

                  {/* Axes suggérés */}
                  <div className="space-y-2 md:col-span-2">
                    <div className="flex items-center justify-between">
                      <Label className="text-xs font-medium">Axes technologiques suggérés</Label>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => applySuggestion('suggested_axes', urlAnalysis.suggested_axes)}
                        disabled={autoApplied.has('suggested_axes')}
                        className="h-6 px-2 text-xs"
                      >
                        {autoApplied.has('suggested_axes') ? (
                          <CheckCircle className="h-3 w-3 text-green-500" />
                        ) : (
                          <Wand2 className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {urlAnalysis.suggested_axes.map(axis => (
                        <Badge key={axis} variant="secondary" className="text-xs">
                          {TECH_AXES.find(a => a.value === axis)?.label}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bouton appliquer tout */}
                <div className="flex justify-center pt-2">
                  <Button
                    onClick={applyAllSuggestions}
                    size="sm"
                    className="flex items-center gap-2"
                  >
                    <Wand2 className="h-4 w-4" />
                    Appliquer Toutes les Suggestions
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Formulaire principal */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="id">Identifiant *</Label>
              <Input
                id="id"
                value={formData.id}
                onChange={(e) => setFormData(prev => ({ ...prev, id: e.target.value }))}
                disabled={!isCreateMode}
                placeholder="github-trending"
                className={autoApplied.has('suggested_name') ? 'border-green-500' : ''}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="name">Nom *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="GitHub Trending"
                className={autoApplied.has('suggested_name') ? 'border-green-500' : ''}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="source_type">Type de Source *</Label>
              <Select
                value={formData.source_type}
                onValueChange={(value) => setFormData(prev => ({ ...prev, source_type: value }))}
              >
                <SelectTrigger className={autoApplied.has('suggested_type') ? 'border-green-500' : ''}>
                  <SelectValue placeholder="Sélectionner un type" />
                </SelectTrigger>
                <SelectContent>
                  {SOURCE_TYPES.map(type => {
                    const Icon = type.icon;
                    return (
                      <SelectItem key={type.value} value={type.value}>
                        <div className="flex items-center gap-2">
                          <Icon className="h-4 w-4" />
                          {type.label}
                        </div>
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="priority">Priorité</Label>
              <Select
                value={formData.priority.toString()}
                onValueChange={(value) => setFormData(prev => ({ ...prev, priority: parseInt(value) }))}
              >
                <SelectTrigger className={autoApplied.has('suggested_priority') ? 'border-green-500' : ''}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map(priority => (
                    <SelectItem key={priority.value} value={priority.value.toString()}>
                      <div className="flex items-center gap-2">
                        <div className={`w-2 h-2 rounded-full ${priority.color}`} />
                        {priority.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2 md:col-span-2">
              <Label>Axes Technologiques *</Label>
              <div className={`flex flex-wrap gap-2 p-3 border rounded-md ${autoApplied.has('suggested_axes') ? 'border-green-500' : ''}`}>
                {TECH_AXES.map(axis => (
                  <Badge
                    key={axis.value}
                    variant={formData.tech_axes.includes(axis.value) ? "default" : "outline"}
                    className="cursor-pointer hover:scale-105 transition-transform"
                    onClick={() => {
                      const newAxes = formData.tech_axes.includes(axis.value)
                        ? formData.tech_axes.filter(a => a !== axis.value)
                        : [...formData.tech_axes, axis.value];
                      setFormData(prev => ({ ...prev, tech_axes: newAxes }));
                    }}
                  >
                    {axis.label}
                  </Badge>
                ))}
              </div>
            </div>
            
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Description de la source..."
                rows={3}
                className={autoApplied.has('suggested_description') ? 'border-green-500' : ''}
              />
            </div>
            
            {/* Paramètres avancés */}
            <div className="space-y-2">
              <Label htmlFor="crawl_frequency">Fréquence (heures)</Label>
              <Input
                id="crawl_frequency"
                type="number"
                min="1"
                max="168"
                value={formData.crawl_frequency}
                onChange={(e) => setFormData(prev => ({ ...prev, crawl_frequency: parseInt(e.target.value) || 24 }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="max_depth">Profondeur Max</Label>
              <Input
                id="max_depth"
                type="number"
                min="1"
                max="5"
                value={formData.max_depth}
                onChange={(e) => setFormData(prev => ({ ...prev, max_depth: parseInt(e.target.value) || 2 }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="max_concurrent">Sessions Parallèles</Label>
              <Input
                id="max_concurrent"
                type="number"
                min="1"
                max="20"
                value={formData.max_concurrent}
                onChange={(e) => setFormData(prev => ({ ...prev, max_concurrent: parseInt(e.target.value) || 5 }))}
              />
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="chunk_size">Taille Chunks</Label>
              <Input
                id="chunk_size"
                type="number"
                min="1000"
                max="10000"
                step="500"
                value={formData.chunk_size}
                onChange={(e) => setFormData(prev => ({ ...prev, chunk_size: parseInt(e.target.value) || 5000 }))}
              />
            </div>
          </div>
          
          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={onCancel}>
              Annuler
            </Button>
            <Button
              onClick={onSubmit}
              disabled={loading || !formData.id || !formData.name || !formData.url || !formData.source_type || formData.tech_axes.length === 0}
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sauvegarde...
                </>
              ) : (
                isCreateMode ? 'Créer la Source' : 'Mettre à jour'
              )}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
} 