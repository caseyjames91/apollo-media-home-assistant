"""Learning-job API for Apollo IR."""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import uuid
from typing import Any

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

DATA_JOBS = "learning_jobs"
DATA_VIEWS_REGISTERED = "views_registered"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LearningJob:
    """State for one IR/RF learning request."""

    id: str
    learner_entity_id: str
    device: str
    command: str
    command_type: str
    timeout: int
    state: str
    message: str
    created_at: str
    updated_at: str
    error: str | None = None

    def as_json(self) -> dict[str, Any]:
        return asdict(self)


def get_jobs(hass: HomeAssistant) -> dict[str, LearningJob]:
    """Return the in-memory learning-job store."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    return domain_data.setdefault(DATA_JOBS, {})


async def _run_learning_job(hass: HomeAssistant, job: LearningJob) -> None:
    """Run remote.learn_command and update the job state."""
    jobs = get_jobs(hass)
    job.state = "waiting_for_signal"
    job.message = (
        "Hold the RF button until Home Assistant completes RF learning."
        if job.command_type == "rf"
        else "Point the original remote at the BroadLink and press the button."
    )
    job.updated_at = _now()

    try:
        await hass.services.async_call(
            "remote",
            "learn_command",
            {
                "device": job.device,
                "command": job.command,
                "command_type": job.command_type,
                "timeout": job.timeout,
            },
            target={"entity_id": job.learner_entity_id},
            blocking=True,
        )
    except asyncio.CancelledError:
        job.state = "cancelled"
        job.message = "Learning cancelled."
        job.updated_at = _now()
        raise
    except Exception as err:  # Home Assistant/integration exception becomes job state.
        text = str(err) or err.__class__.__name__
        lower = text.lower()
        if "timeout" in lower or "timed out" in lower:
            job.state = "timeout"
            job.message = "No command was learned before the timeout."
        else:
            job.state = "error"
            job.message = "Home Assistant could not learn the command."
        job.error = text
        job.updated_at = _now()
        return

    job.state = "learned"
    job.message = f"{job.device} / {job.command} learned successfully."
    job.updated_at = _now()
    jobs[job.id] = job


class ApolloIrLearnView(HomeAssistantView):
    """Create learning jobs."""

    url = "/api/apollo_ir/learn"
    name = "api:apollo_ir:learn"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]

        try:
            data = await request.json()
        except Exception as err:
            raise web.HTTPBadRequest(text="Body must be JSON") from err

        learner = str(data.get("learner_entity_id", "")).strip()
        device = str(data.get("device", "")).strip()
        command = str(data.get("command", "")).strip()
        command_type = str(data.get("command_type", "ir")).strip().lower()

        try:
            timeout = int(data.get("timeout", 30))
        except (TypeError, ValueError) as err:
            raise web.HTTPBadRequest(text="timeout must be an integer") from err

        if not learner.startswith("remote."):
            raise web.HTTPBadRequest(text="learner_entity_id must be a remote entity")
        if not device:
            raise web.HTTPBadRequest(text="device is required")
        if not command:
            raise web.HTTPBadRequest(text="command is required")
        if command_type not in {"ir", "rf"}:
            raise web.HTTPBadRequest(text="command_type must be ir or rf")
        if timeout < 5 or timeout > 120:
            raise web.HTTPBadRequest(text="timeout must be between 5 and 120 seconds")

        state = hass.states.get(learner)
        if state is None:
            raise web.HTTPBadRequest(text=f"Unknown learner entity: {learner}")
        if state.state == "unavailable":
            raise web.HTTPBadRequest(text=f"Learner is unavailable: {learner}")

        job_id = uuid.uuid4().hex
        now = _now()
        job = LearningJob(
            id=job_id,
            learner_entity_id=learner,
            device=device,
            command=command,
            command_type=command_type,
            timeout=timeout,
            state="starting",
            message="Starting learning on Home Assistant…",
            created_at=now,
            updated_at=now,
        )
        get_jobs(hass)[job_id] = job
        hass.async_create_task(_run_learning_job(hass, job))

        return self.json(job.as_json(), status_code=202)


class ApolloIrJobView(HomeAssistantView):
    """Read one learning job."""

    url = "/api/apollo_ir/jobs/{job_id}"
    name = "api:apollo_ir:job"
    requires_auth = True

    async def get(self, request: web.Request, job_id: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        job = get_jobs(hass).get(job_id)
        if job is None:
            raise web.HTTPNotFound(text="Learning job not found")
        return self.json(job.as_json())


class ApolloIrLearnersView(HomeAssistantView):
    """Return candidate remote learners for the AVA setup UI."""

    url = "/api/apollo_ir/learners"
    name = "api:apollo_ir:learners"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        learners = []
        for state in hass.states.async_all("remote"):
            learners.append(
                {
                    "entity_id": state.entity_id,
                    "name": state.name,
                    "state": state.state,
                }
            )
        learners.sort(key=lambda item: (item["name"] or item["entity_id"]).lower())
        return self.json({"learners": learners})


def register_learning_views(hass: HomeAssistant) -> None:
    """Register Apollo IR authenticated API views exactly once."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_VIEWS_REGISTERED):
        return

    hass.http.register_view(ApolloIrLearnView)
    hass.http.register_view(ApolloIrJobView)
    hass.http.register_view(ApolloIrLearnersView)
    domain_data[DATA_VIEWS_REGISTERED] = True
