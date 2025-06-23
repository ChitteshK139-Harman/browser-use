from fastapi import APIRouter, Request
from pydantic import BaseModel
from views import execute_task_stream
from models.models import CommandQueryModel

router = APIRouter(tags=["Automation Agent"])

# Post request - Reuse CommandQueryModel directly
@router.post("/run-browser-task")
async def execute(request: Request, qa_request: CommandQueryModel):
    return await execute_task_stream(request, qa_request)

