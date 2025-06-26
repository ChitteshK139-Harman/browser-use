import asyncio
import logging
import os
import socket
import uuid
import threading
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Set, List
from queue import Queue

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, SecretStr
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

from browser_use import Agent, Controller, ActionResult
from browser_use.browser.profile import BrowserProfile
from browser_use.agent.views import AgentOutput, BrowserStateHistory, AgentStepInfo
from browser_use.browser.views import BrowserStateSummary

load_dotenv()

# Custom logging handler for streaming logs
class StreamingLogHandler(logging.Handler):
    """Custom log handler that captures logs and queues them for streaming"""
    
    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue
    
    def emit(self, record):
        try:
            # Format the log message
            message = self.format(record)
            
            # Create log message structure
            log_message = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "logger_name": record.name,
                "message": message,
                "metadata": {
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno
                }
            }
            
            # Add to queue for streaming
            self.log_queue.put(('log', log_message))
            
        except Exception:
            # Handle errors in log handler silently to avoid recursion
            pass

# Log streaming functionality integrated into main app
class LogMessage(BaseModel):
    """Structure for log messages"""
    timestamp: str
    level: str
    logger_name: str
    message: str
    step_number: Optional[int] = None
    metadata: Optional[dict] = None

class AgentStatus(BaseModel):
    """Status model for agent tracking"""
    agent_id: str
    status: str  # running, completed, stopped, error
    current_step: int
    task: str
    started_at: str
    last_update: str
    metadata: Optional[dict] = None

class AgentStepData(BaseModel):
    """Data structure for agent step information"""
    step_number: int
    timestamp: str
    url: Optional[str] = None
    title: Optional[str] = None
    browser_state: Optional[dict] = None
    model_output: Optional[dict] = None

# Global log streaming state
log_queue: Queue = Queue()
active_connections: Set[WebSocket] = set()
session_connections: Dict[str, Set[WebSocket]] = {}  # session_id -> set of websockets
tracked_agents: Dict[str, AgentStatus] = {}

# Setup streaming logging
def setup_streaming_logging():
    """Setup logging to capture and stream all log messages"""
    # Create our custom handler
    streaming_handler = StreamingLogHandler(log_queue)
    streaming_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(levelname)-8s [%(name)s] %(message)s')
    streaming_handler.setFormatter(formatter)
    
    # Add handler to root logger to catch all logs
    root_logger = logging.getLogger()
    root_logger.addHandler(streaming_handler)
    root_logger.setLevel(logging.DEBUG)
    
    # Specifically add to browser_use logger
    browser_use_logger = logging.getLogger('browser_use')
    browser_use_logger.addHandler(streaming_handler)
    browser_use_logger.setLevel(logging.DEBUG)
    
    # Add to agent_api logger
    agent_api_logger = logging.getLogger('agent_api')
    agent_api_logger.addHandler(streaming_handler)
    agent_api_logger.setLevel(logging.DEBUG)
    
    # Add to agent_interaction logger
    interaction_logger = logging.getLogger('agent_interaction')
    interaction_logger.addHandler(streaming_handler)
    interaction_logger.setLevel(logging.DEBUG)
    
    print("📡 Streaming logging setup complete!")

# Initialize streaming logging
setup_streaming_logging()

# Icons for different action types
ACTION_TYPE_ICONS = {
    'ClickAction': '👆',
    'InputAction': '⌨️',
    'NavigateAction': '🧭',
    'ScrollAction': '📜',
    'WaitAction': '⏳',
    'ExtractAction': '📋',
    'SelectAction': '🎯',
    'HoverAction': '🔍'
}

# Background task for log broadcasting
async def broadcast_logs():
    """Background task to broadcast logs to all connected WebSocket clients"""
    global log_queue, active_connections, session_connections
    
    while True:
        try:
            if not log_queue.empty():
                message_type, data = log_queue.get_nowait()
                
                # Extract session_id from data if available
                session_id = None
                if isinstance(data, dict):
                    session_id = data.get('session_id')
                
                message = {
                    "type": message_type,
                    "data": data
                }
                
                # Broadcast to general connections
                if active_connections:
                    disconnected = set()
                    for connection in active_connections:
                        try:
                            await connection.send_text(json.dumps(message, ensure_ascii=False))
                        except Exception:
                            disconnected.add(connection)
                    
                    # Remove disconnected clients
                    active_connections -= disconnected
                
                # Broadcast to session-specific connections
                if session_id and session_id in session_connections:
                    disconnected = set()
                    for connection in session_connections[session_id]:
                        try:
                            await connection.send_text(json.dumps(message, ensure_ascii=False))
                        except Exception:
                            disconnected.add(connection)
                    
                    # Remove disconnected clients
                    session_connections[session_id] -= disconnected
                    if not session_connections[session_id]:
                        del session_connections[session_id]
                            
            await asyncio.sleep(0.1)  # Small delay to prevent CPU spinning
        except Exception as e:
            print(f"Error in broadcast_logs: {e}")
            await asyncio.sleep(1)

def create_step_callback(agent_id: str, session_id: str):
    """Create a callback function for agent steps"""
    
    async def step_callback(browser_state_summary: BrowserStateSummary, agent_output: AgentOutput, step_number: int):
        """Callback function for each agent step"""
        try:
            if agent_id in tracked_agents:
                tracked_agents[agent_id].current_step = step_number
                tracked_agents[agent_id].last_update = datetime.now().isoformat()
            
            # Process actions with icons
            actions_with_icons = []
            if hasattr(agent_output, 'action') and agent_output.action:
                for action in agent_output.action:
                    action_type = type(action).__name__
                    icon = ACTION_TYPE_ICONS.get(action_type, '🎯')
                    actions_with_icons.append({
                        "action_type": action_type,
                        "icon": icon,
                        "details": str(action),
                        "display_name": f"{icon} {action_type}"
                    })
            
            # Create step data
            step_data = AgentStepData(
                step_number=step_number,
                timestamp=datetime.now().isoformat(),
                url=browser_state_summary.url if browser_state_summary else None,
                title=browser_state_summary.title if browser_state_summary else None,
                browser_state={
                    "url": browser_state_summary.url,
                    "title": browser_state_summary.title,
                    "tabs": browser_state_summary.tabs,
                    "interactive_elements_count": len(browser_state_summary.selector_map) if browser_state_summary.selector_map else 0
                } if browser_state_summary else None,
                model_output={
                    "thinking": getattr(agent_output, 'thinking', None),
                    "evaluation": getattr(agent_output, 'evaluation', None),
                    "memory": getattr(agent_output, 'memory', None),
                    "next_goal": getattr(agent_output, 'next_goal', None),
                    "actions": actions_with_icons
                }            )
            
            # Enhanced step data with agent info
            enhanced_step_data = {
                **step_data.dict(),
                "agent_id": agent_id,
                "session_id": session_id
            }
            
            # Queue the step data for broadcasting
            log_queue.put(('agent_step', enhanced_step_data))
                            
        except Exception as e:
            error_msg = f"❌ Error in step callback for agent {agent_id}: {e}"
            print(error_msg)
            log_queue.put(('log', {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "logger_name": "agent_api",
                "message": error_msg,
                "metadata": {"agent_id": agent_id, "error_context": "step_callback"},
                "session_id": session_id
            }))
    
    return step_callback

def create_done_callback(agent_id: str, session_id: str):
    """Create a callback function for agent completion"""
    
    async def done_callback(history):
        """Callback function when agent completes"""
        try:
            if agent_id in tracked_agents:
                tracked_agents[agent_id].status = "completed"
                tracked_agents[agent_id].last_update = datetime.now().isoformat()
                
                # Determine success status and appropriate icon
                is_successful = history.is_successful() if history else False
                status_icon = "🎉" if is_successful else "⚠️"
                status_message = f"{status_icon} Agent {agent_id} completed {'successfully' if is_successful else 'with issues'}"
                
                # Log completion with icon and metadata
                log_queue.put(('log', {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "logger_name": "agent_api",
                    "message": status_message,
                    "metadata": {"agent_id": agent_id, "action": "agent_completion"},
                    "session_id": session_id
                }))
                
                # Completion data
                completion_data = {
                    "agent_id": agent_id,
                    "session_id": session_id,
                    "final_status": tracked_agents[agent_id].dict(),
                    "total_steps": len(history.history) if history else 0,
                    "success": is_successful,
                    "status_icon": status_icon,
                    "completion_message": status_message
                }
                
                # Queue completion data for broadcasting
                log_queue.put(('agent_completed', completion_data))
                        
        except Exception as e:
            error_msg = f"❌ Error in done callback for agent {agent_id}: {e}"
            print(error_msg)
            log_queue.put(('log', {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "logger_name": "agent_api",
                "message": error_msg,
                "metadata": {"agent_id": agent_id, "error_context": "done_callback"},
                "session_id": session_id
            }))
    
    return done_callback

def register_agent(agent_id: str, task: str, session_id: Optional[str] = None, debug_port: Optional[int] = None):
    """Register a new agent for tracking"""
    metadata = {}
    if session_id:
        metadata['session_id'] = session_id
    if debug_port:
        metadata['debug_port'] = debug_port
        
    tracked_agents[agent_id] = AgentStatus(
        agent_id=agent_id,
        status="running",
        current_step=0,
        task=task,
        started_at=datetime.now().isoformat(),
        last_update=datetime.now().isoformat(),
        metadata=metadata
    )
      # Log agent registration
    log_queue.put(('log', {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "logger_name": "agent_api",
        "message": f"🚀 Agent {agent_id} registered and starting task: {task}",
        "metadata": {"agent_id": agent_id, "action": "agent_registration"},
        "session_id": session_id
    }))

def get_agent_callbacks(agent_id: str, session_id: str):
    """Get callback functions for an agent to enable real-time logging"""
    step_callback = create_step_callback(agent_id, session_id)
    done_callback = create_done_callback(agent_id, session_id)
    return step_callback, done_callback

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_PROFILE_PATH = Path.home() / ".cache" / "browseruse_multi_user_profiles"
controller = Controller()

active_agents: Dict[str, Dict[str, Any]] = {}

class TaskRequest(BaseModel):
    task: str
    user_id: Optional[str] = "default_user"
    headless: Optional[bool] = False
    agent_id: Optional[str] = None
    session_id: Optional[str] = None

class TaskResponse(BaseModel):
    agent_id: str
    session_id: str
    status: str
    websocket_url: str
    session_websocket_url: str
    debug_port: int

class AgentStatusResponse(BaseModel):
    agent_id: str
    status: str
    task: str
    session_id: str
    debug_port: int
    started_at: str

@controller.action('Ask human for help with a question')
def ask_human(question: str) -> ActionResult:
    """Custom action to ask human for help and stream the interaction"""
    
    # Log the question with both standard logging and direct streaming
    question_message = f"🤔 Agent asks: {question}"
    logger.info(question_message)
    
    # Also add directly to queue for immediate streaming
    question_log = {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "logger_name": "agent_interaction",
        "message": f"🤔 Agent Question: {question}",
        "metadata": {
            "type": "agent_question",
            "question": question,
            "action": "user_interaction"
        }
    }
    log_queue.put(('log', question_log))
    log_queue.put(('agent_question', question_log))
    
    # Display to console and get input
    print(f"\n🤔 Agent Question: {question}")
    answer = input("Your response > ")
    
    # Log the human response
    response_message = f"👤 Human responds: {answer}"
    logger.info(response_message)
    
    # Also add response directly to queue for immediate streaming
    answer_log = {
        "timestamp": datetime.now().isoformat(),
        "level": "INFO",
        "logger_name": "agent_interaction",
        "message": f"👤 Human Response: {answer}",
        "metadata": {
            "type": "human_response",
            "response": answer,
            "action": "user_interaction"
        }
    }
    log_queue.put(('log', answer_log))
    log_queue.put(('human_response', answer_log))
    
    return ActionResult(
        extracted_content=f'The human responded with: {answer}',
        include_in_memory=True
    )

def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def get_user_browser_profile(user_id: str, headless: bool = False, debug_port: int | None = None) -> BrowserProfile:
    profile_dir = BASE_PROFILE_PATH / user_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    browser_args = [
        # f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--allow-running-insecure-content"
    ]
    
    if debug_port:
        browser_args.append(f"--remote-debugging-port={debug_port}")
    
    return BrowserProfile(
        # path=profile_dir,
        args=browser_args,
        headless=headless,
        highlight_elements=False
    )

async def run_agent_task(task: str, agent_id: str, session_id: str, user_id: str, headless: bool):
    """Run an agent task with proper logging and streaming"""
    try:
        # Log startup
        startup_message = f"🚀 Starting agent with ID: {agent_id}"
        print(startup_message)
        logger.info(startup_message)
        
        session_message = f"🆔 Session ID: {session_id}"
        print(session_message)
        logger.info(session_message)
        
        task_message = f"📋 Task: {task}"
        print(task_message)
        logger.info(task_message)
        
        debug_port = get_free_port()
        port_message = f"🔌 Assigned debugging port: {debug_port}"
        print(port_message)
        logger.info(port_message)
        
        register_agent(agent_id, task, session_id, debug_port)
        
        step_callback, done_callback = get_agent_callbacks(agent_id, session_id)
        user_profile_config = get_user_browser_profile(user_id, headless=False, debug_port=debug_port)
        
        active_agents[agent_id] = {
            "status": "running",
            "task": task,
            "session_id": session_id,
            "debug_port": debug_port,
            "started_at": datetime.now().isoformat()
        }
        
        # Create agent with enhanced logging
        agent = Agent(
            task=task,
            initial_actions=[
                {'open_tab': {'url': 'https://www.flipkart.com/'}},
            ],
            task_id="1234sdfaef",
            llm=AzureChatOpenAI(
                model=os.getenv("MODEL_NAME"),
                api_key=SecretStr(os.getenv("MODEL_API_KEY") or ""),
                azure_endpoint=os.getenv("MODEL_BASE_URL"),
                api_version=os.getenv("MODEL_API_VERSION"),
                temperature=0.3,
                openai_api_type='azure',
            ),
            browser_profile=user_profile_config,
            controller=controller,
            enable_memory=False,
            register_new_step_callback=step_callback,
            register_done_callback=done_callback
        )
        
        execution_message = f"🎯 Agent {agent_id} starting execution..."
        print(execution_message)
        logger.info(execution_message)
        
        # Run the agent
        await agent.run()
        
        completion_message = f"✅ Agent {agent_id} completed successfully!"
        print(completion_message)
        logger.info(completion_message)
        
        active_agents[agent_id]["status"] = "completed"
        
    except Exception as e:
        error_message = f"❌ Agent {agent_id} encountered an error: {e}"
        print(error_message)
        logger.error(error_message)
        active_agents[agent_id]["status"] = "error"
        raise
    
    # finally:
    #     if hasattr(agent, 'close'):
    #         await agent.close()

# WebSocket endpoints for log streaming
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)

@app.websocket("/ws/session/{session_id}/logs")
async def websocket_session_logs(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for session-specific real-time log streaming"""
    await websocket.accept()
    
    # Initialize session connections if not exists
    if session_id not in session_connections:
        session_connections[session_id] = set()
    
    session_connections[session_id].add(websocket)
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        if session_id in session_connections:
            session_connections[session_id].discard(websocket)
            if not session_connections[session_id]:
                del session_connections[session_id]

@app.on_event("startup")
async def startup_event():
    # Start the background log broadcasting task
    asyncio.create_task(broadcast_logs())
    await asyncio.sleep(1)
    print("📡 Log streaming server integrated successfully!")

@app.post("/agent/start", response_model=TaskResponse)
async def start_agent(request: TaskRequest, background_tasks: BackgroundTasks):
    agent_id = request.agent_id or f"agent_{uuid.uuid4().hex[:8]}"
    session_id = request.session_id or f"session_{uuid.uuid4().hex[:8]}"
    debug_port = get_free_port()
    
    if agent_id in active_agents and active_agents[agent_id]["status"] == "running":
        raise HTTPException(status_code=400, detail="Agent is already running")
    
    background_tasks.add_task(
        run_agent_task,
        request.task,
        agent_id,
        session_id,        request.user_id or "default_user",
        request.headless or False
    )
    
    return TaskResponse(
        agent_id=agent_id,
        session_id=session_id,
        status="starting",
        websocket_url="ws://localhost:8007/ws/logs",
        session_websocket_url=f"ws://localhost:8007/ws/session/{session_id}/logs",
        debug_port=debug_port
    )

@app.get("/agent/{agent_id}/status", response_model=AgentStatusResponse)
async def get_agent_status(agent_id: str):
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    agent_data = active_agents[agent_id]
    return AgentStatusResponse(
        agent_id=agent_id,
        status=agent_data["status"],
        task=agent_data["task"],
        session_id=agent_data["session_id"],
        debug_port=agent_data["debug_port"],
        started_at=agent_data["started_at"]
    )

@app.get("/agents")
async def list_agents():
    return {"agents": active_agents}

@app.delete("/agent/{agent_id}")
async def stop_agent(agent_id: str):
    if agent_id not in active_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    active_agents[agent_id]["status"] = "stopped"
    return {"message": f"Agent {agent_id} stopped"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_agents": len([a for a in active_agents.values() if a["status"] == "running"]),
        "total_agents": len(active_agents),
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007, log_level="info")
