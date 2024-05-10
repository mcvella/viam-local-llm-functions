from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self
from urllib.request import urlretrieve

# this is ugly and hard to maintain, but they seem required for any dep subtype - maybe an issue with registry?
from viam.components import audio_input, arm, base, board, camera, encoder, gantry, generic, gripper, input, motor, movement_sensor, pose_tracker, power_sensor, sensor, servo
from viam.services import generic, mlmodel, motion, navigation, sensors, slam, vision

from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily
from viam.utils import struct_to_dict
from semantic_router import Route
from semantic_router.utils.function_call import get_schema
from semantic_router.encoders import HuggingFaceEncoder


from semantic_router import RouteLayer

from llama_cpp import Llama
from semantic_router.llms.llamacpp import LlamaCppLLM

llm_encoder = HuggingFaceEncoder()

from chat_service_api import Chat
from viam.logging import getLogger

import importlib
import asyncio
import os
import re

LOGGER = getLogger(__name__)
MODEL_DIR = os.environ.get(
    "VIAM_MODULE_DATA", os.path.join(os.path.expanduser("~"), ".data", "models")
)

class localLlmToolRouter(Chat, Reconfigurable):

    MODEL: ClassVar[Model] = Model(ModelFamily("mcvella", "chat"), "local-llm-tool-router")
    LLM_REPO = ""
    LLM_FILE = ""
    MODEL_PATH = os.path.abspath(os.path.join(MODEL_DIR, LLM_FILE))
    llama = None
    rl = RouteLayer
    route_methods = {}

    @classmethod
    def new(cls, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]) -> Self:
        my_class = cls(config.name)
        my_class.reconfigure(config, dependencies)
        return my_class

    @classmethod
    def validate(cls, config: ComponentConfig):
        return

    def reconfigure(self, config: ComponentConfig, dependencies: Mapping[ResourceName, ResourceBase]):
        attrs = struct_to_dict(config.attributes)
        LOGGER.debug(attrs)
        self.LLM_REPO = str(
            attrs.get("llm_repo", "TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
        )
        self.LLM_FILE = str(
            attrs.get("llm_file", "mistral-7b-instruct-v0.2.Q5_K_S.gguf")
        )
        self.MODEL_PATH = os.path.abspath(os.path.join(MODEL_DIR, self.LLM_FILE))

        self.n_gpu_layers = int(attrs.get("n_gpu_layers", -1))
        self.n_ctx = int(attrs.get("n_ctx", 2048))
        self.temperature = float(attrs.get("temperature", 0.75))
        self.system_message = str(
            attrs.get(
                "system_message",
                "A chat between a curious user and a friendly, laconic, and helpful assistant. As an assistant you do provide specific detail from tasks performed.",
            )
        )
        self.route_config = list(attrs.get("tools", []))
        self.debug = bool(attrs.get("debug", False))
        self.deps = dependencies
        asyncio.create_task(self._get_model()).add_done_callback(self._ensure_llama)

    async def chat(self, message: str) -> str:
        if self.llama is None:
            raise Exception("LLM is not ready")

        LOGGER.debug("will do chat")
        rl_response = self.rl(message)
        LOGGER.error(rl_response)
        if (rl_response.name != None):
            output = await self.route_methods[rl_response.name](**rl_response.function_call)
            message = "Say 'OK, I did the task " + message + "' and got the following response: " + str(output)

        LOGGER.debug("MESSAGE: " + message)
        response = self.llama.create_chat_completion(
            messages=[
                {"role": "system", "content": self.system_message},
                {"role": "user", "content": message},
            ],
            temperature=self.temperature,
        )
        return response["choices"][0]["message"]["content"]
    
    async def _get_model(self):
        if not os.path.exists(self.MODEL_PATH):
            LLM_URL = (
                f"https://huggingface.co/{self.LLM_REPO}/resolve/main/{self.LLM_FILE}"
            )
            LOGGER.info(f"Fetching model {self.LLM_FILE} from {LLM_URL}")
            urlretrieve(LLM_URL, self.MODEL_PATH, self._log_progress)

    def _log_progress(self, count: int, block_size: int, total_size: int) -> None:
        percent = count * block_size * 100 // total_size
        LOGGER.info(f"\rDownloading {self.LLM_FILE}: {percent}%")

    def _ensure_llama(self, _task: asyncio.Task[None]):
        self.llama = Llama(
            model_path=self.MODEL_PATH,
            chat_format="chatml",
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=self.n_ctx,
            verbose=self.debug,
        )
        llm = LlamaCppLLM(name="mistral-7b-instruct", llm=self.llama, max_tokens=None)
        self.rl = RouteLayer(encoder=llm_encoder, routes=self._build_routes(), llm=llm)

        LOGGER.debug("LLM is ready")

    def _build_routes(self):
        routes = []
        for r in self.route_config:
            resource_module = importlib.import_module('viam.' + r['type'] + "s" + '.' + r['subtype'])
            base_class = getattr(resource_module, ''.join(x.capitalize() for x in r['subtype'].split('_')))
            resource_dep = self.deps[base_class.get_resource_name(r['dep'])]
            resource = cast(base_class, resource_dep)
            self.route_methods[r['name']] = getattr(resource, r['method'])
            route = Route(
                name=r['name'],
                description=r.get('description', ''),
                utterances=r['utterances'],
                function_schema=get_schema(self.route_methods[r['name']])
            )
            # remote * and **__, rl's get_schema gets tripped up with these
            route.function_schema['signature'] = re.sub( r'\*\s*,|,\s*\*\*__', '', route.function_schema['signature'])           
            LOGGER.debug(route)
            routes.append(route)
        return routes