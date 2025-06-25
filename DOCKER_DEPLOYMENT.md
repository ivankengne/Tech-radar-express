# 🐳 Guide de Déploiement Docker - Tech Radar Express

## Vue d'ensemble

Tech Radar Express utilise une architecture microservices conteneurisée avec Docker Compose pour simplifier le déploiement et garantir la reproductibilité de l'environnement.

## 🏗️ Architecture des Services

```mermaid
graph TB
    subgraph "Frontend"
        FE[Next.js Frontend<br/>Port 3000]
    end
    
    subgraph "Backend Services"
        API[FastAPI Backend<br/>Port 8000]
        WORKER[Celery Worker]
        BEAT[Celery Beat Scheduler]
    end
    
    subgraph "Databases"
        PG[PostgreSQL<br/>Port 5432]
        REDIS[Redis Cache<br/>Port 6379]
        NEO4J[Neo4j Graph DB<br/>Ports 7474/7687]
    end
    
    subgraph "Monitoring"
        RI[Redis Insight<br/>Port 8001]
    end
    
    FE --> API
    API --> PG
    API --> REDIS
    API --> NEO4J
    WORKER --> PG
    WORKER --> REDIS
    BEAT --> PG
    BEAT --> REDIS
    RI --> REDIS
```

## 📋 Prérequis

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Git** (pour cloner le projet)
- **8GB RAM minimum** (recommandé)
- **Ports libres** : 3000, 8000, 5432, 6379, 7474, 7687, 8001

## 🚀 Déploiement Rapide

### 1. Clonage et Configuration

```bash
# Clonage du projet
git clone <votre-repo>
cd Tech-radar-express

# Copie du fichier de configuration
cp backend/config.env.template .env

# Configuration des variables (OBLIGATOIRE)
nano .env  # ou votre éditeur préféré
```

### 2. Déploiement avec le Script Automatisé

```bash
# Rendre le script exécutable
chmod +x deploy.sh

# Déploiement complet
./deploy.sh deploy
```

### 3. Déploiement Manuel (Alternative)

```bash
# Construction des images
docker-compose build

# Démarrage des services
docker-compose up -d

# Vérification du statut
docker-compose ps
```

## ⚙️ Configuration Détaillée

### Variables d'Environnement Critiques

#### Base de Données
```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/tech_radar_db
REDIS_URL=redis://localhost:6379/0
NEO4J_URI=bolt://localhost:7687
```

#### Sécurité
```env
SECRET_KEY=votre-clé-secrète-32-caractères-minimum
ENCRYPT_KEY=votre-clé-chiffrement-32-caractères
```

#### Services Externes (Optionnels)
```env
# Supabase
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_ANON_KEY=votre-clé-anonyme

# Langfuse (Monitoring LLM)
LANGFUSE_PUBLIC_KEY=votre-clé-publique
LANGFUSE_SECRET_KEY=votre-clé-secrète
LANGFUSE_ENABLED=false  # Activez si configuré
```

## 🔧 Gestion des Services

### Commandes du Script de Déploiement

```bash
# Démarrage complet
./deploy.sh deploy
./deploy.sh start

# Arrêt des services
./deploy.sh stop

# Redémarrage
./deploy.sh restart

# Logs en temps réel
./deploy.sh logs

# Status des services
./deploy.sh status

# Nettoyage complet (ATTENTION: supprime les données)
./deploy.sh clean
```

### Commandes Docker Compose Directes

```bash
# Démarrage
docker-compose up -d

# Arrêt
docker-compose down

# Reconstruction après modification du code
docker-compose build --no-cache backend
docker-compose up -d backend

# Logs spécifiques
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f redis

# Shell dans un conteneur
docker-compose exec backend bash
docker-compose exec postgres psql -U postgres -d tech_radar_db
```

## 🌐 Accès aux Services

| Service | URL | Credentials |
|---------|-----|-------------|
| **Backend API** | http://localhost:8000 | - |
| **API Documentation** | http://localhost:8000/docs | - |
| **API Health Check** | http://localhost:8000/health | - |
| **PostgreSQL** | localhost:5432 | postgres/postgres |
| **Redis** | localhost:6379 | (aucun mot de passe) |
| **Neo4j Browser** | http://localhost:7474 | neo4j/neo4jpassword |
| **Redis Insight** | http://localhost:8001 | - |

## 🔍 Surveillance et Débogage

### Health Checks Automatiques

Tous les services incluent des health checks automatiques :

```bash
# Vérification du statut de santé
docker-compose ps

# Logs des health checks
docker-compose logs backend | grep health
```

### Logs Détaillés

```bash
# Logs temps réel de tous les services
docker-compose logs -f

# Logs d'un service spécifique
docker-compose logs -f backend

# Logs avec horodatage
docker-compose logs -f -t backend
```

### Tests de Connectivité

```bash
# Test Redis
docker-compose exec redis redis-cli ping

# Test PostgreSQL
docker-compose exec postgres pg_isready -U postgres

# Test Neo4j
docker-compose exec neo4j cypher-shell -u neo4j -p neo4jpassword "RETURN 1"

# Test Backend API
curl http://localhost:8000/health
```

## 📊 Volumes et Persistance

### Volumes Configurés

- **postgres_data** : Données PostgreSQL persistantes
- **redis_data** : Cache Redis persistant  
- **neo4j_data** : Graphe Neo4j persistant
- **neo4j_logs** : Logs Neo4j
- **redis_insight_data** : Configuration Redis Insight

### Sauvegarde des Données

```bash
# Sauvegarde PostgreSQL
docker-compose exec postgres pg_dump -U postgres tech_radar_db > backup_$(date +%Y%m%d).sql

# Sauvegarde Neo4j
docker-compose exec neo4j neo4j-admin dump --database=neo4j --to=/tmp/neo4j_backup_$(date +%Y%m%d).dump
```

## 🚨 Dépannage

### Problèmes Courants

#### Port déjà utilisé
```bash
# Identifier le processus utilisant le port
lsof -i :8000
# ou
netstat -tulpn | grep :8000

# Arrêter le processus ou changer le port
```

#### Problème de permissions
```bash
# Corriger les permissions des volumes
sudo chown -R $USER:$USER ./backend/logs
sudo chown -R $USER:$USER ./backend/uploads
```

#### Service qui ne démarre pas
```bash
# Vérifier les logs spécifiques
docker-compose logs service_name

# Redémarrer un service spécifique
docker-compose restart service_name

# Reconstruction forcée
docker-compose build --no-cache service_name
docker-compose up -d service_name
```

### Nettoyage en Cas de Problème

```bash
# Arrêt complet et nettoyage
docker-compose down -v --remove-orphans

# Nettoyage des images Docker
docker system prune -f

# Nettoyage complet (ATTENTION: perte de données)
docker-compose down -v
docker system prune -a -f
```

## 🔄 Mise à Jour

### Mise à jour du Code

```bash
# Récupération des dernières modifications
git pull origin main

# Reconstruction et redémarrage
./deploy.sh stop
./deploy.sh deploy
```

### Mise à jour des Dépendances

```bash
# Modification de requirements.txt puis
docker-compose build --no-cache backend
docker-compose up -d backend
```

## 📈 Monitoring de Production

### Métriques Importantes

- **CPU/RAM** des conteneurs
- **Connexions** base de données
- **Taille** des volumes
- **Logs d'erreurs**

```bash
# Stats en temps réel
docker stats

# Utilisation des volumes
docker system df

# Inspection d'un conteneur
docker inspect tech-radar-backend
```

## 🔐 Sécurité

### Bonnes Pratiques

1. **Changez tous les mots de passe par défaut**
2. **Configurez des clés secrètes uniques**
3. **Limitez l'exposition des ports en production**
4. **Utilisez des volumes chiffrés pour les données sensibles**
5. **Mettez à jour régulièrement les images Docker**

### Configuration Production

```bash
# Variables d'environnement de production
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=WARNING

# Utilisation de secrets Docker (recommandé)
docker secret create postgres_password /path/to/password/file
```

## 📞 Support

En cas de problème :

1. Vérifiez les logs : `./deploy.sh logs`
2. Vérifiez le statut : `./deploy.sh status`
3. Consultez la documentation des services individuels
4. Ouvrez une issue sur le repository Git

---

**🎯 Objectif** : Infrastructure robuste et reproductible pour Tech Radar Express 