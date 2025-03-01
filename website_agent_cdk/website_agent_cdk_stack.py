from aws_cdk import Stack
from constructs import Construct
from typing import Any
from .agent_construct import AgentConstruct
from .invoke_agent_lambda import AgentInvokerLambda

class WebsiteAgentCdkStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs: Any) -> None:
        super().__init__(scope, id, **kwargs)

        # Initialize the AgentConstruct
        agent = AgentConstruct(self, "AgentConstruct")

        AgentInvokerLambda(
        self,
        "AgentInvokerLambda",
        agent_id=agent.agent_id,
        agent_alias_id=agent.agent_alias_id 
        )