from pydantic import Field
from typing import List

from pydantic import BaseModel

# class CommandQueryModel(BaseModel):
#     command: str| None = Field(None, description="The command related to web navigation to execute.")  # Required field with description
#     llm_config: dict[str,Any] | None = Field(None, description="The LLM configuration string to use for the agents.")
#     planner_max_chat_round: int = Field(None, description="The maximum number of chat rounds for the planner.")
#     browser_nav_max_chat_round: int = Field(None, description="The maximum number of chat rounds for the browser navigation agent.")
#     clientid: str | None = Field(None, description="Client identifier, optional")
#     request_originator: str | None = Field(None, description="Optional id of the request originator")
#     lastTransationId:str | None = Field(None,description="if user has last transaction id")

class TestStep(BaseModel):
    step: str
    expectedResults: str

class TaskModel(BaseModel):
    testCaseId: str
    testDescription: str
    preconditions: str
    testSteps: List[TestStep]
    expectedResults: str
    Postconditions: str
    uid: str

class CommandQueryModel(BaseModel):
    task: TaskModel