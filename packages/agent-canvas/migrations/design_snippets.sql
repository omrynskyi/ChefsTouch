-- Design snippets table for agent-canvas CSS class vector index.
-- Embedding dimension: 384 (all-MiniLM-L6-v2, local CPU, no API key required)
-- To use OpenAI embeddings instead, change 384 → 1536 everywhere in this file.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS design_snippets (
    id          uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    name        text        NOT NULL UNIQUE,   -- CSS class name or data-component declaration
    description text        NOT NULL,
    tags        text[]      DEFAULT '{}',
    example     text,
    content     text        NOT NULL,          -- full string that was embedded
    embedding   vector(384),
    created_at  timestamptz DEFAULT now()
);

-- HNSW index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS design_snippets_embedding_idx
    ON design_snippets
    USING hnsw (embedding vector_cosine_ops);

-- RPC used by SupabaseCSSRetriever
CREATE OR REPLACE FUNCTION match_design_snippets(
    query_embedding vector(384),
    match_count     int DEFAULT 10
)
RETURNS TABLE (
    id         uuid,
    name       text,
    content    text,
    similarity float
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        name,
        content,
        1 - (embedding <=> query_embedding) AS similarity
    FROM design_snippets
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
