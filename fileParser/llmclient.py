import os
from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()
azure_api_key = os.getenv("MODEL_API_KEY")
azure_model_name = os.getenv("MODEL_NAME")
azure_model_endpoint = os.getenv("MODEL_BASE_URL")
azure_api_version = os.getenv("MODEL_API_VERSION")
deployment_name = os.getenv('DEPLOYMENT_NAME')
api_type = os.getenv('MODEL_API_TYPE')

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

class LLMClient:
    def __init__(self):
        # Optional: store env variables in instance if needed later
        self.api_key = azure_api_key
        self.model_name = azure_model_name
        self.endpoint = azure_model_endpoint
        self.api_version = azure_api_version
        self.deployment_name = deployment_name
        self.api_type = api_type

        self.client = AzureOpenAI(
            azure_endpoint=azure_model_endpoint,
            api_version=azure_api_version,
            api_key=azure_api_key,
        )

    @log_execution_time
    def get_completion(self, messages):
        """
        Get a completion from the Azure OpenAI model based on the provided messages.

        :param messages: List of messages to send to the model. Each message should be a dictionary
                         with 'role' and 'content' keys.
        :return: The model's response as a string.
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.3
            )
            print("LLM Response: ", completion.choices[0].message.content)
            return completion.choices[0].message.content
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
    
    def getLLMconfig(self):
        config_list = [
            {
                "model": self.model_name,
                "api_key": self.api_key,
                "base_url": self.endpoint,
                "api_type": self.api_type,
                "api_version": self.api_version
            }
        ]
        
        llm_config = {
            "seed": 42,
            "config_list": config_list,
            "temperature": 0.5
        }

        return llm_config
