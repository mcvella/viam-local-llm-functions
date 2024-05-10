import asyncio
import sys

from viam.module.module import Module
from chat_service_api import Chat
from .chat.local_llm_tool_router import localLlmToolRouter

async def main():
    """This function creates and starts a new module, after adding all desired resources.
    Resources must be pre-registered. For an example, see the `__init__.py` file.
    """
    module = Module.from_args()
    module.add_model_from_registry(Chat.SUBTYPE, localLlmToolRouter.MODEL)
    await module.start()

if __name__ == "__main__":
    asyncio.run(main())
