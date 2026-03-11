import numpy as np
import pytest

from app.services.projection_engine import ProjectionEngine
from app.services.simulator import Simulator
from app.services.optimizer import LineupOptimizer


def test_calculate_distribution():
    result = ProjectionEngine.calculate_distribution(mean=15.0, std_dev=5.0, n_samples=50000)
    assert abs(result["mean"] - 15.0) < 1.0
    assert result["floor"] < result["median"] < result["ceiling"]
    assert result["p25"] < result["p75"]


def test_correlated_sample_shape():
    means = np.array([15.0, 10.0, 8.0])
    std_devs = np.array([5.0, 3.0, 4.0])
    corr = np.eye(3)
    samples = Simulator.correlated_sample(means, std_devs, corr, n_sims=1000)
    assert samples.shape == (1000, 3)
    assert np.all(samples >= 0)


def test_correlation_matrix_positive_semidefinite():
    """Verify the correlation matrix produced is valid (PSD)."""
    players = [
        {"team": "BUF", "position": "QB", "opponent": "MIA"},
        {"team": "BUF", "position": "WR", "opponent": "MIA"},
        {"team": "BUF", "position": "RB", "opponent": "MIA"},
        {"team": "MIA", "position": "DST", "opponent": "BUF"},
        {"team": "KC", "position": "QB", "opponent": "DEN"},
    ]
    sim = Simulator.__new__(Simulator)
    corr = sim._build_correlation_matrix(players)

    assert corr.shape == (5, 5)
    # Diagonal must be 1
    np.testing.assert_allclose(np.diag(corr), 1.0, atol=0.01)
    # Must be positive semi-definite
    eigvals = np.linalg.eigvalsh(corr)
    assert np.all(eigvals >= -1e-6)


def test_pair_correlations():
    """Check specific pair correlations are sensible."""
    # QB-WR same team: high positive
    rho = Simulator._pair_correlation(
        {"team": "BUF", "position": "QB", "opponent": "MIA"},
        {"team": "BUF", "position": "WR", "opponent": "MIA"},
    )
    assert rho > 0.3

    # QB-DST opposing: negative
    rho = Simulator._pair_correlation(
        {"team": "BUF", "position": "QB", "opponent": "MIA"},
        {"team": "MIA", "position": "DST", "opponent": "BUF"},
    )
    assert rho < -0.2

    # Different game: zero
    rho = Simulator._pair_correlation(
        {"team": "BUF", "position": "QB", "opponent": "MIA"},
        {"team": "KC", "position": "WR", "opponent": "DEN"},
    )
    assert rho == 0.0


def test_optimizer_salary_cap():
    """Optimizer must respect salary cap."""
    players = []
    for i in range(30):
        pos = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "DST"][i % 8]
        players.append({
            "id": f"p{i}",
            "name": f"Player {i}",
            "position": pos,
            "team": f"T{i % 5}",
            "salary": 5000 + (i * 100),
            "projected_points": 10.0 + (i * 0.5),
            "floor": 7.0,
            "ceiling": 15.0,
            "ownership": 10.0,
        })

    opt = LineupOptimizer(platform="draftkings", contest_type="gpp")
    lineups = opt.optimize(players, num_lineups=3, salary_cap=50000)

    assert len(lineups) >= 1
    for lu in lineups:
        assert lu["total_salary"] <= 50000
        assert len(lu["players"]) == 9


def test_optimizer_position_constraints():
    """Optimizer must produce valid position counts."""
    players = []
    positions = ["QB"] * 4 + ["RB"] * 8 + ["WR"] * 10 + ["TE"] * 5 + ["DST"] * 4
    for i, pos in enumerate(positions):
        players.append({
            "id": f"p{i}",
            "name": f"Player {i}",
            "position": pos,
            "team": f"T{i % 8}",
            "salary": 4000 + (i * 100),
            "projected_points": 8.0 + (i * 0.3),
            "floor": 5.0,
            "ceiling": 12.0,
            "ownership": 10.0,
        })

    opt = LineupOptimizer(platform="draftkings", contest_type="gpp")
    lineups = opt.optimize(players, num_lineups=1)

    assert len(lineups) == 1
    lu = lineups[0]
    pos_counts = {}
    for p in lu["players"]:
        pos_counts[p["position"]] = pos_counts.get(p["position"], 0) + 1

    assert pos_counts.get("QB", 0) == 1
    assert pos_counts.get("DST", 0) == 1
    # RB: 2-3 (2 required + flex), WR: 3-4, TE: 1-2
    assert pos_counts.get("RB", 0) >= 2
    assert pos_counts.get("WR", 0) >= 3
    assert pos_counts.get("TE", 0) >= 1


def test_optimizer_csv_export():
    """CSV export produces correct header and row format."""
    players = []
    positions = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "RB", "DST"]
    for i, pos in enumerate(positions):
        players.append({
            "id": f"p{i}",
            "external_id": f"EXT{i}",
            "name": f"Player {i}",
            "position": pos,
            "team": f"T{i % 4}",
            "salary": 5000,
            "projected_points": 10.0,
            "floor": 7.0,
            "ceiling": 13.0,
            "ownership": 10.0,
        })

    opt = LineupOptimizer(platform="draftkings", contest_type="gpp")
    lineups = opt.optimize(players, num_lineups=1, salary_cap=50000)
    csv = opt.export_csv(lineups)

    lines = csv.strip().splitlines()
    assert lines[0].strip() == "QB,RB,RB,WR,WR,WR,TE,FLEX,DST"
    assert len(lines) >= 2  # header + at least 1 lineup


def test_optimizer_diversity():
    """Multiple lineups must differ by at least 3 players."""
    players = []
    positions = ["QB"] * 3 + ["RB"] * 8 + ["WR"] * 10 + ["TE"] * 5 + ["DST"] * 4
    for i, pos in enumerate(positions):
        players.append({
            "id": f"p{i}",
            "name": f"Player {i}",
            "position": pos,
            "team": f"T{i % 8}",
            "salary": 4000 + (i * 80),
            "projected_points": 8.0 + (i * 0.2),
            "floor": 5.0,
            "ceiling": 12.0,
            "ownership": 10.0,
        })

    opt = LineupOptimizer(platform="draftkings", contest_type="gpp")
    lineups = opt.optimize(players, num_lineups=5)

    if len(lineups) >= 2:
        for i in range(len(lineups)):
            for j in range(i + 1, len(lineups)):
                ids_i = {p["id"] for p in lineups[i]["players"]}
                ids_j = {p["id"] for p in lineups[j]["players"]}
                overlap = len(ids_i & ids_j)
                assert overlap <= 6, f"Lineups {i} and {j} overlap by {overlap} players"
