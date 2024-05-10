import asyncio
import os

from viam.robot.client import RobotClient
from viam.logging import getLogger

from chat_service_api import Chat

LOGGER = getLogger(__name__)

# these must be set, you can get them from your robot's 'CODE SAMPLE' tab
machine_api_key_id = os.getenv('API_KEY_ID') or ''
machine_api_key = os.getenv('API_KEY') or ''
machine_address = os.getenv('MACHINE_ADDRESS') or ''

async def connect():
    opts = RobotClient.Options.with_api_key(
      api_key=machine_api_key,
      api_key_id=machine_api_key_id
    )
    return await RobotClient.at_address(machine_address, opts)

async def main():
    robot = await connect()

    LOGGER.info('Resources:')
    LOGGER.info(robot.resource_names)

    llm = Chat.from_robot(robot, name="llm")

    prompt = input("How can I help you today?\n")
    print("Thanks for your request! Working on that now...")

    response =  await llm.chat(prompt)
    LOGGER.info(f"Prompt: {prompt}")
    LOGGER.info(f"Answer: {response}")

    # Don't forget to close the machine when you're done!
    await robot.close()

if __name__ == '__main__':
    asyncio.run(main())