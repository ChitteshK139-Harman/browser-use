## CONTROLLER AND AGENT LOGS

# Standard library imports
import asyncio
import os
import json
import logging
import subprocess
import uuid
import re
import gc
from datetime import datetime
from pathlib import Path
from contextlib import redirect_stdout
from io import StringIO, BytesIO
from typing import AsyncGenerator, Optional, Dict

# Third-party imports
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI
import json_repair


# Local module imports
from browser_use import Agent, Browser, BrowserConfig
from browser_use.agent.views import AgentHistoryList
# from browser_use.browser.browser import BrowserContext, BrowserContextConfig
from utils.decorators import apply_decorators, exceptionHandler
from utils.browseruseUtils import log_execution_time, clean_history, extract_interacted_elements, generate_unique_filename, log_streamer
from fileParser.llmclient import LLMClient
from prompts import EXECUTION_AGENT_FINAL_OUTPUT
from models.models import CommandQueryModel
from controllers.agentController import AgentController
from browser_use import Agent, Browser, BrowserConfig
from browser_use.browser.profile import BrowserProfile


# Load environment variables
load_dotenv()

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# Cache to store session_id -> debugger_port mappings
active_sessions = {}
# Store for active agent controllers
active_agent_controllers: Dict[str, 'AgentController'] = {}

print("Active Sessions: ", active_sessions)
import socket

def get_free_port() -> int:
    """Finds and returns a free port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

from pathlib import Path
BASE_PROFILE_PATH =  "modules/BUDeveloperAgent/.profiles/browseruse_multi_user_profiles"


def get_user_browser_profile(user_id: str, debug_port: str, channel: str = 'chromium', headless: bool = False) -> BrowserProfile:
   user_id = str("user_edge")
   profile_dir = Path(f"{BASE_PROFILE_PATH}/{user_id}")
   profile_dir.mkdir(parents=True, exist_ok=True)
   
   # Create preferences file to override new tab page
   prefs_file = profile_dir / "Preferences"
   prefs = {
       "homepage": "about:blank",
       "homepage_is_newtabpage": False,
       "session": {
           "restore_on_startup": 1,
           "startup_urls": ["about:blank"]
       }
   }
   
   with open(prefs_file, 'w') as f:
       json.dump(prefs, f)
   
   return BrowserProfile(
       user_data_dir=str(profile_dir),
       headless=headless,
       
       args=[
           f'--remote-debugging-port={debug_port}',
           '--no-first-run',
           '--disable-default-apps',
           '--new-tab-page-url=about:blank',
           '--homepage=about:blank'
       ],
       channel=channel,
   )

# 
@apply_decorators([exceptionHandler(returnVal='api')])
async def execute_task_stream(request: Request, query_model: CommandQueryModel):
    try:
        data = await request.json()
        newSession = data.get("isNewSession", True)
        closeSession = data.get("closeSession", False)
        headless = data.get("isHeadless", False)
        credentials = data.get("credentials", {})
        username = credentials.get("username", None)
        password = credentials.get("password", None)
        testcase = data.get("task", None)
        jsonCommand = testcase.get("testSteps", None)
        url = data.get("url", None)
        # userCommand = query_model.command
        # user = data.get("user", None)

        if not jsonCommand:
            return {"error": True, "msg": "No JSON Command Provided", "data": {"error": "Missing jsonCommand parameter"}}
        
        # Create a session ID for this execution
        session_id = data.get("session_id", str(uuid.uuid4()))
        logs_dir = f"./modules/BUDeveloperAgent/logs/session_{session_id}"
        os.makedirs(logs_dir, exist_ok=True)

        # Create session-specific logger configuration
        agent_logger = logging.getLogger(f'browser_use.session.{session_id}.agent')
        agent_logger.propagate = False
        controller_logger = logging.getLogger(f'browser_use.session.{session_id}.controller.service')
        controller_logger.propagate = False

        # Initialize LLM client
        llm = AzureChatOpenAI(
            model=os.getenv("MODEL_NAME"),
            api_key=os.getenv("MODEL_API_KEY"),
            azure_endpoint=os.getenv("MODEL_BASE_URL"),
            api_version=os.getenv("MODEL_API_VERSION"),
            temperature=0.3,
            openai_api_type='azure',
        )

        # # Generate instructions if jsonCommand is provided
        # if jsonCommand:
        #     try:
        #         prompt = f"""
        #         Given the following test case, please generate a single sentence that provides sequential instructions on how to carry out the test steps. The steps should be clear whether typing, clicking, selecting from dropdown. The output should clearly outline the actions to be taken in a concise manner.
        #         Merge steps that are similar and can be combined into a single action.
        #         Example:  Clicking on first and second button can be simply merged into "Click on the first and second button".

        #         Here is Test Case:
        #         {jsonCommand}

        #         Instructions:
        #         Read the Testcase ID and preconditions to understand the context.
        #         Generate a single, clear instruction sentence that combines the test steps in a logical order as detailed and descriptive.
        #         """
        #         print("Making an LLM request")
        #         completion = LLMClient().get_completion(messages=[{"role": "system", "content": prompt}])
        #         instruction = f"""Follow the sequential instructions provided, ensuring each step is successfully completed before proceeding to the next: {completion}.
        #                           If the user is not logged in, use the credentials {username} and {password}."""
        #         # instruction = f"Execute the Test cases: {jsonCommand}. If user is not logged in, use {username} and {password} as credentials."
        #         if userCommand:
        #             instruction += " USER INPUT: " + userCommand

        #         initialCommand = (
        #             f"Go to login page for {url} and use credentials username='{username}' and password='{password}' for login."
        #             if all([credentials, username, password])
        #             else f"Go to {url} and make sure you are on the correct page."
        #         )
        #     except Exception as e:
        #         agent_logger.error(f"Error in LLM processing: {str(e)}")
        #         return {"error": True, "msg": "LLM_PROCESSING_FAILED", "data": {"error": str(e)}}
        # else:
        #     instruction = query_model.command
        #     if jsonCommand is None and username and password:
        #         instruction +=  f"If the user is not logged in, use the credentials {username} and {password}"

        # Define the agent executor
        async def agent_executor():
            try:

                debug_port = get_free_port()
                print(f"Using debugger port: {debug_port}")
                user_profile_config = get_user_browser_profile(user_id= 'Default', debug_port=debug_port, channel='chromium', headless=headless)

                active_sessions[session_id] = {
                    "debugger_port": debug_port,
                    "captured_selectors": []
                }
                print("Active Sessions: ", active_sessions)

                # async with await browser as context:
                # Combine tasks if landing page command exists
                # combined_task = (
                #     f"{initialCommand}\n\nOnce landing page analysis is complete, proceed with: {instruction}"
                #     if jsonCommand
                #     else instruction
                # )
                
                print("Task: ", jsonCommand)
                # async with await browser.new_context() as context:
                # Create unified agent
                # logger=agent_logger
                execution_agent = Agent(
                    task=jsonCommand,
                    llm=llm,
                    # browser_context=context,
                    # browser=browser,
                    generate_gif=False,
                    enable_memory=False,
                    browser_profile=user_profile_config,
                    # planner_llm=llm,
                    # planner_interval=5,
                    # use_vision_for_planner=True,
                    # save_playwright_script_path=generate_unique_filename(f"{logs_dir}/playwright_script", "py"),
                    save_conversation_path=generate_unique_filename(f"{logs_dir}/conversation_merged", "json")
                )
                
                # Create agent controller and store it
                controller = AgentController(execution_agent)
                active_agent_controllers[session_id] = controller
                
                # Run the agent through the controller
                final_history = await controller.start(max_steps=50)

                agent_state = final_history.history[-1].result   # Retrieving last agent history record
                if final_history and final_history.is_successful():

                # Validation code to check if the agent run was successful

                # if agent_state[0].success:
                
                    # Save and clean history
                    conversation_temp_file = generate_unique_filename(f"{logs_dir}/conversation_temp", "json")
                    conversation_cleaned_file = generate_unique_filename(f"{logs_dir}/conversation_cleaned", "json")
                    final_history.save_to_file(conversation_temp_file)
                    cleaned_history_path = clean_history(conversation_temp_file, conversation_cleaned_file)

                    # Extract elements
                    elements_file_path = generate_unique_filename(f"{logs_dir}/elements", "json")
                    elements_file_path = extract_interacted_elements(cleaned_history_path, elements_file_path)
                    await asyncio.sleep(1)
                    agent_logger.info(f"filepath : {elements_file_path}")

            except Exception as e:
                agent_logger.error(f"Error in agent execution: {str(e)}")
                return {"error": True, "msg": "TEST_CASE_EXECUTION_FAILED", "data": {"error": str(e)}}
            finally:
                # Cleanup browser resources
                try:
                    if session_id in active_agent_controllers:
                        print("Cleaning up session: ", session_id)
                        del active_agent_controllers[session_id]
                    # import time
                    # time.sleep(10)
                    # if browser:
                        print("Closing browser")
                        # await asyncio.wait_for(browser.close(), timeout=60.0)
                except asyncio.TimeoutError:
                    agent_logger.warning("Browser close timed out, forcing cleanup")
                except Exception as e:
                    agent_logger.debug(f"Error during browser cleanup: {str(e)}")
                finally:    
                    # del browser
                    gc.collect()
                if session_id in active_sessions:
                    del active_sessions[session_id]

        # Run the agent executor
        agent_run_future = asyncio.ensure_future(agent_executor())
        return StreamingResponse(log_streamer(agent_run_future, session_id), media_type="text/event-stream")

    except json.JSONDecodeError as e:
        agent_logger.error(f"Invalid JSON format in request: {str(e)}")
        return {"error": True, "msg": "INVALID_JSON", "data": {"error": str(e)}}
    except Exception as e:
        agent_logger.error(f"Unexpected error: {str(e)}")
        return {"error": True, "msg": "UNEXPECTED_ERROR", "data": {"error": str(e)}}


@apply_decorators([exceptionHandler(returnVal='api')])
async def get_agent_status(request: Request):
    """Get status of all active agents or a specific one"""
    try:
        session_id = request.query_params.get("session_id")

        if session_id:
            # Get status for specific session
            if session_id not in active_agent_controllers:
                return {
                    "error": True,
                    "msg": "SESSION_NOT_FOUND",
                    "data": {"error": f"No active agent for session {session_id}"}
                }
            controller = active_agent_controllers[session_id]
            return {
                "error": False,
                "data": {
                    "session_id": session_id,
                    "status": controller.get_status(),
                    "port": active_sessions.get(session_id)
                },
                "msg": "AGENT_STATUS_RETRIEVED"
            }
        else:
            # Get status for all sessions
            statuses = {}
            for sid, controller in active_agent_controllers.items():
                statuses[sid] = {
                    "status": controller.get_status(),
                    "port": active_sessions.get(sid)
                }
            return {
                "error": False,
                "data": {
                    "sessions": statuses,
                    "count": len(statuses)
                },
                "msg": "ALL_AGENT_STATUSES_RETRIEVED"
            }
    except Exception as e:
        logger.error(f"Error getting agent status: {str(e)}")
        return {"error": True, "msg": "STATUS_ERROR", "data": {"error": str(e)}}


@apply_decorators([exceptionHandler(returnVal='api')])
async def getDetailsStep(request: Request):
    data = await request.json()
    agents_history = data.get("agents_history")
    jsonCommand = data.get("testCases")
    url = data.get("url")
    credentials = data.get("credentials", {})

    with open(agents_history, 'r') as f:
        agents_history = str(json.load(f))

    response = LLMClient().get_completion(messages=[
        {
            "role": "system",
            "content": f"""{EXECUTION_AGENT_FINAL_OUTPUT}""",
        },
        {
            "role": "user",
            "content": f"""Here is the Agent Chat history: {json.dumps(agents_history)}\nHere is the current test case : {jsonCommand}"""
        }
    ])

    try:
        # Parse the response and extract the Python code
        parsed_response = json_repair.loads(response)
        logger.info(f"Response parsed successfully: {parsed_response}")

        # Validate and flatten if any value is a list of lists
        def flatten_if_needed(value):
            if isinstance(value, list) and value and all(isinstance(i, list) for i in value):
                # Flatten one level
                return [item for sublist in value for item in sublist]
            return value

        details_steps = flatten_if_needed(parsed_response.get("detailsSteps"))
        bdd_steps = flatten_if_needed(parsed_response.get("bddSteps"))
        revised_test_case = flatten_if_needed(parsed_response.get("revisedTestCase"))

        return {
            "error": False,
            "data": {
                "detailsSteps": details_steps,
                "bddSteps": bdd_steps,
                "revisedTestCase": revised_test_case,
                "testCaseId": parsed_response.get("testCaseId"),
            },
            "msg": "SCRIPT_EXECUTED_SUCCESSFULLY"
        }
    except Exception as e:
        logger.error(f"Error parsing response: {str(e)}")
        return {
            "error": True,
            "data": {"error": str(e)},
            "msg": "RESPONSE_PARSING_FAILED"
        }
    except Exception as e:
        logger.error(f"Error in agent execution: {str(e)}")
        return {"error": True, "msg": "EXECUTION_FAILED", "data": {"error": str(e)}}

    return {"error": True, "msg": "No JSON Command Provided", "data": {"error": "Missing jsonCommand parameter"}}


@apply_decorators([exceptionHandler(returnVal='api')])
async def control_agent(request: Request):
    """
    Control an agent's execution with pause, resume, stop capabilities 
    and optional task updating.
    
    Args:
        request: FastAPI request object containing control parameters
        
    Returns:
        Dict containing operation result and status information
    """
    try:
        data = await request.json()
        session_id = data.get("session_id")
        action = data.get("action")
        user_interacted_str= "User has manually interacted with the browser and these are the selectors that user interacted: "
        if not session_id or not action:
            return {
                "error": True, 
                "msg": "INVALID_REQUEST", 
                "data": {"error": "Missing session_id or action"}
            }
            
        # Check if the session exists
        if session_id not in active_agent_controllers:
            return {
                "error": True, 
                "msg": "SESSION_NOT_FOUND", 
                "data": {"error": f"No active agent for session {session_id}"}
            }
            
        controller = active_agent_controllers[session_id]
        result = False
        task_updated = False
        
        # Check for new task in the request
        new_task = data.get("task", None) 
        
        # Handle different control actions
        if action == "pause":
            result = controller.pause()
        elif action == "resume":
            # If there's a new task and the agent is paused, update the task first
            if controller.paused:
                  session_data = active_sessions.get(session_id, {})
                  selectors_list = session_data.get("captured_selectors", [])  
                  # Get all attrs from captured_selectors and flatten into a list
                  curr_task = selectors_list
                  # Assign to new_task (replace with your actual logic as needed)
                  if curr_task:
                    if new_task:
                      # If new_task is provided, append the captured selectors to it
                      new_task = new_task + ' and ' + user_interacted_str + str(curr_task)
                    else:
                      # If no new_task is provided, just use the captured selectors
                      new_task = user_interacted_str + str(curr_task)
                    # Empty the captured_selectors for this session
                    session_data["captured_selectors"] = []
                    active_sessions[session_id] = session_data
                    task_updated = controller.update_task(new_task)
                  else:
                    # If no selectors captured, just update the task with new_task
                    task_updated = controller.update_task(new_task)
            # Then resume the agent
            result = controller.resume()
        elif action == "stop":
            result = controller.stop()
            # Clean up the controller if stopped
            if result and session_id in active_agent_controllers:
                del active_agent_controllers[session_id]
        elif action == "update":
            # Standalone task update action (agent must be paused)
            if not new_task:
                return {
                    "error": True,
                    "msg": "INVALID_REQUEST",
                    "data": {"error": "Missing task for update action"}
                }
            
            # Agent must be paused before updating task
            if not controller.paused:
                return {
                    "error": True,
                    "msg": "AGENT_NOT_PAUSED",
                    "data": {"error": "Agent must be paused before updating task"}
                }
                
            task_updated = controller.update_task(new_task)
            result = task_updated
        else:
            return {
                "error": True, 
                "msg": "INVALID_ACTION", 
                "data": {"error": f"Unknown action: {action}"}
            }
        
        status = controller.get_status()
        
        return {
            "error": False,
            "data": {
                "session_id": session_id,
                "action": action,
                "task_updated": task_updated,
                "success": result,
                "current_status": status
            },
            "msg": f"AGENT_{action.upper()}_{'SUCCEEDED' if result else 'FAILED'}"
        }
            
    except json.JSONDecodeError:
        return {
            "error": True, 
            "msg": "INVALID_JSON", 
            "data": {"error": "Invalid JSON in request body"}
        }
    except Exception as e:
        logger.error(f"Error controlling agent: {str(e)}")
        return {"error": True, "msg": "CONTROL_ERROR", "data": {"error": str(e)}}