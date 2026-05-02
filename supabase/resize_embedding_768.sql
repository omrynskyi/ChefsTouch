-- Run ONCE in the Supabase SQL Editor (or via psql) before re-seeding.
--
-- Resizes the recipes.embedding column from vector(1536) to vector(768) to match
-- the nomic-embed-text-v1 model output dimension, then recreates the HNSW index.
--
-- WARNING: existing embeddings are re-cast via text; they will be numerically wrong
-- after the resize.  Re-run seed.py immediately after to replace them.

DROP INDEX IF EXISTS recipes_embedding_idx;

ALTER TABLE recipes
    ALTER COLUMN embedding TYPE extensions.vector(768)
    USING embedding::text::extensions.vector(768);

CREATE INDEX recipes_embedding_idx
    ON recipes
    USING hnsw (embedding extensions.vector_cosine_ops);
