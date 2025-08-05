from multiprocessing import shared_memory
import json
import uuid
from a2a.types import MessageSendParams, Message, Part, TextPart

def client_send(json_str, shm_name):
    shm = shared_memory.SharedMemory(name=shm_name, create=False)
    #b = json.dumps(msg_dict).encode()
    print("Got here")
    shm.buf[:len(json_str)] = str.encode(json_str)
    shm.close()
    # then monitor another shared memory area for the response

if __name__ == "__main__":
 #   req = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "message/send"}
    text_part = TextPart(text="Hello, agent!", kind="text")
    part = Part(root=text_part)
    message = Message(messageId="msg-001", role="user", parts=[part])

    params = MessageSendParams(message=message, metadata={})

    # Serialize to JSON string (exclude unused optional fields)
    json_str = params.model_dump_json(exclude_none=True)
    client_send(json_str, shm_name="test_shm")
    # then read from "a2a_resp"

