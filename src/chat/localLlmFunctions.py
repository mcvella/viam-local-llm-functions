from typing import ClassVar, Mapping, Sequence, Any, Dict, Optional, Tuple, Final, List, cast
from typing_extensions import Self
from urllib.request import urlretrieve

import viam
from viam.module.types import Reconfigurable
from viam.proto.app.robot import ComponentConfig
from viam.proto.common import ResourceName, Vector3
from viam.resource.base import ResourceBase
from viam.resource.types import Model, ModelFamily

from semantic_router import Route
from semantic_router.utils.function_call import get_schema
from semantic_router.encoders import HuggingFaceEncoder


from semantic_router import RouteLayer

from llama_cpp import Llama
from semantic_router.llms.llamacpp import LlamaCppLLM
import viam.services

encoder = HuggingFaceEncoder()

from chat_service_api import Chat
from viam.logging import getLogger

import time
import asyncio
import os

LOGGER = getLogger(__name__)
MODEL_DIR = os.environ.get(
    "VIAM_MODULE_DATA", os.path.join(os.path.expanduser("~"), ".data", "models")
)

class localLlmFunctions(Chat, Reconfigurable):

    MODEL: ClassVar[Model] = Model(ModelFamily("mcvella", "chat"), "local-llm-functions")
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
        # here we validate config, the following is just an example and should be updated as needed
        some_pin = config.attributes.fields["some_pin"].number_value
        if some_pin == "":
            raise Exception("A some_pin must be defined")
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
                "A chat between a curious user and a friendly, laconic, and helpful assistant",
            )
        )
        self.route_config = list(attrs.get("routes", []))
        self.debug = bool(attrs.get("debug", False))
        self.deps = dependencies
        asyncio.create_task(self._get_model()).add_done_callback(self._ensure_llama)

    async def chat(self, message: str) -> str:
        if self.llama is None:
            raise Exception("LLM is not ready")

        rl_response = self.rl(message)
        if (rl_response.name != None):
            await self.route_methods[rl_response.name](**rl_response.function_call)
            message = "Say 'OK, I did " + message + "'"

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
        self.rl = RouteLayer(encoder=encoder, routes=self._build_routes(), llm=llm)

        LOGGER.debug("LLM is ready")

    def _build_routes(self):
        routes = []
        for r in self.route_config:
            # component or service, but plural
            type = getattr(viam, r.type  + "s")
            subtype = getattr(type, r.subtype)
            base_class = getattr(subtype, ''.join(x.capitalize() for x in r.subtype.split('_')))
            resource_dep = self.deps[base_class.get_resource_name(r.dep)]
            resource = cast(base_class, resource_dep)
            self.route_methods[r.name] = getattr(resource, r.method)
            route = Route(
                name=r.name,
                description=r.get('description', ''),
                utterances=r.utterances,
                function_schema=get_schema(self.route_methods[r.name])
            )
            routes.append(route)
        return routes