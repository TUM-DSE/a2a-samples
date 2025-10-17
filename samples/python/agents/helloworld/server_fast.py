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
    SendMessageRequest,
)
from TimedRequestHandler import *
import sys
import struct

def read_request_from_shm(shm, size):
    """Fast read without rstrip - assumes length prefix"""
    req_len = struct.unpack('I', shm.buf[:4])[0]
    return shm.buf[4:4+req_len].tobytes()

def write_response_to_shm(shm_resp, response_bytes):
    """Write response to shared memory with length prefix"""
    resp_len = len(response_bytes)
    shm_resp.buf[:4] = struct.pack('I', resp_len)
    shm_resp.buf[4:4+resp_len] = response_bytes

async def main_loop(payload_size):
    skill = AgentSkill(
        id='hello_world',
        name='Returns hello world',
        description='just returns hello world',
        tags=['hello world'],
        examples=['hi', 'hello world'],
    )
    
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
        url='http://192.168.32.10:9999',
        version='1.0.0',
        default_input_modes=['text'],
        default_output_modes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        supports_authenticated_extended_card=True,
    )
    
    request_handler = TimedRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    handler = JSONRPCHandler(request_handler=request_handler, agent_card=public_agent_card)
    
    # Create shared memory buffers
    shm_req = shared_memory.SharedMemory(name="test_shm_req", create=True, size=payload_size)
    shm_resp = shared_memory.SharedMemory(name="test_shm_resp", create=True, size=payload_size)
    shm_flag = shared_memory.SharedMemory(name="test_shm_flag", create=True, size=2)
    
    # Initialize flags: [0]=request_ready, [1]=response_ready
    shm_flag.buf[0] = 0
    shm_flag.buf[1] = 0
    
    print(f"Server started, waiting for requests...")
    
    try:
        while True:
            # Busy-wait for request flag (fastest response)
            while shm_flag.buf[0] == 0:
                pass
            
            # Read request
            raw = read_request_from_shm(shm_req, payload_size)
            
            # Clear request flag immediately
            shm_flag.buf[0] = 0
            
            try:
                send_req = SendMessageRequest.model_validate_json(raw.decode())
                
                # Process the request
                response = await handler.on_message_send(send_req)
                
                # Convert response to bytes
                if hasattr(response, 'model_dump_json'):
                    response_bytes = response.model_dump_json(exclude_none=True).encode()
                elif hasattr(response, 'model_dump'):
                    response_bytes = json.dumps(response.model_dump()).encode()
                else:
                    response_bytes = json.dumps(response).encode()
                
                # Write response to shared memory
                write_response_to_shm(shm_resp, response_bytes)
                
                # Set response ready flag
                shm_flag.buf[1] = 1
                
            except Exception as e:
                print(f'Error processing request: {e}')
                error_response = json.dumps({"error": str(e)}).encode()
                write_response_to_shm(shm_resp, error_response)
                shm_flag.buf[1] = 1
                
    finally:
        shm_req.close()
        shm_req.unlink()
        shm_resp.close()
        shm_resp.unlink()
        shm_flag.close()
        shm_flag.unlink()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <payload_size>")
        sys.exit(1)
    payload_size = int(sys.argv[1])
    asyncio.run(main_loop(payload_size + 1000))
