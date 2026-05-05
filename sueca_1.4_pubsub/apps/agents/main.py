from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
import threading
import uuid
from typing import Dict

from .agents import RandomAgent, WeakAgent, AverageAgent, SmartAgent
from shared.ratelimit import rate_limit_dependency

app = FastAPI(title="Sueca Agents Manager")

AGENTS: Dict[str, dict] = {}


class StartRequest(BaseModel):
    agent_type: str
    agent_name: str | None = None
    game_id: str | None = None
    position: str | None = None


@app.get("/health")
def health():
    return {"healthy": True}


@app.get("/types", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def types():
    return {"types": ["RandomAgent", "WeakAgent", "AverageAgent", "SmartAgent"]}


@app.post("/start", dependencies=[Depends(rate_limit_dependency(limit=10, window_seconds=60))])
def start_agent(req: StartRequest):
    cls = None
    if req.agent_type == "RandomAgent":
        cls = RandomAgent
    elif req.agent_type == "WeakAgent":
        cls = WeakAgent
    elif req.agent_type == "AverageAgent":
        cls = AverageAgent
    elif req.agent_type == "SmartAgent":
        cls = SmartAgent
    else:
        raise HTTPException(status_code=400, detail="unknown agent type")

    instance = cls(agent_name=req.agent_name or req.agent_type, game_id=req.game_id, position=req.position)
    thread = threading.Thread(target=instance.run, daemon=True, name=f"agent-{req.agent_type}-{uuid.uuid4().hex[:6]}")
    thread.start()
    agent_id = uuid.uuid4().hex
    AGENTS[agent_id] = {"id": agent_id, "type": req.agent_type, "name": req.agent_name or req.agent_type, "thread": thread, "instance": instance}
    return {"success": True, "agent_id": agent_id}


@app.get("/status", dependencies=[Depends(rate_limit_dependency(limit=60, window_seconds=60))])
def status():
    out = []
    for aid, info in AGENTS.items():
        out.append({"id": aid, "type": info["type"], "name": info["name"], "alive": info["thread"].is_alive()})
    return {"agents": out}


@app.post("/stop/{agent_id}", dependencies=[Depends(rate_limit_dependency(limit=30, window_seconds=60))])
def stop(agent_id: str):
    info = AGENTS.get(agent_id)
    if not info:
        raise HTTPException(status_code=404, detail="not found")
    # best-effort: try to stop by clearing auto_play and letting thread exit
    try:
        inst = info.get("instance")
        if hasattr(inst, "auto_play"):
            inst.auto_play = False
        # no cross-thread kill; user can later remove from registry
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
from fastapi import FastAPI
from pydantic import BaseModel
import time

app = FastAPI(title="Sueca Agents Service")


class ActivateRequest(BaseModel):
    agent_name: str
    params: dict | None = None


@app.get("/health")
def health():
    return {"healthy": True}


@app.post("/activate")
def activate(req: ActivateRequest):
    # placeholder: in future this will trigger agent containerized tasks
    start = time.time()
    # simulate work
    time.sleep(0.1)
    duration = time.time() - start
    return {"success": True, "agent": req.agent_name, "duration": duration}
