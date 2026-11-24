"""A local protocol fixture that asks the real CLI to read and write two diagnostic files."""
import json
import uuid
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlsplit


def scripted_reply(body, token):
    messages = body.get("messages") or body.get("input") or []
    prompt = json.dumps(messages)
    results = []
    for msg in messages if isinstance(messages, list) else []:
        if not isinstance(msg, dict):
            continue
        if msg.get("role") == "tool" or msg.get("type") == "function_call_output":
            results.append(msg.get("content", msg.get("output")))
        parts = msg.get("content")
        if isinstance(parts, list):
            results.extend(p for p in parts if isinstance(p, dict) and p.get("type") == "tool_result")
    output = json.dumps(results)
    direct = "SONAR_DIRECT_TASK" in prompt
    case = "direct" if direct else "tool" if "SONAR_TOOL_TASK" in prompt else None
    if not case or "SONAR_WRITTEN" in output:
        return case, "finish", None, {}
    if direct and token not in prompt:
        return case, "missing direct value", None, {}
    if direct or token in output:
        command = f"printf '%s\\n' '{token}' > /tmp/sonar-submission && echo SONAR_WRITTEN"
        action = "write"
    else:
        command = "cat /tmp/sonar-code"
        action = "read"
    for tool in body.get("tools") or []:
        declaration = tool.get("function", tool)
        name = declaration.get("name", "")
        if name.lower() not in {"bash", "shell", "shell_command", "exec_command", "terminal"}:
            continue
        schema = declaration.get("parameters") or declaration.get("input_schema") or {}
        props = schema.get("properties", {})
        field = next((f for f in ("command", "cmd") if f in props), None)
        if field:
            args = {field: command}
            for key in ("description", "intent"):
                if key in props:
                    args[key] = "Check the Sonar diagnostic file"
            return case, action, name, args
    return case, "no shell tool", None, {}


def anthropic_reply(model, uid, name, args):
    block = ({"type": "tool_use", "id": uid, "name": name, "input": args} if name else
             {"type": "text", "text": "Done."})
    msg = {"id": "msg_" + uid, "type": "message", "role": "assistant", "content": [block], "model": model,
           "stop_reason": "tool_use" if name else "end_turn", "stop_sequence": None,
           "usage": {"input_tokens": 10, "output_tokens": 5}}
    empty = {**block, "input": {}} if name else {"type": "text", "text": ""}
    delta = ({"type": "input_json_delta", "partial_json": json.dumps(args)} if name else
             {"type": "text_delta", "text": "Done."})
    events = [
        {"type": "message_start", "message": {**msg, "content": [], "stop_reason": None}},
        {"type": "content_block_start", "index": 0, "content_block": empty},
        {"type": "content_block_delta", "index": 0, "delta": delta},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": msg["stop_reason"], "stop_sequence": None},
         "usage": {"output_tokens": 5}},
        {"type": "message_stop"}]
    return msg, events


def chat_reply(model, uid, name, args):
    call = {"id": uid, "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}
    msg = {"role": "assistant", **({"tool_calls": [call], "content": None} if name else {"content": "Done."})}
    reason = "tool_calls" if name else "stop"
    base = {"id": uid, "model": model, "created": 1}
    response = {**base, "object": "chat.completion", "choices": [{"index": 0, "message": msg, "finish_reason": reason}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}
    delta = {**msg, "tool_calls": [{**call, "index": 0}]} if name else msg
    return response, [{**base, "object": "chat.completion.chunk",
                       "choices": [{"index": 0, "delta": item, "finish_reason": finish}]}
                      for item, finish in [(delta, None), ({}, reason)]]


def responses_reply(model, uid, name, args):
    item_id = ("fc_" if name else "msg_") + uid
    item = ({"type": "function_call", "id": item_id, "call_id": uid, "name": name, "arguments": json.dumps(args)}
            if name else {"type": "message", "id": item_id, "role": "assistant",
                          "content": [{"type": "output_text", "text": "Done.", "annotations": []}]})
    response = {"id": "resp_" + uid, "object": "response", "created_at": 1, "model": model, "status": "completed",
                "output": [{**item, "status": "completed"}],
                "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}
    start = {**item, "arguments": ""} if name else {**item, "content": []}
    events = [{"type": "response.created", "response": {**response, "status": "in_progress", "output": []}},
              {"type": "response.output_item.added", "output_index": 0, "item": {**start, "status": "in_progress"}}]
    position = {"item_id": item_id, "output_index": 0}
    if name:
        events.extend([{"type": "response.function_call_arguments.delta", **position, "delta": json.dumps(args)},
                       {"type": "response.function_call_arguments.done", **position, "arguments": json.dumps(args)}])
    else:
        events.extend([{"type": "response.content_part.added", **position, "content_index": 0,
                        "part": {"type": "output_text", "text": "", "annotations": []}},
                       {"type": "response.output_text.delta", **position, "content_index": 0, "delta": "Done."},
                       {"type": "response.output_text.done", **position, "content_index": 0, "text": "Done."}])
    events.extend([{"type": "response.output_item.done", "output_index": 0, "item": response["output"][0]},
                   {"type": "response.completed", "response": response}])
    return response, [{**event, "sequence_number": n} for n, event in enumerate(events)]


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def reply(self, content, content_type="application/json"):
        data = (json.dumps(content) if content_type == "application/json" else content).encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if urlsplit(self.path).path.endswith("/models"):
            self.reply({"object": "list", "data": [{"id": model, "object": "model", "owned_by": "sonar"}
                                                  for model in self.server.models]})
        else:
            self.send_error(404)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path.endswith("/count_tokens"):
            return self.reply({"input_tokens": 10})
        method = next((fn for suffix, fn in (("/messages", anthropic_reply), ("/responses", responses_reply),
                                             ("/chat/completions", chat_reply)) if path.endswith(suffix)), None)
        size = int(self.headers.get("Content-Length", 0))
        if not method or not 0 < size <= 8 * 1024 * 1024:
            return self.send_error(400)
        body = json.loads(self.rfile.read(size))
        case, action, name, args = scripted_reply(body, self.server.token)
        model = body.get("model", "")
        fields = {k: body[k] for k in ("max_tokens", "max_output_tokens", "max_completion_tokens", "temperature",
                                       "top_p", "reasoning_effort", "reasoning", "thinking", "output_config") if k in body}
        self.server.receipts.append({"path": path, "model": model, "case": case, "action": action,
                                     "tool": name, "fields": fields})
        response, events = method(model, "call_" + uuid.uuid4().hex[:16], name, args)
        if not body.get("stream"):
            return self.reply(response)
        chunks = []
        for event in events:
            if method is not chat_reply:
                chunks.append("event: " + event["type"] + "\n")
            chunks.append("data: " + json.dumps(event) + "\n\n")
        if method is chat_reply:
            chunks.append("data: [DONE]\n\n")
        self.reply("".join(chunks), "text/event-stream")


@contextmanager
def scripted_server(token, models, bind):
    with ThreadingHTTPServer((bind, 0), Handler) as server:
        server.token, server.models, server.receipts = token, sorted(set(models)), []
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server
        finally:
            server.shutdown()
            thread.join()
