-- Regulatory Intelligence System Database Schema
-- PostgreSQL with pgvector extension for Supabase

-- Enable pgvector extension for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- Create enum types for consistency
CREATE TYPE gap_severity_enum AS ENUM ('low', 'medium', 'high', 'critical');

-- Regulation Documents table
-- Stores raw regulatory documents from various sources
CREATE TABLE regulations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source VARCHAR(50) NOT NULL, -- 'fincen', 'sec', 'federal_register', etc.
  document_id VARCHAR(100) UNIQUE NOT NULL, -- Source-specific document ID
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  content TEXT, -- Full document text
  published_date TIMESTAMPTZ,
  ingested_at TIMESTAMPTZ DEFAULT NOW(),
  content_hash VARCHAR(64), -- SHA-256 for deduplication
  metadata JSONB, -- Source-specific metadata
  embedding vector(1536), -- OpenAI embedding for similarity search

  -- Indexes for performance
  CONSTRAINT regulations_source_document_id_unique UNIQUE (source, document_id)
);

-- Classification Results table
-- Stores ML classification output for each document
CREATE TABLE classifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regulation_id UUID NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 5), -- 0-5 BSA/AML relevance
  confidence DECIMAL(3,2) NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  bsa_pillars JSONB, -- Array of relevant BSA Five Pillars
  categories JSONB, -- Detailed classification categories
  classification_reasoning TEXT, -- LLM reasoning for transparency
  model_used VARCHAR(50), -- GPT-4o-mini, GPT-4, etc.
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Ensure one classification per regulation
  CONSTRAINT classifications_regulation_id_unique UNIQUE (regulation_id)
);

-- Gap Analysis table
-- Stores detailed gap analysis for relevant regulations
CREATE TABLE gap_analyses (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  regulation_id UUID NOT NULL REFERENCES regulations(id) ON DELETE CASCADE,
  affected_controls JSONB NOT NULL, -- Array of control framework mappings
  gap_severity gap_severity_enum NOT NULL,
  remediation_effort_hours INTEGER CHECK (remediation_effort_hours > 0),
  similar_implementations JSONB, -- References to similar past implementations
  analysis_summary TEXT NOT NULL,
  recommendations JSONB, -- Structured action items
  model_used VARCHAR(50),
  created_at TIMESTAMPTZ DEFAULT NOW(),

  -- Ensure one gap analysis per regulation
  CONSTRAINT gap_analyses_regulation_id_unique UNIQUE (regulation_id)
);

-- Create indexes for performance
CREATE INDEX idx_regulations_source ON regulations(source);
CREATE INDEX idx_regulations_published_date ON regulations(published_date DESC);
CREATE INDEX idx_regulations_ingested_at ON regulations(ingested_at DESC);
CREATE INDEX idx_regulations_content_hash ON regulations(content_hash);
CREATE INDEX idx_regulations_embedding ON regulations USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX idx_classifications_relevance_score ON classifications(relevance_score);
CREATE INDEX idx_classifications_confidence ON classifications(confidence DESC);
CREATE INDEX idx_classifications_created_at ON classifications(created_at DESC);

CREATE INDEX idx_gap_analyses_gap_severity ON gap_analyses(gap_severity);
CREATE INDEX idx_gap_analyses_created_at ON gap_analyses(created_at DESC);

-- Create views for common queries
CREATE VIEW recent_regulations AS
SELECT
  r.id,
  r.source,
  r.title,
  r.url,
  r.published_date,
  c.relevance_score,
  c.confidence,
  c.bsa_pillars,
  g.gap_severity,
  g.remediation_effort_hours
FROM regulations r
LEFT JOIN classifications c ON r.id = c.regulation_id
LEFT JOIN gap_analyses g ON r.id = g.regulation_id
WHERE r.published_date >= NOW() - INTERVAL '90 days'
ORDER BY r.published_date DESC;

-- View for high-priority items requiring attention
CREATE VIEW priority_regulations AS
SELECT
  r.id,
  r.source,
  r.title,
  r.url,
  r.published_date,
  c.relevance_score,
  c.confidence,
  g.gap_severity,
  g.remediation_effort_hours
FROM regulations r
JOIN classifications c ON r.id = c.regulation_id
LEFT JOIN gap_analyses g ON r.id = g.regulation_id
WHERE
  (c.relevance_score >= 3 AND c.confidence >= 0.8)
  OR g.gap_severity IN ('high', 'critical')
ORDER BY
  CASE g.gap_severity
    WHEN 'critical' THEN 1
    WHEN 'high' THEN 2
    WHEN 'medium' THEN 3
    ELSE 4
  END,
  c.relevance_score DESC,
  r.published_date DESC;

-- Insert some example data for testing (remove in production)
INSERT INTO regulations (source, document_id, title, url, content, published_date, content_hash) VALUES
('fincen', 'FIN-2024-001', 'Updated Guidance on Digital Asset Transactions', 'https://fincen.gov/example', 'Example content...', '2024-01-15 10:00:00+00', 'abc123'),
('sec', 'SEC-2024-002', 'Staff Accounting Bulletin on Cryptocurrency Holdings', 'https://sec.gov/example', 'Example SEC content...', '2024-01-10 15:30:00+00', 'def456');