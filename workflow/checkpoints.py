from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer


def build_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("engine.schemas", "ValidationResult"),
        ]
    )


def build_checkpointer() -> InMemorySaver:
    return InMemorySaver(serde=build_serializer())


def build_thread_config(thread_id: str) -> dict:
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }
