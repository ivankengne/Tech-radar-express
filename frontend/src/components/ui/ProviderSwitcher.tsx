'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';

interface LLMModel {
  id: string;
  name: string;
  context_length: number;
  max_output_tokens: number;
  cost_per_1k_tokens: number;
  cost_output_per_1k_tokens: number;
  supports_function_calling: boolean;
  multimodal: boolean;
  description: string;
}

interface LLMProvider {
  id: string;
  name: string;
  enabled: boolean;
  status: 'healthy' | 'error' | 'unknown';
  models: LLMModel[];
}

interface ProviderSwitcherProps {
  currentProvider?: string;
  currentModel?: string;
  onProviderChange?: (provider: string, model?: string) => void;
  className?: string;
  compact?: boolean;
}

export default function ProviderSwitcher({
  currentProvider,
  currentModel,
  onProviderChange,
  className = '',
  compact = false
}: ProviderSwitcherProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState<string>(currentProvider || '');
  const [selectedModel, setSelectedModel] = useState<string>(currentModel || '');
  const [availableModels, setAvailableModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingModels, setLoadingModels] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Charger les providers au montage
  useEffect(() => {
    loadProviders();
  }, []);

  // Charger les modèles quand le provider change
  useEffect(() => {
    if (selectedProvider) {
      loadModelsForProvider(selectedProvider);
    }
  }, [selectedProvider]);

  // Synchroniser avec les props
  useEffect(() => {
    if (currentProvider !== selectedProvider) {
      setSelectedProvider(currentProvider || '');
    }
  }, [currentProvider]);

  useEffect(() => {
    if (currentModel !== selectedModel) {
      setSelectedModel(currentModel || '');
    }
  }, [currentModel]);

  const loadProviders = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/llm/status');
      if (!response.ok) throw new Error('Erreur chargement providers');
      
      const data = await response.json();
      const providersList = Object.entries(data.providers || {}).map(([id, info]: [string, any]) => ({
        id,
        name: info.name || id,
        enabled: info.enabled || false,
        status: (info.healthy ? 'healthy' : 'error') as 'healthy' | 'error' | 'unknown',
        models: []
      }));
      
      setProviders(providersList);
      
      // Définir le provider par défaut si pas déjà sélectionné
      if (!selectedProvider && data.active_provider) {
        setSelectedProvider(data.active_provider);
      }
      
    } catch (error) {
      console.error('Erreur chargement providers:', error);
      setError('Impossible de charger les providers');
    } finally {
      setLoading(false);
    }
  };

  const loadModelsForProvider = async (providerId: string) => {
    setLoadingModels(true);
    
    try {
      const response = await fetch(`/api/v1/llm/models/${providerId}`);
      if (!response.ok) throw new Error('Erreur chargement modèles');
      
      const data = await response.json();
      setAvailableModels(data.models || []);
      
      // Sélectionner le premier modèle si aucun n'est sélectionné
      if (!selectedModel && data.models.length > 0) {
        setSelectedModel(data.models[0].id);
      }
      
    } catch (error) {
      console.error('Erreur chargement modèles:', error);
      setAvailableModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleProviderChange = (providerId: string) => {
    setSelectedProvider(providerId);
    setSelectedModel(''); // Reset model selection
    onProviderChange?.(providerId);
  };

  const handleModelChange = (modelId: string) => {
    setSelectedModel(modelId);
    onProviderChange?.(selectedProvider, modelId);
  };

  const handleApplyChanges = async () => {
    if (!selectedProvider) return;
    
    try {
      const response = await fetch('/api/v1/llm/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: selectedProvider,
          model: selectedModel || undefined
        })
      });
      
      if (!response.ok) throw new Error('Erreur changement provider');
      
      // Callback de succès
      onProviderChange?.(selectedProvider, selectedModel);
      
    } catch (error) {
      console.error('Erreur changement provider:', error);
      setError('Impossible de changer le provider');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <span className="h-2 w-2 rounded-full bg-green-500"></span>;
      case 'error':
        return <span className="h-2 w-2 rounded-full bg-red-500"></span>;
      default:
        return <span className="h-2 w-2 rounded-full bg-yellow-500"></span>;
    }
  };

  const formatCost = (cost: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 4 
    }).format(cost);
  };

  const selectedModelInfo = availableModels.find(m => m.id === selectedModel);

  if (loading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
        <span className="text-sm text-gray-600 dark:text-gray-400">Chargement...</span>
      </div>
    );
  }

  if (compact) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <Select value={selectedProvider} onValueChange={handleProviderChange}>
          <SelectTrigger className="w-32">
            <SelectValue placeholder="Provider" />
          </SelectTrigger>
          <SelectContent>
            {providers.filter(p => p.enabled).map((provider) => (
              <SelectItem key={provider.id} value={provider.id}>
                <div className="flex items-center space-x-2">
                  {getStatusIcon(provider.status)}
                  <span>{provider.name}</span>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {selectedProvider && (
          <Select value={selectedModel} onValueChange={handleModelChange}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Modèle" />
            </SelectTrigger>
            <SelectContent>
              {loadingModels ? (
                <div className="p-2 text-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mx-auto"></div>
                </div>
              ) : (
                availableModels.map((model) => (
                  <SelectItem key={model.id} value={model.id}>
                    <div className="flex flex-col">
                      <span>{model.name}</span>
                      <span className="text-xs text-gray-500">
                        {model.context_length.toLocaleString()} tokens
                      </span>
                    </div>
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
        )}

        <Button
          size="sm"
          onClick={handleApplyChanges}
          disabled={!selectedProvider || !selectedModel}
        >
          Appliquer
        </Button>
      </div>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center space-x-2">
          <span>🔄</span>
          <span>Sélection Provider & Modèle</span>
        </CardTitle>
        <CardDescription>
          Choisissez le provider LLM et le modèle à utiliser
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Sélection du provider */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Provider LLM</label>
          <Select value={selectedProvider} onValueChange={handleProviderChange}>
            <SelectTrigger>
              <SelectValue placeholder="Sélectionner un provider" />
            </SelectTrigger>
            <SelectContent>
                          {providers.filter(p => p.enabled).map((provider) => (
              <SelectItem 
                key={provider.id} 
                value={provider.id}
              >
                <div className="flex items-center justify-between w-full">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(provider.status)}
                    <span>{provider.name}</span>
                  </div>
                </div>
              </SelectItem>
            ))}
            </SelectContent>
          </Select>
        </div>

        {/* Sélection du modèle */}
        {selectedProvider && (
          <div className="space-y-2">
            <label className="text-sm font-medium">Modèle</label>
            <Select value={selectedModel} onValueChange={handleModelChange}>
              <SelectTrigger>
                <SelectValue placeholder="Sélectionner un modèle" />
              </SelectTrigger>
              <SelectContent>
                {loadingModels ? (
                  <div className="p-4 text-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500 mx-auto"></div>
                    <p className="text-xs text-gray-500 mt-2">Chargement des modèles...</p>
                  </div>
                ) : (
                  availableModels.map((model) => (
                    <SelectItem key={model.id} value={model.id}>
                      <div className="flex flex-col w-full">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{model.name}</span>
                          <span className="text-xs text-gray-500">
                            {formatCost(model.cost_per_1k_tokens)}/1K
                          </span>
                        </div>
                        <div className="flex items-center space-x-2 mt-1">
                          <span className="text-xs text-gray-500">
                            {model.context_length.toLocaleString()} tokens
                          </span>
                          {model.supports_function_calling && (
                            <Badge variant="secondary" className="text-xs">Functions</Badge>
                          )}
                          {model.multimodal && (
                            <Badge variant="secondary" className="text-xs">Multimodal</Badge>
                          )}
                        </div>
                      </div>
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Informations du modèle sélectionné */}
        {selectedModelInfo && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
            <h4 className="font-medium text-sm mb-2">Informations du modèle</h4>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div>
                <span className="text-gray-600 dark:text-gray-400">Contexte:</span>
                <span className="ml-1 font-medium">
                  {selectedModelInfo.context_length.toLocaleString()} tokens
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Sortie max:</span>
                <span className="ml-1 font-medium">
                  {selectedModelInfo.max_output_tokens?.toLocaleString() || 'N/A'} tokens
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Coût input:</span>
                <span className="ml-1 font-medium">
                  {formatCost(selectedModelInfo.cost_per_1k_tokens)}/1K
                </span>
              </div>
              <div>
                <span className="text-gray-600 dark:text-gray-400">Coût output:</span>
                <span className="ml-1 font-medium">
                  {formatCost(selectedModelInfo.cost_output_per_1k_tokens)}/1K
                </span>
              </div>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
              {selectedModelInfo.description}
            </p>
          </div>
        )}

        {/* Boutons d'action */}
        <div className="flex items-center justify-between pt-2">
          <div className="flex items-center space-x-2">
            {currentProvider && (
              <Badge variant="outline" className="text-xs">
                Actuel: {currentProvider}
                {currentModel && ` / ${currentModel}`}
              </Badge>
            )}
          </div>
          <div className="flex space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSelectedProvider(currentProvider || '');
                setSelectedModel(currentModel || '');
              }}
            >
              Annuler
            </Button>
            <Button
              size="sm"
              onClick={handleApplyChanges}
              disabled={!selectedProvider || !selectedModel || 
                (selectedProvider === currentProvider && selectedModel === currentModel)}
            >
              Appliquer
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
} 