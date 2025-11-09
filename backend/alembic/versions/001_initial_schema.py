"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema."""
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Data sources table
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('connection_config', postgresql.JSONB, nullable=False),
        sa.Column('sync_schedule', sa.String(50), nullable=True),
        sa.Column('last_sync_at', sa.DateTime, nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.CheckConstraint("type IN ('postgres', 'mysql', 'sqlserver', 'iceberg', 'delta')", name='ck_data_sources_type'),
        sa.CheckConstraint("status IN ('active', 'error', 'disabled')", name='ck_data_sources_status')
    )
    op.create_index('idx_datasources_type', 'data_sources', ['type'])
    op.create_index('idx_datasources_status', 'data_sources', ['status'])

    # Datasets table
    op.create_table(
        'datasets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fully_qualified_name', sa.String(500), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('schema_name', sa.String(255), nullable=True),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('last_synced_at', sa.DateTime, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.CheckConstraint(
            "type IN ('table', 'view', 'materialized_view', 'iceberg_table', 'delta_table', 'file')",
            name='ck_datasets_type'
        )
    )
    op.create_index('idx_datasets_source', 'datasets', ['data_source_id'])
    op.create_index('idx_datasets_fqn', 'datasets', ['fully_qualified_name'])
    op.create_index('idx_datasets_name', 'datasets', ['name'])
    op.create_index('idx_datasets_type', 'datasets', ['type'])

    # Columns table
    op.create_table(
        'columns',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('data_type', sa.String(100), nullable=True),
        sa.Column('ordinal_position', sa.Integer, nullable=True),
        sa.Column('is_nullable', sa.Boolean, nullable=False, server_default='true'),
        sa.Column('is_primary_key', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('dataset_id', 'name', name='uq_dataset_column')
    )
    op.create_index('idx_columns_dataset', 'columns', ['dataset_id'])
    op.create_index('idx_columns_name', 'columns', ['name'])

    # Transformations table
    op.create_table(
        'transformations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('source_dataset_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False),
        sa.Column('target_dataset_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.Text, nullable=False),
        sa.Column('language', sa.String(50), nullable=False),
        sa.Column('dialect', sa.String(50), nullable=True),
        sa.Column('transformation_type', sa.String(50), nullable=True),
        sa.Column('extracted_from', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['target_dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.CheckConstraint("language IN ('sql', 'python')", name='ck_transformations_language')
    )
    op.create_index('idx_transformations_target', 'transformations', ['target_dataset_id'])
    op.create_index('idx_transformations_language', 'transformations', ['language'])

    # Column lineage table
    op.create_table(
        'column_lineage',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('source_column_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_column_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('transformation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expression', sa.Text, nullable=True),
        sa.Column('confidence', sa.Float, nullable=False, server_default='1.0'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['source_column_id'], ['columns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_column_id'], ['columns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['transformation_id'], ['transformations.id'], ondelete='SET NULL'),
        sa.CheckConstraint('confidence >= 0 AND confidence <= 1', name='ck_lineage_confidence'),
        sa.UniqueConstraint('source_column_id', 'target_column_id', 'transformation_id', name='uq_column_lineage')
    )
    op.create_index('idx_lineage_source', 'column_lineage', ['source_column_id'])
    op.create_index('idx_lineage_target', 'column_lineage', ['target_column_id'])
    op.create_index('idx_lineage_transform', 'column_lineage', ['transformation_id'])

    # Sync jobs table
    op.create_table(
        'sync_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('stats', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ondelete='CASCADE'),
        sa.CheckConstraint("status IN ('running', 'completed', 'failed')", name='ck_syncjobs_status')
    )
    op.create_index('idx_syncjobs_source', 'sync_jobs', ['data_source_id'])
    op.create_index('idx_syncjobs_status', 'sync_jobs', ['status'])
    op.create_index('idx_syncjobs_started', 'sync_jobs', ['started_at'], postgresql_ops={'started_at': 'DESC'})

    # Create updated_at triggers
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)

    for table in ['data_sources', 'datasets', 'columns', 'transformations']:
        op.execute(f"""
            CREATE TRIGGER update_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('sync_jobs')
    op.drop_table('column_lineage')
    op.drop_table('transformations')
    op.drop_table('columns')
    op.drop_table('datasets')
    op.drop_table('data_sources')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
