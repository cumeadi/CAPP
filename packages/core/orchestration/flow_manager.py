"""
Flow Manager

Thin adapter to FinancialOrchestrator for managing payment processing flow lifecycle.
Flow state is persisted to Redis via StateManager.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from packages.core.orchestration.state_manager import StateManager

if TYPE_CHECKING:
    # Imported only for type-checking; the runtime dependency on FinancialOrchestrator
    # would create a circular import through packages.core.agents.
    from packages.core.orchestration.orchestrator import FinancialOrchestrator

logger = logging.getLogger(__name__)

_FLOW_KEY_PREFIX = "flow:"


class FlowManager:
    """Thin adapter to FinancialOrchestrator for flow lifecycle management.

    All flow state is persisted through StateManager (Redis), so flow progress
    survives process restarts and is visible across distributed instances.
    Workflow registration and query operations delegate to the orchestrator.
    """

    def __init__(self, orchestrator: FinancialOrchestrator, state_manager: StateManager):
        self._orchestrator = orchestrator
        self._state_manager = state_manager

    # ------------------------------------------------------------------
    # Flow lifecycle
    # ------------------------------------------------------------------

    async def start_flow(self, flow_id: str, steps: List[str]) -> bool:
        """Start a new payment flow and persist its initial state to Redis."""
        try:
            await self._state_manager.set_state(
                f"{_FLOW_KEY_PREFIX}{flow_id}",
                {
                    "flow_id": flow_id,
                    "steps": steps,
                    "status": "started",
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "completed_at": None,
                    "error": None,
                },
            )
            logger.info("Flow started: %s", flow_id)
            return True
        except Exception as e:
            logger.error("Failed to start flow %s: %s", flow_id, e)
            return False

    async def complete_flow(self, flow_id: str) -> bool:
        """Mark a payment flow as completed in Redis."""
        try:
            flow = await self._state_manager.get_state(f"{_FLOW_KEY_PREFIX}{flow_id}")
            if flow is None:
                logger.warning("complete_flow: flow not found: %s", flow_id)
                return False
            flow["status"] = "completed"
            flow["completed_at"] = datetime.now(timezone.utc).isoformat()
            await self._state_manager.set_state(f"{_FLOW_KEY_PREFIX}{flow_id}", flow)
            logger.info("Flow completed: %s", flow_id)
            return True
        except Exception as e:
            logger.error("Failed to complete flow %s: %s", flow_id, e)
            return False

    async def fail_flow(self, flow_id: str, error: str) -> bool:
        """Mark a payment flow as failed in Redis."""
        try:
            flow = await self._state_manager.get_state(f"{_FLOW_KEY_PREFIX}{flow_id}")
            if flow is None:
                return False
            flow["status"] = "failed"
            flow["error"] = error
            flow["completed_at"] = datetime.now(timezone.utc).isoformat()
            await self._state_manager.set_state(f"{_FLOW_KEY_PREFIX}{flow_id}", flow)
            logger.info("Flow failed: %s (%s)", flow_id, error)
            return True
        except Exception as e:
            logger.error("Failed to mark flow %s as failed: %s", flow_id, e)
            return False

    # ------------------------------------------------------------------
    # Query helpers (delegate to orchestrator / state manager)
    # ------------------------------------------------------------------

    async def get_flow_status(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve flow state from Redis."""
        return await self._state_manager.get_state(f"{_FLOW_KEY_PREFIX}{flow_id}")

    async def get_registered_workflows(self) -> Dict[str, Any]:
        """Return all workflows registered on the orchestrator."""
        return {
            wf_id: {
                "workflow_id": wf_id,
                "workflow_name": wf.workflow_name,
                "steps": [s.step_id for s in wf.steps],
            }
            for wf_id, wf in self._orchestrator._workflows.items()
        }
