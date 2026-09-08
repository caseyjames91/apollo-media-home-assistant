from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
import uuid
from typing import Any

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

APP_VERSION = os.environ.get("APOLLO_IR_VERSION", "dev")
HA_URL = os.environ.get("HOME_ASSISTANT_URL", "http://supervisor/core").rstrip("/")
HA_TOKEN = os.environ.get("HOME_ASSISTANT_TOKEN", "")
API_KEY = os.environ.get("APOLLO_IR_API_KEY", "")

app = FastAPI(title="Apollo IR Server", version=APP_VERSION)
jobs: dict[str, dict[str, Any]] = {}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_api_key(x_apollo_ir_key: str | None) -> None:
    if API_KEY and x_apollo_ir_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Apollo IR API key")


def ha_headers() -> dict[str, str]:
    if not HA_TOKEN:
        raise HTTPException(status_code=500, detail="Supervisor token is unavailable")
    return {
        "Authorization": f"Bearer {HA_TOKEN}",
        "Content-Type": "application/json",
    }


class LearnRequest(BaseModel):
    learner_entity_id: str
    device: str = Field(min_length=1, max_length=128)
    command: str = Field(min_length=1, max_length=128)
    command_type: str = "ir"
    timeout: int = Field(default=30, ge=5, le=120)


async def run_learning_job(job_id: str, req: LearnRequest) -> None:
    job = jobs[job_id]
    job["state"] = "waiting_for_signal"
    job["message"] = (
        "Hold/press the original RF remote button as instructed by BroadLink."
        if req.command_type == "rf"
        else "Point the original remote at the BroadLink and press the button."
    )
    job["updated_at"] = now_iso()

    payload = {
        "entity_id": req.learner_entity_id,
        "device": req.device,
        "command": req.command,
        "command_type": req.command_type,
        "timeout": req.timeout,
    }

    try:
        async with httpx.AsyncClient(timeout=req.timeout + 15.0) as client:
            response = await client.post(
                f"{HA_URL}/api/services/remote/learn_command",
                headers=ha_headers(),
                json=payload,
            )
        response.raise_for_status()
    except asyncio.CancelledError:
        job["state"] = "cancelled"
        job["message"] = "Learning cancelled."
        job["updated_at"] = now_iso()
        raise
    except Exception as err:
        text = str(err)
        low = text.lower()
        job["state"] = "timeout" if "timeout" in low else "error"
        job["message"] = (
            "No command was learned before the timeout."
            if job["state"] == "timeout"
            else "Home Assistant could not learn the command."
        )
        job["error"] = text
        job["updated_at"] = now_iso()
        return

    job["state"] = "learned"
    job["message"] = f"{req.device} / {req.command} learned successfully."
    job["updated_at"] = now_iso()


@app.get("/status")
async def status(x_apollo_ir_key: str | None = Header(default=None)) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    return {
        "ok": True,
        "service": "apollo_ir_server",
        "version": APP_VERSION,
        "ha_backend": True,
    }


@app.get("/api/learners")
async def learners(x_apollo_ir_key: str | None = Header(default=None)) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{HA_URL}/api/states",
            headers=ha_headers(),
        )
    response.raise_for_status()

    result = []
    for state in response.json():
        entity_id = state.get("entity_id", "")
        if not entity_id.startswith("remote."):
            continue
        attrs = state.get("attributes") or {}
        result.append(
            {
                "entity_id": entity_id,
                "name": attrs.get("friendly_name", entity_id),
                "state": state.get("state"),
            }
        )

    result.sort(key=lambda item: str(item["name"]).lower())
    return {"learners": result}


@app.post("/api/learn", status_code=202)
async def learn(
    req: LearnRequest,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)

    if req.command_type not in {"ir", "rf"}:
        raise HTTPException(status_code=400, detail="command_type must be ir or rf")
    if not req.learner_entity_id.startswith("remote."):
        raise HTTPException(status_code=400, detail="learner_entity_id must be remote.*")

    # Validate that the selected HA entity exists before creating a job.
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            f"{HA_URL}/api/states/{req.learner_entity_id}",
            headers=ha_headers(),
        )
    if response.status_code == 404:
        raise HTTPException(status_code=400, detail="Unknown learner entity")
    response.raise_for_status()

    job_id = uuid.uuid4().hex
    created = now_iso()
    jobs[job_id] = {
        "id": job_id,
        "learner_entity_id": req.learner_entity_id,
        "device": req.device,
        "command": req.command,
        "command_type": req.command_type,
        "timeout": req.timeout,
        "state": "starting",
        "message": "Starting learning through Home Assistant…",
        "created_at": created,
        "updated_at": created,
        "error": None,
    }
    asyncio.create_task(run_learning_job(job_id, req))
    return jobs[job_id]


@app.get("/api/jobs/{job_id}")
async def get_job(
    job_id: str,
    x_apollo_ir_key: str | None = Header(default=None),
) -> dict[str, Any]:
    require_api_key(x_apollo_ir_key)
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Learning job not found")
    return jobs[job_id]
