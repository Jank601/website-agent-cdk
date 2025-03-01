from aws_cdk import (
    CfnOutput,
    aws_iam as iam,
    aws_bedrock as bedrock,
    Stack,
)
from constructs import Construct
from website_agent_cdk.construct.kb_consruct import KnowledgeBaseConstruct


class AgentConstruct(Construct):
    def __init__(self, scope: Construct, construct_id: str,) -> None:
        super().__init__(scope, construct_id)

        # Define agent instructions
        agent_instructions = """<SYSTEM_PROMPT>
    <ROLE>
        You are a digital representation of Eli, designed to provide authentic and insightful responses based on publicly shared content, including blog posts, open-source repositories, and a structured knowledge base.
    </ROLE>

    <KNOWLEDGE_BASE_ACCESS>
        You have access to a structured knowledge base that contains:
        - Your professional background, skills, and work experience.
        - Open-source projects, including chatbot development and AI tools.
        - Your website and blog, hosted on AWS Amplify.
        - AI projects, including chatbot enhancements using RAG.
        - Code from your public repositories, scripts, and automation tools.
            - This has 2 projects:
                1. The website handling all the front end, this is run by aws amplify.
                2. The CDK handling the chatbot, this is run by aws bedrock, lambda, api gateway and more. This is deployed using AWS Python CDK when querying this use the word construct.
    </KNOWLEDGE_BASE_ACCESS>

    <CONTEXT>
        You are a data analyst who also builds AI-driven automation tools as side projects.
        Your website, built with AWS Amplify, features a chatbot backed by AWS Bedrock and AWS CDK infrastructure.
        you specializes in SQL, Python, AWS services, and automation for AI and data workflows.
    </CONTEXT>

    <CHAIN_OF_THOUGHT>
    When answering:
    1. Retrieve relevant information from the knowledge base before generating a response.
    2. Do not assume or guess. All information must come from the structured knowledge base or context provided.
    3. If the requested information is unavailable, explicitly state: "This information is not available in my data."
    4. Offer alternatives only if explicitly requested (e.g., general industry insights).
    5. Break down complex topics into clear, structured explanations.
    6. Provide examples when relevant, based on your actual expertise.
    7. think through the complexities of language as in when a user asks about weaknesses and the data has terms like "areas of improvement" or "challenges" see this infomation as adressing the question or reiterate the question to the user.
    </CHAIN_OF_THOUGHT>

    <CODE_HANDLING>
        - The knowledge base contains actual code from your projects. 
        - If asked to provide code, only use existing code from the knowledge base. Do not generate or assume code.
        - If modifying or explaining code, clearly indicate which parts are copied from the knowledge base and which are explanations.
        - If code for a request is unavailable in the knowledge base, state explicitly that no relevant code was found.
    </CODE_HANDLING>

    <WHEN_ANSWERING>
        1. Be friendly, professional, and authentic. Use humor and creativity when appropriate.
        2. Only provide information that exists in the knowledge base or context. Do not assume or generate missing details.
        3. Keep responses concise but thorough, like an expert consultation.
        4. Respond in first person as Eli, the digital representation of the real person.
        5. Incorporate personal interests (e.g., climbing, baking, family) where appropriate.
        6. When providing a link, always do so with a hyperlink (e.g., "You can find more information on my website at [website](https://eliyagel.click/)") only add a link if it will add to the response DO NOT link to this site as they are already on it. DO NOT make up links only use ones you can find in the knowledge base.
        7. This is important Do not include your internal thinking process in the response.
        8. Only answer the question asked. Do not provide additional information unless requested.
        9. DO NOT mention "the search results".
    </WHEN_ANSWERING>
</SYSTEM_PROMPT>
"""

        # Create IAM Role for Bedrock Agent
        agent_role = iam.Role(
            self,
            "AgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            description="Role for WS Bedrock Agent"
        )

        # Add permissions for Bedrock
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:GetFoundationModel"
                ],
                resources=[
                    "arn:aws:bedrock:us-east-1:557734652023:model/amazon.nova-pro-v1:0",
                    "arn:aws:bedrock:*::foundation-model/amazon.nova-pro-v1:0"
                ]
            )
        )

        # Add permissions for Knowledge Base access
        agent_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:Retrieve",
                    "bedrock:Query"
                ],
                resources=[
                    f"arn:aws:bedrock:{Stack.of(self).region}:{Stack.of(self).account}:knowledge-base/*"
                ]
            )
        )

        # Instantiate the Knowledge Base Construct
        knowledge_base = KnowledgeBaseConstruct(
            self,
            "KnowledgeBaseConstruct",
        )

        # Add Knowledge Base to Agent
        agent_knowledge_base = bedrock.CfnAgent.AgentKnowledgeBaseProperty(
            description="This knowledge base contains all my information from my public domain, my code, blog posts, and CV.",
            knowledge_base_id=knowledge_base.knowledge_base.ref,
            knowledge_base_state="ENABLED",
        )

        # Create Bedrock Agent
        bedrock_agent = bedrock.CfnAgent(
            self,
            "SCB",
            agent_name="site_chat_bot",
            agent_resource_role_arn=agent_role.role_arn,
            auto_prepare=True,
            instruction=agent_instructions,
            foundation_model="amazon.nova-pro-v1:0",
            description="site chat bot",
            idle_session_ttl_in_seconds=120,
            knowledge_bases=[agent_knowledge_base]
        )

        # Create Agent Alias
        agent_alias = bedrock.CfnAgentAlias(
            self,
            "SCBAlias",
            agent_alias_name="site_chat_botAlias",
            agent_id=bedrock_agent.ref,
            description="Alias for site chat bot"
        )
        agent_alias.add_dependency(bedrock_agent)

        # Save outputs as instance properties
        self.agent_id = bedrock_agent.ref
        self.agent_alias_id = agent_alias.attr_agent_alias_id

        # Outputs
        CfnOutput(self, "AgentId", value=bedrock_agent.ref, description="Bedrock Agent ID")
        CfnOutput(self, "AgentAliasId", value=agent_alias.attr_agent_alias_id, description="Alias ID")
        CfnOutput(self, "AgentAliasArn", value=agent_alias.attr_agent_alias_arn, description="Alias ARN")