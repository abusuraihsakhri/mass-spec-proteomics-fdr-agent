"""
FastAPI REST API Server for ProteoFDR: Target-Decoy Search & Peptide-Spectrum Match (PSM) Agent.
"""
from typing import Dict, Any
from .models import FrontierPayload
from .agents import ProteomicsFDRCoordinator
from .fdr import analyze_psms

coordinator = ProteomicsFDRCoordinator()


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
        from pydantic import BaseModel

        app = FastAPI(
            title="ProteoFDR: Target-Decoy Search & Peptide-Spectrum Match (PSM) Agent",
            description="PSM target-decoy q-value calculation and legacy parameter-alert orchestration.",
            version="2.0.0-FRONTIER",
        )

        class TaskRequest(BaseModel):
            task_id: str = "TASK-2026-001"
            target_identifier: str = "TARGET-BIO-KEY"
            primary_metric: float = 28.5
            secondary_metric: float = 14.2
            status_descriptor: str = "DISCORDANT_ANOMALY"
            is_critical_flag: bool = True
            attributes: Dict[str, Any] = {}

        class ChatRequest(BaseModel):
            query: str

        @app.get("/health")
        def health():
            return {"status": "HEALTHY", "system": "mass-spec-proteomics-fdr-agent", "domain": "Proteomics", "version": "2.0.0-FRONTIER"}

        @app.post("/api/audit")
        def api_audit(req: TaskRequest):
            payload = FrontierPayload(
                task_id=req.task_id,
                target_identifier=req.target_identifier,
                primary_metric=req.primary_metric,
                secondary_metric=req.secondary_metric,
                status_descriptor=req.status_descriptor,
                is_critical_flag=req.is_critical_flag,
                attributes=req.attributes,
            )
            return coordinator.process(payload)

        @app.post("/api/chat")
        def api_chat(req: ChatRequest):
            return {"response": coordinator.query_supervisory_chat(req.query)}

        @app.post("/api/fdr")
        def api_fdr(payload: Dict[str, Any]):
            """Requires already-competed PSM winner rows."""
            try:
                psms = payload.get("psms")
                if not isinstance(psms, list):
                    raise ValueError("psms must be a list")
                if len(psms) > 50000:
                    raise HTTPException(status_code=413, detail="Maximum 50,000 PSMs")
                return analyze_psms(psms, alpha=payload.get("alpha", 0.01))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        return app
    except ImportError:
        return None
