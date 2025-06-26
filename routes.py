from fastapi import APIRouter, Request
from pydantic import BaseModel
from views import execute_task_stream, control_agent, get_agent_status
from models.models import CommandQueryModel

router = APIRouter(tags=["Automation Agent"])

# Post request - Reuse CommandQueryModel directly
@router.post("/run-browser-task")
async def execute(request: Request, qa_request: CommandQueryModel):
    return await execute_task_stream(request, qa_request)

@router.post("/control-browser-task")
async def execute(request: Request):
    return await control_agent(request)

@router.post("/get_agent_status")
async def execute(request: Request):
    return await get_agent_status(request)
