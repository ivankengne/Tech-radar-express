"use client";

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Bell, 
  Plus, 
  Settings, 
  Play,
  Trash2,
  AlertTriangle,
  Shield,
  Brain,
  Smartphone,
  Cloud,
  Loader2,
  Search,
  X
} from 'lucide-react';

interface Alert {
  id: string;
  name: string;
  description: string;
  priority: string;
  status: string;
  created_at: string;
  last_triggered?: string;
  trigger_count: number;
}

interface AlertStats {
  total_alerts: number;
  active_alerts: number;
  priority_distribution: Record<string, number>;
  recent_triggers_24h: number;
}

const AlertsManagement: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Formulaire de création
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    keywords: '',
    tech_areas: [] as string[],
    min_impact_level: 1,
    priority: 'medium'
  });

  // Aires technologiques disponibles
  const techAreas = [
    { value: 'AI/ML', label: 'IA/ML', icon: <Brain className="w-4 h-4" /> },
    { value: 'Security', label: 'Sécurité', icon: <Shield className="w-4 h-4" /> },
    { value: 'Frontend', label: 'Frontend', icon: <Smartphone className="w-4 h-4" /> },
    { value: 'Backend', label: 'Backend', icon: <Settings className="w-4 h-4" /> },
    { value: 'Cloud', label: 'Cloud', icon: <Cloud className="w-4 h-4" /> }
  ];

  // Chargement initial
  useEffect(() => {
    loadAlerts();
    loadStats();
  }, []);

  const loadAlerts = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/v1/alerts/list');
      const data = await response.json();
      
      if (data.success) {
        setAlerts(data.data.alerts || []);
      } else {
        setError(data.error || 'Erreur chargement alertes');
      }
    } catch (err) {
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/alerts/stats/overview');
      const data = await response.json();
      
      if (data.success) {
        setStats(data.data.stats);
      }
    } catch (err) {
      console.error('Erreur stats:', err);
    }
  };

  const createAlert = async () => {
    try {
      setLoading(true);
      
      const alertData = {
        name: formData.name,
        description: formData.description,
        criteria: {
          keywords: formData.keywords.split(',').map(k => k.trim()).filter(k => k),
          excluded_keywords: [],
          tech_areas: formData.tech_areas,
          sources: [],
          min_impact_level: formData.min_impact_level
        },
        notifications: {
          email_recipients: [],
          throttle_minutes: 60
        },
        priority: formData.priority
      };

      const response = await fetch('/api/v1/alerts/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(alertData),
      });

      const data = await response.json();

      if (data.success) {
        setShowCreateForm(false);
        resetForm();
        loadAlerts();
        loadStats();
      } else {
        setError(data.error || 'Erreur création alerte');
      }
    } catch (err) {
      setError('Erreur de connexion');
    } finally {
      setLoading(false);
    }
  };

  const deleteAlert = async (alertId: string) => {
    if (!confirm('Supprimer cette alerte ?')) {
      return;
    }

    try {
      const response = await fetch(`/api/v1/alerts/${alertId}`, {
        method: 'DELETE',
      });

      const data = await response.json();

      if (data.success) {
        loadAlerts();
        loadStats();
      } else {
        setError(data.error || 'Erreur suppression');
      }
    } catch (err) {
      setError('Erreur de connexion');
    }
  };

  const checkAlerts = async () => {
    try {
      await fetch('/api/v1/alerts/check', { method: 'POST' });
      loadStats();
    } catch (err) {
      setError('Erreur vérification');
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      description: '',
      keywords: '',
      tech_areas: [],
      min_impact_level: 1,
      priority: 'medium'
    });
  };

  const loadTemplate = (templateKey: string) => {
    const templates = {
      security: {
        name: 'Alertes Sécurité',
        description: 'Surveillance des vulnérabilités critiques',
        keywords: 'vulnerability, breach, exploit, critical',
        tech_areas: ['Security'],
        min_impact_level: 4,
        priority: 'critical'
      },
      ai: {
        name: 'Innovations IA',
        description: 'Nouvelles technologies IA',
        keywords: 'GPT, LLM, AI, machine learning',
        tech_areas: ['AI/ML'],
        min_impact_level: 3,
        priority: 'high'
      }
    };

    const template = templates[templateKey as keyof typeof templates];
    if (template) {
      setFormData(template);
    }
  };

  // Filtrage des alertes
  const filteredAlerts = alerts.filter(alert => 
    searchTerm === '' || 
    alert.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    alert.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPriorityColor = (priority: string) => {
    const colors = {
      low: 'bg-blue-100 text-blue-800',
      medium: 'bg-yellow-100 text-yellow-800',
      high: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return colors[priority as keyof typeof colors] || colors.medium;
  };

  const getStatusColor = (status: string) => {
    const colors = {
      active: 'bg-green-100 text-green-800',
      paused: 'bg-gray-100 text-gray-800'
    };
    return colors[status as keyof typeof colors] || colors.active;
  };

  return (
    <div className="space-y-6">
      {/* En-tête */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bell className="w-6 h-6 text-blue-600" />
          <h1 className="text-2xl font-bold">Alertes Personnalisées</h1>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={checkAlerts} variant="outline" size="sm">
            <Play className="w-4 h-4 mr-2" />
            Vérifier
          </Button>
          <Button onClick={() => setShowCreateForm(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Nouvelle Alerte
          </Button>
        </div>
      </div>

      {/* Statistiques */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-blue-600">{stats.total_alerts}</div>
              <div className="text-sm text-gray-500">Total alertes</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-green-600">{stats.active_alerts}</div>
              <div className="text-sm text-gray-500">Actives</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-orange-600">
                {stats.priority_distribution.critical || 0}
              </div>
              <div className="text-sm text-gray-500">Critiques</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-2xl font-bold text-purple-600">{stats.recent_triggers_24h}</div>
              <div className="text-sm text-gray-500">Déclenchements 24h</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Erreur */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                <span>{error}</span>
              </div>
              <Button onClick={() => setError(null)} variant="ghost" size="sm">
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Formulaire création */}
      {showCreateForm && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Créer une alerte</CardTitle>
              <Button onClick={() => setShowCreateForm(false)} variant="ghost" size="sm">
                <X className="w-4 h-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Templates */}
            <div>
              <label className="block text-sm font-medium mb-2">Templates</label>
              <div className="flex gap-2">
                <Button onClick={() => loadTemplate('security')} variant="outline" size="sm">
                  Sécurité
                </Button>
                <Button onClick={() => loadTemplate('ai')} variant="outline" size="sm">
                  IA/ML
                </Button>
              </div>
            </div>

            {/* Formulaire */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">Nom</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                  placeholder="Nom de l'alerte"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Priorité</label>
                <select
                  value={formData.priority}
                  onChange={(e) => setFormData({...formData, priority: e.target.value})}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                >
                  <option value="low">Faible</option>
                  <option value="medium">Moyenne</option>
                  <option value="high">Élevée</option>
                  <option value="critical">Critique</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                className="w-full px-3 py-2 border rounded-md text-sm"
                rows={3}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Mots-clés (séparés par virgules)</label>
              <input
                type="text"
                value={formData.keywords}
                onChange={(e) => setFormData({...formData, keywords: e.target.value})}
                className="w-full px-3 py-2 border rounded-md text-sm"
                placeholder="vulnerability, breach, exploit"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Aires technologiques</label>
              <div className="flex flex-wrap gap-2">
                {techAreas.map(area => (
                  <Button
                    key={area.value}
                    onClick={() => {
                      const newAreas = formData.tech_areas.includes(area.value)
                        ? formData.tech_areas.filter(a => a !== area.value)
                        : [...formData.tech_areas, area.value];
                      setFormData({...formData, tech_areas: newAreas});
                    }}
                    variant={formData.tech_areas.includes(area.value) ? "default" : "outline"}
                    size="sm"
                    className="flex items-center space-x-1"
                  >
                    {area.icon}
                    <span>{area.label}</span>
                  </Button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Niveau d'impact minimum</label>
              <select
                value={formData.min_impact_level}
                onChange={(e) => setFormData({...formData, min_impact_level: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border rounded-md text-sm"
              >
                <option value={1}>1 - Très faible</option>
                <option value={2}>2 - Faible</option>
                <option value={3}>3 - Moyen</option>
                <option value={4}>4 - Élevé</option>
                <option value={5}>5 - Critique</option>
              </select>
            </div>

            {/* Boutons */}
            <div className="flex items-center justify-end space-x-2">
              <Button onClick={() => setShowCreateForm(false)} variant="outline">
                Annuler
              </Button>
              <Button
                onClick={createAlert}
                disabled={loading || !formData.name || !formData.keywords}
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
                Créer
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recherche */}
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Rechercher une alerte..."
              className="w-full pl-10 pr-3 py-2 border rounded-md text-sm"
            />
          </div>
        </CardContent>
      </Card>

      {/* Liste des alertes */}
      <div className="space-y-4">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          </div>
        )}

        {!loading && filteredAlerts.length === 0 && (
          <Card>
            <CardContent className="pt-6">
              <div className="text-center text-gray-500">
                Aucune alerte trouvée
              </div>
            </CardContent>
          </Card>
        )}

        {!loading && filteredAlerts.map(alert => (
          <Card key={alert.id}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-2">
                    <h3 className="text-lg font-semibold">{alert.name}</h3>
                    <Badge className={getPriorityColor(alert.priority)}>
                      {alert.priority}
                    </Badge>
                    <Badge className={getStatusColor(alert.status)}>
                      {alert.status}
                    </Badge>
                  </div>
                  
                  <p className="text-sm text-gray-600 mb-3">{alert.description}</p>
                  
                  <div className="text-sm text-gray-500">
                    Créée le {new Date(alert.created_at).toLocaleDateString('fr-FR')}
                    {alert.last_triggered && (
                      <span> • Dernier déclenchement: {new Date(alert.last_triggered).toLocaleDateString('fr-FR')}</span>
                    )}
                    <span> • {alert.trigger_count} déclenchements</span>
                  </div>
                </div>
                
                <Button
                  onClick={() => deleteAlert(alert.id)}
                  variant="outline"
                  size="sm"
                  className="text-red-600 hover:text-red-700"
                >
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default AlertsManagement; 