import asyncio
import json
import logging
import os
import re
import uuid
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import AsyncGenerator

# Set up logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

import time
import functools
def log_execution_time(func):
    @functools.wraps(func)  # Preserve original function metadata
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Function '{func.__name__}' took {execution_time:.4f} seconds to execute.")
        return result

    return wrapper

def generate_unique_filename(base_path: str, extension: str) -> str:
    """Generate a unique filename with timestamp and UUID"""
    # Create directory if it doesn't exist
    directory = os.path.dirname(base_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{base_path}_{timestamp}_{unique_id}.{extension}"
    return filename


def extract_code_from_markdown(markdown_content: str) -> str:
    """Extract Python code blocks from markdown content"""
    # Pattern to match Python code blocks (```python ... ```)
    pattern = r"```python\s*(.*?)\s*```"
    match = re.search(pattern, markdown_content, re.DOTALL)

    if match:
        return match.group(1).strip()
    return None


# Function to clean history
def clean_history(input_path: str, output_path: str) -> str:
    """
    Clean screenshot values and coordinate objects from history JSON file.
    """
    logger.info(f"Cleaning history file: {input_path}")
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(exist_ok=True)

    with open(input_path, "r") as f:
        history_data = json.load(f)

    for entry in history_data.get("history", []):
        state = entry.get("state", {})
        if "screenshot" in state:
            state["screenshot"] = ""
        for element in state.get("interacted_element", []):
            if isinstance(element, dict):
                element["page_coordinates"] = {}
                element["viewport_coordinates"] = {}
                element["viewport_info"] = {}

    with open(output_path, "w") as f:
        json.dump(history_data, f, indent=2)

    logger.info(f"Cleaned history saved to: {output_path}")
    return str(output_path)


def extract_interacted_elements(
    cleaned_history_path: str, elements_file_path: str
) -> str:
    """
    Extract interacted elements, current_state, and actions from cleaned
    history and save to a new JSON file.

    Args:
        cleaned_history_path: Path to the cleaned history JSON file.

    Returns:
        Path to the JSON file containing the extracted data.
    """
    logger.info("Extracting interacted elements and model outputs")

    with open(cleaned_history_path, "r") as f:
        history_data = json.load(f)

    extracted_data = []
    for entry in history_data.get("history", []):
        # Extract current_state and action from model_output
        model_output = entry.get("model_output", {})
        current_state = model_output.get("current_state", {})
        action = model_output.get("action", [])
        result = model_output.get("result", {})

        # Extract interacted elements
        elements = entry.get("state", {}).get("interacted_element", [])
        interacted_elements = [
            {
                "tag_name": element.get("tag_name"),
                "xpath": element.get("xpath"),
                "attributes": element.get("attributes"),
                "css_selector": element.get("css_selector"),
                "entire_parent_branch_path": element.get(
                    "entire_parent_branch_path"
                ),
            }
            for element in elements
            if isinstance(element, dict)
        ]

        # Combine extracted data into a single structure
        extracted_data.append(
            {
                "current_state": current_state,
                "action": action,
                "interacted_elements": interacted_elements,
                "result": result,
            }
        )

    # Save the extracted data to the JSON file
    with open(elements_file_path, "w") as f:
        json.dump({"extracted_data": extracted_data}, f, indent=2)

    logger.info(f"Extracted data saved to: {elements_file_path}")
    return str(elements_file_path)


async def log_streamer(
    agent_run_future: asyncio.Future, session_id: str
) -> AsyncGenerator[str, None]:
    """Session-aware log streamer with isolated loggers"""
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    # Create session-specific loggers
    agent_logger = logging.getLogger(f"browser_use.session.{session_id}.agent")
    controller_logger = logging.getLogger(
        f"browser_use.session.{session_id}.controller.service"
    )

    # Prevent propagation to root logger
    agent_logger.propagate = False
    controller_logger.propagate = False

    # Add handlers to session loggers
    agent_logger.addHandler(handler)
    controller_logger.addHandler(handler)
    agent_logger.setLevel(logging.INFO)
    controller_logger.setLevel(logging.INFO)

    try:
        yield (
            f'data: {{"message": "Session Started", "type": "step",'
            f' "session_id": "{session_id}"}}\n\n'
        )

        while not agent_run_future.done():
            await asyncio.sleep(0.1)
            logs = log_capture.getvalue()
            if logs:
                for line in logs.strip().split("\n"):
                    # Filter out 'Task Status: Unknown' with blank page scenario
                    if "Task Status: Unknown" in line:
                        continue
                    if not line.strip():
                        continue

                    # Handle 'Agent Memory:'
                    if line.startswith("🤖 Agent Memory:"):
                        # parts = line.split(":", 1)
                        # if len(parts) > 1:
                        #     info_content = parts[1].strip()
                        #     if info_content:  # Only send if there's content
                        #         yield (
                        #             f'data: {{"message": "{info_content}",'
                        #             f' "type": "step", "session_id":'
                        #             f' "{session_id}", "info": "Agent Memory"}}\n\n'
                        #         )
                        continue

                    # Handle 'Agent\'s Next Task:'
                    if line.startswith("🎯 Agent Next Task:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            next_task = parts[1].strip()
                            yield (
                                f'data: {{"message": "{next_task}", "type":'
                                f' "step", "session_id": "{session_id}", "info":'
                                f' "Agent Next Task"}}\n\n'
                            )
                        continue

                    # Handle 'Agent Task Status:'
                    if line.startswith("✔️ Task Status:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            task_status = parts[1].strip()
                            yield (
                                f'data: {{"message": "{task_status}", "type":'
                                f' "step", "session_id": "{session_id}", "info":'
                                f' "Agent Task Status"}}\n\n'
                            )
                        continue

                    # Handle '✨ Starting task:'
                    if line.startswith("✨ Starting task:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            task_content = parts[1].strip()
                            yield (
                                f'data: {{"message": "Initiating Agents ...",'
                                f' "type": "step", "session_id":'
                                f' "{session_id}", "info": "Starting Task"}}\n\n'
                            )
                        continue

                    if line.startswith("📄 Result:"):
                        parts = line.split(":", 1)
                        if len(parts) > 1:
                            result_content = parts[1].strip()
                            yield (
                                f'data: {{"message": "{result_content}",'
                                f' "type": "step", "session_id":'
                                f' "{session_id}", "info": "Task Result"}}\n\n'
                            )
                        continue

                    if line.startswith("✅ Task completed"):
                        yield (
                            f'data: {{"message": "Task completed", "type":'
                            f' "step", "session_id": "{session_id}", "info":'
                            f' "Task Completed"}}\n\n'
                        )

                    # Filter out 'filepath' lines
                    if "filepath" in line:
                        match = re.search(r"filepath\s*:\s*(.+)", line)
                        if match:
                            elements_file_path = match.group(1)
                            yield (
                                f'data: {{"message": "Test Case Received as'
                                f' TASK", "type": "step", "path":'
                                f' "{elements_file_path}", "session_id":'
                                f' "{session_id}"}}\n\n'
                            )
                        continue


                log_capture.seek(0)
                log_capture.truncate()

        result = await agent_run_future
        yield (
            f'data: {{"message": "Session Ended", "type": "step",'
            f' "session_id": "{session_id}"}}\n\n'
        )

    except Exception as e:
        yield (
            f'data: {{"message": "Error occurred: {str(e)}", "type":'
            f' "error", "session_id": "{session_id}"}}\n\n'
        )
        raise e
