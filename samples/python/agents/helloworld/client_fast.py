from multiprocessing import shared_memory
import json
import struct
from a2a.types import MessageSendParams, Message, Part, TextPart, SendMessageRequest
import time
import sys
from my_outl import *

BENCHMARK_PORT = 0xf4

def client_send(payload_bytes, shm_req, shm_resp, shm_flag, payload_size):
    """Send request and wait for response - optimized for speed"""
    payload_len = len(payload_bytes)
    
    # Write length and payload
    shm_req.buf[:4] = struct.pack('I', payload_len)
    shm_req.buf[4:4+payload_len] = payload_bytes
    
    # Send benchmark signal
    lib.my_ioperm(c_ushort(BENCHMARK_PORT))
    lib.my_outl(payload_size, c_ubyte(200))
    
    # Set request ready flag
    shm_flag.buf[0] = 1
    
    # Busy-wait for response flag (fastest response)
    while shm_flag.buf[1] == 0:
        pass
    
    # Read response immediately
    resp_len = struct.unpack('I', shm_resp.buf[:4])[0]
    response_bytes = shm_resp.buf[4:4+resp_len].tobytes()
    
    # Clear response flag
    shm_flag.buf[1] = 0
    
    return json.loads(response_bytes.decode())

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python client_shm.py <payload_size>")
        sys.exit(1)
    
    payload_size = int(sys.argv[1])
    text = "a" * payload_size

    
    text_part = TextPart(text=text, kind="text")
    part = Part(root=text_part)
    message = Message(messageId="msg-001", role="user", parts=[part], context_id=f'{payload_size}')
    params = MessageSendParams(message=message, metadata={}, context_id=payload_size)
    req = SendMessageRequest(id="req-001", params=params)
    
    # Pre-serialize to bytes (do once, reuse)
    json_bytes = req.model_dump_json(exclude_none=True).encode()
    
    # Connect to shared memory buffers
    shm_req = shared_memory.SharedMemory(name="test_shm_req", create=False)
    shm_resp = shared_memory.SharedMemory(name="test_shm_resp", create=False)
    shm_flag = shared_memory.SharedMemory(name="test_shm_flag", create=False)


    # -------------- warmup -------------------
    # warmup
    #for i in range(5):
    #    text_w = "f" * payload_size
    #    text_part_w = TextPart(text=text_w, kind="text")
    #    part_w = Part(root=text_part_w)
    #    message_w = Message(messageId="msg-001", role="user", parts=[part], context_id=f'{payload_size}')
    #    params_w = MessageSendParams(message=message_w, metadata={}, context_id=0)
    #    req_w = SendMessageRequest(id="req-001", params=params_w)
    #    
    #    # Pre-serialize to bytes (do once, reuse)
    #    json_bytes_w = req_w.model_dump_json(exclude_none=True).encode()
    #    start = time.perf_counter()

    #    # Send request and wait for response
    #    response = client_send(json_bytes_w, shm_req, shm_resp, shm_flag, payload_size)

    #    elapsed = time.perf_counter() - start

    #    # Send completion signal
    #    lib.my_outl(0, c_ubyte(203))

    #    # Print result
    #    if 'error' in response:
    #        print(f"Error: {response['error']}")
    #    else:
    #        print(f"Warmup ({elapsed*1000:.2f}ms)")
    
    try:
        for i in range(100):
            print(f"Request {i+1}/100", end=" ")
            
            start = time.perf_counter()
            
            # Send request and wait for response
            response = client_send(json_bytes, shm_req, shm_resp, shm_flag, payload_size)
            
            elapsed = time.perf_counter() - start
            
            # Send completion signal
            lib.my_outl(payload_size, c_ubyte(203))
            
            # Print result
            if 'error' in response:
                print(f"Error: {response['error']}")
            else:
                #print('OK')
                print(f"OK ({elapsed*1000:.2f}ms)")
            
            time.sleep(0.01)  # Minimal delay
            
    finally:
        shm_req.close()
        shm_resp.close()
        shm_flag.close()
