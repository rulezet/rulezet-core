"""add bundle_note_tag table (curated tags on bundle notes)

Revision ID: f5b2d8e4c1a9
Revises: e3a7c9d1b5f8
Create Date: 2026-09-24 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5b2d8e4c1a9'
down_revision = 'e3a7c9d1b5f8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'bundle_note_tag',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('note_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['note_id'], ['bundle_note.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('note_id', 'tag_id', name='uq_bundle_note_tag'),
    )
    with op.batch_alter_table('bundle_note_tag', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_bundle_note_tag_note_id'), ['note_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_bundle_note_tag_tag_id'), ['tag_id'], unique=False)


def downgrade():
    with op.batch_alter_table('bundle_note_tag', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bundle_note_tag_tag_id'))
        batch_op.drop_index(batch_op.f('ix_bundle_note_tag_note_id'))
    op.drop_table('bundle_note_tag')
