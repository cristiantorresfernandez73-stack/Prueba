import json
import os
import secrets
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Literal

import pymysql
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

app = FastAPI(title="Nexo TFT API", version="1.0.0")
allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


class Composition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    tier: Literal["S", "A", "B", "C", "D"]
    category: Literal["Comps", "Emblem"] = "Comps"
    firstRate: float = Field(ge=0, le=100)
    top4Rate: float = Field(ge=0, le=100)
    avgPlace: float = Field(ge=1, le=8)
    pickRate: float = Field(ge=0, le=100)


class SnapshotPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    season: str = Field(min_length=1, max_length=32)
    patch: str = Field(min_length=1, max_length=32)
    region: str = Field(min_length=1, max_length=64)
    rank: str = Field(min_length=1, max_length=64)
    checkedAt: date
    source: HttpUrl
    compositions: list[Composition] = Field(min_length=10, max_length=100)


def connect_db():
    required = ["DB_NAME", "DB_USER", "DB_PASSWORD"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing database configuration: {', '.join(missing)}")

    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
        autocommit=True,
    )


def require_admin(authorization: str | None = Header(default=None)) -> None:
    expected = os.getenv("ADMIN_TOKEN", "")
    scheme, separator, supplied = (authorization or "").partition(" ")
    if not expected:
        raise HTTPException(status_code=503, detail="Admin token is not configured")
    if scheme.lower() != "bearer" or not separator or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=401,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def serialize_snapshot(row: dict) -> dict:
    compositions = row["compositions"]
    if isinstance(compositions, str):
        compositions = json.loads(compositions)
    return {
        "season": row["season"],
        "patch": row["patch"],
        "region": row["region"],
        "rank": row["rank_label"],
        "checkedAt": row["checked_at"].isoformat(),
        "source": row["source_url"],
        "compositions": compositions,
        "publishedAt": row["created_at"].isoformat(),
    }


@app.get("/api/health")
def health() -> dict:
    try:
        with closing(connect_db()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except (pymysql.MySQLError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Database unavailable or misconfigured") from error
    return {"status": "ok", "database": "connected"}


@app.get("/api/v1/meta/current")
def current_meta() -> dict:
    try:
        with closing(connect_db()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """SELECT season, patch, region, rank_label, checked_at, source_url,
                              compositions, created_at
                       FROM meta_snapshots ORDER BY id DESC LIMIT 1"""
                )
                row = cursor.fetchone()
    except (pymysql.MySQLError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Database unavailable or misconfigured") from error

    if row is None:
        raise HTTPException(status_code=404, detail="No season snapshot has been published")
    return serialize_snapshot(row)


@app.post("/api/v1/admin/meta", status_code=201, dependencies=[Depends(require_admin)])
def publish_meta(snapshot: SnapshotPayload) -> dict:
    compositions = sorted(
        (composition.model_dump() for composition in snapshot.compositions),
        key=lambda composition: composition["firstRate"],
        reverse=True,
    )

    try:
        with closing(connect_db()) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """INSERT INTO meta_snapshots
                       (season, patch, region, rank_label, checked_at, source_url, compositions)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        snapshot.season,
                        snapshot.patch,
                        snapshot.region,
                        snapshot.rank,
                        snapshot.checkedAt,
                        str(snapshot.source),
                        json.dumps(compositions, ensure_ascii=False),
                    ),
                )
                snapshot_id = cursor.lastrowid
                cursor.execute(
                    """SELECT season, patch, region, rank_label, checked_at, source_url,
                              compositions, created_at
                       FROM meta_snapshots WHERE id = %s""",
                    (snapshot_id,),
                )
                row = cursor.fetchone()
    except (pymysql.MySQLError, RuntimeError, ValueError) as error:
        raise HTTPException(status_code=503, detail="Could not publish the season snapshot") from error

    return serialize_snapshot(row)