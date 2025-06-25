#!/bin/bash

# ===== TECH RADAR EXPRESS - SCRIPT DE DÉPLOIEMENT =====
# Script automatisé pour démarrer l'infrastructure complète

set -e

echo "🚀 Démarrage de Tech Radar Express..."

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction pour afficher les messages colorés
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Vérification des prérequis
check_requirements() {
    log_info "Vérification des prérequis..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé. Veuillez l'installer depuis https://docker.com"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose n'est pas installé."
        exit 1
    fi
    
    log_success "Prérequis vérifiés ✓"
}

# Configuration de l'environnement
setup_environment() {
    log_info "Configuration de l'environnement..."
    
    if [ ! -f ".env" ]; then
        if [ -f "backend/config.env.template" ]; then
            log_info "Copie du fichier template vers .env"
            cp backend/config.env.template .env
            log_warning "Veuillez configurer les variables dans le fichier .env"
        else
            log_error "Fichier template de configuration introuvable"
            exit 1
        fi
    else
        log_success "Fichier .env existant trouvé"
    fi
}

# Arrêt des services existants
stop_services() {
    log_info "Arrêt des services existants..."
    docker-compose down --remove-orphans 2>/dev/null || true
    log_success "Services arrêtés"
}

# Construction des images
build_images() {
    log_info "Construction des images Docker..."
    docker-compose build --no-cache backend
    log_success "Images construites"
}

# Démarrage des services
start_services() {
    log_info "Démarrage des services..."
    
    # Démarrage en mode détaché
    docker-compose up -d
    
    log_success "Services démarrés"
}

# Vérification de la santé des services
check_health() {
    log_info "Vérification de la santé des services..."
    
    # Attendre que les services soient prêts
    echo "Attente du démarrage des services (30s)..."
    sleep 30
    
    # Vérification Redis
    if docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis : OK"
    else
        log_warning "Redis : Non disponible"
    fi
    
    # Vérification PostgreSQL
    if docker-compose exec -T postgres pg_isready -U postgres | grep -q "accepting connections"; then
        log_success "PostgreSQL : OK"
    else
        log_warning "PostgreSQL : Non disponible"
    fi
    
    # Vérification Neo4j
    if docker-compose exec -T neo4j cypher-shell -u neo4j -p neo4jpassword "RETURN 1" 2>/dev/null | grep -q "1"; then
        log_success "Neo4j : OK"
    else
        log_warning "Neo4j : Non disponible"
    fi
    
    # Vérification Backend API
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend API : OK"
    else
        log_warning "Backend API : Non disponible"
    fi
}

# Affichage des informations de connexion
show_info() {
    echo ""
    echo "🎉 Tech Radar Express déployé avec succès !"
    echo ""
    echo "📋 Services disponibles :"
    echo "  • Backend API      : http://localhost:8000"
    echo "  • API Docs         : http://localhost:8000/docs"
    echo "  • PostgreSQL       : localhost:5432"
    echo "  • Redis            : localhost:6379"
    echo "  • Neo4j Browser    : http://localhost:7474 (neo4j/neo4jpassword)"
    echo "  • Redis Insight    : http://localhost:8001"
    echo ""
    echo "📁 Logs des services :"
    echo "  docker-compose logs -f [service_name]"
    echo ""
    echo "🛠️  Commandes utiles :"
    echo "  • Arrêter : docker-compose down"
    echo "  • Logs    : docker-compose logs -f"
    echo "  • Status  : docker-compose ps"
    echo ""
}

# Menu principal
main() {
    case "${1:-deploy}" in
        "deploy"|"start")
            check_requirements
            setup_environment
            stop_services
            build_images
            start_services
            check_health
            show_info
            ;;
        "stop")
            stop_services
            log_success "Services arrêtés"
            ;;
        "restart")
            stop_services
            start_services
            check_health
            show_info
            ;;
        "logs")
            docker-compose logs -f
            ;;
        "status")
            docker-compose ps
            ;;
        "clean")
            stop_services
            docker-compose down -v --remove-orphans
            docker system prune -f
            log_success "Nettoyage terminé"
            ;;
        *)
            echo "Usage: $0 {deploy|start|stop|restart|logs|status|clean}"
            echo ""
            echo "Commandes disponibles :"
            echo "  deploy/start  - Déploie l'infrastructure complète"
            echo "  stop          - Arrête tous les services"
            echo "  restart       - Redémarre les services"
            echo "  logs          - Affiche les logs en temps réel"
            echo "  status        - Affiche le status des services"
            echo "  clean         - Nettoie tout (volumes inclus)"
            exit 1
            ;;
    esac
}

# Exécution du script
main "$@" 