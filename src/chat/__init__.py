"""
This file registers the model with the Python SDK.
"""

from viam.resource.registry import Registry, ResourceCreatorRegistration

from chat_service_api import Chat
from .localLlmFunctions import localLlmFunctions

Registry.register_resource_creator(Chat.SUBTYPE, localLlmFunctions.MODEL, ResourceCreatorRegistration(localLlmFunctions.new))
