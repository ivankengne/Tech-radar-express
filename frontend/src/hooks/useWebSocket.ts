/**
 * Tech Radar Express - Hook useWebSocket
 * Hook React pour gestion des connexions WebSocket temps réel
 * Support streaming réponses recherche, notifications et updates dashboard
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'

export interface WebSocketMessage {
  type: string
  data: any
  timestamp: number
  id?: string
}

export interface WebSocketConfig {
  url?: string
  protocols?: string[]
  reconnectAttempts?: number
  reconnectInterval?: number
  heartbeatInterval?: number
  onConnect?: () => void
  onDisconnect?: () => void
  onError?: (error: Event) => void
  onMessage?: (message: WebSocketMessage) => void
  autoConnect?: boolean
}

export interface UseWebSocketReturn {
  // État de la connexion
  isConnected: boolean
  isConnecting: boolean
  isReconnecting: boolean
  
  // Fonctions de contrôle
  connect: () => void
  disconnect: () => void
  send: (message: any) => boolean
  
  // Messages et événements
  lastMessage: WebSocketMessage | null
  connectionError: string | null
  
  // Métriques
  reconnectCount: number
  messageCount: number
}

const DEFAULT_CONFIG: WebSocketConfig = {
  url: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/ws',
  protocols: [],
  reconnectAttempts: 5,
  reconnectInterval: 3000,
  heartbeatInterval: 30000,
  autoConnect: true
}

export function useWebSocket(config: WebSocketConfig = {}): UseWebSocketReturn {
  const router = useRouter()
  
  // Configuration fusionnée
  const fullConfig = { ...DEFAULT_CONFIG, ...config }
  
  // Refs pour éviter les re-renders
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const heartbeatTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const messageQueueRef = useRef<any[]>([])
  
  // État du hook
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isReconnecting, setIsReconnecting] = useState(false)
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [reconnectCount, setReconnectCount] = useState(0)
  const [messageCount, setMessageCount] = useState(0)
  
  // ===================================
  // FONCTIONS UTILITAIRES
  // ===================================
  
  const clearTimeouts = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }
    if (heartbeatTimeoutRef.current) {
      clearTimeout(heartbeatTimeoutRef.current)
      heartbeatTimeoutRef.current = null
    }
  }, [])
  
  const startHeartbeat = useCallback(() => {
    if (!fullConfig.heartbeatInterval) return
    
    heartbeatTimeoutRef.current = setTimeout(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }))
        startHeartbeat() // Programmer le prochain heartbeat
      }
    }, fullConfig.heartbeatInterval)
  }, [fullConfig.heartbeatInterval])
  
  const processMessageQueue = useCallback(() => {
    while (messageQueueRef.current.length > 0 && wsRef.current?.readyState === WebSocket.OPEN) {
      const message = messageQueueRef.current.shift()
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])
  
  // ===================================
  // GESTION DE LA CONNEXION
  // ===================================
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('WebSocket déjà connecté')
      return
    }
    
    if (isConnecting) {
      console.log('Connexion WebSocket en cours...')
      return
    }
    
    setIsConnecting(true)
    setConnectionError(null)
    clearTimeouts()
    
    try {
      console.log(`Connexion WebSocket à ${fullConfig.url}`)
      
      wsRef.current = new WebSocket(fullConfig.url!, fullConfig.protocols)
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connecté avec succès')
        setIsConnected(true)
        setIsConnecting(false)
        setIsReconnecting(false)
        setConnectionError(null)
        setReconnectCount(0)
        
        // Traiter la queue des messages en attente
        processMessageQueue()
        
        // Démarrer le heartbeat
        startHeartbeat()
        
        // Callback utilisateur
        fullConfig.onConnect?.()
      }
      
      wsRef.current.onmessage = (event) => {
        try {
          const messageData = JSON.parse(event.data)
          const message: WebSocketMessage = {
            type: messageData.type || 'message',
            data: messageData.data || messageData,
            timestamp: messageData.timestamp || Date.now(),
            id: messageData.id
          }
          
          setLastMessage(message)
          setMessageCount(prev => prev + 1)
          
          // Callback utilisateur
          fullConfig.onMessage?.(message)
          
          // Gestion des messages système
          if (message.type === 'pong') {
            // Réponse au ping - maintenir la connexion
            console.log('Heartbeat reçu')
          }
          
        } catch (error) {
          console.error('Erreur parsing message WebSocket:', error)
        }
      }
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket fermé:', event.code, event.reason)
        setIsConnected(false)
        setIsConnecting(false)
        clearTimeouts()
        
        // Callback utilisateur
        fullConfig.onDisconnect?.()
        
        // Tentative de reconnexion si pas volontaire
        if (event.code !== 1000 && reconnectCount < fullConfig.reconnectAttempts!) {
          scheduleReconnect()
        }
      }
      
      wsRef.current.onerror = (error) => {
        console.error('Erreur WebSocket:', error)
        setConnectionError('Erreur de connexion WebSocket')
        setIsConnecting(false)
        
        // Callback utilisateur
        fullConfig.onError?.(error)
      }
      
    } catch (error) {
      console.error('Erreur création WebSocket:', error)
      setConnectionError(`Erreur création WebSocket: ${error}`)
      setIsConnecting(false)
    }
  }, [
    fullConfig,
    isConnecting,
    reconnectCount,
    clearTimeouts,
    processMessageQueue,
    startHeartbeat
  ])
  
  const scheduleReconnect = useCallback(() => {
    if (reconnectCount >= fullConfig.reconnectAttempts!) {
      console.log('Nombre max de tentatives de reconnexion atteint')
      setIsReconnecting(false)
      return
    }
    
    setIsReconnecting(true)
    setReconnectCount(prev => prev + 1)
    
    const delay = fullConfig.reconnectInterval! * Math.pow(1.5, reconnectCount) // Backoff exponentiel
    
    console.log(`Reconnexion WebSocket dans ${delay}ms (tentative ${reconnectCount + 1}/${fullConfig.reconnectAttempts})`)
    
    reconnectTimeoutRef.current = setTimeout(() => {
      connect()
    }, delay)
  }, [reconnectCount, fullConfig.reconnectAttempts, fullConfig.reconnectInterval, connect])
  
  const disconnect = useCallback(() => {
    console.log('Déconnexion WebSocket volontaire')
    clearTimeouts()
    setReconnectCount(fullConfig.reconnectAttempts!) // Empêcher la reconnexion auto
    
    if (wsRef.current) {
      wsRef.current.close(1000, 'Disconnection requested')
      wsRef.current = null
    }
    
    setIsConnected(false)
    setIsConnecting(false)
    setIsReconnecting(false)
  }, [clearTimeouts, fullConfig.reconnectAttempts])
  
  // ===================================
  // ENVOI DE MESSAGES
  // ===================================
  
  const send = useCallback((message: any): boolean => {
    if (!message) {
      console.warn('Tentative d\'envoi d\'un message vide')
      return false
    }
    
    const messageWithTimestamp = {
      ...message,
      timestamp: Date.now()
    }
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify(messageWithTimestamp))
        console.log('Message WebSocket envoyé:', messageWithTimestamp.type || 'message')
        return true
      } catch (error) {
        console.error('Erreur envoi message WebSocket:', error)
        return false
      }
    } else {
      // Ajouter à la queue si pas connecté
      console.log('WebSocket non connecté, ajout du message à la queue')
      messageQueueRef.current.push(messageWithTimestamp)
      
      // Essayer de se connecter si pas déjà en cours
      if (!isConnecting && !isConnected) {
        connect()
      }
      
      return false
    }
  }, [isConnecting, isConnected, connect])
  
  // ===================================
  // EFFETS DE CYCLE DE VIE
  // ===================================
  
  // Auto-connexion au montage
  useEffect(() => {
    if (fullConfig.autoConnect) {
      connect()
    }
    
    // Nettoyage au démontage
    return () => {
      clearTimeouts()
      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounting')
      }
    }
  }, []) // Volontairement vide pour n'exécuter qu'au montage
  
  // Gestion de la visibilité de la page
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // Page cachée - réduire l'activité
        clearTimeouts()
      } else if (isConnected) {
        // Page visible - reprendre l'activité
        startHeartbeat()
      } else if (fullConfig.autoConnect) {
        // Tentative de reconnexion si déconnecté
        connect()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [isConnected, fullConfig.autoConnect, connect, startHeartbeat, clearTimeouts])
  
  return {
    // État
    isConnected,
    isConnecting,
    isReconnecting,
    
    // Contrôle
    connect,
    disconnect,
    send,
    
    // Messages
    lastMessage,
    connectionError,
    
    // Métriques
    reconnectCount,
    messageCount
  }
}

// Hook spécialisé pour le streaming de recherche
export function useSearchStream() {
  const [streamingResults, setStreamingResults] = useState<any[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamError, setStreamError] = useState<string | null>(null)
  
  const { isConnected, send, lastMessage } = useWebSocket({
    onMessage: (message) => {
      if (message.type.startsWith('search_')) {
        handleSearchMessage(message)
      }
    }
  })
  
  const handleSearchMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'search_start':
        setIsStreaming(true)
        setStreamingResults([])
        setStreamError(null)
        break
        
      case 'search_result':
        setStreamingResults(prev => [...prev, message.data])
        break
        
      case 'search_complete':
        setIsStreaming(false)
        break
        
      case 'search_error':
        setIsStreaming(false)
        setStreamError(message.data.error || 'Erreur de recherche')
        break
    }
  }, [])
  
  const startSearchStream = useCallback((query: string, options: any = {}) => {
    if (!isConnected) {
      console.warn('WebSocket non connecté pour le streaming de recherche')
      return false
    }
    
    return send({
      type: 'search_request',
      data: {
        query,
        ...options,
        streaming: true
      }
    })
  }, [isConnected, send])
  
  return {
    streamingResults,
    isStreaming,
    streamError,
    startSearchStream,
    isConnected
  }
}

export default useWebSocket 