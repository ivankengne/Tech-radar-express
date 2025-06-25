# PRD - Tech Radar Express
## Document de Spécifications Produit

**Version :** 1.0  
**Date :** Juin 2025  
**Équipe :** Silamir Innovation  
**Auteur :** Assistant IA  

---

## 1. Introduction / Vue d'ensemble

Tech Radar Express est un portail de veille technologique temps réel destiné aux collaborateurs de Silamir. L'application résout le problème critique de **fragmentation de la veille technologique** en centralisant et contextualisant l'information selon les axes stratégiques de l'entreprise.

**Problème résolu :** Les consultants perdent actuellement 2-3h/jour à chercher des insights pertinents sur 15+ sources dispersées, avec un risque de rater des opportunités technologiques critiques.

**Solution :** Une plateforme unifiée exploitant le backend MCP crawl4ai + Local AI Package pour délivrer des insights personnalisés, avec recherche conversationnelle et changement de fournisseur LLM à chaud.

---

## 2. Objectifs

### Objectifs Principaux
1. **Réduire le temps de recherche de 70%** : passer de 180min à 50min/jour par consultant
2. **Améliorer la qualité des propositions** : +25% de taux de conversion commercial
3. **Accélérer la détection de tendances** : 48h d'avance vs concurrence
4. **Centraliser la veille technologique** : source unique de vérité pour tous les collaborateurs

### Objectifs Techniques
- Temps de réponse RAG < 3 secondes
- Uptime système > 99.5%  
- Précision RAG > 85%
- Taux succès crawling > 95%

---

## 3. User Stories

### 👥 Consultant Senior
- **En tant que** consultant senior, **je veux** obtenir en 30 secondes les dernières innovations sur mon domaine d'expertise **afin de** préparer mes propositions clients avec les technologies les plus récentes
- **En tant que** consultant, **je veux** poser des questions en langage naturel sur les tendances techniques **afin d'** obtenir des réponses sourcées et fiables instantanément
- **En tant que** consultant, **je veux** être alerté des nouveautés critiques dans mes domaines **afin de** ne jamais rater une opportunité technologique

### 👥 Sales/Business Developer  
- **En tant que** sales, **je veux** accéder au "Mode Focus" quotidien **afin d'** obtenir en 2 minutes les arguments technologiques pour mes pitches du jour
- **En tant que** business developer, **je veux** rechercher rapidement des cas d'usage concrets d'une technologie **afin de** répondre aux questions techniques des prospects

### 👥 Direction Innovation
- **En tant que** directeur innovation, **je veux** visualiser l'évolution des tendances par axe stratégique **afin de** ajuster la stratégie technologique de Silamir
- **En tant que** direction, **je veux** recevoir des rapports exécutifs automatisés **afin de** suivre l'évolution du marché sans effort manuel

### 👥 Administrateur
- **En tant qu'** admin, **je veux** ajouter/supprimer des sources de veille en quelques clics **afin de** maintenir la pertinence du système
- **En tant qu'** admin, **je veux** changer de fournisseur LLM via l'interface **afin d'** optimiser les performances selon les besoins

---

## 4. Exigences Fonctionnelles

### 4.1 Dashboard Principal (Priorité CRITIQUE)
1. Le système DOIT afficher un tableau de bord avec filtres par axes Silamir, période et sources
2. Le système DOIT présenter des "Hero KPI" sous forme de cartes d'impact (ex: 5 nouveaux patchs sécurité)
3. Le système DOIT afficher une timeline verticale avec pastilles couleur par axe technologique
4. Le système DOIT générer un RadarChart montrant le volume par thématique
5. Le système DOIT proposer un bouton "Mode Focus" donnant un résumé du jour en 2 minutes

### 4.2 Recherche/Chat Conversationnel (Priorité CRITIQUE)
6. Le système DOIT permettre la saisie de questions en langage naturel
7. Le système DOIT maintenir un historique déroulant des recherches
8. Le système DOIT proposer un bouton "/think" pour raisonnement approfondi
9. Le système DOIT afficher les citations cliquables menant aux sources originales
10. Le système DOIT répondre en moins de 3 secondes pour les requêtes RAG

### 4.3 Mode Focus Quotidien (Priorité CRITIQUE)
11. Le système DOIT générer automatiquement un résumé quotidien structuré
12. Le résumé DOIT inclure 3 tendances émergentes prioritaires avec score d'impact
13. Le résumé DOIT afficher les alertes critiques (concurrents, réglementations)
14. Le résumé DOIT proposer 2-3 insights exploitables immédiatement

### 4.4 Gestion des Sources (Priorité CRITIQUE)
15. Le système DOIT permettre l'ajout/suppression de sources via interface graphique
16. Le système DOIT supporter les formats RSS, HTML, PDF et API
17. Le système DOIT attribuer automatiquement les axes Silamir aux sources
18. Le système DOIT tester le crawling instantanément avec aperçu des chunks
19. Le système DOIT logger le statut de chaque source (OK, erreur 404, etc.)

### 4.5 Configuration LLM Modulaire (Priorité CRITIQUE)
20. Le système DOIT permettre le changement de fournisseur LLM sans redémarrage
21. Le système DOIT supporter OpenAI, Anthropic et Google avec validation des clés API
22. Le système DOIT proposer un dropdown des modèles par fournisseur
23. Le système DOIT valider la connectivité avant sauvegarde (test ping)
24. Le système DOIT implémenter un fallback automatique sur Ollama local

### 4.6 Alertes Personnalisées (Priorité IMPORTANTE)
25. Le système DOIT permettre la configuration d'alertes par mots-clés, axes et sources
26. Le système DOIT proposer différentes fréquences (temps réel, quotidien, hebdomadaire)
27. Le système DOIT implémenter un seuil de pertinence configurable (score 0-100)
28. Le système DOIT envoyer les notifications via WebSocket temps réel

### 4.7 Détail des Insights
29. Le système DOIT afficher les tags thématiques (#GenAI, #Cloud)
30. Le système DOIT générer un résumé IA de 150 mots maximum
31. Le système DOIT calculer un score de crédibilité de la source
32. Le système DOIT proposer une visualisation graphique des relations (Neo4j)

### 4.8 Authentification et Sécurité
33. Le système DOIT s'intégrer avec l'authentification LDAP/SSO de Silamir
34. Le système DOIT implémenter des rôles : Viewer, Analyst, Admin
35. Le système DOIT chiffrer toutes les données sensibles bout-en-bout
36. Le système DOIT maintenir des logs d'audit complets

### 4.9 Performance et Monitoring
37. Le système DOIT crawler les sources critiques toutes les 30 minutes
38. Le système DOIT maintenir un cache Redis pour les requêtes fréquentes
39. Le système DOIT monitorer la latence et disponibilité des API LLM
40. Le système DOIT alerter en cas d'échec de crawling ou dépassement de quota

---

## 5. Non-Objectifs (Hors Périmètre)

### Phase 1.0 - Fonctionnalités EXCLUES :
- **Collaboration temps réel** entre utilisateurs (commentaires, partage)
- **API externe** pour intégration avec d'autres systèmes Silamir
- **Analytics avancés** d'usage utilisateur (heatmaps, parcours)
- **Multi-langue** (seul le français supporté initialement)
- **Mobile app native** (responsive web uniquement)
- **Intégration calendrier** pour planification de veille
- **Génération automatique** de présentations PowerPoint
- **Système de notation** des insights par les utilisateurs
- **Chatbot** intégré aux équipes (Slack/Teams)
- **Workflow approbation** pour publication d'insights

### Contraintes Techniques EXCLUES :
- **Hébergement cloud public** (AWS, Azure, GCP)
- **Intégration** avec systèmes CRM externes
- **Synchronisation** avec bases de données clients
- **Export massif** de données (> 1000 insights)

---

## 6. Considérations de Design

### 6.1 Principes UX/UI
- **Design responsive** : mobile, tablette, desktop avec breakpoints CSS
- **Navigation "three-clicks-max"** : aucune information clé au-delà de 3 clics
- **Mode sombre/clair** avec persistance dans localStorage
- **Accessibilité WCAG 2.1 AA** : contraste, lecteurs d'écran, raccourcis clavier

### 6.2 Composants UI Spécifiques
- **ProviderSwitcher** : widget en header avec logo LLM actuel + modal configuration
- **ImpactCard** : cartes KPI avec animations "flip" lors des mises à jour
- **GraphView** : visualisation d3-force des relations entre insights/sources/axes  
- **QueryCitation** : tags cliquables dans le chat ouvrant un volet latéral avec source complète

### 6.3 Charte Graphique
- **Couleurs** : palette Silamir avec codes couleur par axe technologique
- **Typographie** : police corporate + police monospace pour code
- **Iconographie** : icônes Material Design + icônes custom pour technologies

---

## 7. Considérations Techniques

### 7.1 Architecture Backend
- **API Gateway** : FastAPI avec modules auth, LLM provider, WebSocket
- **MCP Crawl4AI** : exploitation des 8 outils disponibles (crawl, RAG, knowledge graph)
- **Local AI Stack** : Ollama + N8N + SearXNG + Neo4j intégration
- **Base de données** : Supabase (vector search) + Neo4j (knowledge graph) + Redis (cache)

### 7.2 Sécurité et Conformité
- **Hébergement on-premise** obligatoire (pas de cloud public)
- **Chiffrement** : TLS 1.3 + chiffrement application données sensibles  
- **Authentification** : JWT + intégration LDAP/SSO existant
- **Conformité** : RGPD + ISO 27001 compatible

### 7.3 Performance
- **Scalabilité** : architecture horizontale, Docker Compose
- **Cache** : Redis pour requêtes fréquentes (TTL 1h)
- **Parallélisation** : crawling 50+ pages/minute
- **Monitoring** : Langfuse pour traces LLM + métriques système

### 7.4 Intégration avec Écosystème Existant
- **SSO** : Keycloak ou Active Directory
- **Monitoring** : intégration avec outils Silamir existants
- **Backup** : stratégie sauvegarde compatible infrastructure

---

## 8. Métriques de Succès

### 8.1 Métriques Métier
| Métrique | Baseline Actuelle | Objectif 6 mois | Méthode de Mesure |
|----------|-------------------|------------------|-------------------|
| Temps recherche/jour | 180 min | 50 min (-70%) | Enquête utilisateur |
| Taux conversion commerciale | Baseline | +25% | CRM Silamir |
| Délai détection tendances | Baseline | -48h vs concurrence | Analyse comparative |
| Satisfaction utilisateur | N/A | >4/5 | Enquête mensuelle |

### 8.2 Métriques Techniques
| Métrique | Seuil Critique | Objectif | Monitoring |
|----------|----------------|----------|------------|
| Temps réponse RAG | < 5 sec | < 3 sec | Logs application |
| Uptime système | > 99% | > 99.5% | Monitoring infra |
| Taux succès crawling | > 90% | > 95% | Dashboard admin |
| Précision RAG | > 80% | > 85% | Évaluation humaine |

### 8.3 Métriques d'Adoption
- **Utilisateurs actifs quotidiens** : >80% des licences
- **Requêtes par utilisateur/jour** : >10 requêtes
- **Sources consultées** : répartition équilibrée sur tous les axes
- **Temps session moyen** : 15-30 minutes (zone optimale)

---

## 9. Questions Ouvertes

### 9.1 Questions Techniques
1. **Stratégie de migration** : comment migrer les données de veille existantes ?
2. **Plan de montée en charge** : comment gérer l'évolution de 25 à 50+ utilisateurs ?
3. **Stratégie backup/restore** : quelle fréquence pour les sauvegardes Neo4j ?
4. **Gestion des pannes** : procédure de fallback si le système local AI est indisponible ?

### 9.2 Questions Métier  
5. **Processus validation** : qui valide la pertinence des nouveaux axes technologiques ?
6. **Gouvernance des sources** : qui décide d'ajouter/supprimer des sources de veille ?
7. **Formation utilisateurs** : quel plan de formation pour l'adoption ?
8. **Evolution des besoins** : comment adapter les axes selon l'évolution stratégique Silamir ?

### 9.3 Questions Réglementaires
9. **Conformité données** : comment gérer la RGPD pour les données crawlées ?
10. **Propriété intellectuelle** : quelle politique pour les contenus crawlés ?
11. **Audit de sécurité** : fréquence et méthode d'audit de sécurité ?

---

## Annexes

### Annexe A : Glossaire
- **Axe Silamir** : domaine d'expertise technologique de l'entreprise
- **Insight** : information technologique analysée et contextualisée
- **RAG** : Retrieval Augmented Generation (recherche augmentée par IA)
- **MCP** : Model Context Protocol (framework d'intégration AI)

### Annexe B : Références
- Documentation MCP crawl4ai
- Spécifications Local AI Package  
- Architecture système Silamir existante

---

**Fin du PRD Tech Radar Express v1.0**