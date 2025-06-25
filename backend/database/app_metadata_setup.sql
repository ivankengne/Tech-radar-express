-- ===================================
-- Tech Radar Express - Tables Métadonnées Application
-- Tables complémentaires pour dashboard, analytics et configuration
-- Le vector search est géré par le MCP crawl4ai-rag
-- ===================================

-- Activer l'extension pour les UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ===================================
-- Table: user_sessions (Sessions utilisateur)
-- ===================================

CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_token VARCHAR(255) UNIQUE NOT NULL,
    user_ip INET,
    user_agent TEXT,
    preferences JSONB DEFAULT '{}',
    last_activity TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '24 hours'
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_activity ON user_sessions(last_activity DESC);

-- ===================================
-- Table: search_history (Historique recherches)
-- ===================================

CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES user_sessions(id) ON DELETE CASCADE,
    query_text TEXT NOT NULL,
    query_type VARCHAR(50) DEFAULT 'general' CHECK (query_type IN ('general', 'code', 'technical', 'trend')),
    results_count INTEGER DEFAULT 0,
    response_time_ms INTEGER,
    user_rating SMALLINT CHECK (user_rating >= 1 AND user_rating <= 5),
    feedback_text TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour analytics
CREATE INDEX IF NOT EXISTS idx_search_history_session ON search_history(session_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created ON search_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_search_history_type ON search_history(query_type);

-- ===================================
-- Table: dashboard_metrics (Métriques dashboard)
-- ===================================

CREATE TABLE IF NOT EXISTS dashboard_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,2) NOT NULL,
    metric_type VARCHAR(50) NOT NULL CHECK (metric_type IN ('count', 'percentage', 'duration', 'score')),
    technology_axis VARCHAR(100),
    time_period VARCHAR(20) DEFAULT 'daily' CHECK (time_period IN ('hourly', 'daily', 'weekly', 'monthly')),
    metadata JSONB DEFAULT '{}',
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour requêtes dashboard
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_name ON dashboard_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_axis ON dashboard_metrics(technology_axis);
CREATE INDEX IF NOT EXISTS idx_dashboard_metrics_period ON dashboard_metrics(time_period, calculated_at DESC);

-- ===================================
-- Table: system_alerts (Alertes système)
-- ===================================

CREATE TABLE IF NOT EXISTS system_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN ('info', 'warning', 'error', 'success')),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    technology_axis VARCHAR(100),
    priority SMALLINT DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    auto_dismiss_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour notifications temps réel
CREATE INDEX IF NOT EXISTS idx_system_alerts_type ON system_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_system_alerts_priority ON system_alerts(priority DESC, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_alerts_unread ON system_alerts(is_read, created_at DESC);

-- ===================================
-- Table: llm_provider_config (Configuration LLM)
-- ===================================

CREATE TABLE IF NOT EXISTS llm_provider_config (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name VARCHAR(50) NOT NULL UNIQUE CHECK (provider_name IN ('openai', 'anthropic', 'google', 'ollama')),
    is_active BOOLEAN DEFAULT FALSE,
    api_key_encrypted TEXT, -- Clé chiffrée
    base_url TEXT,
    default_model VARCHAR(100),
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3,2) DEFAULT 0.7 CHECK (temperature >= 0 AND temperature <= 2),
    timeout_seconds INTEGER DEFAULT 30,
    rate_limit_per_minute INTEGER DEFAULT 60,
    cost_per_1k_tokens DECIMAL(8,6),
    configuration JSONB DEFAULT '{}',
    last_test_at TIMESTAMPTZ,
    test_success BOOLEAN,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour configuration LLM
CREATE INDEX IF NOT EXISTS idx_llm_config_provider ON llm_provider_config(provider_name);
CREATE INDEX IF NOT EXISTS idx_llm_config_active ON llm_provider_config(is_active);

-- ===================================
-- Table: crawl_schedules (Planification crawls)
-- ===================================

CREATE TABLE IF NOT EXISTS crawl_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_url TEXT NOT NULL,
    technology_axis VARCHAR(100) NOT NULL,
    crawl_frequency VARCHAR(20) DEFAULT 'daily' CHECK (crawl_frequency IN ('hourly', 'daily', 'weekly', 'monthly')),
    is_active BOOLEAN DEFAULT TRUE,
    last_crawl_at TIMESTAMPTZ,
    next_crawl_at TIMESTAMPTZ,
    crawl_depth INTEGER DEFAULT 3,
    max_pages INTEGER DEFAULT 100,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error_message TEXT,
    configuration JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour scheduler
CREATE INDEX IF NOT EXISTS idx_crawl_schedules_next ON crawl_schedules(next_crawl_at) WHERE is_active = TRUE;
CREATE INDEX IF NOT EXISTS idx_crawl_schedules_axis ON crawl_schedules(technology_axis);
CREATE INDEX IF NOT EXISTS idx_crawl_schedules_active ON crawl_schedules(is_active);

-- ===================================
-- Table: usage_analytics (Analytics utilisation)
-- ===================================

CREATE TABLE IF NOT EXISTS usage_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    event_data JSONB NOT NULL DEFAULT '{}',
    session_id UUID REFERENCES user_sessions(id) ON DELETE SET NULL,
    user_ip INET,
    page_path VARCHAR(255),
    technology_axis VARCHAR(100),
    duration_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index pour analytics
CREATE INDEX IF NOT EXISTS idx_usage_analytics_type ON usage_analytics(event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_analytics_session ON usage_analytics(session_id);
CREATE INDEX IF NOT EXISTS idx_usage_analytics_created ON usage_analytics(created_at DESC);

-- ===================================
-- Vues pour Dashboard Analytics
-- ===================================

-- Vue: Statistiques quotidiennes
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_searches,
    COUNT(DISTINCT session_id) as unique_users,
    AVG(response_time_ms) as avg_response_time,
    AVG(user_rating) as avg_rating
FROM search_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Vue: Top requêtes par axe
CREATE OR REPLACE VIEW popular_queries_by_axis AS
SELECT 
    query_text,
    query_type,
    COUNT(*) as search_count,
    AVG(user_rating) as avg_rating,
    MAX(created_at) as last_searched
FROM search_history
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY query_text, query_type
ORDER BY search_count DESC
LIMIT 100;

-- ===================================
-- Fonctions Analytics
-- ===================================

-- Fonction: Calculer métriques dashboard
CREATE OR REPLACE FUNCTION calculate_dashboard_metrics()
RETURNS TABLE (
    metric_name text,
    metric_value decimal,
    calculated_for date
)
LANGUAGE plpgsql
AS $$
BEGIN
    -- Calculer les métriques des dernières 24h
    RETURN QUERY
    WITH daily_metrics AS (
        SELECT 
            'total_searches'::text as metric_name,
            COUNT(*)::decimal as metric_value,
            CURRENT_DATE as calculated_for
        FROM search_history
        WHERE created_at >= CURRENT_DATE
        
        UNION ALL
        
        SELECT 
            'unique_users'::text,
            COUNT(DISTINCT session_id)::decimal,
            CURRENT_DATE
        FROM search_history
        WHERE created_at >= CURRENT_DATE
        
        UNION ALL
        
        SELECT 
            'avg_response_time'::text,
            ROUND(AVG(response_time_ms), 2)::decimal,
            CURRENT_DATE
        FROM search_history
        WHERE created_at >= CURRENT_DATE
    )
    SELECT * FROM daily_metrics;
END;
$$;

-- Fonction: Obtenir alertes actives
CREATE OR REPLACE FUNCTION get_active_alerts()
RETURNS TABLE (
    id uuid,
    alert_type varchar(50),
    title varchar(255),
    message text,
    priority smallint,
    created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        a.id,
        a.alert_type,
        a.title,
        a.message,
        a.priority,
        a.created_at
    FROM system_alerts a
    WHERE a.is_dismissed = FALSE
      AND (a.auto_dismiss_at IS NULL OR a.auto_dismiss_at > NOW())
    ORDER BY a.priority DESC, a.created_at DESC
    LIMIT 50;
END;
$$;

-- ===================================
-- Triggers pour timestamps automatiques
-- ===================================

-- Fonction trigger pour updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers sur les tables
CREATE TRIGGER update_system_alerts_updated_at 
    BEFORE UPDATE ON system_alerts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_llm_provider_config_updated_at 
    BEFORE UPDATE ON llm_provider_config 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_crawl_schedules_updated_at 
    BEFORE UPDATE ON crawl_schedules 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ===================================
-- RLS (Row Level Security)
-- ===================================

-- Activer RLS sur les tables sensibles
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE search_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE llm_provider_config ENABLE ROW LEVEL SECURITY;

-- Politiques pour lecture publique limitée
CREATE POLICY "Allow public read access to non-sensitive data" ON dashboard_metrics FOR SELECT USING (true);
CREATE POLICY "Allow public read access to alerts" ON system_alerts FOR SELECT USING (true);

-- Politiques pour service role
CREATE POLICY "Allow service role full access" ON user_sessions FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON search_history FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON dashboard_metrics FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON system_alerts FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON llm_provider_config FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON crawl_schedules FOR ALL USING (true);
CREATE POLICY "Allow service role full access" ON usage_analytics FOR ALL USING (true);

-- ===================================
-- Données de test initiales
-- ===================================

-- Configuration LLM par défaut
INSERT INTO llm_provider_config (provider_name, is_active, default_model, max_tokens, temperature)
VALUES 
('ollama', true, 'qwen2.5:7b-instruct-q4_K_M', 4000, 0.7),
('openai', false, 'gpt-4o-mini', 4000, 0.7),
('anthropic', false, 'claude-3-sonnet-20240229', 4000, 0.7),
('google', false, 'gemini-pro', 4000, 0.7)
ON CONFLICT (provider_name) DO NOTHING;

-- Alerte de bienvenue
INSERT INTO system_alerts (alert_type, title, message, priority)
VALUES ('info', 'Tech Radar Express initialisé', 'Le système de veille technologique est opérationnel.', 2)
ON CONFLICT DO NOTHING;

-- Message de confirmation
DO $$
BEGIN
    RAISE NOTICE '✅ Tables métadonnées application créées avec succès!';
    RAISE NOTICE '📊 Tables: user_sessions, search_history, dashboard_metrics, system_alerts';
    RAISE NOTICE '⚙️ Configuration: llm_provider_config, crawl_schedules';
    RAISE NOTICE '📈 Analytics: usage_analytics + vues dashboard';
    RAISE NOTICE '🔍 Le vector search reste géré par le MCP crawl4ai-rag';
END $$; 