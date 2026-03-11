from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_get_projections_auto_generates(client):
    """GET /api/projections auto-generates projections from mock data."""
    response = await client.get("/api/projections/?season=2025&week=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    first = data[0]
    assert "name" in first
    assert "projected_points" in first
    assert first["projected_points"] > 0


@pytest.mark.asyncio
async def test_projections_filter_by_position(client):
    # Seed data
    await client.get("/api/projections/?season=2025&week=1")
    # Filter to QB only
    response = await client.get("/api/projections/?season=2025&week=1&position=QB")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(p["position"] == "QB" for p in data)


@pytest.mark.asyncio
async def test_projections_sorted_by_points(client):
    response = await client.get("/api/projections/?season=2025&week=1&sort=projected_points")
    assert response.status_code == 200
    data = response.json()
    pts = [p["projected_points"] for p in data]
    assert pts == sorted(pts, reverse=True)


@pytest.mark.asyncio
async def test_projections_free_tier_no_floor_ceiling(client):
    """Free users should not see floor/ceiling/value."""
    response = await client.get("/api/projections/?season=2025&week=1")
    assert response.status_code == 200
    data = response.json()
    for p in data:
        assert p["floor"] is None
        assert p["ceiling"] is None
        assert p["value"] is None


@pytest.mark.asyncio
async def test_projections_pro_tier_has_floor_ceiling(client, auth_headers):
    """Authenticated (trial=pro) users should see floor/ceiling."""
    response = await client.get("/api/projections/?season=2025&week=1", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    has_floor = any(p["floor"] is not None for p in data)
    assert has_floor


@pytest.mark.asyncio
async def test_get_player_projection(client):
    # Get a player ID from the list
    resp = await client.get("/api/projections/?season=2025&week=1")
    data = resp.json()
    assert len(data) > 0
    player_id = data[0]["id"]
    # Fetch individual projection
    resp2 = await client.get(f"/api/projections/{player_id}?season=2025&week=1")
    assert resp2.status_code == 200
    proj = resp2.json()
    assert proj["projected_points"] > 0


@pytest.mark.asyncio
async def test_get_player_projection_not_found(client):
    resp = await client.get("/api/projections/nonexistent?season=2025&week=1")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_projection_values_reasonable(client):
    """QB projections should be roughly 15-30 pts, RB 10-25."""
    resp = await client.get("/api/projections/?season=2025&week=1&position=QB")
    data = resp.json()
    for p in data:
        assert 5.0 <= p["projected_points"] <= 40.0, f"QB {p['name']} has unreasonable projection: {p['projected_points']}"
    resp2 = await client.get("/api/projections/?season=2025&week=1&position=RB")
    data2 = resp2.json()
    for p in data2:
        assert 2.0 <= p["projected_points"] <= 35.0, f"RB {p['name']} has unreasonable projection: {p['projected_points']}"
