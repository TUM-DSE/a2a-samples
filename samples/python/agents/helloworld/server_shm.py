# shared_server.py

import asyncio
from multiprocessing import shared_memory
import json
from a2a.server.request_handlers import JSONRPCHandler
from agent_executor import HelloWorldAgentExecutor
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
)
from TimedRequestHandler import *

def read_request_from_shm(shm, size):
    b = shm.buf[:size].tobytes()
    shm.buf[:size] = b'\x00' * size
    return b.rstrip(b"\x00")

async def main_loop():

    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )
    # --8<-- [end:AgentSkill]

    extended_skill = AgentSkill(
        id='super_hello_world',
        name='Returns a SUPER Hello World',
        description='A more enthusiastic greeting, only for authenticated users.',
        tags=['hello world', 'super', 'extended'],
        examples=['super hi', 'give me a super hello'],
    )
    public_agent_card = AgentCard(
        name='Hello World Agent',
        description='Just a hello world agent',
        #url='http://localhost:9999/',
        url='http://192.168.32.10:9999',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],  # Only the basic skill for the public card
        supports_authenticated_extended_card=True,
    )

    request_handler = TimedRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    handler = JSONRPCHandler(request_handler=request_handler, agent_card=public_agent_card)
    shm = shared_memory.SharedMemory(name="test_shm", create=True, size=1024);
    while True:
        raw = read_request_from_shm(shm, 1024)
        if not raw:
            await asyncio.sleep(0.1)
            continue
        req = json.loads(raw.decode())
        # mimic ASGI request body and request scope
        print(f'Request: {raw.decode()}')
        #response = await handler.handle_jsonrpc(req)
        mparams = MessageSendParams.model_validate_json(raw.decode()) 
        print(f"Mparams: {mparams}")
        response = await handler.request_handler.on_message_send(params=mparams)
        #resp_bytes = json.dumps(response).encode()
        print(f'Response: {response}')
        # write back to shared memory or another output region...
        # (you define output buffer similarly)
        await asyncio.sleep(0.1)
    shm.close()
    shm.unlink()

if __name__ == "__main__":
    import argparse
    asyncio.run(main_loop())

