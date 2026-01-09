# python
import json
import logging
from logging.handlers import RotatingFileHandler
import time
from functools import wraps
from typing import Any, Callable, Optional, Dict

# Optional: token pricing (per 1k tokens) - update to match your model/pricing
TOKEN_PRICING = {
    "gpt-4o": {"prompt": 0.03, "completion": 0.06},  # example prices per 1k tokens
    "gpt-4": {"prompt": 0.03, "completion": 0.06},
    "gpt-3.5-turbo": {"prompt": 0.0015, "completion": 0.002},
}


def setup_logger(log_path: str = "logs/openai_usage.log", jsonl_path: str = "logs/openai_usage.jsonl"):
    logger = logging.getLogger("openai_usage")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    # Keep a JSONL writer for structured records
    def write_jsonl(record: Dict[str, Any]):
        with open(jsonl_path, "a", encoding="utf8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return logger, write_jsonl


def _compute_cost_from_usage(usage: Dict[str, int], model: Optional[str] = None) -> Optional[float]:
    if not usage:
        return None
    model_prices = TOKEN_PRICING.get(model or "", None)
    if not model_prices:
        return None
    prompt_t = usage.get("prompt_tokens", 0)
    completion_t = usage.get("completion_tokens", 0)
    cost = (prompt_t / 1000.0) * model_prices.get("prompt", 0.0) + (completion_t / 1000.0) * model_prices.get("completion", 0.0)
    return round(cost, 8)


def log_openai_response(response: Any, jsonl_writer: Callable[[Dict[str, Any]], None], logger: logging.Logger,
                        context: Optional[Dict[str, Any]] = None):
    """
    Extract usage info from common OpenAI response shapes and write a log record.
    Works for responses that expose .usage or ['usage'] and that contain ids and model.
    """
    context = context or {}
    # attempt to access usage in different shapes
    usage = None
    try:
        usage = getattr(response, "usage", None) or (response.get("usage") if isinstance(response, dict) else None)
    except Exception:
        usage = None

    # basic metadata
    record = {
        "ts": int(time.time()),
        "model": getattr(response, "model", response.get("model") if isinstance(response, dict) else None),
        "id": getattr(response, "id", response.get("id") if isinstance(response, dict) else None),
        "object": getattr(response, "object", response.get("object") if isinstance(response, dict) else None),
        "usage": usage,
        "context": context,
    }
    # compute cost if possible
    try:
        record["estimated_cost_usd"] = _compute_cost_from_usage(usage or {}, record["model"])
    except Exception:
        record["estimated_cost_usd"] = None

    logger.info("OpenAI usage: id=%s model=%s tokens=%s cost=%s",
                record["id"], record["model"], usage, record["estimated_cost_usd"])
    jsonl_writer(record)


def call_chat_completion(client, model: str, messages: list, logger: logging.Logger, jsonl_writer: Callable,
                         **kwargs) -> Any:
    """
    Example wrapper for the Chat Completions style call using openai.OpenAI client:
      response = client.chat.completions.create(model=..., messages=..., **kwargs)
    """
    start = time.time()
    response = client.chat.completions.create(model=model, messages=messages, **kwargs)
    duration = time.time() - start

    metadata = {"api": "chat.completions.create", "duration_s": duration, "messages_count": len(messages)}
    log_openai_response(response, jsonl_writer, logger, context=metadata)
    return response


def call_responses_api(client, model: str, input: str, logger: logging.Logger, jsonl_writer: Callable,
                       **kwargs) -> Any:
    """
    Example wrapper for the Responses API:
      response = client.responses.create(model=..., input=..., **kwargs)
    """
    start = time.time()
    response = client.responses.create(model=model, input=input, **kwargs)
    duration = time.time() - start

    metadata = {"api": "responses.create", "duration_s": duration, "input_len": len(input)}
    log_openai_response(response, jsonl_writer, logger, context=metadata)
    return response


def log_tool(tool_name: str, logger: logging.Logger, jsonl_writer: Callable[[Dict[str, Any]], None]):
    """
    Decorator factory to log tool usage: call counts, args summary, duration, exceptions.
    Use on functions that implement tools (web search, file fetch, DB query, etc.).
    """
    def decorator(fn: Callable):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            ts = time.time()
            try:
                result = fn(*args, **kwargs)
                success = True
                exc = None
            except Exception as e:
                result = None
                success = False
                exc = repr(e)
                raise
            finally:
                duration = time.time() - ts
                record = {
                    "ts": int(ts),
                    "tool": tool_name,
                    "args_summary": {"args": len(args), "kwargs_keys": list(kwargs.keys())},
                    "duration_s": duration,
                    "success": success,
                    "exception": exc,
                }
                logger.info("Tool call: %s duration=%.3fs success=%s", tool_name, duration, success)
                jsonl_writer(record)
            return result
        return wrapper
    return decorator


# Optional: estimate tokens locally using tiktoken when the server doesn't return usage.
try:
    import tiktoken
    def estimate_tokens_for_messages(model: str, messages: list) -> int:
        enc = tiktoken.encoding_for_model(model)
        # rough heuristic for chat messages: count tokens in concatenated role+content
        total = 0
        for m in messages:
            total += len(enc.encode(m.get("role", "") + " " + m.get("content", "")))
        return total
except Exception:
    def estimate_tokens_for_messages(model: str, messages: list) -> int:
        return 0  # fallback if tiktoken isn't available


# Example usage:
# logger, jsonl_writer = setup_logger()
# response = call_chat_completion(client, model="gpt-3.5-turbo", messages=[{"role":"user","content":"Hello"}], logger=logger, jsonl_writer=jsonl_writer)
#
# @log_tool("web_search", logger, jsonl_writer)
# def web_search(q):
#     # implement search
#     return {"results": []}
#
# web_search("Bundesregierung Finanzen")
