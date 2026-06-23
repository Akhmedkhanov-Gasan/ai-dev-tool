from collections.abc import Callable
from typing import Literal
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from engine.schemas import AgentState
from workflow.nodes import (
    baseline_validation,
    candidate_validation,
    finalize_review,
    generate_candidate,
    prepare_retry_or_fail,
    request_human_review,
    route_guard,
)

ReviewHandler = Callable[[AgentState], str]


def route_after_generation(
    state: AgentState,
) -> Literal["route_guard", "prepare_retry_or_fail"]:
    if state.status == "generation_failed":
        return "prepare_retry_or_fail"

    return "route_guard"


def route_after_guard(
    state: AgentState,
) -> Literal["baseline_validation", "prepare_retry_or_fail"]:
    if state.status == "route_protection_failed":
        return "prepare_retry_or_fail"

    return "baseline_validation"


def route_after_baseline(
    state: AgentState,
) -> Literal["candidate_validation", "prepare_retry_or_fail"]:
    if state.status == "baseline_validation_failed":
        return "prepare_retry_or_fail"

    return "candidate_validation"


def route_after_candidate(
    state: AgentState,
) -> Literal["request_human_review", "prepare_retry_or_fail"]:
    if state.status == "candidate_validation_passed":
        return "request_human_review"

    return "prepare_retry_or_fail"


def route_after_retry(
    state: AgentState,
) -> Literal["generate_candidate", "__end__"]:
    if state.status == "retrying":
        return "generate_candidate"

    return END


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("generate_candidate", generate_candidate)
    graph.add_node("route_guard", route_guard)
    graph.add_node("baseline_validation", baseline_validation)
    graph.add_node("candidate_validation", candidate_validation)
    graph.add_node("prepare_retry_or_fail", prepare_retry_or_fail)
    graph.add_node("request_human_review", request_human_review)
    graph.add_node("finalize_review", finalize_review)

    graph.add_edge(START, "generate_candidate")

    graph.add_conditional_edges("generate_candidate", route_after_generation)
    graph.add_conditional_edges("route_guard", route_after_guard)
    graph.add_conditional_edges("baseline_validation", route_after_baseline)
    graph.add_conditional_edges("candidate_validation", route_after_candidate)
    graph.add_conditional_edges("prepare_retry_or_fail", route_after_retry)

    graph.add_edge("request_human_review", "finalize_review")
    graph.add_edge("finalize_review", END)

    serializer = JsonPlusSerializer(
        allowed_msgpack_modules=[
            ("engine.schemas", "ValidationResult"),
        ]
    )

    checkpointer = InMemorySaver(serde=serializer)

    return graph.compile(checkpointer=checkpointer)


def run_agent_workflow(
    state: AgentState,
    on_update: Callable[[str, dict], None] | None = None,
    on_review: ReviewHandler | None = None,
) -> AgentState:
    graph = build_agent_graph()
    current_state = state.model_dump()

    config = {
        "configurable": {
            "thread_id": str(uuid4()),
        }
    }

    graph_input = current_state

    while True:
        interrupted = False

        for event in graph.stream(
            graph_input,
            config=config,
            stream_mode="updates",
        ):
            if "__interrupt__" in event:
                current_state["status"] = "human_review_required"

                if on_update is not None:
                    on_update(
                        "request_human_review",
                        {"status": "human_review_required"},
                    )

                if on_review is None:
                    return AgentState.model_validate(current_state)

                review_state = AgentState.model_validate(current_state)
                decision = on_review(review_state)

                graph_input = Command(resume=decision)
                interrupted = True
                break

            for node_name, update in event.items():
                current_state.update(update)

                if on_update is not None:
                    on_update(node_name, update)

        if not interrupted:
            break

    return AgentState.model_validate(current_state)
