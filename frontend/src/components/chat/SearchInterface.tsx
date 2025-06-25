"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Lightbulb, Clock, Sparkles } from 'lucide-react';
import QueryCitation, { CitationData } from './QueryCitation';

// Types pour les messages du chat
interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  isThinking?: boolean;
  citations?: CitationData[];
  metadata?: {
    sources: string[];
    processingTime: number;
    tokensUsed: number;
  };
}

// Utilisation du type CitationData importé de QueryCitation

interface SearchInterfaceProps {
  className?: string;
}

export function SearchInterface({ className = "" }: SearchInterfaceProps) {
  // États locaux
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  
  // Refs pour le scroll automatique
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll vers le bas quand de nouveaux messages arrivent
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Ajuster la hauteur du textarea automatiquement
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px';
    }
  }, [inputValue]);

  // Message d'accueil initial
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage: ChatMessage = {
        id: 'welcome',
        type: 'system',
        content: `👋 Bonjour ! Je suis votre assistant IA spécialisé en veille technologique.

🔍 **Je peux vous aider à :**
- Rechercher des informations techniques précises
- Analyser les tendances technologiques 
- Comparer des frameworks et outils
- Identifier les innovations émergentes

💡 **Conseils :**
- Utilisez le bouton "/think" pour une analyse approfondie
- Posez des questions spécifiques pour de meilleurs résultats
- Je cite toujours mes sources pour que vous puissiez approfondir

*Que souhaitez-vous découvrir aujourd'hui ?*`,
        timestamp: new Date(),
      };
      setMessages([welcomeMessage]);
    }
  }, []);

  // Exemples de questions suggérées
  const suggestedQuestions = [
    "Quelles sont les tendances React en 2024 ?",
    "Compare FastAPI vs Django pour APIs",
    "Nouveautés Docker et Kubernetes récentes",
    "Meilleures pratiques sécurité frontend",
  ];

  const handleSendMessage = async (content: string, isThinkMode: boolean = false) => {
    if (!content.trim() || isLoading) return;

    // Message utilisateur
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      type: 'user', 
      content: content.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    // ID pour le message assistant (utilisé aussi en mode think)
    const assistantMessageId = `assistant-${Date.now()}`;

    try {
      // Mode "think" avec streaming progressif de la réflexion
      if (isThinkMode) {
        setIsThinking(true);
        
        // Initialiser un message assistant vide pour le streaming
        const initialMessage: ChatMessage = {
          id: assistantMessageId,
          type: 'assistant',
          content: '',
          timestamp: new Date(),
          isThinking: true,
        };
        
        setMessages(prev => [...prev, initialMessage]);
        
        // Étapes de réflexion avec streaming progressif
        const thinkingSteps = [
          {
            content: '🤔 **Analyse approfondie initiée...**\n\nJ\'identifie les concepts clés de votre question.',
            delay: 800
          },
          {
            content: '🤔 **Analyse approfondie initiée...**\n\nJ\'identifie les concepts clés de votre question.\n\n🔍 **Recherche en cours...**\nCollecte d\'informations depuis la base de veille technologique.',
            delay: 1200
          },
          {
            content: '🤔 **Analyse approfondie initiée...**\n\nJ\'identifie les concepts clés de votre question.\n\n🔍 **Recherche en cours...**\nCollecte d\'informations depuis la base de veille technologique.\n\n📊 **Analyse des données...**\nÉvaluation de la pertinence et croisement des sources.',
            delay: 1000
          },
          {
            content: '🤔 **Analyse approfondie initiée...**\n\nJ\'identifie les concepts clés de votre question.\n\n🔍 **Recherche en cours...**\nCollecte d\'informations depuis la base de veille technologique.\n\n📊 **Analyse des données...**\nÉvaluation de la pertinence et croisement des sources.\n\n🧠 **Synthèse et structuration...**\nOrganisation des informations pour une réponse complète.',
            delay: 800
          }
        ];

        // Streaming progressif des étapes de réflexion
        for (const step of thinkingSteps) {
          await new Promise(resolve => setTimeout(resolve, step.delay));
          
          setMessages(prev => prev.map(msg => 
            msg.id === assistantMessageId 
              ? { ...msg, content: step.content }
              : msg
          ));
        }
        
        // Petite pause avant la réponse finale
        await new Promise(resolve => setTimeout(resolve, 500));
        setIsThinking(false);
      }

      // TODO: Intégrer avec l'API backend /api/v1/search/query
      // Pour l'instant, simulation d'une réponse
      const mockResponse = await simulateAPIResponse(content, isThinkMode);
      
      if (isThinkMode) {
        // Mettre à jour le message existant avec la réponse finale
        setMessages(prev => prev.map(msg => 
          msg.id === assistantMessageId 
            ? { 
                ...msg, 
                content: mockResponse.content,
                isThinking: false,
                citations: mockResponse.citations,
                metadata: mockResponse.metadata
              }
            : msg
        ));
      } else {
        // Message assistant normal (mode non-think)
        const assistantMessage: ChatMessage = {
          id: `assistant-${Date.now()}`,
          type: 'assistant',
          content: mockResponse.content,
          timestamp: new Date(),
          citations: mockResponse.citations,
          metadata: mockResponse.metadata,
        };

        setMessages(prev => [...prev, assistantMessage]);
      }

    } catch (error) {
      console.error('Erreur lors de l\'envoi du message:', error);
      
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        type: 'system',
        content: '❌ Désolé, une erreur est survenue. Veuillez réessayer.',
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      setIsThinking(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage(inputValue);
    }
  };

  const handleThinkMode = () => {
    if (inputValue.trim()) {
      handleSendMessage(inputValue, true);
    }
  };

  const handleSuggestionClick = (question: string) => {
    setInputValue(question);
    textareaRef.current?.focus();
  };

  return (
    <div className={`flex flex-col h-full bg-white dark:bg-gray-900 ${className}`}>
      {/* En-tête du chat */}
      <div className="flex-shrink-0 border-b border-gray-200 dark:border-gray-700 p-4">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
            <Bot className="w-6 h-6 text-white" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              Assistant IA Tech Radar
            </h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Recherche conversationnelle avec citations
            </p>
          </div>
          
          {/* Indicateur de statut */}
          <div className="ml-auto flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-xs text-gray-500 dark:text-gray-400">En ligne</span>
            </div>
          </div>
        </div>
      </div>

      {/* Zone des messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {/* Indicateur de frappe */}
        {(isLoading || isThinking) && (
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg">
              <Bot className="w-6 h-6 text-white" />
            </div>
            <div className="bg-gray-100 dark:bg-gray-800 rounded-lg p-3">
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  {isThinking ? 'Réflexion approfondie...' : 'Recherche en cours...'}
                </span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions rapides (seulement si le chat est vide) */}
      {messages.length <= 1 && (
        <div className="flex-shrink-0 p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="mb-3">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
              💡 Questions suggérées :
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {suggestedQuestions.map((question, index) => (
                <button
                  key={index}
                  onClick={() => handleSuggestionClick(question)}
                  className="text-left p-3 bg-gray-50 dark:bg-gray-800 rounded-lg text-sm
                           hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors
                           border border-gray-200 dark:border-gray-600"
                >
                  {question}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Zone de saisie */}
      <div className="flex-shrink-0 border-t border-gray-200 dark:border-gray-700 p-4">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Posez votre question sur la tech... (Entrée pour envoyer, Shift+Entrée pour nouvelle ligne)"
              className="w-full resize-none rounded-lg border border-gray-300 dark:border-gray-600
                       bg-white dark:bg-gray-800 px-4 py-3 pr-12
                       text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400
                       focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                       min-h-[2.75rem] max-h-32"
              rows={1}
              disabled={isLoading}
            />
            
            {/* Bouton /think */}
            {inputValue.trim() && (
              <button
                onClick={handleThinkMode}
                disabled={isLoading}
                className="absolute right-12 top-1/2 -translate-y-1/2 p-1.5 
                         text-purple-600 hover:text-purple-700 dark:text-purple-400 
                         hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-md
                         transition-colors disabled:opacity-50"
                title="Mode réflexion approfondie"
              >
                <Lightbulb className="w-4 h-4" />
              </button>
            )}
          </div>
          
          <button
            onClick={() => handleSendMessage(inputValue)}
            disabled={!inputValue.trim() || isLoading}
            className="flex-shrink-0 p-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400
                     text-white rounded-lg transition-colors disabled:cursor-not-allowed"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
        
        <div className="mt-2 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
          <span>Entrée pour envoyer • Shift+Entrée pour nouvelle ligne</span>
          <span className="flex items-center gap-1">
            <Lightbulb className="w-3 h-3" />
            Bouton "/think" pour analyse approfondie
          </span>
        </div>
      </div>
    </div>
  );
}

// Composant pour afficher un message individual
function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.type === 'user';
  const isSystem = message.type === 'system';
  const isThinking = message.isThinking;

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
        isUser 
          ? 'bg-green-100 dark:bg-green-900/20 text-green-600 dark:text-green-400'
          : isSystem
          ? 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'  
          : isThinking
          ? 'bg-gradient-to-r from-purple-500 to-pink-500 text-white animate-pulse'
          : 'bg-gradient-to-r from-blue-500 to-purple-600 text-white'
      }`}>
        {isUser ? <User className="w-4 h-4" /> : 
         isSystem ? <Sparkles className="w-4 h-4" /> : 
         isThinking ? <Lightbulb className="w-4 h-4 animate-bounce" /> :
         <Bot className="w-4 h-4" />}
      </div>

      {/* Bulle de message */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'text-right' : ''}`}>
        <div className={`inline-block rounded-lg p-4 ${
          isUser 
            ? 'bg-blue-600 text-white'
            : isSystem
            ? 'bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700'
            : isThinking
            ? 'bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 text-purple-900 dark:text-purple-100 border-2 border-purple-200 dark:border-purple-700 shadow-lg'
            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white'
        }`}>
          {/* Contenu du message */}
          <div className={`prose prose-sm max-w-none ${
            isUser ? 'prose-invert' : 'dark:prose-invert'
          }`}>
            <p className="whitespace-pre-wrap">{message.content}</p>
          </div>

          {/* Citations avec volet latéral */}
          {message.citations && message.citations.length > 0 && (
            <QueryCitation citations={message.citations} />
          )}

          {/* Métadonnées */}
          {message.metadata && (
            <div className="mt-2 pt-2 border-t border-gray-300 dark:border-gray-600 text-xs opacity-75">
              <div className="flex items-center gap-4">
                <span>⏱️ {message.metadata.processingTime}ms</span>
                <span>📊 {message.metadata.sources.length} sources</span>
                <span>🎯 {message.metadata.tokensUsed} tokens</span>
              </div>
            </div>
          )}
        </div>

        {/* Timestamp */}
        <div className={`text-xs text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1 ${
          isUser ? 'justify-end' : ''
        }`}>
          <Clock className="w-3 h-3" />
          {message.timestamp.toLocaleTimeString('fr-FR', { 
            hour: '2-digit', 
            minute: '2-digit' 
          })}
        </div>
      </div>
    </div>
  );
}

// Simulation d'une réponse API (à remplacer par le vrai appel)
async function simulateAPIResponse(query: string, isThinkMode: boolean) {
  // Simulation d'un délai réseau
  await new Promise(resolve => setTimeout(resolve, isThinkMode ? 3000 : 1500));

  const mockCitations: CitationData[] = [
    {
      id: '1',
      text: 'React 19 introduit les Server Components qui révolutionnent le rendu côté serveur, améliore les performances de 40% et simplifie la gestion de l\'état des formulaires.',
      source: 'React.dev',
      url: 'https://react.dev/blog/2024/react-19',
      type: 'document',
      chunk_id: 'react-19-release-chunk-1',
      title: 'React 19 - Official Release Notes',
      score: 0.95,
      metadata: {
        word_count: 150,
        char_count: 850,
        rerank_score: 0.92,
        summary: 'Guide complet des nouveautés React 19 avec focus sur les Server Components et l\'amélioration des performances.'
      }
    },
    {
      id: '2',
      text: 'Étude comparative approfondie montrant que FastAPI surpasse Django REST Framework et Flask de 3x en throughput et 60% en latence réduite.',
      source: 'FastAPI Documentation',
      url: 'https://fastapi.tiangolo.com/benchmarks/',
      type: 'document',
      chunk_id: 'fastapi-benchmarks-chunk-2',
      title: 'FastAPI Performance Benchmarks 2024',
      score: 0.88,
      metadata: {
        word_count: 200,
        char_count: 1200,
        rerank_score: 0.85,
        summary: 'Analyse détaillée des performances FastAPI vs alternatives Python avec métriques précises et cas d\'usage.'
      }
    },
    {
      id: '3',
      text: 'Les patterns architecturaux émergents pour les applications frontend modernes, incluant micro-frontends et composants distribués.',
      source: 'web.dev',
      url: 'https://web.dev/modern-frontend-patterns',
      type: 'document',
      chunk_id: 'frontend-patterns-chunk-3',
      title: 'Modern Frontend Architecture Patterns 2024',
      score: 0.78,
      metadata: {
        word_count: 180,
        char_count: 950,
        rerank_score: 0.75,
        summary: 'Exploration des patterns architecturaux modernes pour scalabilité et maintenabilité des applications frontend.'
      }
    }
  ];

  const responseContent = isThinkMode ? 
    `💡 **ANALYSE APPROFONDIE COMPLÈTE**

## 🎯 Synthèse de ma réflexion

Après avoir traité votre question "${query}" à travers plusieurs filtres d'analyse, voici ma conclusion structurée :

### 🔍 **Phase 1 : Identification des concepts clés**
J'ai identifié les termes techniques principaux et leur contexte dans l'écosystème actuel.

### 📊 **Phase 2 : Croisement des données**
${query.includes('React') ? `**React & Écosystème Frontend :**
- Server Components : révolution architectural majeure
- Performance : 40% d'amélioration sur le Time to Interactive
- Adoption entreprise : 78% des nouvelles applications React 18+
- Compatibilité : migration progressive recommandée` : 
  query.includes('FastAPI') ? `**FastAPI & Backend Python :**
- Performance : 3x plus rapide que Django sur endpoints REST
- Écosystème : intégration native avec Pydantic, SQLAlchemy 2.0
- Adoption : 65% de croissance en entreprise (2024)
- Documentation auto-générée : OpenAPI/Swagger natif` :
  `**Analyse technique approfondie :**
- Maturité technologique : évaluée sur 12 critères
- Performance comparative : benchmarks multi-environnements
- Écosystème : compatibilité et intégrations disponibles
- Roadmap : évolutions prévues sur 18 mois`}

### 🧠 **Phase 3 : Recommandations stratégiques**

**📈 Court terme (0-3 mois) :**
- Tests pilotes en environnement contrôlé
- Formation équipe technique sur les concepts clés
- Évaluation ROI et impact performance

**🚀 Moyen terme (3-12 mois) :**
- Migration progressive des composants critiques
- Mise en place monitoring et métriques
- Optimisation architecture existante

**🎯 Long terme (12+ mois) :**
- Adoption complète avec best practices
- Formation avancée équipe élargie
- Capitalisation sur l'écosystème mature

### ⚠️ **Facteurs de risque identifiés**
- Courbe d'apprentissage : 2-4 semaines selon profil
- Dépendances : vérifier compatibilité stack existant  
- Migration : planifier la coexistence temporaire

### 📚 **Sources et validation**
*Analyse basée sur ${Math.floor(Math.random() * 40) + 25} sources techniques récentes, benchmarks indépendants, et retours d'expérience communauté.*

---
💡 **Cette réflexion approfondie a pris en compte les aspects techniques, stratégiques et organisationnels pour vous donner une vision complète.**` :
    
    `Voici ce que j'ai trouvé concernant votre question sur "${query}" :

${query.includes('React') ? `React 19 apporte des innovations majeures, notamment les Server Components qui permettent un rendu hybride client/serveur plus efficace.` :
  query.includes('FastAPI') ? `FastAPI se distingue par ses performances exceptionnelles et sa facilité d'utilisation pour créer des APIs modernes.` :
  `Les informations les plus récentes sur ce sujet montrent des développements intéressants.`}

**Points clés :**
• Performance optimisée pour les applications modernes
• Communauté active et documentation complète  
• Compatibilité avec les standards actuels
• Roadmap claire pour les évolutions futures

*Sources consultées : documentation officielle, benchmarks récents, retours communauté.*`;

  return {
    content: responseContent,
    citations: mockCitations,
    metadata: {
      sources: ['React.dev', 'FastAPI Docs', 'GitHub Trending'],
      processingTime: Math.floor(Math.random() * 1000) + 500,
      tokensUsed: Math.floor(Math.random() * 300) + 150
    }
  };
} 