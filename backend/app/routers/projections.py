from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_effective_tier
from app.models.player import Player
from app.models.projection import Projection
from app.models.user import User
from app.schemas.player import PlayerWithProjection, ProjectionResponse
from app.services.auth_service import AuthService
from app.services.projection_engine import ProjectionEngine

router = APIRouter()

DEFAULT_SEASON = 2025
DEFAULT_WEEK = 1
FREE_LIMIT_PER_POSITION = 20


async def _optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> Optional[User]:
    """Extract user from Bearer token if present, otherwise return None."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1]
    payload = AuthService.verify_token(token)
    if not payload:
        return None
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.get("/", response_model=List[PlayerWithProjection])
async def get_projections(
    season: int = Query(DEFAULT_SEASON),
    week: int = Query(DEFAULT_WEEK),
    position: Optional[str] = Query(None),
    sort: str = Query("projected_points"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(_optional_user),
):
    """Player projections with tier-based access control.

    Free: top 20 per position, no ceiling/floor/value.
    Pro+: full list with ceiling/floor/value.
    Elite: includes ownership projections.
    """
    tier = get_effective_tier(user) if user else "free"

    # Auto-generate projections if none exist
    exists_q = select(Projection.id).where(
        Projection.season == season, Projection.week == week
    ).limit(1)
    if not (await db.execute(exists_q)).scalar_one_or_none():
        engine = ProjectionEngine(db)
        await engine.generate_projections(season, week)

    # Join players with projections
    stmt = (
        select(Player, Projection)
        .outerjoin(
            Projection,
            (Player.id == Projection.player_id)
            & (Projection.season == season)
            & (Projection.week == week),
        )
        .where(Player.season == season, Player.week == week)
    )
    if position and position.upper() != "ALL":
        stmt = stmt.where(Player.position == position.upper())

    sort_map = {
        "projected_points": Projection.projected_points,
        "salary": Player.salary,
        "ceiling": Projection.ceiling,
        "floor": Projection.floor,
        "name": Player.name,
    }
    order_col = sort_map.get(sort, Projection.projected_points)
    if sort == "name":
        stmt = stmt.order_by(order_col.asc())
    else:
        stmt = stmt.order_by(order_col.desc().nullslast())

    rows = (await db.execute(stmt)).all()

    results: List[PlayerWithProjection] = []
    pos_counts: dict = {}
    for player, proj in rows:
        pos = player.position
        if tier == "free":
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
            if pos_counts[pos] > FREE_LIMIT_PER_POSITION:
                continue

        salary = player.salary or 0
        pts = proj.projected_points if proj else 0.0
        value = round(pts / (salary / 1000), 2) if salary and pts else None

        results.append(PlayerWithProjection(
            id=player.id,
            name=player.name,
            team=player.team,
            position=pos,
            salary=player.salary,
            projected_points=pts,
            floor=proj.floor if proj and tier in ("pro", "elite") else None,
            ceiling=proj.ceiling if proj and tier in ("pro", "elite") else None,
            std_dev=proj.std_dev if proj and tier in ("pro", "elite") else None,
            ownership=player.ownership if tier == "elite" else None,
            value=value if tier in ("pro", "elite") else None,
            pass_yds=proj.pass_yds if proj else None,
            pass_tds=proj.pass_tds if proj else None,
            rush_yds=proj.rush_yds if proj else None,
            rush_tds=proj.rush_tds if proj else None,
            rec=proj.rec if proj else None,
            rec_yds=proj.rec_yds if proj else None,
            rec_tds=proj.rec_tds if proj else None,
        ))

    return results


@router.get("/compare")
async def compare_players(
    players: str = Query(..., description="Comma-separated player IDs"),
    season: int = Query(DEFAULT_SEASON),
    week: int = Query(DEFAULT_WEEK),
    db: AsyncSession = Depends(get_db),
):
    player_ids = [pid.strip() for pid in players.split(",") if pid.strip()]
    if len(player_ids) > 5:
        raise HTTPException(status_code=400, detail="Max 5 players for comparison")
    out = []
    for pid in player_ids:
        stmt = (
            select(Player, Projection)
            .outerjoin(Projection, (Player.id == Projection.player_id)
                       & (Projection.season == season)
                       & (Projection.week == week))
            .where(Player.id == pid)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            continue
        p, pr = row
        out.append({
            "id": p.id, "name": p.name, "team": p.team,
            "position": p.position, "salary": p.salary,
            "projected_points": pr.projected_points if pr else 0,
            "floor": pr.floor if pr else None,
            "ceiling": pr.ceiling if pr else None,
        })
    return out


@router.get("/{player_id}", response_model=ProjectionResponse)
async def get_player_projection(
    player_id: str,
    season: int = Query(DEFAULT_SEASON),
    week: int = Query(DEFAULT_WEEK),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Projection).where(
        Projection.player_id == player_id,
        Projection.season == season,
        Projection.week == week,
    )
    proj = (await db.execute(stmt)).scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Projection not found")
    return proj
