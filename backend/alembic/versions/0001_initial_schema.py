"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-03-10
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tier", sa.String(20), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True),
        sa.Column("trial_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Players
    op.create_table(
        "players",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("external_id", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("team", sa.String(5), nullable=False),
        sa.Column("position", sa.String(5), nullable=False),
        sa.Column("salary", sa.Integer(), nullable=True),
        sa.Column("ownership", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_players_external_id", "players", ["external_id"], unique=True)
    op.create_index("ix_players_season_week_position", "players", ["season", "week", "position"])

    # Projections
    op.create_table(
        "projections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="model"),
        sa.Column("projected_points", sa.Float(), nullable=False),
        sa.Column("floor", sa.Float(), nullable=True),
        sa.Column("ceiling", sa.Float(), nullable=True),
        sa.Column("std_dev", sa.Float(), nullable=True),
        sa.Column("pass_yds", sa.Float(), nullable=True),
        sa.Column("pass_tds", sa.Float(), nullable=True),
        sa.Column("rush_yds", sa.Float(), nullable=True),
        sa.Column("rush_tds", sa.Float(), nullable=True),
        sa.Column("rec", sa.Float(), nullable=True),
        sa.Column("rec_yds", sa.Float(), nullable=True),
        sa.Column("rec_tds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_projections_player_id", "projections", ["player_id"])
    op.create_index("ix_projections_player_season_week", "projections", ["player_id", "season", "week"])
    op.create_index("ix_projections_season_week_source", "projections", ["season", "week", "source"])

    # Simulation Runs
    op.create_table(
        "sim_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("num_sims", sa.Integer(), nullable=False, server_default=sa.text("10000")),
        sa.Column("platform", sa.String(20), nullable=False, server_default="draftkings"),
        sa.Column("contest_type", sa.String(20), nullable=False, server_default="gpp"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("results_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sim_runs_user_id", "sim_runs", ["user_id"])
    op.create_index("ix_sim_runs_user_season_week", "sim_runs", ["user_id", "season", "week"])

    # Simulation Results
    op.create_table(
        "sim_results",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sim_run_id", sa.String(36), sa.ForeignKey("sim_runs.id"), nullable=False),
        sa.Column("player_id", sa.String(36), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("avg_points", sa.Float(), nullable=False),
        sa.Column("median_points", sa.Float(), nullable=False),
        sa.Column("std_dev", sa.Float(), nullable=False),
        sa.Column("floor", sa.Float(), nullable=False),
        sa.Column("ceiling", sa.Float(), nullable=False),
        sa.Column("percentile_25", sa.Float(), nullable=True),
        sa.Column("percentile_75", sa.Float(), nullable=True),
        sa.Column("optimal_rate", sa.Float(), nullable=True),
    )
    op.create_index("ix_sim_results_sim_run_id", "sim_results", ["sim_run_id"])
    op.create_index("ix_sim_results_run_player", "sim_results", ["sim_run_id", "player_id"])


def downgrade() -> None:
    op.drop_table("sim_results")
    op.drop_table("sim_runs")
    op.drop_table("projections")
    op.drop_table("players")
    op.drop_table("users")
