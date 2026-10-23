"""Durable LangGraph interrupts for fact confirmation and explicit patch approval."""
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt, Command
from packages.agent_core.checkpoints import SQLCheckpointer


class ApprovalState(TypedDict, total=False):
    facts_confirmed: bool
    fact_ids: list
    approved_fact_ids: list


def workflow(factory, owner):
    def confirm_facts(state):
        if state.get("facts_confirmed"):
            return {}
        answer = interrupt({"action": "confirm_facts", "message": "等待用户核对解析事实"})
        return {"facts_confirmed": True, "fact_ids": answer["fact_ids"]}

    def approve_patch(state):
        answer = interrupt({"action": "approve_rewrite", "message": "等待用户明确授权段落及改写文本"})
        return {"approved_fact_ids": answer["approved_fact_ids"]}

    graph = StateGraph(ApprovalState)
    graph.add_node("confirm_facts", confirm_facts)
    graph.add_node("approve_patch", approve_patch)
    graph.set_entry_point("confirm_facts")
    graph.add_edge("confirm_facts", "approve_patch")
    graph.add_edge("approve_patch", END)
    return graph.compile(checkpointer=SQLCheckpointer(factory, owner))


def start(factory, owner, thread_id, confirmed=False, fact_ids=None):
    workflow(factory, owner).invoke({"facts_confirmed": confirmed, "fact_ids": fact_ids or [], "approved_fact_ids": []}, {"configurable": {"thread_id": thread_id}})


def confirm(factory, owner, thread_id, fact_ids):
    graph = workflow(factory, owner)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        start(factory, owner, thread_id)
        snapshot = graph.get_state(config)
    if not snapshot.values.get("facts_confirmed"):
        graph.invoke(Command(resume={"fact_ids": fact_ids}), config)


def approve(factory, owner, thread_id, fact_ids, approved_fact_ids):
    graph = workflow(factory, owner)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if not snapshot.values:
        start(factory, owner, thread_id, True, fact_ids)
    confirm(factory, owner, thread_id, fact_ids)
    result = graph.invoke(Command(resume={"approved_fact_ids": approved_fact_ids}), config)
    if result["approved_fact_ids"] != approved_fact_ids:
        raise ValueError("Approval checkpoint mismatch")
