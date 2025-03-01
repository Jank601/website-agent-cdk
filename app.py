#!/usr/bin/env python3
# This is the entry point for your AWS CDK application.
# It imports the necessary CDK modules and initializes the stack for deployment.
import aws_cdk as cdk
from website_agent_cdk.website_agent_cdk_stack import WebsiteAgentCdkStack

# Initialize the CDK application.
app = cdk.App()

# Add the MainStack to the application.
WebsiteAgentCdkStack(app, "WebsiteAgentCdkStack")

# Synthesize the app into an AWS CloudFormation template.
app.synth()