"""Integration tests for simulation and lineup API endpoints."""
from __future__ import annotations

import pytest


async def test_create_simulation_requires_auth(client):
    resp = await client.post("/api/simulations/", json={"season": 2025, "week": 1})
    assert resp.status_code == 401


async def test_create_simulation_and_get_results(client, auth_headers):
    # Create simulation (runs inline in test mode)
    resp = await client.post(
        "/api/simulations/",
        json={"season": 2025, "week": 1, "num_sims": 500, "platform": "draftkings"},
        headers=auth_headers,
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "completed"
    sim_id = data["id"]

    # Get simulation
    resp = await client.get(f"/api/simulations/{sim_id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Get results
    resp = await client.get(f"/api/simulations/{sim_id}/results", headers=auth_headers)
    assert resp.status_code == 200
    results = resp.json()
    assert results["status"] == "completed"
    assert len(results["players"]) > 0
    assert results["lineup_score_avg"] is not None

    # Check player result structure
    player = results["players"][0]
    assert "avg_points" in player
    assert "boom_rate" in player
    assert "bust_rate" in player
    assert player["avg_points"] > 0


async def test_list_simulations(client, auth_headers):
    # Create one
    await client.post(
        "/api/simulations/",
        json={"season": 2025, "week": 1, "num_sims": 500},
        headers=auth_headers,
    )

    resp = await client.get("/api/simulations/", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_delete_simulation(client, auth_headers):
    resp = await client.post(
        "/api/simulations/",
        json={"season": 2025, "week": 1, "num_sims": 500},
        headers=auth_headers,
    )
    sim_id = resp.json()["id"]

    resp = await client.delete(f"/api/simulations/{sim_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = await client.get(f"/api/simulations/{sim_id}", headers=auth_headers)
    assert resp.status_code == 404


async def test_optimize_lineups(client, auth_headers):
    resp = await client.post(
        "/api/lineups/optimize",
        json={"season": 2025, "week": 1, "num_lineups": 3, "platform": "draftkings"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    lineups = resp.json()
    assert len(lineups) >= 1

    lu = lineups[0]
    assert lu["total_salary"] <= 50000
    assert len(lu["players"]) == 9
    assert lu["total_projected"] > 0


async def test_optimize_lineups_requires_auth(client):
    resp = await client.post(
        "/api/lineups/optimize",
        json={"season": 2025, "week": 1, "num_lineups": 1},
    )
    assert resp.status_code == 401


async def test_sim_player_distributions_reasonable(client, auth_headers):
    """Sim results should have bell-curve-ish distributions."""
    resp = await client.post(
        "/api/simulations/",
        json={"season": 2025, "week": 1, "num_sims": 1000},
        headers=auth_headers,
    )
    sim_id = resp.json()["id"]

    resp = await client.get(f"/api/simulations/{sim_id}/results", headers=auth_headers)
    results = resp.json()

    for player in results["players"]:
        # Floor should be less than avg which is less than ceiling
        assert player["floor"] <= player["avg_points"] + 0.5
        assert player["avg_points"] <= player["ceiling"] + 0.5
        # Std dev should be positive
        assert player["std_dev"] > 0
        # Boom + bust shouldn't be 100%
        assert player["boom_rate"] + player["bust_rate"] < 100
