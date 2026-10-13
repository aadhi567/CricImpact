"""
FastAPI Backend API for Cricket Batter Contribution Analytics.
Visualizes validated Phase 5B and Phase 6A model outputs.
Backend is the SINGLE SOURCE OF TRUTH.
"""

from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.services.data_service import data_service

app = FastAPI(
    title="Cricket Batter Contribution Analytics API",
    description="Backend API serving Phase 5B Contextual Contribution and Phase 6A Season Aggregations.",
    version="1.0.0",
)

# Enable CORS for Vite frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def check_deactivated_competition(request: Request, call_next):
    comp = request.query_params.get("competition")
    if comp and comp.strip().lower() == "smat":
        return JSONResponse(
            status_code=400,
            content={"detail": "Syed Mushtaq Ali Trophy (SMAT) data support is temporarily deactivated due to incomplete match coverage."}
        )
    return await call_next(request)


@app.exception_handler(ValueError)
async def value_error_exception_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "phase": "Phase 6A-Frontend",
        "service": "Cricket Batter Contribution Analytics",
    }


@app.get("/api/competitions")
def list_competitions():
    """Returns available competitions and default selection."""
    return {
        "competitions": data_service.get_competitions(),
        "default_competition": "ipl",
    }


@app.get("/api/seasons")
def list_seasons(
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """Returns available seasons in chronological order with display labels and default season."""
    meta = data_service.get_season_metadata(competition=competition, tournament_type=tournament_type)
    return {
        "seasons": meta["seasons"],
        "season_options": meta["season_options"],
        "default_season": meta["default_season"],
        "total_seasons": len(meta["seasons"]),
        "competition": competition,
        "tournament_type": tournament_type,
    }


@app.get("/api/teams")
def list_teams(
    season: Optional[str] = Query(None, description="Optional season filter"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """Returns teams available, optionally filtered by season and tournament type."""
    teams = data_service.get_teams(season=season, competition=competition, tournament_type=tournament_type)
    return {
        "teams": teams,
        "season": season,
        "total_teams": len(teams),
        "competition": competition,
        "tournament_type": tournament_type,
    }


@app.get("/api/dashboard/summary")
def get_dashboard_summary(
    season: Optional[str] = Query(None, description="Season (e.g. 2024 or 2016)"),
    team: Optional[str] = Query(None, description="Team name"),
    min_runs: int = Query(0, ge=0, description="Minimum runs threshold (e.g. 100, 200, 300)"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """
    Returns dashboard summary cards:
    - Players count
    - Batting innings
    - Average contribution score
    - Total positive contribution
    - Average team contribution share
    """
    return data_service.get_dashboard_summary(
        season=season,
        team=team,
        min_runs=min_runs,
        competition=competition,
        tournament_type=tournament_type,
    )


@app.get("/api/players")
def list_players(
    season: Optional[str] = Query(None, description="Season"),
    team: Optional[str] = Query(None, description="Team"),
    min_runs: int = Query(0, ge=0, description="Minimum actual runs filter"),
    min_innings: int = Query(0, ge=0, description="Minimum batting innings filter"),
    min_balls: int = Query(0, ge=0, description="Minimum balls faced filter"),
    search: Optional[str] = Query(None, description="Search player name"),
    limit: int = Query(500, ge=1, le=2000, description="Max rows to return"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """
    Returns analytical player table records for the season.
    Filters select player subsets without altering underlying contribution metrics.
    """
    players = data_service.get_players(
        season=season,
        team=team,
        min_runs=min_runs,
        min_innings=min_innings,
        min_balls=min_balls,
        search=search,
        limit=limit,
        competition=competition,
        tournament_type=tournament_type,
    )
    return {
        "players": players,
        "count": len(players),
        "season": season,
        "team": team,
        "min_runs": min_runs,
        "competition": competition,
        "tournament_type": tournament_type,
    }


@app.get("/api/player/{player_id}/season/{season:path}")
def get_player_season(
    player_id: str,
    season: str,
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament type filter (e.g. world_cup)"),
):
    """
    Returns detailed player profile for a given season:
    - View A (all-innings metrics)
    - View B (qualified metrics)
    - Contextual breakdown (first innings, chase, powerplay, middle overs, death overs, high pressure)
    """
    rec = data_service.get_player_season(
        player_id=player_id,
        season=season,
        competition=competition,
        tournament_type=tournament_type,
    )
    if not rec:
        raise HTTPException(
            status_code=404,
            detail=f"Player '{player_id}' not found for season '{season}' in {competition}."
        )
    return rec


@app.get("/api/player/{player_id}/matches")
def get_player_matches(
    player_id: str,
    season: str = Query(..., description="Season"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament type filter (e.g. world_cup)"),
):
    """
    Returns all match appearances for a player in a season.
    DNB matches are explicitly marked with is_dnb=True and return contribution_score=null.
    """
    matches = data_service.get_player_matches(
        player_id=player_id,
        season=season,
        competition=competition,
        tournament_type=tournament_type,
    )
    return {
        "player": player_id,
        "season": season,
        "matches": matches,
        "total_appearances": len(matches),
        "batting_innings": sum(1 for m in matches if not m["is_dnb"]),
        "dnb_matches": sum(1 for m in matches if m["is_dnb"]),
        "competition": competition,
        "tournament_type": tournament_type,
    }


@app.get("/api/match/{match_id}/player/{player_id}")
def get_match_detail(
    match_id: str,
    player_id: str,
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
):
    """
    Returns granular match contribution breakdown:
    - Basic performance
    - Match situation & context
    - Phase 7G Context-as-Leverage: P1 Context (Leverage Signal), P2 Performance (50%), P3 State (50%), P4 Diagnostic (0%)
    - Signals-based dynamic explanation
    """
    detail = data_service.get_match_detail(match_id=match_id, player_id=player_id, competition=competition)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"No contribution record found for match {match_id} and player '{player_id}' in {competition}."
        )
    return detail


@app.get("/api/match/{match_id}/player/{player_id}/anchor-analysis")
def get_anchor_analysis(
    match_id: str,
    player_id: str,
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
):
    """
    Returns structured Anchor Innings Analysis:
    - Why is P3 high? (Evidence-backed bullets with Supported/Mixed/Inconclusive labels)
    - Anchor batting profile & phase metrics
    - Partnership dynamics (side-by-side & bowler matchups)
    - P3 component breakdown (z_efs, traj_dev, accel, S_res)
    - Over-by-over timeline with progressive disclosure bullets
    - Final takeaway with attribution caveat
    """
    detail = data_service.get_match_detail(match_id=match_id, player_id=player_id, competition=competition)
    if not detail:
        raise HTTPException(
            status_code=404,
            detail=f"No contribution record found for match {match_id} and player '{player_id}' in {competition}."
        )
    anchor_analysis = detail.get("anchor_analysis")
    if not anchor_analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No anchor innings analysis available for match {match_id} and player '{player_id}'."
        )
    return anchor_analysis


@app.get("/api/charts/scatter")
def get_scatter_data(
    season: Optional[str] = Query(None, description="Season"),
    team: Optional[str] = Query(None, description="Team"),
    player: Optional[str] = Query(None, description="Player"),
    limit: int = Query(1500, ge=10, le=5000),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """
    Returns batting innings points for scatter visualizations:
    - Runs vs Contribution Score
    - Strike Rate vs Contribution Score
    """
    data = data_service.get_innings_scatter(
        season=season,
        team=team,
        player=player,
        limit=limit,
        competition=competition,
        tournament_type=tournament_type,
    )
    return {"points": data, "count": len(data), "competition": competition, "tournament_type": tournament_type}


@app.get("/api/contribution/compare")
def compare_players(
    season: str = Query(..., description="Season to compare batters in (mandatory)"),
    players: str = Query(..., description="Comma-separated player names (min 2, max 5)"),
    view: str = Query("view_a", description="View mode: 'view_a' (primary) or 'view_b' (qualified)"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """
    Phase 7A: Multi-Player Contribution Comparison (Max 5 Players).
    Compares between 2 and 5 batters side-by-side within the same season.
    Consumes pre-computed Phase 5B and Phase 6A metrics without alteration.
    """
    player_list = [p.strip() for p in players.split(",") if p.strip()]
    if len(player_list) < 2:
        raise HTTPException(
            status_code=400,
            detail="Minimum 2 players required for comparison.",
        )
    if len(player_list) > 5:
        raise HTTPException(
            status_code=400,
            detail="Maximum 5 players can be compared.",
        )
    try:
        return data_service.compare_players(
            season=season,
            player_names=player_list,
            view=view,
            competition=competition,
            tournament_type=tournament_type,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except KeyError as ke:
        raise HTTPException(status_code=404, detail=str(ke))


@app.get("/api/matchups/rankings")
def get_matchup_rankings(
    season: Optional[str] = Query(None, description="Optional season filter"),
    team: Optional[str] = Query(None, description="Optional batting team filter"),
    bowling_type: Optional[str] = Query(None, description="'pace', 'spin', or omit for both"),
    min_balls: int = Query(100, ge=0, description="Minimum balls faced (default 100)"),
    min_runs: int = Query(80, ge=0, description="Minimum runs scored (default 80)"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
):
    """
    Returns rankings of top batters against Pace and Spin.
    Eligibility rule: Balls Faced >= min_balls OR Runs >= min_runs.
    Ranked descending by Strike Rate = (Runs / Balls) * 100.
    Separate from Contribution Score.
    """
    return data_service.get_matchup_rankings(
        season=season,
        team=team,
        bowling_type=bowling_type,
        min_balls=min_balls,
        min_runs=min_runs,
        competition=competition,
    )


@app.get("/api/matchups/player/{player_id}")
def get_batter_matchup_detail(
    player_id: str,
    season: Optional[str] = Query(None, description="Optional season filter"),
    team: Optional[str] = Query(None, description="Optional batting team filter"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
):
    """
    Returns matchup breakdown (vs Pace and vs Spin) for a specific batter.
    Includes difference in SR, runs, and balls.
    """
    res = data_service.get_batter_matchup_detail(
        batter=player_id,
        season=season,
        team=team,
        competition=competition,
    )
    if not res:
        raise HTTPException(
            status_code=404,
            detail=f"No bowling matchup data found for batter '{player_id}' in {competition}."
        )
    return res


@app.get("/api/tournaments")
def get_tournaments(
    competition: str = Query("t20i", description="Competition: ipl, t20i"),
):
    """
    Returns list of tournaments/events for a competition.
    Enables dedicated filtering for T20 World Cup, Asia Cup, and other tournaments.
    """
    return data_service.get_tournaments(competition=competition)


@app.get("/api/matches")
def list_matches(
    season: Optional[str] = Query(None, description="Optional season filter"),
    team: Optional[str] = Query(None, description="Optional team filter"),
    opponent: Optional[str] = Query(None, description="Optional opponent filter"),
    tournament: Optional[str] = Query(None, description="Optional tournament filter (e.g. ICC Men's T20 World Cup)"),
    search: Optional[str] = Query(None, description="Search team or venue name"),
    limit: int = Query(200, ge=1, le=1000, description="Max matches to return"),
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
    tournament_type: Optional[str] = Query(None, description="Tournament Type: all, world_cup, asia_cup, bilateral, other"),
):
    """
    Returns list of matches for match-by-match analysis.
    Consumes pre-computed matches data without alteration.
    """
    matches = data_service.get_matches(
        season=season,
        team=team,
        opponent=opponent,
        tournament=tournament,
        search=search,
        limit=limit,
        competition=competition,
        tournament_type=tournament_type,
    )
    return {
        "matches": matches,
        "count": len(matches),
        "season": season,
        "team": team,
        "tournament": tournament,
        "tournament_type": tournament_type,
        "competition": competition,
    }


@app.get("/api/match/{match_id}")
def get_match_overview(
    match_id: str,
    competition: str = Query("ipl", description="Competition: ipl, t20i"),
):
    """
    Returns comprehensive match summary and all batter contribution ratings.
    Evaluates every batter with an actual batting opportunity in that match.
    Strictly excludes DNB appearances from receiving zero scores.
    """
    overview = data_service.get_match_overview(match_id=match_id, competition=competition)
    if not overview:
        raise HTTPException(
            status_code=404,
            detail=f"Match #{match_id} not found in {competition} dataset.",
        )
    return overview


@app.post("/api/pipeline/process-match/{match_id}")
def process_completed_match(
    match_id: str,
    provider: Optional[str] = Query(None, description="Optional provider override ('cricketdata.org', 'cricsheet', 'mock')"),
    competition: Optional[str] = Query("ipl", description="Competition identifier: ipl, t20i"),
):
    """
    Automated Post-Match Processing Endpoint (T20 ONLY).
    Validates official T20 format, prevents duplicates, computes production contribution
    ratings, preserves DNB as null, and updates data service within 60s SLA.
    """
    from app.adapters.factory import get_cricket_adapter
    from app.services.post_match_processor import PostMatchProcessor

    adapter = get_cricket_adapter(provider_name=provider)
    processor = PostMatchProcessor(adapter=adapter)
    result = processor.process_match(match_id=match_id, competition=competition)
    if result.get("status") == "rejected":
        raise HTTPException(status_code=400, detail=result.get("reason"))
    return result


@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Returns current status of post-match processor and registered processed matches."""
    from app.adapters.factory import get_cricket_adapter
    from app.services.post_match_processor import PostMatchProcessor

    adapter = get_cricket_adapter()
    processor = PostMatchProcessor(adapter=adapter)
    return {
        "status": "ready",
        "provider": adapter.provider_name,
        "processed_matches_count": len(processor._registry),
        "registry_path": str(processor.registry_path),
    }

