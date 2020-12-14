"""Modify oauth2_token for authlib

Revision ID: 4c21d127611f
Revises: 0e18bc284f12
Create Date: 2020-12-11 13:16:35.898085

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4c21d127611f'
down_revision = '0e18bc284f12'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic; adjusted ###
    op.execute('delete from oauth2_token')
    op.add_column('oauth2_token', sa.Column('client_id', sa.String(), nullable=False))
    op.add_column('oauth2_token', sa.Column('token_type', sa.String(), nullable=True))
    op.add_column('oauth2_token', sa.Column('access_token', sa.String(), nullable=True))
    op.add_column('oauth2_token', sa.Column('refresh_token', sa.String(), nullable=True))
    op.add_column('oauth2_token', sa.Column('id_token', sa.String(), nullable=True))
    op.add_column('oauth2_token', sa.Column('expires_at', sa.Integer(), nullable=True))
    op.drop_index('ix_oauth2_token_provider', table_name='oauth2_token')
    op.drop_constraint('oauth2_token_provider_user_id_key', 'oauth2_token', type_='unique')
    op.create_unique_constraint('oauth2_token_client_id_user_id_key', 'oauth2_token', ['client_id', 'user_id'])
    op.drop_column('oauth2_token', 'provider')
    op.drop_column('oauth2_token', 'token')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic; adjusted ###
    op.execute('delete from oauth2_token')
    op.add_column('oauth2_token', sa.Column('token', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=False))
    op.add_column('oauth2_token', sa.Column('provider', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_constraint('oauth2_token_client_id_user_id_key', 'oauth2_token', type_='unique')
    op.create_unique_constraint('oauth2_token_provider_user_id_key', 'oauth2_token', ['provider', 'user_id'])
    op.create_index('ix_oauth2_token_provider', 'oauth2_token', ['provider'], unique=False)
    op.drop_column('oauth2_token', 'token_type')
    op.drop_column('oauth2_token', 'refresh_token')
    op.drop_column('oauth2_token', 'id_token')
    op.drop_column('oauth2_token', 'expires_at')
    op.drop_column('oauth2_token', 'client_id')
    op.drop_column('oauth2_token', 'access_token')
    # ### end Alembic commands ###
