"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Switch } from '../ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Alert, AlertDescription } from '../ui/alert';
import { Textarea } from '../ui/textarea';

interface NotificationPreferences {
  enabled_types: string[];
  min_priority: string;
  pertinence_threshold: number;
  quiet_hours_start: string | null;
  quiet_hours_end: string | null;
  max_notifications_per_hour: number;
  email_notifications: boolean;
  desktop_notifications: boolean;
  sound_enabled: boolean;
}

interface NotificationMessage {
  id: string;
  type: string;
  priority: string;
  title: string;
  message: string;
  pertinence_score: number;
  created_at: string;
  test?: boolean;
}

interface NotificationType {
  value: string;
  label: string;
  description: string;
}

interface NotificationPriority {
  value: string;
  label: string;
  description: string;
}

interface WebSocketStats {
  total_connections: number;
  unique_users: number;
  active_topics: number;
  last_updated: string;
}

const NotificationCenter: React.FC = () => {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    enabled_types: ["critical_alert", "custom_alert", "daily_summary"],
    min_priority: "medium",
    pertinence_threshold: 0.7,
    quiet_hours_start: null,
    quiet_hours_end: null,
    max_notifications_per_hour: 10,
    email_notifications: false,
    desktop_notifications: true,
    sound_enabled: true
  });

  const [notifications, setNotifications] = useState<NotificationMessage[]>([]);
  const [types, setTypes] = useState<NotificationType[]>([]);
  const [priorities, setPriorities] = useState<NotificationPriority[]>([]);
  const [websocketStats, setWebsocketStats] = useState<WebSocketStats | null>(null);
  
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  
  const [testNotification, setTestNotification] = useState({
    title: "Test de notification",
    message: "Ceci est un test de notification temps réel",
    type: "system_status",
    priority: "medium",
    pertinence_score: 0.8
  });

  const websocket = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    loadInitialData();
    connectWebSocket();
    
    return () => {
      if (websocket.current) {
        websocket.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
    };
  }, []);

  const loadInitialData = async () => {
    try {
      setLoading(true);
      
      // Chargement des préférences
      const prefsResponse = await fetch('/api/v1/notifications/preferences');
      if (prefsResponse.ok) {
        const prefsData = await prefsResponse.json();
        if (prefsData.success) {
          setPreferences(prefsData.data.preferences);
        }
      }

      // Chargement des types et priorités
      const typesResponse = await fetch('/api/v1/notifications/types');
      if (typesResponse.ok) {
        const typesData = await typesResponse.json();
        if (typesData.success) {
          setTypes(typesData.data.types);
          setPriorities(typesData.data.priorities);
        }
      }

      // Chargement des stats WebSocket
      await loadWebSocketStats();

    } catch (error) {
      console.error('Erreur chargement données:', error);
      setError('Erreur lors du chargement des données');
    } finally {
      setLoading(false);
    }
  };

  const loadWebSocketStats = async () => {
    try {
      const response = await fetch('/api/v1/notifications/websocket/stats');
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setWebsocketStats(data.data.websocket_stats);
        }
      }
    } catch (error) {
      console.error('Erreur chargement stats WebSocket:', error);
    }
  };

  const connectWebSocket = () => {
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/v1/notifications/ws?user_id=default`;
      
      websocket.current = new WebSocket(wsUrl);
      
      websocket.current.onopen = () => {
        setIsConnected(true);
        setError(null);
        console.log('WebSocket connecté');
        
        // Ping périodique
        const pingInterval = setInterval(() => {
          if (websocket.current?.readyState === WebSocket.OPEN) {
            websocket.current.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);
      };
      
      websocket.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          
          if (message.type === 'notification') {
            const notification: NotificationMessage = {
              id: message.data.id,
              type: message.data.type,
              priority: message.data.priority,
              title: message.data.title,
              message: message.data.message,
              pertinence_score: message.data.pertinence_score,
              created_at: message.data.created_at,
              test: message.data.test
            };
            
            setNotifications(prev => [notification, ...prev].slice(0, 50));
            
            // Notification navigateur si activée
            if (preferences.desktop_notifications && 'Notification' in window) {
              if (Notification.permission === 'granted') {
                new Notification(notification.title, {
                  body: notification.message,
                  icon: '/favicon.ico'
                });
              }
            }
            
            // Son si activé
            if (preferences.sound_enabled) {
              const audio = new Audio('/notification-sound.mp3');
              audio.volume = 0.3;
              audio.play().catch(() => {}); // Ignore si pas de son
            }
          }
          
        } catch (error) {
          console.error('Erreur parsing message WebSocket:', error);
        }
      };
      
      websocket.current.onclose = () => {
        setIsConnected(false);
        console.log('WebSocket déconnecté');
        
        // Reconnexion automatique
        reconnectTimeout.current = setTimeout(() => {
          connectWebSocket();
        }, 5000);
      };
      
      websocket.current.onerror = (error) => {
        console.error('Erreur WebSocket:', error);
        setError('Erreur de connexion WebSocket');
      };
      
    } catch (error) {
      console.error('Erreur création WebSocket:', error);
      setError('Impossible de créer la connexion WebSocket');
    }
  };

  const savePreferences = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/notifications/preferences', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(preferences)
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess('Préférences sauvegardées avec succès');
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Erreur lors de la sauvegarde');
      }
      
    } catch (error) {
      console.error('Erreur sauvegarde:', error);
      setError('Erreur lors de la sauvegarde des préférences');
    } finally {
      setLoading(false);
    }
  };

  const sendTestNotification = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/v1/notifications/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(testNotification)
      });
      
      const data = await response.json();
      
      if (data.success) {
        setSuccess(`Notification de test envoyée à ${data.data.sent_to_connections} connexion(s)`);
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(data.error || 'Erreur lors de l\'envoi du test');
      }
      
    } catch (error) {
      console.error('Erreur test notification:', error);
      setError('Erreur lors de l\'envoi de la notification de test');
    } finally {
      setLoading(false);
    }
  };

  const requestNotificationPermission = async () => {
    if ('Notification' in window && Notification.permission === 'default') {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        setSuccess('Permissions de notification accordées');
        setTimeout(() => setSuccess(null), 3000);
      }
    }
  };

  const getPriorityColor = (priority: string) => {
    const colors = {
      low: 'bg-gray-100 text-gray-800',
      medium: 'bg-blue-100 text-blue-800',
      high: 'bg-yellow-100 text-yellow-800',
      urgent: 'bg-orange-100 text-orange-800',
      critical: 'bg-red-100 text-red-800'
    };
    return colors[priority as keyof typeof colors] || colors.medium;
  };

  const getTypeIcon = (type: string) => {
    const icons = {
      critical_alert: '🚨',
      custom_alert: '📢',
      daily_summary: '📋',
      focus_mode: '🎯',
      system_status: 'ℹ️'
    };
    return icons[type as keyof typeof icons] || '🔔';
  };

  return (
    <div className="space-y-6">
      {/* Indicateurs de statut */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">WebSocket</p>
                <p className={`text-lg font-bold ${isConnected ? 'text-green-600' : 'text-red-600'}`}>
                  {isConnected ? 'Connecté' : 'Déconnecté'}
                </p>
              </div>
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Notifications</p>
                <p className="text-lg font-bold text-blue-600">
                  {notifications.length}
                </p>
              </div>
              <span className="text-2xl">🔔</span>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Connexions</p>
                <p className="text-lg font-bold text-purple-600">
                  {websocketStats?.total_connections || 0}
                </p>
              </div>
              <span className="text-2xl">👥</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Messages d'état */}
      {error && (
        <Alert className="border-red-200 bg-red-50">
          <AlertDescription className="text-red-800">
            {error}
          </AlertDescription>
        </Alert>
      )}
      
      {success && (
        <Alert className="border-green-200 bg-green-50">
          <AlertDescription className="text-green-800">
            {success}
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="preferences" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="preferences">Préférences</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="test">Test</TabsTrigger>
          <TabsTrigger value="stats">Statistiques</TabsTrigger>
        </TabsList>

        {/* Onglet Préférences */}
        <TabsContent value="preferences" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Préférences de Notifications</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Types de notifications */}
              <div>
                <Label className="text-base font-medium">Types de notifications activés</Label>
                <div className="mt-2 space-y-2">
                  {types.map((type) => (
                    <div key={type.value} className="flex items-center space-x-2">
                      <Switch
                        checked={preferences.enabled_types.includes(type.value)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setPreferences(prev => ({
                              ...prev,
                              enabled_types: [...prev.enabled_types, type.value]
                            }));
                          } else {
                            setPreferences(prev => ({
                              ...prev,
                              enabled_types: prev.enabled_types.filter(t => t !== type.value)
                            }));
                          }
                        }}
                      />
                      <div className="flex-1">
                        <Label className="font-medium">{type.label}</Label>
                        <p className="text-sm text-gray-600">{type.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Priorité minimum */}
              <div>
                <Label className="text-base font-medium">Priorité minimum</Label>
                <select
                  value={preferences.min_priority}
                  onChange={(e) => setPreferences(prev => ({ ...prev, min_priority: e.target.value }))}
                  className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                >
                  {priorities.map((priority) => (
                    <option key={priority.value} value={priority.value}>
                      {priority.label} - {priority.description}
                    </option>
                  ))}
                </select>
              </div>

              {/* Seuil de pertinence */}
              <div>
                <Label className="text-base font-medium">
                  Seuil de pertinence: {preferences.pertinence_threshold.toFixed(1)}
                </Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={preferences.pertinence_threshold}
                  onChange={(e) => setPreferences(prev => ({ 
                    ...prev, 
                    pertinence_threshold: parseFloat(e.target.value) 
                  }))}
                  className="mt-1 w-full"
                />
                <div className="flex justify-between text-sm text-gray-500 mt-1">
                  <span>Tous (0.0)</span>
                  <span>Sélectif (1.0)</span>
                </div>
              </div>

              {/* Heures de silence */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-base font-medium">Début silence</Label>
                  <Input
                    type="time"
                    value={preferences.quiet_hours_start || ''}
                    onChange={(e) => setPreferences(prev => ({ 
                      ...prev, 
                      quiet_hours_start: e.target.value || null 
                    }))}
                  />
                </div>
                <div>
                  <Label className="text-base font-medium">Fin silence</Label>
                  <Input
                    type="time"
                    value={preferences.quiet_hours_end || ''}
                    onChange={(e) => setPreferences(prev => ({ 
                      ...prev, 
                      quiet_hours_end: e.target.value || null 
                    }))}
                  />
                </div>
              </div>

              {/* Limite par heure */}
              <div>
                <Label className="text-base font-medium">
                  Notifications max par heure: {preferences.max_notifications_per_hour}
                </Label>
                <input
                  type="range"
                  min="1"
                  max="50"
                  value={preferences.max_notifications_per_hour}
                  onChange={(e) => setPreferences(prev => ({ 
                    ...prev, 
                    max_notifications_per_hour: parseInt(e.target.value) 
                  }))}
                  className="mt-1 w-full"
                />
              </div>

              {/* Options supplémentaires */}
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={preferences.desktop_notifications}
                    onCheckedChange={(checked) => setPreferences(prev => ({ 
                      ...prev, 
                      desktop_notifications: checked 
                    }))}
                  />
                  <Label>Notifications navigateur</Label>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={requestNotificationPermission}
                  >
                    Autoriser
                  </Button>
                </div>
                
                <div className="flex items-center space-x-2">
                  <Switch
                    checked={preferences.sound_enabled}
                    onCheckedChange={(checked) => setPreferences(prev => ({ 
                      ...prev, 
                      sound_enabled: checked 
                    }))}
                  />
                  <Label>Son activé</Label>
                </div>
              </div>

              <Button 
                onClick={savePreferences} 
                disabled={loading}
                className="w-full"
              >
                {loading ? 'Sauvegarde...' : 'Sauvegarder les préférences'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Onglet Notifications */}
        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Notifications Reçues ({notifications.length})</CardTitle>
            </CardHeader>
            <CardContent>
              {notifications.length === 0 ? (
                <p className="text-gray-500 text-center py-8">
                  Aucune notification reçue
                </p>
              ) : (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className="border rounded-lg p-3 hover:bg-gray-50"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center space-x-2 mb-2">
                            <span className="text-lg">
                              {getTypeIcon(notification.type)}
                            </span>
                            <Badge className={getPriorityColor(notification.priority)}>
                              {notification.priority}
                            </Badge>
                            <Badge variant="outline">
                              {notification.pertinence_score.toFixed(1)}
                            </Badge>
                            {notification.test && (
                              <Badge variant="secondary">TEST</Badge>
                            )}
                          </div>
                          <h4 className="font-medium text-sm">
                            {notification.title}
                          </h4>
                          <p className="text-sm text-gray-600 mt-1">
                            {notification.message}
                          </p>
                        </div>
                        <div className="text-xs text-gray-500">
                          {new Date(notification.created_at).toLocaleTimeString()}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Onglet Test */}
        <TabsContent value="test" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Test de Notification</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Titre</Label>
                <Input
                  value={testNotification.title}
                  onChange={(e) => setTestNotification(prev => ({ 
                    ...prev, 
                    title: e.target.value 
                  }))}
                />
              </div>
              
              <div>
                <Label>Message</Label>
                <Textarea
                  value={testNotification.message}
                  onChange={(e) => setTestNotification(prev => ({ 
                    ...prev, 
                    message: e.target.value 
                  }))}
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Type</Label>
                  <select
                    value={testNotification.type}
                    onChange={(e) => setTestNotification(prev => ({ 
                      ...prev, 
                      type: e.target.value 
                    }))}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    {types.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>
                
                <div>
                  <Label>Priorité</Label>
                  <select
                    value={testNotification.priority}
                    onChange={(e) => setTestNotification(prev => ({ 
                      ...prev, 
                      priority: e.target.value 
                    }))}
                    className="mt-1 block w-full border border-gray-300 rounded-md px-3 py-2"
                  >
                    {priorities.map((priority) => (
                      <option key={priority.value} value={priority.value}>
                        {priority.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              
              <div>
                <Label>Score de pertinence: {testNotification.pertinence_score}</Label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={testNotification.pertinence_score}
                  onChange={(e) => setTestNotification(prev => ({ 
                    ...prev, 
                    pertinence_score: parseFloat(e.target.value) 
                  }))}
                  className="mt-1 w-full"
                />
              </div>
              
              <Button 
                onClick={sendTestNotification} 
                disabled={loading || !isConnected}
                className="w-full"
              >
                {loading ? 'Envoi...' : 'Envoyer Test'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Onglet Statistiques */}
        <TabsContent value="stats" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Statistiques WebSocket</CardTitle>
            </CardHeader>
            <CardContent>
              {websocketStats ? (
                <div className="grid grid-cols-2 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">
                      {websocketStats.total_connections}
                    </p>
                    <p className="text-sm text-gray-600">Connexions totales</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">
                      {websocketStats.unique_users}
                    </p>
                    <p className="text-sm text-gray-600">Utilisateurs uniques</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Chargement des statistiques...</p>
              )}
              
              <Button 
                onClick={loadWebSocketStats} 
                variant="outline" 
                className="w-full mt-4"
              >
                Actualiser
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default NotificationCenter;