-- ============================================================================
-- AstroGeo AI — PostGIS + pgvector Initialization
-- ============================================================================
-- Run: psql -U astrogeo_user -d astrogeo_db -f scripts/init_postgis.sql
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Agent 1: Satellite Change Detection vector store
-- ============================================================================
CREATE TABLE IF NOT EXISTS change_event_embeddings (
    id SERIAL PRIMARY KEY,
    event_id UUID DEFAULT gen_random_uuid(),
    region_name VARCHAR(100),
    geometry GEOMETRY(Polygon, 4326),
    event_date DATE,
    change_type VARCHAR(50),
    ndvi_delta FLOAT,
    area_ha FLOAT,
    data_source VARCHAR(100),
    summary_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_change_emb ON change_event_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ============================================================================
-- Agent 2: Asteroid Observation Planner vector store
-- ============================================================================
CREATE TABLE IF NOT EXISTS asteroid_obs_embeddings (
    id SERIAL PRIMARY KEY,
    asteroid_id VARCHAR(50),
    approach_date TIMESTAMP,
    observer_lat FLOAT,
    observer_lon FLOAT,
    magnitude FLOAT,
    distance_au FLOAT,
    cloud_cover FLOAT,
    moon_phase FLOAT,
    outcome BOOLEAN,
    mpc_verified BOOLEAN DEFAULT false,
    summary_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_asteroid_emb ON asteroid_obs_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ============================================================================
-- Agent 3: Drought Intelligence vector store
-- ============================================================================
CREATE TABLE IF NOT EXISTS drought_event_embeddings (
    id SERIAL PRIMARY KEY,
    district_name VARCHAR(100),
    state_name VARCHAR(100),
    geometry GEOMETRY(Polygon, 4326),
    event_date DATE,
    severity_score FLOAT,
    soil_moisture FLOAT,
    rainfall_anomaly FLOAT,
    ndvi_delta FLOAT,
    imd_verified BOOLEAN DEFAULT false,
    summary_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drought_emb ON drought_event_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ============================================================================
-- Agent 4: Ground Truth Validation vector store
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_embeddings (
    id SERIAL PRIMARY KEY,
    prediction_id UUID DEFAULT gen_random_uuid(),
    agent_name VARCHAR(50),
    predicted_value TEXT,
    actual_value TEXT,
    was_correct BOOLEAN,
    source VARCHAR(100),
    summary_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pred_emb ON prediction_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ============================================================================
-- Agent 5: GraphRAG knowledge graph
-- ============================================================================
CREATE TABLE IF NOT EXISTS graph_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_type VARCHAR(50),
    domain VARCHAR(30),
    label TEXT,
    properties JSONB DEFAULT '{}',
    event_date DATE,
    summary_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50),
    confidence FLOAT DEFAULT 1.0,
    evidence_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Alias view for LangGraph pipeline compatibility
CREATE OR REPLACE VIEW graph_node_embeddings AS
SELECT id, node_type, domain, label, summary_text, embedding, created_at
FROM graph_nodes;

CREATE INDEX IF NOT EXISTS idx_graph_node_emb ON graph_nodes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX IF NOT EXISTS idx_graph_edges_src ON graph_edges(source_id);
CREATE INDEX IF NOT EXISTS idx_graph_edges_tgt ON graph_edges(target_id);

-- ============================================================================
-- Immutable audit ledger (Verifiable AI)
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_ledger (
    id SERIAL PRIMARY KEY,
    prediction_id UUID NOT NULL DEFAULT gen_random_uuid(),
    agent_name VARCHAR(50),
    model_version VARCHAR(20),
    input_hash VARCHAR(64),
    output_hash VARCHAR(64),
    prev_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- Done
-- ============================================================================
SELECT 'AstroGeo pgvector tables created successfully!' AS status;
