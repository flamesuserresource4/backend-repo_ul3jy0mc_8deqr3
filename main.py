import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bson import ObjectId

from database import db, create_document, get_documents

app = FastAPI(title="Esports Tournament Management System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility to convert Mongo docs

def serialize_doc(doc):
    if not doc:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc


# Request models
class CreateTournamentRequest(BaseModel):
    tournament_name: str
    game: str

class CreateTeamRequest(BaseModel):
    team_name: str
    team_logo: Optional[str] = None

class CreatePlayerRequest(BaseModel):
    IGN: str
    UID: str
    player_photo: Optional[str] = None
    team_id: Optional[str] = None

class GroupGenerationRequest(BaseModel):
    number_of_teams: int
    number_of_groups: int

class AttachTeamRequest(BaseModel):
    team_id: str

class UpdateStandingRequest(BaseModel):
    team_id: Optional[str] = None
    team_country_flag: Optional[str] = None
    team_logo: Optional[str] = None
    team_name: Optional[str] = None
    total_points: Optional[int] = None

class UpdateMatchRequest(BaseModel):
    team1_id: Optional[str] = None
    team2_id: Optional[str] = None
    winner_id: Optional[str] = None


@app.get("/")
def read_root():
    return {"message": "Esports Tournament Management System Backend"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()
            response["database"] = "✅ Connected & Working"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


# Games: seed two games for landing page
@app.get("/games")
def get_games():
    return [
        {"name": "PUBG Mobile", "icon": "pubg.png"},
        {"name": "Honor of Kings", "icon": "hok.png"},
    ]

# Tournaments
@app.get("/tournaments")
def list_tournaments(game: Optional[str] = None):
    if db is None:
        return []
    filter_q = {"game": game} if game else {}
    docs = get_documents("tournament", filter_q, None)
    return [serialize_doc(d) for d in docs]

@app.get("/tournaments/{tournament_id}")
def get_tournament(tournament_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        tid = ObjectId(tournament_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tournament id")
    doc = db["tournament"].find_one({"_id": tid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return serialize_doc(doc)

@app.post("/tournaments")
def create_tournament(payload: CreateTournamentRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    data = {"name": payload.tournament_name, "game": payload.game, "team_ids": []}
    inserted_id = create_document("tournament", data)
    return {"id": inserted_id, "name": payload.tournament_name, "game": payload.game, "team_ids": []}

# Teams
@app.get("/teams")
def list_teams():
    docs = get_documents("team", {}, None) if db else []
    return [serialize_doc(d) for d in docs]

@app.post("/teams")
def create_team(payload: CreateTeamRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    inserted_id = create_document("team", payload.model_dump())
    return {"id": inserted_id, **payload.model_dump()}

# Attach team to tournament
@app.post("/tournaments/{tournament_id}/teams")
def attach_team(tournament_id: str, payload: AttachTeamRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        tid = ObjectId(tournament_id)
        team_oid = ObjectId(payload.team_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid IDs")

    team = db["team"].find_one({"_id": team_oid})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    db["tournament"].update_one({"_id": tid}, {"$addToSet": {"team_ids": payload.team_id}})
    return {"ok": True}

# Players
@app.get("/players")
def list_players():
    docs = get_documents("player", {}, None) if db else []
    return [serialize_doc(d) for d in docs]

@app.post("/players")
def create_player(payload: CreatePlayerRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    inserted_id = create_document("player", payload.model_dump())
    return {"id": inserted_id, **payload.model_dump()}


# Brackets generation and retrieval
@app.post("/tournaments/{tournament_id}/brackets/generate")
def generate_brackets(tournament_id: str):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        tid = ObjectId(tournament_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tournament id")

    tournament = db["tournament"].find_one({"_id": tid})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    team_ids = tournament.get("team_ids", [])
    matches = []
    for i in range(0, len(team_ids), 2):
        t1 = team_ids[i] if i < len(team_ids) else None
        t2 = team_ids[i+1] if i+1 < len(team_ids) else None
        matches.append({
            "tournament_id": tournament_id,
            "round": 1,
            "team1_id": t1,
            "team2_id": t2,
            "winner_id": None,
        })
    if matches:
        db["match"].insert_many(matches)
    return {"created": len(matches)}

@app.get("/tournaments/{tournament_id}/matches")
def list_matches(tournament_id: str):
    if db is None:
        return []
    docs = db["match"].find({"tournament_id": tournament_id})
    return [serialize_doc(d) for d in docs]

@app.put("/matches/{match_id}")
def update_match(match_id: str, payload: UpdateMatchRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        mid = ObjectId(match_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid match id")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"ok": True}
    db["match"].update_one({"_id": mid}, {"$set": updates})
    return {"ok": True}


# Group generation and standings
@app.post("/tournaments/{tournament_id}/groups/generate")
def generate_groups(tournament_id: str, payload: GroupGenerationRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        tid = ObjectId(tournament_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tournament id")

    tournament = db["tournament"].find_one({"_id": tid})
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    group_names = [chr(ord('A') + i) for i in range(payload.number_of_groups)]
    groups = [{"tournament_id": tournament_id, "name": g} for g in group_names]
    if groups:
        db["group"].insert_many(groups)

    standings = []
    slots_per_group = max(1, payload.number_of_teams // payload.number_of_groups)
    for g in group_names:
        for _ in range(slots_per_group):
            standings.append({
                "tournament_id": tournament_id,
                "group_name": g,
                "team_id": None,
                "team_country_flag": None,
                "team_logo": None,
                "team_name": None,
                "total_points": 0,
            })
    if standings:
        db["standing"].insert_many(standings)

    return {"groups_created": len(groups), "standing_slots": len(standings)}

@app.get("/tournaments/{tournament_id}/groups")
def list_groups(tournament_id: str):
    if db is None:
        return []
    docs = db["group"].find({"tournament_id": tournament_id})
    return [serialize_doc(d) for d in docs]

@app.get("/tournaments/{tournament_id}/standings")
def list_standings(tournament_id: str):
    if db is None:
        return []
    docs = db["standing"].find({"tournament_id": tournament_id})
    return [serialize_doc(d) for d in docs]

@app.put("/standings/{standing_id}")
def update_standing(standing_id: str, payload: UpdateStandingRequest):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")
    try:
        sid = ObjectId(standing_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid standing id")
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not updates:
        return {"ok": True}
    db["standing"].update_one({"_id": sid}, {"$set": updates})
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
