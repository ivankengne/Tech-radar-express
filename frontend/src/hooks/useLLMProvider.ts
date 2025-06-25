import { useState, useEffect, useCallback } from 'react';

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
  healthy: boolean;
  models: LLMModel[];
  statistics: {
    total_requests: number;
    total_tokens: number;
    total_cost: number;
    avg_response_time: number;
    error_rate: number;
    last_used: string;
  };
}

interface LLMStatus {
  active_provider: string | null;
  active_model: string | null;
  providers: Record<string, LLMProvider>;
  total_providers: number;
  enabled_providers: number;
  healthy_providers: number;
}

export function useLLMProvider() {
  const [status, setStatus] = useState<LLMStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Charger le statut des providers
  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/v1/llm/status');
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`);
      }

      const data = await response.json();
      setStatus(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue';
      setError(errorMessage);
      console.error('Erreur chargement status LLM:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Charger les modèles pour un provider spécifique
  const loadModels = useCallback(async (providerId: string, refresh = false): Promise<LLMModel[]> => {
    try {
      const url = `/api/v1/llm/models/${providerId}${refresh ? '?refresh=true' : ''}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Erreur chargement modèles: ${response.status}`);
      }

      const data = await response.json();
      return data.models || [];
    } catch (err) {
      console.error('Erreur chargement modèles:', err);
      return [];
    }
  }, []);

  // Changer de provider actif
  const switchProvider = useCallback(async (providerId: string, modelId?: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/llm/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          model: modelId
        })
      });

      if (!response.ok) {
        throw new Error(`Erreur switch provider: ${response.status}`);
      }

      // Recharger le statut après le changement
      await loadStatus();
      return true;
    } catch (err) {
      console.error('Erreur switch provider:', err);
      setError(err instanceof Error ? err.message : 'Erreur switch provider');
      return false;
    }
  }, [loadStatus]);

  // Valider une clé API
  const validateApiKey = useCallback(async (providerId: string, apiKey: string): Promise<boolean> => {
    try {
      const response = await fetch('/api/v1/llm/validate-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider: providerId,
          api_key: apiKey
        })
      });

      if (!response.ok) {
        return false;
      }

      const data = await response.json();
      return data.valid === true;
    } catch (err) {
      console.error('Erreur validation clé API:', err);
      return false;
    }
  }, []);

  // Mettre à jour la configuration d'un provider
  const updateProviderConfig = useCallback(async (
    providerId: string, 
    config: Record<string, any>
  ): Promise<boolean> => {
    try {
      const response = await fetch(`/api/v1/llm/config/${providerId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });

      if (!response.ok) {
        throw new Error(`Erreur configuration: ${response.status}`);
      }

      // Recharger le statut après la mise à jour
      await loadStatus();
      return true;
    } catch (err) {
      console.error('Erreur configuration provider:', err);
      setError(err instanceof Error ? err.message : 'Erreur configuration');
      return false;
    }
  }, [loadStatus]);

  // Récupérer les statistiques
  const getStatistics = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/llm/statistics');
      if (!response.ok) {
        throw new Error(`Erreur statistiques: ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (err) {
      console.error('Erreur statistiques:', err);
      return null;
    }
  }, []);

  // Vider le cache des modèles
  const resetCache = useCallback(async (providerId?: string): Promise<boolean> => {
    try {
      const url = `/api/v1/llm/reset-cache${providerId ? `?provider=${providerId}` : ''}`;
      const response = await fetch(url, { method: 'POST' });

      if (!response.ok) {
        throw new Error(`Erreur reset cache: ${response.status}`);
      }

      return true;
    } catch (err) {
      console.error('Erreur reset cache:', err);
      return false;
    }
  }, []);

  // Charger le statut au montage du hook
  useEffect(() => {
    loadStatus();
  }, [loadStatus]);

  // Helpers pour accéder aux données
  const getProvider = useCallback((providerId: string): LLMProvider | null => {
    return status?.providers[providerId] || null;
  }, [status]);

  const getEnabledProviders = useCallback((): LLMProvider[] => {
    if (!status) return [];
    return Object.values(status.providers).filter(p => p.enabled);
  }, [status]);

  const getHealthyProviders = useCallback((): LLMProvider[] => {
    if (!status) return [];
    return Object.values(status.providers).filter(p => p.healthy);
  }, [status]);

  const isProviderActive = useCallback((providerId: string): boolean => {
    return status?.active_provider === providerId;
  }, [status]);

  const isModelActive = useCallback((modelId: string): boolean => {
    return status?.active_model === modelId;
  }, [status]);

  return {
    // État
    status,
    loading,
    error,

    // Actions
    loadStatus,
    loadModels,
    switchProvider,
    validateApiKey,
    updateProviderConfig,
    getStatistics,
    resetCache,

    // Helpers
    getProvider,
    getEnabledProviders,
    getHealthyProviders,
    isProviderActive,
    isModelActive,

    // Données dérivées
    activeProvider: status?.active_provider || null,
    activeModel: status?.active_model || null,
    providers: status ? Object.values(status.providers) : [],
    enabledProviders: status?.enabled_providers || 0,
    healthyProviders: status?.healthy_providers || 0,
    totalProviders: status?.total_providers || 0
  };
} 