"""Every request goes through the model's observe-act-verify agent loop."""
from command_types import RequestResult

class RequestCancelled(RuntimeError): pass

class RequestProcessor:
    def __init__(self,brain,executor_factory=None,on_progress=None):
        self.brain=brain
        self.executor_factory=executor_factory
        self.on_progress=on_progress

    def handle(self,query,cancel_event=None):
        from agent_tools import AgentToolExecutor
        executor=(self.executor_factory or AgentToolExecutor)()
        reply=self.brain.run(query,executor,cancel_event=cancel_event,on_progress=self.on_progress)
        kind='agent' if executor.trace else 'answer'
        return RequestResult(reply,kind)
