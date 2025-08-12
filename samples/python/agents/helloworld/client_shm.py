from multiprocessing import shared_memory
import json
import uuid
from a2a.types import MessageSendParams, Message, Part, TextPart, SendMessageRequest
import time
import sys
from my_outl import *

BENCHMARK_PORT = 0xf4 

def client_send(json_str, shm):
    #b = json.dumps(msg_dict).encode()
    payload = str.encode(json_str)
    payload_len = len(json_str)
    lib.my_ioperm(c_ushort(BENCHMARK_PORT));
    lib.my_outl(1, c_ubyte(200))
    shm.buf[:payload_len] = payload
    #shm.close()
    # then monitor another shared memory area for the response

if __name__ == "__main__":
 #   req = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "message/send"}


    if len(sys.argv) != 2:
        print("Usage: python client_shm.py <payload_size>")
        sys.exit(1)

    payload_size = int(sys.argv[1])

    text="a" * payload_size;
    text_part = TextPart(text=text, kind="text")
    part = Part(root=text_part)
    message = Message(messageId="msg-001", role="user", parts=[part])

    params = MessageSendParams(message=message, metadata={})
    req = SendMessageRequest(id="req-001", params=params)

    # Serialize to JSON string (exclude unused optional fields)
    #json_str = params.model_dump_json(exclude_none=True)
    json_str = req.model_dump_json(exclude_none=True)
    shm = shared_memory.SharedMemory(name="test_shm", create=False)
    for i in range(10):
        print(f"{i}/10")

        client_send(json_str, shm)
        # TODO: wait for response
        lib.my_outl(1, c_ubyte(203))
        time.sleep(1)

    # then read from "a2a_resp"

