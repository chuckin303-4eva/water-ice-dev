"""Phase 1 core schema: identity/access, geography, brands, host
businesses, and locations.

Revision ID: 0001
Revises:
Create Date: 2026-07-28

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("code", name="uq_states_code"),
    )

    op.create_table(
        "counties",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
        sa.Column("fips_code", sa.String(length=5), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("fips_code", name="uq_counties_fips_code"),
        sa.UniqueConstraint("state_id", "name", name="uq_counties_state_name"),
    )
    op.create_index("ix_counties_state_id", "counties", ["state_id"])

    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
        sa.Column("county_id", sa.Integer(), sa.ForeignKey("counties.id"), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_cities_state_id", "cities", ["state_id"])
    op.create_index("ix_cities_county_id", "cities", ["county_id"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=False
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
    )
    op.create_index("ix_roles_organization_id", "roles", ["organization_id"])

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.UniqueConstraint("slug", name="uq_permissions_slug"),
    )

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column(
            "permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True
        ),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
    )

    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id", sa.Integer(), sa.ForeignKey("organizations.id"), nullable=True
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_brands_organization_id", "brands", ["organization_id"])

    op.create_table(
        "host_businesses",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("state_id", sa.Integer(), sa.ForeignKey("states.id"), nullable=False),
        sa.Column("county_id", sa.Integer(), sa.ForeignKey("counties.id"), nullable=False),
        sa.Column("city_id", sa.Integer(), sa.ForeignKey("cities.id"), nullable=False),
        sa.Column("zip_code", sa.String(length=10), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=False),
        sa.Column("brand_id", sa.Uuid(as_uuid=True), sa.ForeignKey("brands.id"), nullable=True),
        sa.Column("serves_ice", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("serves_water", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("machine_type", sa.String(length=100), nullable=True),
        sa.Column(
            "host_business_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("host_businesses.id"),
            nullable=True,
        ),
        sa.Column("is_inside", sa.Boolean(), nullable=True),
        sa.Column("visibility_rating", sa.Integer(), nullable=True),
        sa.Column("traffic_score", sa.Numeric(10, 2), nullable=True),
        sa.Column("population", sa.Integer(), nullable=True),
        sa.Column("median_income", sa.Numeric(12, 2), nullable=True),
        sa.Column("growth_rate", sa.Numeric(6, 3), nullable=True),
        sa.Column("competition_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("opportunity_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("confidence_score", sa.Numeric(6, 3), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="prospect"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_source", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
    )
    op.create_index("ix_locations_state_id", "locations", ["state_id"])
    op.create_index("ix_locations_county_id", "locations", ["county_id"])
    op.create_index("ix_locations_city_id", "locations", ["city_id"])
    op.create_index("ix_locations_zip_code", "locations", ["zip_code"])
    op.create_index("ix_locations_latitude", "locations", ["latitude"])
    op.create_index("ix_locations_longitude", "locations", ["longitude"])
    op.create_index("ix_locations_brand_id", "locations", ["brand_id"])
    op.create_index("ix_locations_host_business_id", "locations", ["host_business_id"])
    op.create_index("ix_locations_status", "locations", ["status"])


def downgrade() -> None:
    op.drop_table("locations")
    op.drop_table("host_businesses")
    op.drop_table("brands")
    op.drop_table("user_roles")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("cities")
    op.drop_table("counties")
    op.drop_table("states")
    op.drop_table("organizations")
