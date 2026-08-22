from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
ADAPTIVE_MEMORY_DIR = BASE_DIR / "AdaptiveMemory"
if str(ADAPTIVE_MEMORY_DIR) not in sys.path:
    sys.path.insert(0, str(ADAPTIVE_MEMORY_DIR))

from Core.AMA import AMA  # noqa: E402
from StoreFunc.SQLite import sqliteFunc  # noqa: E402


app = FastAPI(title="AMA Sidecar")
instances: dict[str, AMA] = {}


class InitRequest(BaseModel):
    user: str
    dataDir: str
    modelMemory: str = "gpt-4o-mini"
    temperature: float = 0.0
    memoryWindowSize: int = 100000
    memoryWindowLength: int = 20
    turnRetrieve: int = 1


class ForwardUserRequest(BaseModel):
    user: str
    userInput: Union[str, Dict[str, Any]]
    showUsage: bool = False


class ForwardRobotRequest(BaseModel):
    user: str
    robotOutput: str
    showUsage: bool = False
    timeInput: Optional[str] = None


class ForwardRetrieveRequest(BaseModel):
    user: str
    userInput: str
    showUsage: bool = False
    strongRetrieve: bool = False


class UserRequest(BaseModel):
    user: str


def _require_instance(user: str) -> AMA:
    instance = instances.get(user)
    if instance is None:
        raise HTTPException(status_code=404, detail=f"User '{user}' is not initialized")
    return instance


def _parse_forward_user_output(raw: str) -> dict[str, Any]:
    retrieval_marker = "Retrieval results:\n"
    memory_marker = "\nMemory Window:\n"
    if not raw.startswith(retrieval_marker) or memory_marker not in raw:
        raise ValueError("Unexpected forwardUser output format")

    payload = raw[len(retrieval_marker):]
    retrievals_raw, memory_raw = payload.split(memory_marker, 1)
    return {
        "retrievals": json.loads(retrievals_raw),
        "memoryWindow": json.loads(memory_raw),
    }


def _table_count(table_name: str, data_dir: str | None) -> int:
    sqliteFunc.set_data_dir(data_dir)
    db_path = sqliteFunc.get_db_path()
    conn = sqlite3.connect(db_path, timeout=10)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
            (table_name,),
        )
        if cursor.fetchone() is None:
            return 0
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/init")
def init(body: InitRequest) -> dict[str, str]:
    if body.user in instances:
        return {"status": "already_initialized", "user": body.user}

    instance = AMA(
        user=body.user,
        memoryWindowSize=body.memoryWindowSize,
        memoryWindowLength=body.memoryWindowLength,
        modelMemory=body.modelMemory,
        temperature=body.temperature,
        turnRetrieve=body.turnRetrieve,
        data_dir=body.dataDir,
    )
    instances[body.user] = instance
    return {"status": "initialized", "user": body.user}


@app.post("/forward-user")
def forward_user(body: ForwardUserRequest) -> dict[str, Any]:
    instance = _require_instance(body.user)
    raw = instance.forwardUser(userInput=body.userInput, showUsage=body.showUsage)
    try:
        return _parse_forward_user_output(raw)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse forward-user output: {exc}") from exc


@app.post("/forward-robot")
def forward_robot(body: ForwardRobotRequest) -> dict[str, Any]:
    instance = _require_instance(body.user)
    return instance.forwardRobot(
        robotOutput=body.robotOutput,
        showUsage=body.showUsage,
        timeInput=body.timeInput,
    )


@app.post("/forward-retrieve")
def forward_retrieve(body: ForwardRetrieveRequest) -> dict[str, Any]:
    instance = _require_instance(body.user)
    raw = instance.forwardRetrieve(
        userInput=body.userInput,
        showUsage=body.showUsage,
        strongRetrieve=body.strongRetrieve,
    )
    return json.loads(raw)


@app.post("/judge-and-generate")
def judge_and_generate(body: UserRequest) -> dict[str, str]:
    instance = _require_instance(body.user)
    instance.judgeAndGenerate()
    return {"status": "ok"}


@app.post("/clear-all-memory")
def clear_all_memory(body: UserRequest) -> dict[str, str]:
    instance = _require_instance(body.user)
    instance.clearAllMemory()
    return {"status": "cleared", "user": body.user}


@app.get("/stats/{user}")
def stats(user: str) -> dict[str, Any]:
    instance = _require_instance(user)
    return {
        "user": user,
        "memoryWindowSize": len(instance.memoryWindow),
        "records": {
            "dialogues": _table_count(instance.user, instance.data_dir),
            "facts": _table_count(instance.factSql, instance.data_dir),
            "episodes": _table_count(instance.episodeSql, instance.data_dir),
            "sentences": _table_count(instance.sentenceSql, instance.data_dir),
        },
    }
