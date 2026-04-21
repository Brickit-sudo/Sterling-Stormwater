"""crm expansion — leads, service_items, quotes, invoices

Revision ID: crm_expansion_001
Revises: 85b6912926cd
Create Date: 2026-04-20 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'crm_expansion_001'
down_revision: Union[str, None] = '85b6912926cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('leads',
        sa.Column('lead_id', sa.UUID(), nullable=False),
        sa.Column('company_name', sa.String(), nullable=False),
        sa.Column('site_description', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=True),
        sa.Column('state', sa.String(), nullable=True),
        sa.Column('zip', sa.String(), nullable=True),
        sa.Column('property_type', sa.String(), nullable=True),
        sa.Column('managing_company', sa.String(), nullable=True),
        sa.Column('contact_name', sa.String(), nullable=True),
        sa.Column('contact_role', sa.String(), nullable=True),
        sa.Column('contact_email', sa.String(), nullable=True),
        sa.Column('contact_phone', sa.String(), nullable=True),
        sa.Column('decision_maker_type', sa.String(), nullable=True),
        sa.Column('compliance_type', sa.String(), nullable=True),
        sa.Column('observed_bmps', sa.Text(), nullable=True),
        sa.Column('permit_indicator', sa.String(), nullable=True),
        sa.Column('source_1', sa.String(), nullable=True),
        sa.Column('source_2', sa.String(), nullable=True),
        sa.Column('lead_priority', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('notes_for_outreach', sa.Text(), nullable=True),
        sa.Column('last_verified_date', sa.Date(), nullable=True),
        sa.Column('converted_client_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('lead_id'),
    )
    op.create_index('ix_leads_company_name', 'leads', ['company_name'], unique=False)
    op.create_index('ix_leads_converted_client_id', 'leads', ['converted_client_id'], unique=False)

    op.create_table('service_items',
        sa.Column('service_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_unit_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('unit', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('service_id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('ix_service_items_name', 'service_items', ['name'], unique=True)

    op.create_table('quotes',
        sa.Column('quote_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('quote_number', sa.String(), nullable=True),
        sa.Column('quote_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('sent_date', sa.Date(), nullable=True),
        sa.Column('accepted_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('contract_number', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('quote_id'),
        sa.UniqueConstraint('quote_number'),
    )
    op.create_index('ix_quotes_site_id', 'quotes', ['site_id'], unique=False)
    op.create_index('ix_quotes_client_id', 'quotes', ['client_id'], unique=False)
    op.create_index('ix_quotes_quote_number', 'quotes', ['quote_number'], unique=True)

    op.create_table('quote_line_items',
        sa.Column('line_item_id', sa.UUID(), nullable=False),
        sa.Column('quote_id', sa.UUID(), nullable=False),
        sa.Column('service_item_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 3), nullable=True),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.quote_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_item_id'], ['service_items.service_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('line_item_id'),
    )
    op.create_index('ix_quote_line_items_quote_id', 'quote_line_items', ['quote_id'], unique=False)

    op.create_table('invoices',
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('client_id', sa.UUID(), nullable=False),
        sa.Column('quote_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('invoice_number', sa.String(), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('invoice_total', sa.Numeric(10, 2), nullable=True),
        sa.Column('balance_due', sa.Numeric(10, 2), nullable=True),
        sa.Column('contract_number', sa.String(), nullable=True),
        sa.Column('po_number', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.client_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['quote_id'], ['quotes.quote_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['site_id'], ['sites.site_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('invoice_id'),
        sa.UniqueConstraint('invoice_number'),
    )
    op.create_index('ix_invoices_site_id', 'invoices', ['site_id'], unique=False)
    op.create_index('ix_invoices_client_id', 'invoices', ['client_id'], unique=False)
    op.create_index('ix_invoices_invoice_number', 'invoices', ['invoice_number'], unique=True)

    op.create_table('invoice_line_items',
        sa.Column('line_item_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('service_item_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 3), nullable=True),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('completion_date', sa.Date(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.invoice_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_item_id'], ['service_items.service_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('line_item_id'),
    )
    op.create_index('ix_invoice_line_items_invoice_id', 'invoice_line_items', ['invoice_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_invoice_line_items_invoice_id', table_name='invoice_line_items')
    op.drop_table('invoice_line_items')
    op.drop_index('ix_invoices_invoice_number', table_name='invoices')
    op.drop_index('ix_invoices_client_id', table_name='invoices')
    op.drop_index('ix_invoices_site_id', table_name='invoices')
    op.drop_table('invoices')
    op.drop_index('ix_quote_line_items_quote_id', table_name='quote_line_items')
    op.drop_table('quote_line_items')
    op.drop_index('ix_quotes_quote_number', table_name='quotes')
    op.drop_index('ix_quotes_client_id', table_name='quotes')
    op.drop_index('ix_quotes_site_id', table_name='quotes')
    op.drop_table('quotes')
    op.drop_index('ix_service_items_name', table_name='service_items')
    op.drop_table('service_items')
    op.drop_index('ix_leads_converted_client_id', table_name='leads')
    op.drop_index('ix_leads_company_name', table_name='leads')
    op.drop_table('leads')
