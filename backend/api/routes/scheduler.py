"""
Routes API pour l'administration du scheduler APScheduler.

Permet de :
- Lister les tâches programmées
- Consulter les statuts et métriques
- Gérer les tâches (activer/désactiver)
- Forcer l'exécution manuelle
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.scheduler import TaskScheduler, ScheduledTask

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])
limiter = Limiter(key_func=get_remote_address)

# === Modèles de réponse ===

class TaskStatusResponse(BaseModel):
    """Réponse détaillée pour le statut d'une tâche."""
    id: str
    name: str
    description: str
    status: str
    enabled: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    error_count: int
    max_retries: int
    
class TaskMetricsResponse(BaseModel):
    """Métriques d'exécution d'une tâche."""
    task_id: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_execution_time: float
    last_execution: Optional[datetime]
    last_error: Optional[str]

class SchedulerStatusResponse(BaseModel):
    """Statut global du scheduler."""
    is_running: bool
    total_tasks: int
    active_tasks: int
    tasks_running: int
    tasks_completed: int
    tasks_failed: int
    uptime: str

class CreateTaskRequest(BaseModel):
    """Requête pour créer une nouvelle tâche."""
    id: str = Field(..., description="Identifiant unique de la tâche")
    name: str = Field(..., description="Nom de la tâche")
    description: str = Field(..., description="Description de la tâche")
    cron: str = Field(..., description="Expression cron (format: minute hour day month day_of_week)")
    enabled: bool = Field(True, description="Activer la tâche immédiatement")

# === Dépendances ===

async def get_scheduler(request: Request) -> TaskScheduler:
    """Récupère l'instance du scheduler depuis l'état de l'application."""
    if not hasattr(request.app.state, 'scheduler'):
        raise HTTPException(status_code=503, detail="Scheduler non initialisé")
    return request.app.state.scheduler

# === Endpoints ===

@router.get("/status", response_model=SchedulerStatusResponse)
@limiter.limit("10/minute")
async def get_scheduler_status(
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Récupère le statut global du scheduler."""
    try:
        tasks = await scheduler.get_all_tasks()
        
        # Calcul des statistiques
        active_tasks = sum(1 for t in tasks if t.enabled)
        tasks_running = sum(1 for t in tasks if t.status == "running")
        tasks_completed = sum(1 for t in tasks if t.status == "completed")
        tasks_failed = sum(1 for t in tasks if t.status == "failed")
        
        # Calcul de l'uptime (depuis le dernier démarrage)
        uptime = "À implémenter"  # Placeholder
        
        return SchedulerStatusResponse(
            is_running=scheduler.is_running,
            total_tasks=len(tasks),
            active_tasks=active_tasks,
            tasks_running=tasks_running,
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            uptime=uptime
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération du statut: {e}")

@router.get("/tasks", response_model=List[TaskStatusResponse])
@limiter.limit("20/minute")
async def list_tasks(
    request: Request,
    enabled_only: bool = False,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Liste toutes les tâches programmées avec leurs statuts."""
    try:
        tasks = await scheduler.get_all_tasks()
        
        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        
        return [
            TaskStatusResponse(
                id=task.id,
                name=task.name,
                description=task.description,
                status=task.status,
                enabled=task.enabled,
                last_run=task.last_run,
                next_run=task.next_run,
                error_count=task.error_count,
                max_retries=task.max_retries
            )
            for task in tasks
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des tâches: {e}")

@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
@limiter.limit("30/minute")
async def get_task_status(
    task_id: str,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Récupère le statut détaillé d'une tâche spécifique."""
    try:
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        return TaskStatusResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            enabled=task.enabled,
            last_run=task.last_run,
            next_run=task.next_run,
            error_count=task.error_count,
            max_retries=task.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération de la tâche: {e}")

@router.get("/tasks/{task_id}/metrics", response_model=TaskMetricsResponse)
@limiter.limit("20/minute")
async def get_task_metrics(
    task_id: str,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Récupère les métriques d'exécution d'une tâche."""
    try:
        # Vérification de l'existence de la tâche
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        # Récupération des métriques depuis Redis
        metrics_key = f"scheduler:metrics:{task_id}"
        redis_client = request.app.state.redis
        metrics = await redis_client.get(metrics_key) or {
            'total_executions': 0,
            'successful_executions': 0,
            'failed_executions': 0,
            'total_execution_time': 0.0,
            'last_execution': None,
            'last_error': None
        }
        
        # Calcul des statistiques
        success_rate = 0.0
        average_execution_time = 0.0
        
        if metrics['total_executions'] > 0:
            success_rate = (metrics['successful_executions'] / metrics['total_executions']) * 100
            average_execution_time = metrics['total_execution_time'] / metrics['total_executions']
        
        return TaskMetricsResponse(
            task_id=task_id,
            total_executions=metrics['total_executions'],
            successful_executions=metrics['successful_executions'],
            failed_executions=metrics['failed_executions'],
            success_rate=round(success_rate, 2),
            average_execution_time=round(average_execution_time, 2),
            last_execution=datetime.fromisoformat(metrics['last_execution']) if metrics['last_execution'] else None,
            last_error=metrics['last_error']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des métriques: {e}")

@router.post("/tasks/{task_id}/run")
@limiter.limit("5/minute")
async def run_task_manually(
    task_id: str,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Force l'exécution manuelle d'une tâche."""
    try:
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        if task.status == "running":
            raise HTTPException(status_code=409, detail="La tâche est déjà en cours d'exécution")
        
        # Déclenchement manuel via APScheduler
        job = scheduler.scheduler.get_job(task_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job APScheduler introuvable")
        
        # Exécution immédiate
        scheduler.scheduler.modify_job(task_id, next_run_time=datetime.now())
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tâche {task.name} planifiée pour exécution immédiate",
                "task_id": task_id,
                "status": "scheduled"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du déclenchement de la tâche: {e}")

@router.put("/tasks/{task_id}/toggle")
@limiter.limit("10/minute")
async def toggle_task(
    task_id: str,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Active ou désactive une tâche."""
    try:
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        new_status = not task.enabled
        
        if new_status:
            # Activation de la tâche
            job = scheduler.scheduler.get_job(task_id)
            if not job:
                # Recréer le job s'il n'existe pas
                # Cette logique dépend de la configuration de la tâche
                pass
            else:
                scheduler.scheduler.resume_job(task_id)
        else:
            # Désactivation de la tâche
            scheduler.scheduler.pause_job(task_id)
        
        # Mise à jour du statut
        task.enabled = new_status
        await scheduler._save_task_to_redis(task)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tâche {task.name} {'activée' if new_status else 'désactivée'}",
                "task_id": task_id,
                "enabled": new_status
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la modification de la tâche: {e}")

@router.post("/tasks", response_model=TaskStatusResponse)
@limiter.limit("5/minute")
async def create_task(
    task_request: CreateTaskRequest,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Crée une nouvelle tâche programmée personnalisée."""
    try:
        # Vérification de l'unicité de l'ID
        existing_task = await scheduler.get_task_status(task_request.id)
        if existing_task:
            raise HTTPException(status_code=409, detail=f"Une tâche avec l'ID {task_request.id} existe déjà")
        
        # Validation de l'expression cron
        try:
            scheduler._parse_cron(task_request.cron)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Expression cron invalide: {e}")
        
        # Fonction placeholder pour les tâches personnalisées
        async def custom_task_function():
            """Fonction placeholder pour les tâches personnalisées."""
            return {"message": "Tâche personnalisée exécutée", "timestamp": datetime.utcnow().isoformat()}
        
        # Ajout de la tâche
        await scheduler.add_task(
            id=task_request.id,
            name=task_request.name,
            description=task_request.description,
            cron=task_request.cron,
            func=custom_task_function,
            enabled=task_request.enabled
        )
        
        # Récupération de la tâche créée
        task = await scheduler.get_task_status(task_request.id)
        
        return TaskStatusResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            enabled=task.enabled,
            last_run=task.last_run,
            next_run=task.next_run,
            error_count=task.error_count,
            max_retries=task.max_retries
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la création de la tâche: {e}")

@router.delete("/tasks/{task_id}")
@limiter.limit("5/minute")
async def delete_task(
    task_id: str,
    request: Request,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Supprime une tâche programmée."""
    try:
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        # Empêcher la suppression des tâches système
        system_tasks = [
            "sync_mcp_sources",
            "cleanup_cache", 
            "daily_report",
            "update_langfuse_metrics",
            "backup_metadata"
        ]
        
        if task_id in system_tasks:
            raise HTTPException(status_code=403, detail="Impossible de supprimer une tâche système")
        
        # Suppression de la tâche
        await scheduler.remove_task(task_id)
        
        return JSONResponse(
            status_code=200,
            content={
                "message": f"Tâche {task.name} supprimée avec succès",
                "task_id": task_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression de la tâche: {e}")

@router.get("/logs/{task_id}")
@limiter.limit("10/minute")
async def get_task_logs(
    task_id: str,
    request: Request,
    limit: int = 50,
    scheduler: TaskScheduler = Depends(get_scheduler)
):
    """Récupère les logs d'exécution d'une tâche."""
    try:
        task = await scheduler.get_task_status(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Tâche {task_id} introuvable")
        
        # Récupération des logs depuis Redis (si implémenté)
        logs_key = f"scheduler:logs:{task_id}"
        redis_client = request.app.state.redis
        logs = await redis_client.get(logs_key) or []
        
        # Limitation du nombre de logs retournés
        if len(logs) > limit:
            logs = logs[-limit:]
        
        return JSONResponse(
            status_code=200,
            content={
                "task_id": task_id,
                "logs": logs,
                "total_logs": len(logs)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des logs: {e}") 