"""
Database Schemas for Esports Tournament Management System

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""
from typing import List, Optional
from pydantic import BaseModel, Field

# Core domain models
class Game(BaseModel):
    name: str = Field(..., description="Game name")
    icon: Optional[str] = Field(None, description="Icon filename or URL")

class Team(BaseModel):
    team_name: str = Field(..., description="Team name")
    team_logo: Optional[str] = Field(None, description="Logo URL or filename")

class Player(BaseModel):
    IGN: str = Field(..., description="In-game name")
    UID: str = Field(..., description="Unique in-game identifier")
    player_photo: Optional[str] = Field(None, description="Photo URL or filename")
    team_id: Optional[str] = Field(None, description="Associated Team ID")

class Tournament(BaseModel):
    name: str = Field(..., description="Tournament name")
    game: str = Field(..., description="Game name for this tournament")
    team_ids: List[str] = Field(default_factory=list, description="Teams registered for this tournament")

# Brackets and matches
class Match(BaseModel):
    tournament_id: str
    round: int = Field(..., ge=1)
    team1_id: Optional[str] = None
    team2_id: Optional[str] = None
    winner_id: Optional[str] = None

# Groups and standings
class Group(BaseModel):
    tournament_id: str
    name: str = Field(..., description="Group name e.g., A, B, C")

class Standing(BaseModel):
    tournament_id: str
    group_name: str
    team_id: Optional[str] = None
    team_country_flag: Optional[str] = None
    team_logo: Optional[str] = None
    team_name: Optional[str] = None
    total_points: int = 0
