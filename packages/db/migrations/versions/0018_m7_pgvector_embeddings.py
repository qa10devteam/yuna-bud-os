"""M7: pgvector embeddings + doc_chunks + chat_session + mv + ai_feedback.

Revision ID: 0018_m7
Revises: 0017_perf_indexes_buyer_name
Create Date: 2026-07-13
"""
from alembic import op
import sqlalchemy as sa

revision = "0018_m7"
down_revision = "0017_perf_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector already installed as extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Embedding columns on tender and analysis (384-dim for multilingual-MiniLM)
    op.execute("ALTER TABLE tender ADD COLUMN IF NOT EXISTS embedding vector(384)")
    op.execute("ALTER TABLE analysis ADD COLUMN IF NOT EXISTS embedding vector(384)")

    # HNSW indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS tender_embedding_hnsw_idx
        ON tender USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS analysis_embedding_hnsw_idx
        ON analysis USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)
    """)

    # doc_chunks table for RAG
    op.execute("""
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tender_id uuid REFERENCES tender(id) ON DELETE CASCADE,
            source_type text DEFAULT 'bzp_document',
            source_id uuid,
            chunk_idx integer NOT NULL,
            text text NOT NULL,
            embedding vector(384),
            metadata jsonb DEFAULT '{}',
            created_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS doc_chunks_tender_idx ON doc_chunks(tender_id)")
    op.execute("""
        CREATE INDEX IF NOT EXISTS doc_chunks_embedding_hnsw_idx
        ON doc_chunks USING hnsw (embedding vector_cosine_ops)
        WITH (m=16, ef_construction=64)
    """)

    # chat_session table for multi-turn chat
    op.execute("""
        CREATE TABLE IF NOT EXISTS chat_session (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL,
            page_context text,
            tender_id uuid REFERENCES tender(id) ON DELETE SET NULL,
            messages jsonb NOT NULL DEFAULT '[]',
            summary text,
            created_at timestamptz DEFAULT now(),
            updated_at timestamptz DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS chat_session_tenant_idx ON chat_session(tenant_id, updated_at DESC)")

    # ai_feedback table
    op.execute("""
        CREATE TABLE IF NOT EXISTS ai_feedback (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id uuid NOT NULL,
            agent_run_id uuid,
            tender_id uuid,
            rating smallint CHECK (rating BETWEEN 1 AND 5),
            comment text,
            created_at timestamptz DEFAULT now()
        )
    """)

    # Materialized Views
    # MV 1: Pipeline KPI (enum: new/matched/watching/analyzing/estimated/decided_go/decided_nogo/archived)
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_pipeline_kpi AS
        SELECT
            tenant_id,
            COUNT(*) FILTER (WHERE status != 'new') as active_count,
            SUM(value_pln) FILTER (WHERE status NOT IN ('new','archived','decided_nogo')) as pipeline_value,
            COUNT(*) FILTER (WHERE status = 'decided_go' AND created_at >= NOW() - INTERVAL '30 days') as won_mtd,
            COUNT(*) FILTER (WHERE status IN ('decided_go','decided_nogo') AND created_at >= NOW() - INTERVAL '30 days') as decided_mtd,
            AVG(value_pln) FILTER (WHERE status = 'decided_go') as avg_deal_size,
            SUM(value_pln) FILTER (WHERE status = 'decided_go') as total_won_value
        FROM tender
        GROUP BY tenant_id
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS mv_pipeline_kpi_tenant_idx ON mv_pipeline_kpi(tenant_id)")

    # MV 2: CPV Heatmap
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_cpv_heatmap AS
        SELECT
            LEFT(cpv_code, 5) as cpv5,
            voivodeship,
            COUNT(*) as tender_count,
            AVG(value_pln) as avg_value,
            SUM(value_pln) as total_value
        FROM tender, LATERAL UNNEST(cpv) as cpv_code
        WHERE published_at >= NOW() - INTERVAL '2 years'
        GROUP BY cpv5, voivodeship
    """)
    op.execute("CREATE INDEX IF NOT EXISTS mv_cpv_heatmap_cpv5_idx ON mv_cpv_heatmap(cpv5)")
    op.execute("CREATE INDEX IF NOT EXISTS mv_cpv_heatmap_voiv_idx ON mv_cpv_heatmap(voivodeship)")

    # MV 3: Market Forecast
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_market_forecast AS
        SELECT
            DATE_TRUNC('month', published_at) as month,
            LEFT(cpv_code, 5) as cpv5,
            COUNT(*) as tender_count,
            SUM(value_pln) as total_value,
            AVG(value_pln) as avg_value
        FROM tender, LATERAL UNNEST(cpv) as cpv_code
        WHERE published_at IS NOT NULL
        GROUP BY month, cpv5
        ORDER BY month
    """)
    op.execute("CREATE INDEX IF NOT EXISTS mv_market_forecast_cpv5_idx ON mv_market_forecast(cpv5)")
    op.execute("CREATE INDEX IF NOT EXISTS mv_market_forecast_month_idx ON mv_market_forecast(month)")


def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_market_forecast")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_cpv_heatmap")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_pipeline_kpi")
    op.execute("DROP TABLE IF EXISTS ai_feedback")
    op.execute("DROP TABLE IF EXISTS chat_session")
    op.execute("DROP TABLE IF EXISTS doc_chunks")
    op.execute("ALTER TABLE analysis DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE tender DROP COLUMN IF EXISTS embedding")
