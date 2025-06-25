# Tasks - Tech Radar Express
## Liste des tâches de développement basée sur le PRD

**Version :** 1.0  
**Date :** Juin 2025  
**Basé sur :** PRD Tech Radar Express v1.0  
**Target :** Équipe développement junior  

---

## Relevant Files

### Backend (FastAPI) ✅ Configuré + MCP Intégré
- `backend/main.py` - Point d'entrée principal FastAPI avec routes et middleware ✅ Créé
- `backend/requirements.txt` - Dépendances Python backend ✅ Créé  
- `backend/Dockerfile` - Configuration Docker pour containerisation ✅ Créé
- `backend/config.env.template` - Template configuration environnement ✅ Créé
- `backend/__init__.py` - Package Python principal ✅ Créé
- `backend/api/__init__.py` - Module API routes ✅ Créé
- `backend/api/routes/__init__.py` - Package routes ✅ Créé
- `backend/core/__init__.py` - Module core ✅ Créé
- `backend/database/__init__.py` - Module database ✅ Créé
- `backend/models/__init__.py` - Module models ✅ Créé
- `backend/utils/__init__.py` - Module utils ✅ Créé
- `backend/core/mcp_client.py` - Client MCP crawl4ai-rag avec 8 outils intégrés ✅ Créé
- `backend/core/config_manager.py` - Gestionnaire configuration centralisé Pydantic ✅ Créé
- `backend/core/scheduler.py` - Gestionnaire APScheduler tâches récurrentes et sync MCP ✅ Créé
- `backend/core/langfuse_manager.py` - Gestionnaire monitoring LLM et métriques Langfuse ✅ Créé
- `backend/core/llm_tracer.py` - Décorateurs traçage automatique appels LLM ✅ Créé
- `backend/api/routes/mcp.py` - Routes API pour exposition des 8 outils MCP ✅ Créé
- `backend/api/routes/scheduler.py` - Routes API administration et monitoring scheduler ✅ Créé
- `backend/api/routes/monitoring.py` - Routes API dashboard et métriques Langfuse ✅ Créé
- `backend/api/routes/llm.py` - Routes pour configuration LLM et switch provider ✅ Créé
- `backend/api/routes/sources.py` - CRUD sources de veille et gestion crawling ✅ Créé
- `backend/api/routes/search.py` - Endpoints recherche conversationnelle RAG ✅ Créé
- `backend/api/routes/dashboard.py` - APIs données dashboard et KPI ✅ Créé
- `backend/api/routes/websocket.py` - WebSocket pour notifications temps réel ✅ Créé
- `backend/core/llm_provider_manager.py` - Manager switch OpenAI/Claude/Gemini ✅ Créé
- `backend/core/source_manager.py` - Orchestrateur sources et crawls MCP avec planification ✅ Créé
- `backend/core/crawl_monitor.py` - Système monitoring avancé crawls MCP avec alertes ✅ Créé
- `backend/api/routes/crawl_monitoring.py` - Routes API monitoring temps réel crawls ✅ Créé
- `backend/api/routes/source_supervision.py` - Routes API dashboard supervision sources avec MCP ✅ Créé
- `backend/core/mcp_client.py` - Client pour intégration MCP crawl4ai tools ✅ Créé
- `backend/core/websocket_manager.py` - Gestionnaire connexions WebSocket
- `backend/core/rate_limiter.py` - Protection contre spam et quotas
- `backend/core/config_manager.py` - Configuration dynamique système
- `backend/core/scheduler.py` - APScheduler pour tâches récurrentes
- `backend/database/app_metadata_setup.sql` - Tables métadonnées application (analytics, config) ✅ Créé
- `backend/database/neo4j_client.py` - Client Neo4j knowledge graph
- `backend/database/redis_client.py` - Client Redis/Valkey cache et pub/sub ✅ Créé
- `backend/models/insight.py` - Modèles Pydantic pour insights
- `backend/models/source.py` - Modèles Pydantic pour sources
- `backend/models/llm_config.py` - Modèles configuration LLM
- `backend/utils/embeddings.py` - Fonctions génération embeddings
- `backend/core/daily_summary_generator.py` - Générateur résumés quotidiens intelligents avec données MCP ✅ Créé
- `backend/api/routes/daily_summary.py` - Routes API génération et récupération résumés quotidiens ✅ Créé
- `frontend/src/components/dashboard/DailySummary.tsx` - Composant React affichage résumés quotidiens ✅ Créé
- `backend/core/focus_mode_generator.py` - Générateur synthèses focus rapides (4 modes, <2min) ✅ Créé
- `backend/api/routes/focus_mode.py` - Routes API mode focus avec timer et benchmark ✅ Créé
- `frontend/src/components/dashboard/FocusMode.tsx` - Composant React mode focus avec sélection et timer ✅ Créé
- `backend/core/alerts_manager.py` - Gestionnaire alertes personnalisées avec critères configurables et notifications ✅ Créé
- `backend/api/routes/alerts.py` - Routes API CRUD alertes avec templates et tests ✅ Créé
- `frontend/src/components/admin/AlertsManagement.tsx` - Interface gestion alertes avec formulaire et filtres ✅ Créé
- `frontend/src/app/admin/alerts/page.tsx` - Page administration alertes personnalisées ✅ Créé
- `backend/core/critical_alerts_detector.py` - Détecteur alertes critiques automatique via analyse LLM ✅ Créé
- `backend/api/routes/critical_alerts.py` - Routes API détection automatique alertes critiques ✅ Créé
- `frontend/src/components/admin/CriticalAlertsMonitor.tsx` - Interface monitoring alertes critiques avec détails ✅ Créé
- `frontend/src/app/admin/critical-alerts/page.tsx` - Page administration alertes critiques automatiques ✅ Créé
- `backend/core/notifications_manager.py` - Gestionnaire notifications WebSocket avec seuils configurables ✅ Créé
- `backend/core/websocket_manager.py` - Gestionnaire connexions WebSocket temps réel ✅ Créé
- `backend/api/routes/notifications.py` - Routes API préférences notifications et tests ✅ Créé
- `frontend/src/components/admin/NotificationCenter.tsx` - Centre notifications complet avec préférences ✅ Créé
- `frontend/src/app/admin/notifications/page.tsx` - Page administration notifications WebSocket ✅ Créé
- `backend/core/activity_feed_manager.py` - Orchestrateur sources et crawls MCP avec planification ✅ Modifié (diffusion WebSocket)
- `frontend/src/components/dashboard/ActivityFeed.tsx` - Composant React affichage flux temps réel ✅ Modifié (intégration WebSocket + indicateur favoris)
- `backend/core/activity_feed_manager.py` - Gestion bookmarks utilisateur (persistant Redis) ✅ Modifié
- `backend/api/routes/activity_feed.py` - Endpoint `/bookmarks` pour récupérer favoris ✅ Créé

### Frontend (Next.js) ✅ Créé Base
- `frontend/package.json` - Dépendances Node.js avec framer-motion et heroicons ✅ Mis à jour
- `frontend/next.config.ts` - Configuration Next.js ✅ Créé
- `frontend/postcss.config.mjs` - Configuration PostCSS Tailwind v4 ✅ Créé
- `frontend/tsconfig.json` - Configuration TypeScript avec alias @/* ✅ Créé
- `frontend/src/app/globals.css` - Styles globaux Tailwind CSS v4 ✅ Créé
- `frontend/src/app/layout.tsx` - Layout principal avec thème dark/light ✅ Créé
- `frontend/src/components/ui/ThemeProvider.tsx` - Provider gestion thèmes avec localStorage ✅ Créé
- `frontend/src/components/ui/ThemeToggle.tsx` - Bouton switch thèmes (light/dark/system) ✅ Créé
- `frontend/src/components/ui/Header.tsx` - Header navigation avec logo et menu ✅ Créé
- `frontend/src/components/ui/HeroKPI.tsx` - Cartes KPI avec animations flip et count-up ✅ Créé
- `frontend/src/components/dashboard/Timeline.tsx` - Timeline verticale avec pastilles colorées par axe tech ✅ Créé
- `frontend/src/components/dashboard/RadarChart.tsx` - Graphique radar volumes par thématique avec Recharts ✅ Créé
- `frontend/src/app/page.tsx` - Page d'accueil Dashboard Global
- `frontend/src/app/search/page.tsx` - Page Recherche/Chat ✅ Créé
- `frontend/src/app/insight/[id]/page.tsx` - Page Détail Insight
- `frontend/src/app/live/page.tsx` - Page Flux en direct
- `frontend/src/app/admin/sources/page.tsx` - Administration sources ✅ Créé
- `frontend/src/app/admin/llm/page.tsx` - Administration LLM config ✅ Créé
- `frontend/src/components/dashboard/HeroKPI.tsx` - Cartes KPI principales
- `frontend/src/components/dashboard/Timeline.tsx` - Timeline verticale insights
- `frontend/src/components/dashboard/RadarChart.tsx` - Chart volume thématiques
- `frontend/src/components/chat/SearchInterface.tsx` - Interface chat conversationnel ✅ Créé
- `frontend/src/components/chat/QueryCitation.tsx` - Citations cliquables avec permaliens vers chunks MCP ✅ Créé
- `frontend/src/components/ui/ProviderSwitcher.tsx` - Switch LLM provider ✅ Créé
- `frontend/src/components/ui/ImpactCard.tsx` - Cartes avec animations flip
- `frontend/src/components/ui/GraphView.tsx` - Visualisation d3-force Neo4j
- `frontend/src/components/admin/SmartSourceForm.tsx` - Formulaire intelligent ajout sources avec mapping automatique ✅ Créé
- `frontend/src/components/admin/CrawlMonitoring.tsx` - Interface monitoring temps réel crawls MCP ✅ Créé
- `frontend/src/app/admin/monitoring/page.tsx` - Page administration monitoring crawls ✅ Créé
- `frontend/src/components/admin/SourceSupervision.tsx` - Dashboard supervision sources avec intégration MCP ✅ Créé
- `frontend/src/app/admin/supervision/page.tsx` - Page administration supervision sources ✅ Créé
- `frontend/src/components/admin/SourceManager.tsx` - Gestion sources CRUD
- `frontend/src/components/admin/LLMConfig.tsx` - Configuration LLM
- `frontend/src/hooks/useWebSocket.ts` - Hook WebSocket temps réel avec streaming et reconnexion ✅ Créé
- `frontend/src/hooks/useLLMProvider.ts` - Hook gestion provider LLM ✅ Créé
- `frontend/src/lib/api.ts` - Client API backend avec types TypeScript
- `frontend/src/lib/websocket.ts` - Client WebSocket avec reconnexion
- `frontend/src/store/llmStore.ts` - State management configuration LLM (Zustand)
- `frontend/src/store/dashboardStore.ts` - State management dashboard data
- `frontend/src/types/index.ts` - Types TypeScript partagés
- `frontend/src/utils/storage.ts` - Utilitaires localStorage sécurisé

### Configuration & Infrastructure
- `docker-compose.yml` - Stack complète (FastAPI + Next.js + Services)
- `docker-compose.dev.yml` - Configuration développement
- `.env.example` - Variables d'environnement exemple
- `README.md` - Documentation projet et setup

### Tests
- `backend/tests/test_llm_provider.py` - Tests unitaires LLM provider
- `backend/tests/test_mcp_client.py` - Tests intégration MCP
- `backend/tests/test_websocket.py` - Tests WebSocket
- `frontend/src/components/__tests__/ProviderSwitcher.test.tsx` - Tests composants UI
- `frontend/src/hooks/__tests__/useWebSocket.test.ts` - Tests hooks React

### Notes

- **Stack Tech** : FastAPI (backend) + Next.js 14 (frontend) + TypeScript + Tailwind CSS
- **Moteur RAG** : **MCP crawl4ai-rag** (crawling, embeddings, vector search complet)
- **Base de données** : Supabase (métadonnées app) + Neo4j (knowledge graph) + Redis/Valkey (cache)
- **AI/ML** : Ollama local (qwen2.5 + nomic-embed) + OpenAI/Claude/Gemini switch
- **Temps réel** : WebSocket pour notifications et streaming
- **Tests** : pytest (backend) + Jest/RTL (frontend)
- **Déploiement** : Docker Compose avec services orchestrés locaux
- **Monitoring** : Langfuse local pour traces LLM + métriques système

## Tasks

- [x] 1.0 Configuration Backend & Infrastructure (Architecture MCP + Local AI)
  - [x] 1.1 Configurer environnement FastAPI avec structure modulaire et Docker
  - [x] 1.2 Intégrer MCP crawl4ai-rag comme moteur principal (crawl, embeddings, vector search)
  - [x] 1.3 Configurer tables Supabase métadonnées application (analytics, config, sessions)
  - [x] 1.4 Configurer Redis/Valkey pour cache, sessions et pub/sub WebSocket
  - [x] 1.5 Implémenter APScheduler pour tâches récurrentes et synchronisation MCP
  - [x] 1.6 Configurer monitoring Langfuse local pour traces LLM et métriques

- [x] 2.0 Dashboard Principal & Visualisations (KPI + Timeline + RadarChart)
  - [x] 2.1 Créer application Next.js 14 avec TypeScript et Tailwind CSS
  - [x] 2.2 Implémenter layout principal avec mode dark/light et localStorage persistence
  - [x] 2.3 Développer composant HeroKPI avec cartes d'impact et animations flip
  - [x] 2.4 Créer Timeline verticale avec pastilles couleur par axe technologique
  - [x] 2.5 Implémenter RadarChart avec visualisation volume par thématique
  - [x] 2.6 Développer système de filtres (axes, période, sources) avec state management ✅
  - [x] 2.7 Créer API endpoint `/api/v1/dashboard/data` pour données temps réel
  - [x] 2.8 Implémenter WebSocket pour updates temps réel avec badge "NEW" animé

- [x] 3.0 Interface de Recherche Conversationnelle (Chat + Citations MCP)
  - [x] 3.1 Développer interface chat type Copilot avec historique déroulant
  - [x] 3.2 Implémenter bouton "/think" pour raisonnement approfondi avec streaming
  - [x] 3.3 Créer système citations cliquables avec volet latéral source complète
  - [x] 3.4 Développer API endpoint `/api/v1/search/query` proxy vers MCP crawl4ai-rag
  - [x] 3.5 Intégrer fonctions MCP perform_rag_query et search_code_examples
  - [x] 3.6 Créer hook useWebSocket pour streaming réponses en temps réel
  - [x] 3.7 Développer composant QueryCitation avec permaliens vers chunks MCP

- [x] 4.0 Administration Sources & Configuration (Interface + Orchestration MCP)
  - [x] 4.1 Développer LLMProviderManager avec switch OpenAI/Claude/Gemini/Ollama ✅ Terminé
  - [x] 4.2 Créer interface configuration LLM avec validation clés API temps réel ✅ Terminé
  - [x] 4.3 Implémenter dropdown modèles par provider avec appel `/api/v1/llm/models` ✅ Terminé
  - [x] 4.4 Développer SourceManager pour orchestrer crawls via MCP smart_crawl_url ✅ Terminé
  - [x] 4.5 Créer interface ajout sources avec mapping automatique axes technologiques ✅ Terminé
  - [x] 4.6 Implémenter monitoring crawls MCP avec statut et gestion erreurs ✅ Terminé
  - [x] 4.7 Développer dashboard supervision sources avec get_available_sources MCP ✅ Terminé

- [x] 5.0 Intelligence & Alertes (Résumés automatisés + Knowledge Graph)
  - [x] 5.1 Développer générateur résumé quotidien via LLM avec données MCP
  - [x] 5.2 Créer bouton "Mode Focus" avec synthèse structurée en 2 minutes
  - [x] 5.3 Implémenter système alertes personnalisées (mots-clés, axes, sources)
  - [x] 5.4 Développer détection alertes critiques via analyse LLM contenu MCP
  - [x] 5.5 Créer système notifications WebSocket avec seuil pertinence configurable ✅
  - [x] 5.6 Implémenter flux temps réel avec liste défilante type "activity feed"
  - [x] 5.7 Développer système bookmarks avec sauvegarde de favoris

---

**Phase 2 Terminée :** Sous-tâches détaillées générées avec architecture technique précise (FastAPI + Next.js + MCP crawl4ai + Local AI Stack).

**Total : 32 sous-tâches** couvrant l'implémentation complète selon les spécifications détaillées fournies. 