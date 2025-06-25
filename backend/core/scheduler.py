"""
Gestionnaire APScheduler pour tâches récurrentes et synchronisation MCP.

Ce module gère :
- Synchronisation périodique des sources MCP
- Nettoyage des caches Redis
- Génération de rapports quotidiens
- Mise à jour des métriques Langfuse
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.redis import RedisJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from pydantic import BaseModel, Field

from .config_manager import ConfigManager
# CORRECTION: MCPClient n'existe pas encore, on l'importera quand il sera créé
# from .mcp_client import MCPClient
from database.redis_client import RedisClient

logger = logging.getLogger(__name__)

class ScheduledTask(BaseModel):
    """Modèle pour une tâche programmée."""
    id: str
    name: str
    description: str
    cron: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str = "pending"  # pending, running, completed, failed
    error_count: int = 0
    max_retries: int = 3

class TaskScheduler:
    """Gestionnaire principal des tâches programmées."""
    
    def __init__(self, config_manager: ConfigManager, redis_client: RedisClient):
        self.config = config_manager
        self.redis = redis_client
        self.scheduler: Optional[AsyncIOScheduler] = None
        # CORRECTION: MCPClient sera ajouté plus tard
        # self.mcp_client: Optional[MCPClient] = None
        self.tasks: Dict[str, ScheduledTask] = {}
        self.is_running = False
        
        # Configuration du scheduler
        self.job_defaults = {
            'coalesce': False,
            'max_instances': 1,
            'misfire_grace_time': 30
        }
        
    async def initialize(self):
        """Initialise le scheduler avec la configuration Redis."""
        try:
            # Configuration Redis pour persistance des jobs
            redis_config = self.config.redis
            jobstore = RedisJobStore(
                host=redis_config.host,
                port=redis_config.port,
                password=redis_config.password,
                db=1,  # Base différente pour les jobs
                decode_responses=True
            )
            
            # Configuration du scheduler
            self.scheduler = AsyncIOScheduler(
                jobstores={'default': jobstore},
                executors={'default': AsyncIOExecutor()},
                job_defaults=self.job_defaults,
                timezone='UTC'
            )
            
            # Écouteurs d'événements
            self.scheduler.add_listener(
                self._job_executed_listener, 
                EVENT_JOB_EXECUTED
            )
            self.scheduler.add_listener(
                self._job_error_listener, 
                EVENT_JOB_ERROR
            )
            
            # CORRECTION: MCPClient sera initialisé plus tard
            # self.mcp_client = MCPClient(self.config)
            # await self.mcp_client.initialize()
            
            logger.info("TaskScheduler initialisé avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du scheduler: {e}")
            raise
    
    async def start(self):
        """Démarre le scheduler et configure les tâches par défaut."""
        if not self.scheduler:
            await self.initialize()
            
        try:
            self.scheduler.start()
            self.is_running = True
            
            # Configuration des tâches par défaut
            await self._setup_default_tasks()
            
            logger.info("TaskScheduler démarré")
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du scheduler: {e}")
            raise
    
    async def shutdown(self):
        """Arrête proprement le scheduler."""
        if self.scheduler and self.is_running:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            
            # CORRECTION: MCPClient sera fermé plus tard
            # if self.mcp_client:
            #     await self.mcp_client.close()
                
            logger.info("TaskScheduler arrêté")
    
    async def _setup_default_tasks(self):
        """Configure les tâches récurrentes par défaut."""
        default_tasks = [
            # Synchronisation sources MCP (toutes les 4 heures)
            {
                'id': 'sync_mcp_sources',
                'name': 'Synchronisation Sources MCP',
                'description': 'Met à jour la liste des sources disponibles via MCP',
                'cron': '0 */4 * * *',  # Toutes les 4 heures
                'func': self._sync_mcp_sources
            },
            
            # Nettoyage cache Redis (quotidien à 2h00)
            {
                'id': 'cleanup_cache',
                'name': 'Nettoyage Cache Redis',
                'description': 'Supprime les entrées expirées du cache',
                'cron': '0 2 * * *',  # Quotidien à 2h00
                'func': self._cleanup_redis_cache
            },
            
            # Génération rapport quotidien (à 8h00)
            {
                'id': 'daily_report',
                'name': 'Rapport Quotidien',
                'description': 'Génère le résumé quotidien via LLM',
                'cron': '0 8 * * *',  # Quotidien à 8h00
                'func': self._generate_daily_report
            },
            
            # Mise à jour métriques Langfuse (toutes les heures)
            {
                'id': 'update_langfuse_metrics',
                'name': 'Métriques Langfuse',
                'description': 'Met à jour les métriques de traçage LLM',
                'cron': '0 * * * *',  # Toutes les heures
                'func': self._update_langfuse_metrics
            },
            
            # Sauvegarde métadonnées (quotidienne à 3h00)
            {
                'id': 'backup_metadata',
                'name': 'Sauvegarde Métadonnées',
                'description': 'Sauvegarde les métadonnées critiques',
                'cron': '0 3 * * *',  # Quotidien à 3h00
                'func': self._backup_metadata
            },
            
            # Vérification alertes personnalisées (toutes les 30 minutes)
            {
                'id': 'check_alerts',
                'name': 'Vérification Alertes',
                'description': 'Vérifie les alertes personnalisées et envoie les notifications',
                'cron': '*/30 * * * *',  # Toutes les 30 minutes
                'func': self._check_alerts
            },
            
            # Détection alertes critiques LLM (toutes les 15 minutes)
            {
                'id': 'critical_alerts_detection',
                'name': 'Détection Alertes Critiques',
                'description': 'Analyse automatique via LLM pour détecter les alertes critiques',
                'cron': '*/15 * * * *',  # Toutes les 15 minutes
                'func': self._detect_critical_alerts
            },
            
            # Nettoyage notifications expirées (toutes les heures)
            {
                'id': 'notifications_cleanup',
                'name': 'Nettoyage Notifications',
                'description': 'Supprime les notifications expirées et nettoie le cache',
                'cron': '0 * * * *',  # Toutes les heures à la minute 0
                'func': self._cleanup_notifications
            }
        ]
        
        for task_config in default_tasks:
            await self.add_task(**task_config)
    
    async def add_task(self, id: str, name: str, description: str, 
                      cron: str, func, enabled: bool = True):
        """Ajoute une nouvelle tâche programmée."""
        try:
            task = ScheduledTask(
                id=id,
                name=name,
                description=description,
                cron=cron,
                enabled=enabled
            )
            
            if enabled:
                # Ajout au scheduler APScheduler
                self.scheduler.add_job(
                    func=self._execute_task_wrapper,
                    trigger='cron',
                    id=id,
                    name=name,
                    args=[id, func],
                    **self._parse_cron(cron),
                    replace_existing=True
                )
                
                # Calcul prochaine exécution
                job = self.scheduler.get_job(id)
                if job:
                    task.next_run = job.next_run_time
            
            # Sauvegarde en mémoire et Redis
            self.tasks[id] = task
            await self._save_task_to_redis(task)
            
            logger.info(f"Tâche '{name}' ajoutée avec succès")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la tâche {id}: {e}")
            raise
    
    async def remove_task(self, task_id: str):
        """Supprime une tâche programmée."""
        try:
            if task_id in self.tasks:
                # Suppression du scheduler
                if self.scheduler.get_job(task_id):
                    self.scheduler.remove_job(task_id)
                
                # Suppression locale et Redis
                del self.tasks[task_id]
                await self.redis.delete_key(f"scheduler:task:{task_id}")
                
                logger.info(f"Tâche {task_id} supprimée")
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de la tâche {task_id}: {e}")
    
    async def get_task_status(self, task_id: str) -> Optional[ScheduledTask]:
        """Récupère le statut d'une tâche."""
        return self.tasks.get(task_id)
    
    async def get_all_tasks(self) -> List[ScheduledTask]:
        """Récupère toutes les tâches configurées."""
        return list(self.tasks.values())
    
    async def _execute_task_wrapper(self, task_id: str, func):
        """Wrapper d'exécution avec gestion des erreurs et métriques."""
        task = self.tasks.get(task_id)
        if not task:
            logger.error(f"Tâche {task_id} introuvable")
            return
        
        start_time = datetime.utcnow()
        
        try:
            # Mise à jour du statut
            task.status = "running"
            task.last_run = start_time
            await self._save_task_to_redis(task)
            
            logger.info(f"Exécution de la tâche: {task.name}")
            
            # Exécution de la fonction
            if asyncio.iscoroutinefunction(func):
                result = await func()
            else:
                result = func()
            
            # Succès
            task.status = "completed"
            task.error_count = 0
            
            # Calcul prochaine exécution
            job = self.scheduler.get_job(task_id)
            if job:
                task.next_run = job.next_run_time
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Tâche {task.name} terminée en {execution_time:.2f}s")
            
            # Métriques Redis
            await self._record_task_metrics(task_id, "success", execution_time)
            
        except Exception as e:
            # Échec
            task.status = "failed"
            task.error_count += 1
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Erreur dans la tâche {task.name}: {e}")
            
            # Métriques d'erreur
            await self._record_task_metrics(task_id, "error", execution_time, str(e))
            
            # Retry si nécessaire
            if task.error_count < task.max_retries:
                logger.info(f"Planification d'un retry pour {task.name} (tentative {task.error_count + 1})")
                
        finally:
            await self._save_task_to_redis(task)
    
    # === Tâches spécifiques ===
    
    async def _sync_mcp_sources(self):
        """Synchronise les sources disponibles via MCP."""
        try:
            # CORRECTION: Simulation jusqu'à ce que MCPClient soit implémenté
            logger.info("Début synchronisation sources MCP (simulée)")
            
            # Simulation de sources pour les tests
            simulated_sources = {
                "success": True,
                "data": [
                    {"id": "test_source_1", "name": "Source Test 1", "type": "web"},
                    {"id": "test_source_2", "name": "Source Test 2", "type": "documentation"}
                ]
            }
            
            # Sauvegarde en cache Redis avec TTL
            cache_key = "mcp:sources:available"
            await self.redis.set(
                cache_key, 
                simulated_sources, 
                expire=int(timedelta(hours=6).total_seconds())
            )
            
            logger.info(f"Synchronisation MCP terminée (simulée): {len(simulated_sources.get('data', []))} sources")
            
        except Exception as e:
            logger.error(f"Erreur synchronisation MCP: {e}")
            raise
    
    async def _cleanup_redis_cache(self):
        """Nettoie les entrées expirées du cache Redis."""
        try:
            # CORRECTION: Redis cleanup simplifié avec les méthodes existantes
            # Nettoyage des clés tech_radar expirées
            total_deleted = 0
            
            # Simulation de nettoyage car get_keys_pattern n'existe pas
            # Dans une vraie implémentation, on utiliserait SCAN avec des patterns
            logger.info("Nettoyage cache simulé - fonctionnalité à implémenter avec SCAN Redis")
            
            # Exemple de ce qui serait fait avec les vraies méthodes :
            # keys_to_check = ["cache:expired", "session:old", "temp:cleanup"]
            # for key in keys_to_check:
            #     if await self.redis.exists(key):
            #         await self.redis.delete(key)
            #         total_deleted += 1
            
            logger.info(f"Nettoyage cache: {total_deleted} clés supprimées")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage cache: {e}")
            raise
    
    async def _generate_daily_report(self):
        """Génère le rapport quotidien via LLM."""
        try:
            # Import local pour éviter les dépendances circulaires
            from .daily_summary_generator import get_daily_summary_generator
            
            logger.info("Début génération rapport quotidien automatique")
            
            # Récupération du générateur de résumés
            generator = await get_daily_summary_generator()
            
            # Génération du résumé pour hier
            from datetime import datetime, timedelta
            yesterday = datetime.now() - timedelta(days=1)
            
            summary = await generator.generate_daily_summary(
                date=yesterday
            )
            
            # Sauvegarde du résumé en cache Redis
            cache_key = f"daily_summary:{yesterday.strftime('%Y-%m-%d')}"
            summary_data = {
                "date": summary.date.isoformat(),
                "sections_count": len(summary.sections),
                "total_sources": summary.total_sources,
                "generation_time": summary.generation_time,
                "generated_at": datetime.now().isoformat(),
                "markdown": generator.format_as_markdown(summary)
            }
            
            # Sauvegarde avec TTL de 7 jours
            await self.redis.set(
                cache_key, 
                summary_data, 
                expire=int(timedelta(days=7).total_seconds())
            )
            
            logger.info(
                "Rapport quotidien généré avec succès",
                date=yesterday.strftime('%Y-%m-%d'),
                sections=len(summary.sections),
                sources=summary.total_sources,
                time=f"{summary.generation_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Erreur génération rapport quotidien: {e}")
            raise
    
    async def _update_langfuse_metrics(self):
        """Met à jour les métriques Langfuse."""
        try:
            # Import local pour éviter les dépendances circulaires
            from .langfuse_manager import LangfuseManager
            
            # Vérification de la disponibilité du gestionnaire Langfuse
            # Cette méthode sera appelée depuis le scheduler, donc on essaie d'accéder
            # au gestionnaire via les moyens disponibles
            
            # Flush des métriques en attente si un gestionnaire existe
            cache_key = "langfuse:metrics:summary"
            
            # CORRECTION: Simulation de mise à jour des métriques Langfuse
            # Génération d'un résumé des métriques (simulé)
            
            # Simulation car get_keys_pattern n'existe pas
            total_metrics = 5  # Simulé
            
            summary = {
                'last_update': datetime.utcnow().isoformat(),
                'total_cached_metrics': total_metrics,
                'cache_keys_count': total_metrics,
                'status': 'updated'
            }
            
            await self.redis.set(cache_key, summary, expire=int(timedelta(hours=24).total_seconds()))
            
            logger.info(f"Métriques Langfuse mises à jour (simulées): {total_metrics} métriques en cache")
            
        except Exception as e:
            logger.error(f"Erreur mise à jour métriques Langfuse: {e}")
            raise
    
    async def _backup_metadata(self):
        """Effectue une sauvegarde des métadonnées critiques."""
        try:
            # Sauvegarde des configurations et statistiques
            backup_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'tasks': {k: v.dict() for k, v in self.tasks.items()},
                'config_snapshot': {
                    'redis_connected': await self.redis.ping(),
                    # CORRECTION: Simulation jusqu'à ce que MCPClient soit implémenté
                    'mcp_initialized': False  # self.mcp_client is not None
                }
            }
            
            backup_key = f"backup:metadata:{datetime.utcnow().strftime('%Y%m%d')}"
            await self.redis.set(backup_key, backup_data, expire=int(timedelta(days=30).total_seconds()))
            
            logger.info("Sauvegarde métadonnées effectuée")
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde métadonnées: {e}")
            raise

    async def _check_alerts(self):
        """Vérifie les alertes personnalisées et déclenche les notifications."""
        try:
            # Import local pour éviter les dépendances circulaires
            from .alerts_manager import get_alerts_manager
            
            logger.info("Début vérification alertes personnalisées")
            
            # Récupération du gestionnaire d'alertes
            alerts_manager = await get_alerts_manager()
            
            # Vérification de toutes les alertes actives
            triggers = await alerts_manager.check_alerts()
            
            if triggers:
                # Sauvegarde des déclenchements en cache Redis
                cache_key = f"alerts:triggers:{datetime.now().strftime('%Y-%m-%d-%H')}"
                triggers_data = {
                    "timestamp": datetime.now().isoformat(),
                    "triggers_count": len(triggers),
                    "triggers": [
                        {
                            "alert_id": trigger.alert.id,
                            "alert_name": trigger.alert.name,
                            "priority": trigger.alert.priority.value,
                            "matches_count": len(trigger.matches),
                            "notification_sent": trigger.notification_sent
                        }
                        for trigger in triggers
                    ]
                }
                
                # Sauvegarde avec TTL de 24 heures
                await self.redis.set(
                    cache_key, 
                    triggers_data, 
                    expire=int(timedelta(hours=24).total_seconds())
                )
                
                logger.info(
                    "Alertes vérifiées avec déclenchements",
                    triggers=len(triggers),
                    notifications_sent=sum(1 for t in triggers if t.notification_sent)
                )
            else:
                logger.info("Alertes vérifiées - Aucun déclenchement")
            
        except Exception as e:
            logger.error(f"Erreur vérification alertes: {e}")
            raise
    
    async def _detect_critical_alerts(self):
        """Détecte automatiquement les alertes critiques via analyse LLM."""
        try:
            # Import local pour éviter les dépendances circulaires
            from .critical_alerts_detector import get_critical_alerts_detector
            
            logger.info("Début détection alertes critiques")
            
            # Récupération du détecteur
            detector = await get_critical_alerts_detector()
            
            # Analyse du contenu récent (1 heure)
            critical_alerts = await detector.analyze_recent_content(hours_back=1)
            
            if critical_alerts:
                # Sauvegarde des alertes critiques en cache Redis
                cache_key = f"critical_alerts:detected:{datetime.now().strftime('%Y-%m-%d-%H')}"
                alerts_data = {
                    "timestamp": datetime.now().isoformat(),
                    "alerts_count": len(critical_alerts),
                    "alerts": [
                        {
                            "id": alert.id,
                            "priority_score": alert.priority_score,
                            "criticality_level": alert.analysis.criticality_level.value,
                            "confidence_score": alert.analysis.confidence_score,
                            "source": alert.analysis.source,
                            "categories": [cat.value for cat in alert.analysis.categories],
                            "key_factors": alert.analysis.key_factors,
                            "created_at": alert.created_at.isoformat()
                        }
                        for alert in critical_alerts
                    ]
                }
                
                # Sauvegarde avec TTL de 48 heures
                await self.redis.set(
                    cache_key, 
                    alerts_data, 
                    expire=int(timedelta(hours=48).total_seconds())
                )
                
                # Log des alertes critiques détectées
                emergency_alerts = [a for a in critical_alerts 
                                  if a.analysis.criticality_level.value == "emergency"]
                critical_level_alerts = [a for a in critical_alerts 
                                       if a.analysis.criticality_level.value == "critical"]
                
                logger.warning(
                    "Alertes critiques détectées automatiquement",
                    total=len(critical_alerts),
                    emergency=len(emergency_alerts),
                    critical=len(critical_level_alerts),
                    avg_confidence=sum(a.analysis.confidence_score for a in critical_alerts) / len(critical_alerts)
                )
                
                # Log détaillé pour les alertes d'urgence
                for alert in emergency_alerts:
                    logger.error(
                        "🚨 ALERTE URGENTE DÉTECTÉE",
                        alert_id=alert.id,
                        source=alert.analysis.source,
                        confidence=alert.analysis.confidence_score,
                        factors=alert.analysis.key_factors[:3],  # Top 3 facteurs
                        impact=alert.analysis.impact_assessment[:100] + "..."
                    )
            else:
                logger.info("Détection terminée - Aucune alerte critique détectée")
            
        except Exception as e:
            logger.error(f"Erreur détection alertes critiques: {e}")
            raise
    
    async def _cleanup_notifications(self):
        """Nettoie les notifications expirées et optimise le cache."""
        try:
            logger.info("Début nettoyage notifications expirées")
            
            # Statistiques initiales
            initial_keys = 0
            expired_keys = 0
            
            # Récupération des clés de notifications via pattern (simulation)
            notification_keys = [
                "notifications:data:*",
                "notifications:stats:*", 
                "notifications:preferences:*"
            ]
            
            # Dans une vraie implémentation, on utiliserait Redis SCAN
            # Ici on simule le nettoyage
            
            # Simulation du nettoyage des notifications expirées
            cache_keys_to_check = [
                "notifications:temp:cleanup_test",
                "websocket:expired_connections",
                "rate_limit:old_records"
            ]
            
            for key in cache_keys_to_check:
                initial_keys += 1
                # Simulation de vérification d'expiration
                # Dans la vraie implémentation, on vérifierait TTL et contenu
                if key.endswith("_test") or "expired" in key:
                    try:
                        await self.redis.delete_key(key)
                        expired_keys += 1
                    except Exception:
                        pass  # Clé n'existe pas ou autre erreur
            
            # Nettoyage des statistiques de rate limiting anciennes
            await self._cleanup_rate_limit_stats()
            
            # Optimisation des connexions WebSocket (nettoyage métadonnées)
            await self._cleanup_websocket_metadata()
            
            # Mise à jour des métriques de nettoyage
            cleanup_stats = {
                "total_keys_checked": initial_keys,
                "expired_keys_removed": expired_keys,
                "cleanup_timestamp": datetime.now().isoformat(),
                "next_cleanup": (datetime.now() + timedelta(hours=1)).isoformat()
            }
            
            # Sauvegarde des stats de nettoyage avec TTL
            await self.redis.set(
                "notifications:cleanup:last_stats",
                cleanup_stats,
                expire=int(timedelta(hours=2).total_seconds())
            )
            
            logger.info(
                f"Nettoyage notifications terminé: {expired_keys}/{initial_keys} clés supprimées"
            )
            
        except Exception as e:
            logger.error(f"Erreur nettoyage notifications: {e}")
            raise
    
    async def _cleanup_rate_limit_stats(self):
        """Nettoie les anciennes statistiques de rate limiting."""
        try:
            # Simulation du nettoyage des anciens compteurs de rate limiting
            # Dans la vraie implémentation, on chercherait les clés avec pattern "rate_limit:*"
            # et on supprimerait celles plus anciennes que X heures
            
            cutoff_time = datetime.now() - timedelta(hours=6)
            cleaned_count = 0
            
            # Simulation des clés de rate limiting à nettoyer
            old_rate_limit_keys = [
                f"rate_limit:user_default:{int(cutoff_time.timestamp())}",
                f"rate_limit:notifications:{int(cutoff_time.timestamp())}"
            ]
            
            for key in old_rate_limit_keys:
                try:
                    await self.redis.delete_key(key)
                    cleaned_count += 1
                except Exception:
                    pass
            
            if cleaned_count > 0:
                logger.debug(f"Nettoyage rate limiting: {cleaned_count} anciennes entrées supprimées")
                
        except Exception as e:
            logger.warning(f"Erreur nettoyage rate limiting: {e}")
    
    async def _cleanup_websocket_metadata(self):
        """Nettoie les métadonnées des connexions WebSocket fermées."""
        try:
            # Simulation du nettoyage des métadonnées WebSocket orphelines
            # Dans la vraie implémentation, on vérifierait les connexions actives
            # et on supprimerait les métadonnées des connexions fermées
            
            websocket_keys = [
                "websocket:connection:old_connection_1",
                "websocket:stats:expired_session",
                "websocket:user_mapping:disconnected_user"
            ]
            
            cleaned_count = 0
            for key in websocket_keys:
                try:
                    # Vérification si la clé existe avant suppression
                    if await self.redis.exists(key):
                        await self.redis.delete_key(key)
                        cleaned_count += 1
                except Exception:
                    pass
            
            if cleaned_count > 0:
                logger.debug(f"Nettoyage WebSocket: {cleaned_count} métadonnées orphelines supprimées")
                
        except Exception as e:
            logger.warning(f"Erreur nettoyage WebSocket metadata: {e}")
    
    async def _send_system_notification(self, title: str, message: str, level: str = "info"):
        """Envoie une notification système via le gestionnaire de notifications."""
        try:
            # Import local pour éviter les dépendances circulaires
            from core.notifications_manager import get_notifications_manager
            
            notifications_manager = await get_notifications_manager()
            await notifications_manager.send_system_notification(title, message, level)
            
        except Exception as e:
            logger.warning(f"Erreur envoi notification système: {e}")
            # Ne pas faire échouer la tâche principale pour une notification
    
    # === Méthodes utilitaires ===
    
    def _parse_cron(self, cron_expression: str) -> Dict:
        """Parse une expression cron pour APScheduler."""
        parts = cron_expression.split()
        if len(parts) != 5:
            raise ValueError(f"Expression cron invalide: {cron_expression}")
        
        return {
            'minute': parts[0],
            'hour': parts[1],
            'day': parts[2],
            'month': parts[3],
            'day_of_week': parts[4]
        }
    
    async def _save_task_to_redis(self, task: ScheduledTask):
        """Sauvegarde une tâche en Redis."""
        key = f"scheduler:task:{task.id}"
        await self.redis.set(key, task.dict(), expire=int(timedelta(days=30).total_seconds()))
    
    async def _record_task_metrics(self, task_id: str, status: str, 
                                 execution_time: float, error: str = None):
        """Enregistre les métriques d'exécution d'une tâche."""
        metrics_key = f"scheduler:metrics:{task_id}"
        
        current_metrics = await self.redis.get(metrics_key) or {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0,
            'last_execution': None,
            'last_error': None
        }
        
        # Mise à jour des métriques
        current_metrics['total_executions'] += 1
        current_metrics['total_execution_time'] += execution_time
        current_metrics['last_execution'] = datetime.utcnow().isoformat()
        
        if status == "success":
            current_metrics['successful_executions'] += 1
        else:
            current_metrics['failed_executions'] += 1
            current_metrics['last_error'] = error
        
        await self.redis.set(metrics_key, current_metrics, expire=int(timedelta(days=90).total_seconds()))
    
    def _job_executed_listener(self, event):
        """Écouteur d'événement pour les jobs exécutés."""
        logger.debug(f"Job {event.job_id} exécuté avec succès")
    
    def _job_error_listener(self, event):
        """Écouteur d'événement pour les erreurs de jobs."""
        logger.error(f"Erreur dans le job {event.job_id}: {event.exception}")

# === Context Manager pour utilisation dans FastAPI ===

@asynccontextmanager
async def create_task_scheduler(config_manager: ConfigManager, redis_client: RedisClient):
    """Context manager pour le gestionnaire de tâches."""
    scheduler = TaskScheduler(config_manager, redis_client)
    
    try:
        await scheduler.start()
        yield scheduler
    finally:
        await scheduler.shutdown()