from browser_use import Agent
import asyncio


class AgentController:
    """Controls an agent's execution with pause, resume, and stop capabilities"""
    
    def __init__(self, agent: Agent):
        """Initialize with an agent instance"""
        self.agent = agent
        self.running = False
        self.paused = False
        self._run_task = None
        
    async def run_agent(self, max_steps=30):
        """Run the agent with control flow for pausing and stopping"""
        self.running = True
        try:
            result = await self.agent.run(max_steps=max_steps)
            return result
        finally:
            self.running = False
            
    def start(self, max_steps=30):
        """Start the agent execution and store the task"""
        if self._run_task is None or self._run_task.done():
            self._run_task = asyncio.create_task(self.run_agent(max_steps=max_steps))
        return self._run_task
    
    def pause(self):
        """Pause the agent execution"""
        if self.running and not self.paused:
            self.agent.pause()
            self.paused = True
            return True
        return False
    
    def resume(self):
        """Resume the agent execution if paused"""
        if self.running and self.paused:
            self.agent.resume()
            self.paused = False
            return True
        return False
    
    def stop(self):
        """Stop the agent execution"""
        if self.running:
            self.agent.stop()
            self.running = False
            return True
        return False
    
    def get_status(self):
        """Get the current status of the agent"""
        if not self.running:
            return "stopped"
        elif self.paused:
            return "paused"
        else:
            return "running"
        

    def update_task(self, new_task: str) -> bool:
        """Update the agent's task with new instructions"""
        if self.running and self.paused:
            self.agent.add_new_task(new_task)
            return True
        return False