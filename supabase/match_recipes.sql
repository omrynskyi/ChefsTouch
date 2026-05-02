-- Run once in the Supabase SQL Editor after resize_embedding_768.sql.
--
-- Creates (or replaces) the match_recipes RPC used by the recipe agent's Phase 1
-- vector search.  Embeddings are 768-dimensional (nomic-embed-text-v1).

CREATE OR REPLACE FUNCTION match_recipes(
    query_embedding extensions.vector(768),
    match_threshold float DEFAULT 0.72,
    match_count     int   DEFAULT 5
)
RETURNS TABLE (
    recipe_id        uuid,
    title            text,
    description      text,
    duration_minutes int,
    servings         int,
    tags             text[],
    steps            jsonb,
    source           text,
    similarity       float
)
LANGUAGE sql STABLE AS $$
    SELECT
        recipe_id,
        title,
        description,
        duration_minutes,
        servings,
        tags,
        steps,
        source,
        1 - (embedding <=> query_embedding) AS similarity
    FROM recipes
    WHERE 1 - (embedding <=> query_embedding) > match_threshold
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;
