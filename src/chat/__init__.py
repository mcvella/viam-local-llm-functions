"""
This file registers the model with the Python SDK.
"""

from viam.resource.registry import Registry, ResourceCreatorRegistration

from chat_service_api import Chat
from .local_llm_tool_router import localLlmToolRouter

Registry.register_resource_creator(Chat.SUBTYPE, localLlmToolRouter.MODEL, ResourceCreatorRegistration(localLlmToolRouter.new))
