# local-llm-tool_router modular service

This module implements the [viam-labs chat API](https://github.com/viam-labs/chat-api) in a mcvella:chat:local-llm-tool_router model.
This model leverages [semantic router](https://github.com/aurelio-labs/semantic-router) and a local llm to allow you to specify specific configured tools - component and service functions that can be contextually routed to and executed, based on chat input.

For example, if your machine has a configured servo called 'headMotor', you could configure a tool to know about the *move()* method for this servo, creating a tool called "turn_head".
You can then say something like "Turn your head to the right", and the move command parameters would be generated by the LLM and the move() function called to move the head right.

## Requirements

This module uses llama.cpp, with the default model mistral-7b-instruct-v0.2.Q5_K_S.gguf.
This model will run on most CPUs, and on most laptops, but will be much more performant with Nvidia (CUDA) GPUs.

## Build and Run

To use this module, follow these instructions to [add a module from the Viam Registry](https://docs.viam.com/registry/configure/#add-a-modular-resource-from-the-viam-registry) and select the `mcvella:chat:local-llm-tool_router` model from the [`mcvella:chat:local-llm-tool_router` module](https://github.com/mcvella/viam-local-llm-tool_router).

## Configure your chat

> [!NOTE]  
> Before configuring your chat, you must [create a machine](https://docs.viam.com/manage/fleet/machines/#add-a-new-machine).

Navigate to the **Config** tab of your robot’s page in [the Viam app](https://app.viam.com/).
Click on the **Components** subtab and click **Create component**.
Select the `chat` type, then select the `mcvella:chat:local-llm-tool_router` model.
Enter a name for your chat and click **Create**.

On the new component panel, copy and paste the following attribute template into your chat’s **Attributes** box:

```json
{
    "system_message": "A chat between a curious user and a friendly, laconic, and helpful assistant. As an assistant you do provide specific detail from tasks performed.",
    "n_gpu_layers": -1,
    "temperature": 0.75,
    "debug": false,
    "llm_repo": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
    "llm_file": "mistral-7b-instruct-v0.2.Q5_K_S.gguf"
}
```

> [!NOTE]  
> For more information, see [Configure a Robot](https://docs.viam.com/manage/configuration/).

### Attributes

The following attributes are available for `viam-labs:chat:mcvella:chat:local-llm-tool_router` chats:

| Name | Type | Inclusion | Description |
| ---- | ---- | --------- | ----------- |
| `system_message` | string | Optional |  The system message to pass as context to each chat interaction. |
| `n_gpu_layers` | int | Optional |  The number of GPU layers to use, default -1 (all).  For CPU, use 0 |
| `temperature` | float | Optional |  value to determine the randomness of the responses from the model. A high temperature, i.e. 5, would result in very different values while running the same prompt repeatedly. A value that's too low, i.e. 0.2, would result in more "robotic" responses. Default value is 0.75. |
| `llm_repo` | string | Optional |  The HuggingFace repo id used to download the model. Defaults to "TheBloke/Mistral-7B-Instruct-v0.2-GGUF" |
| `llm_file` | int | Optional |  The HuggingFace file used to download the model. Must be specified if llm_repo is specified. Defaults to "mistral-7b-instruct-v0.2.Q5_K_S.gguf" |
| `debug` | bool | Optional |  Turn on LLM debug output if set to true.  Defaults to false. |
| `n_ctx` | integer | Optional | The maximum number of tokens that the model can account for when processing a response.  Defaults to 2048 |
| `tools` | object | Required | The route configuration for LLM functions.  See below for details. |

### Example Configuration

```json
{
  "tools": [
    {
      "name": "move_head",
      "description": "Move robot's head by moving a servo to a given angle, 90 degrees being straight, 0 degrees being far left, 180 degrees being far right",
      "dep": "neckServo",
      "type": "component",
      "subtype": "servo",
      "method": "move",
      "utterances": [
        "Turn your head to the left",
        "Look straight ahead",
        "Turn your head to the right",
        "Look left",
        "Turn your head left now"
      ]
    }
 ]
}
```

A tool gives the LLM information about a given Viam component or service method that is associated with a specified dependency.
The specified resource (*dep*) must be included in the *depends_on* field for the configured *local-llm-tool_router* service.
You must then specify the resource *type* (component or service), the resource *subtype* (for example, 'motor'), and associated method.

This module is written in Python and uses the [Viam Python SDK](https://python.viam.dev/), so you must use methods as they are specified in the Python SDK.
For example, you can select 'set_power' as a valid *method* for a motor component, not 'SetPower'.
Currently, only built-in resource APIs are supported, custom APIs are not.

The method documentation and signature will be read by the LLM in order to attempt to understand how to use the method.
You can provide additional information with a *description*, where you can provide detail around this specific instance of the method.
For example, if you have one servo that controls a robot's head and another servo that controls the robot's jaw, you would set up two routes and can explain what each servo is for in the respective *description* fields.

*name* is a unique identifier for the tool.

*utterances* are example phrases that should trigger routing to a given tool.
