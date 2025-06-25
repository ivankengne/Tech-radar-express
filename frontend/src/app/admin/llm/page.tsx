'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Alert, AlertDescription } from '@/components/ui/alert';
import ProviderSwitcher from '@/components/ui/ProviderSwitcher';
import { useLLMProvider } from '@/hooks/useLLMProvider';
import { motion, AnimatePresence } from 'framer-motion';

// Composants UI manquants
function Badge({ children, variant = 'default', className = '' }: { 
  children: React.ReactNode; 
  variant?: 'default' | 'secondary' | 'outline';
  className?: string;
}) {
  const baseClasses = 'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium';
  const variants = {
    default: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
    secondary: 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
    outline: 'border border-gray-200 text-gray-800 dark:border-gray-700 dark:text-gray-300'
  };
  
  return (
    <span className={`${baseClasses} ${variants[variant]} ${className}`}>
      {children}
    </span>
  );
}

function Label({ children, htmlFor, className = '' }: { 
  children: React.ReactNode; 
  htmlFor?: string;
  className?: string;
}) {
  return (
    <label 
      htmlFor={htmlFor} 
      className={`text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 ${className}`}
    >
      {children}
    </label>
  );
}

// Interfaces corrigées pour correspondre aux données du hook
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

interface ProviderConfig {
  api_key?: string;
  base_url?: string;
  organization?: string;
  project?: string;
  region?: string;
  timeout: number;
  max_retries: number;
  rate_limit_rpm?: number;
  rate_limit_tpm?: number;
}

interface ProviderStats {
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time: number;
  error_rate: number;
  last_used: string;
}

// Interface simplifiée qui correspond aux données réelles du hook
interface Provider {
  id: string;
  name: string;
  enabled: boolean;
  models: LLMModel[];
}

export default function LLMAdminPage() {
  const {
    status,
    loading,
    error: llmError,
    activeProvider,
    activeModel,
    providers,
    switchProvider,
    validateApiKey,
    updateProviderConfig,
    loadStatus
  } = useLLMProvider();

  const [saving, setSaving] = useState(false);
  const [validatingKey, setValidatingKey] = useState<string | null>(null);
  const [keyValidation, setKeyValidation] = useState<Record<string, boolean>>({});

  // Fonction pour obtenir le statut d'un provider (mock pour le moment)
  const getProviderStatus = (providerId: string): 'healthy' | 'error' | 'unknown' => {
    // Logique de détermination du statut basée sur l'état du provider
    return 'healthy'; // Par défaut
  };

  // Fonction pour obtenir la config d'un provider (mock pour le moment)
  const getProviderConfig = (providerId: string): ProviderConfig => {
    return {
      timeout: 30,
      max_retries: 3,
    };
  };

  // Fonction pour obtenir les stats d'un provider (mock pour le moment)
  const getProviderStats = (providerId: string): ProviderStats => {
    return {
      total_requests: 0,
      total_tokens: 0,
      total_cost: 0,
      avg_response_time: 0,
      error_rate: 0,
      last_used: new Date().toISOString(),
    };
  };

  const handleValidateApiKey = async (providerId: string, apiKey: string) => {
    if (!apiKey.trim()) return;
    
    setValidatingKey(providerId);
    try {
      const isValid = await validateApiKey(providerId, apiKey);
      setKeyValidation(prev => ({ ...prev, [providerId]: isValid }));
    } catch (error) {
      setKeyValidation(prev => ({ ...prev, [providerId]: false }));
    } finally {
      setValidatingKey(null);
    }
  };

  const handleUpdateProviderConfig = async (providerId: string, config: Partial<ProviderConfig>) => {
    setSaving(true);
    try {
      await updateProviderConfig(providerId, config);
    } catch (error) {
      console.error('Erreur sauvegarde config:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleSwitchProvider = async (providerId: string, modelId?: string) => {
    try {
      await switchProvider(providerId, modelId);
    } catch (error) {
      console.error('Erreur switch provider:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return <span className="h-3 w-3 rounded-full bg-green-500"></span>;
      case 'error':
        return <span className="h-3 w-3 rounded-full bg-red-500"></span>;
      default:
        return <span className="h-3 w-3 rounded-full bg-yellow-500"></span>;
    }
  };

  const formatCost = (cost: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 4 
    }).format(cost);
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Configuration LLM</h1>
          <p className="text-gray-600 dark:text-gray-400">
            Gérez les providers et modèles de langage
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Badge variant={activeProvider ? 'default' : 'secondary'}>
            {activeProvider ? `Actif: ${activeProvider}` : 'Aucun provider actif'}
          </Badge>
          {activeModel && (
            <Badge variant="outline">{activeModel}</Badge>
          )}
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {providers.map((provider) => (
          <Card 
            key={provider.id}
            className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
              activeProvider === provider.id ? 'ring-2 ring-blue-500' : ''
            }`}
            onClick={() => switchProvider(provider.id)}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getStatusIcon(getProviderStatus(provider.id))}
                  <span className="font-medium">{provider.name}</span>
                </div>
                <Switch 
                  checked={provider.enabled}
                  onCheckedChange={(enabled) => {
                    // Mise à jour de l'état enabled via une API dédiée
                    fetch(`/api/v1/llm/config/${provider.id}`, {
                      method: 'PATCH',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ enabled })
                    }).then(() => loadStatus());
                  }}
                />
              </div>
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {provider.models.length} modèles disponibles
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Provider Configuration */}
      <Tabs defaultValue="config" className="space-y-4">
        <TabsList>
          <TabsTrigger value="config">
            <span className="flex items-center space-x-2">
              <span>⚙️</span>
              <span>Configuration</span>
            </span>
          </TabsTrigger>
          <TabsTrigger value="models">
            <span className="flex items-center space-x-2">
              <span>🤖</span>
              <span>Modèles</span>
            </span>
          </TabsTrigger>
          <TabsTrigger value="stats">
            <span className="flex items-center space-x-2">
              <span>📊</span>
              <span>Statistiques</span>
            </span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="config" className="space-y-4">
          {providers.map((provider) => (
            <Card key={provider.id}>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <span>🔑</span>
                  <span>{provider.name}</span>
                  {getStatusIcon(getProviderStatus(provider.id))}
                </CardTitle>
                <CardDescription>
                  Configuration des paramètres de connexion
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProviderConfigForm
                  provider={provider}
                  config={getProviderConfig(provider.id)}
                  onUpdate={(config) => updateProviderConfig(provider.id, config)}
                  onValidateKey={(key) => validateApiKey(provider.id, key)}
                  validating={validatingKey === provider.id}
                  keyValid={keyValidation[provider.id]}
                  saving={saving}
                />
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="models" className="space-y-4">
          {providers.map((provider) => (
            <Card key={provider.id}>
              <CardHeader>
                <CardTitle>{provider.name} - Modèles</CardTitle>
                <CardDescription>
                  {provider.models.length} modèles disponibles
                </CardDescription>
              </CardHeader>
              <CardContent>
                <ModelsList
                  models={provider.models}
                  activeModel={activeModel || ''}
                  onSelectModel={(modelId) => switchProvider(provider.id, modelId)}
                />
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        <TabsContent value="stats" className="space-y-4">
          {providers.map((provider) => (
            <Card key={provider.id}>
              <CardHeader>
                <CardTitle>{provider.name} - Statistiques</CardTitle>
              </CardHeader>
              <CardContent>
                <ProviderStats stats={getProviderStats(provider.id)} />
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Composant de configuration provider
function ProviderConfigForm({ 
  provider, 
  config,
  onUpdate, 
  onValidateKey, 
  validating, 
  keyValid, 
  saving 
}: {
  provider: Provider;
  config: ProviderConfig;
  onUpdate: (config: Partial<ProviderConfig>) => void;
  onValidateKey: (key: string) => void;
  validating: boolean;
  keyValid?: boolean;
  saving: boolean;
}) {
  const [localConfig, setLocalConfig] = useState(config);

  const handleConfigChange = (field: string, value: any) => {
    const newConfig = { ...localConfig, [field]: value };
    setLocalConfig(newConfig);
  };

  const handleSave = () => {
    onUpdate(localConfig);
  };

  const handleKeyValidation = () => {
    if (localConfig.api_key) {
      onValidateKey(localConfig.api_key);
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div className="space-y-4">
        <div>
          <Label htmlFor="api_key">Clé API</Label>
          <div className="flex space-x-2">
            <Input
              id="api_key"
              type="password"
              value={localConfig.api_key || ''}
              onChange={(e) => handleConfigChange('api_key', e.target.value)}
              placeholder="sk-..."
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleKeyValidation}
              disabled={validating || !localConfig.api_key}
            >
              {validating ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500" />
              ) : (
                'Valider'
              )}
            </Button>
          </div>
          <AnimatePresence>
            {keyValid !== undefined && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
              >
                <Alert className={`mt-2 ${keyValid ? 'border-green-500' : 'border-red-500'}`}>
                  <AlertDescription className="flex items-center space-x-2">
                    {keyValid ? (
                      <>
                        <span className="h-4 w-4 text-green-500">✅</span>
                        <span>Clé API valide</span>
                      </>
                    ) : (
                      <>
                        <span className="h-4 w-4 text-red-500">❌</span>
                        <span>Clé API invalide</span>
                      </>
                    )}
                  </AlertDescription>
                </Alert>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {provider.id === 'openai' && (
          <>
            <div>
              <Label htmlFor="organization">Organisation</Label>
              <Input
                id="organization"
                value={localConfig.organization || ''}
                onChange={(e) => handleConfigChange('organization', e.target.value)}
                placeholder="org-..."
              />
            </div>
            <div>
              <Label htmlFor="project">Projet</Label>
              <Input
                id="project"
                value={localConfig.project || ''}
                onChange={(e) => handleConfigChange('project', e.target.value)}
                placeholder="proj_..."
              />
            </div>
          </>
        )}

        {provider.id === 'gemini' && (
          <div>
            <Label htmlFor="region">Région</Label>
            <Select
              value={localConfig.region || 'us-central1'}
              onValueChange={(value) => handleConfigChange('region', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="us-central1">US Central</SelectItem>
                <SelectItem value="europe-west1">Europe West</SelectItem>
                <SelectItem value="asia-southeast1">Asia Southeast</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {provider.id === 'ollama' && (
          <div>
            <Label htmlFor="base_url">URL de base</Label>
            <Input
              id="base_url"
              value={localConfig.base_url || 'http://localhost:11434'}
              onChange={(e) => handleConfigChange('base_url', e.target.value)}
              placeholder="http://localhost:11434"
            />
          </div>
        )}
      </div>

      <div className="space-y-4">
        <div>
          <Label htmlFor="timeout">Timeout (secondes)</Label>
          <Input
            id="timeout"
            type="number"
            value={localConfig.timeout}
            onChange={(e) => handleConfigChange('timeout', parseInt(e.target.value))}
            min={5}
            max={300}
          />
        </div>

        <div>
          <Label htmlFor="max_retries">Tentatives max</Label>
          <Input
            id="max_retries"
            type="number"
            value={localConfig.max_retries}
            onChange={(e) => handleConfigChange('max_retries', parseInt(e.target.value))}
            min={0}
            max={10}
          />
        </div>

        <div>
          <Label htmlFor="rate_limit_rpm">Limite req/min</Label>
          <Input
            id="rate_limit_rpm"
            type="number"
            value={localConfig.rate_limit_rpm || ''}
            onChange={(e) => handleConfigChange('rate_limit_rpm', e.target.value ? parseInt(e.target.value) : null)}
            placeholder="Optionnel"
          />
        </div>

        <div>
          <Label htmlFor="rate_limit_tpm">Limite tokens/min</Label>
          <Input
            id="rate_limit_tpm"
            type="number"
            value={localConfig.rate_limit_tpm || ''}
            onChange={(e) => handleConfigChange('rate_limit_tpm', e.target.value ? parseInt(e.target.value) : null)}
            placeholder="Optionnel"
          />
        </div>
      </div>

      <div className="md:col-span-2 flex justify-end">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Sauvegarde...' : 'Sauvegarder'}
        </Button>
      </div>
    </div>
  );
}

// Composant liste des modèles
function ModelsList({ 
  models, 
  activeModel, 
  onSelectModel 
}: {
  models: LLMModel[];
  activeModel: string;
  onSelectModel: (modelId: string) => void;
}) {
  const formatCost = (cost: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 4 
    }).format(cost);
  };

  return (
    <div className="space-y-2">
      {models.map((model) => (
        <Card 
          key={model.id}
          className={`cursor-pointer transition-all duration-200 hover:shadow-md ${
            activeModel === model.id ? 'ring-2 ring-blue-500' : ''
          }`}
          onClick={() => onSelectModel(model.id)}
        >
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <h4 className="font-medium">{model.name}</h4>
                <p className="text-sm text-gray-600 dark:text-gray-400">{model.description}</p>
              </div>
              <div className="text-right text-sm">
                <div>{model.context_length.toLocaleString()} tokens</div>
                <div className="text-gray-600 dark:text-gray-400">
                  {formatCost(model.cost_per_1k_tokens)}/1K
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-2 mt-2">
              {model.supports_function_calling && (
                <Badge variant="secondary" className="text-xs">Functions</Badge>
              )}
              {model.multimodal && (
                <Badge variant="secondary" className="text-xs">Multimodal</Badge>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Composant statistiques provider
function ProviderStats({ stats }: { stats: ProviderStats }) {
  const formatCost = (cost: number) => {
    return new Intl.NumberFormat('fr-FR', { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 4 
    }).format(cost);
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      <div className="text-center">
        <div className="text-2xl font-bold">{stats.total_requests.toLocaleString()}</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Requêtes totales</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold">{stats.total_tokens.toLocaleString()}</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Tokens utilisés</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold">{formatCost(stats.total_cost)}</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Coût total</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold">{stats.avg_response_time.toFixed(0)}ms</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Temps moyen</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold">{(stats.error_rate * 100).toFixed(1)}%</div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Taux d'erreur</div>
      </div>
      <div className="text-center">
        <div className="text-2xl font-bold">
          {stats.last_used ? new Date(stats.last_used).toLocaleDateString() : 'Jamais'}
        </div>
        <div className="text-sm text-gray-600 dark:text-gray-400">Dernière utilisation</div>
      </div>
    </div>
  );
} 