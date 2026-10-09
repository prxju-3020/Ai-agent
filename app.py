"""Agentic AI Agent - DA-III AI-Agent Development
A Claude-powered agent that decides on its own which tools to use
(calculator, date/time, Wikipedia lookup, notes) and loops until the task is done.
UI: Streamlit.  Run: streamlit run app.py
"""
import ast
import json
import operator
import os
from datetime import datetime

import requests
import streamlit as st

MODEL = "claude-haiku-5-5"
NOTES_FILE = "notes.json"
MAX_STEPS = 6  # safety limit for the agent loop

SYSTEM_PROMPT = (
    "You are a helpful autonomous agent. Break the user's task into steps and use "
    "the available tools whenever they help (math, time, facts, notes). "
    "Use tools instead of guessing. When finished, give a short clear final answer."
)

# ----------------------------------------------------------------- TOOLS
_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Unsupported expression")


def calculator(expression: str) -> str:
    try:
        return str(_eval(ast.parse(expression, mode="eval").body))
    except Exception as e:
        return f"Calculator error: {e}"


def get_datetime() -> str:
    return datetime.now().strftime("%A, %d %B %Y, %H:%M:%S")


def wikipedia_summary(topic: str) -> str:
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + topic.replace(" ", "_")
        r = requests.get(url, timeout=10, headers={"User-Agent": "DA3-agent/1.0"})
        if r.status_code != 200:
            return f"No Wikipedia page found for '{topic}'."
        return r.json().get("extract", "No summary available.")
    except Exception as e:
        return f"Lookup error: {e}"


def _load_notes() -> list:
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE) as f:
            return json.load(f)
    return []


def save_note(text: str) -> str:
    notes = _load_notes()
    notes.append(text)
    with open(NOTES_FILE, "w") as f:
        json.dump(notes, f)
    return f"Note saved. You now have {len(notes)} note(s)."


def list_notes() -> str:
    notes = _load_notes()
    return "\n".join(f"{i+1}. {n}" for i, n in enumerate(notes)) or "No notes yet."


TOOL_FUNCS = {
    "calculator": lambda a: calculator(a["expression"]),
    "get_datetime": lambda a: get_datetime(),
    "wikipedia_summary": lambda a: wikipedia_summary(a["topic"]),
    "save_note": lambda a: save_note(a["text"]),
    "list_notes": lambda a: list_notes(),
}

TOOLS = [
    {"name": "calculator", "description": "Evaluate a math expression like '(12+8)*3/2'.",
     "input_schema": {"type": "object", "properties": {"expression": {"type": "string"}},
                      "required": ["expression"]}},
    {"name": "get_datetime", "description": "Get the current date and time.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "wikipedia_summary", "description": "Get a short Wikipedia summary of a topic.",
     "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}},
                      "required": ["topic"]}},
    {"name": "save_note", "description": "Save a note for the user.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}},
                      "required": ["text"]}},
    {"name": "list_notes", "description": "List all saved notes.",
     "input_schema": {"type": "object", "properties": {}}},
]


# ----------------------------------------------------------------- AGENT LOOP
def run_agent(client, messages: list, trace: list) -> str:
    """Think -> call tool -> observe -> repeat until the model gives a final answer."""
    for _ in range(MAX_STEPS):
        resp = client.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM_PROMPT,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        results = []
        for block in resp.content:
            if block.type == "tool_use":
                out = TOOL_FUNCS[block.name](block.input)
                trace.append(f"🔧 **{block.name}**({json.dumps(block.input)}) → {out}")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": out})
        messages.append({"role": "user", "content": results})
    return "Stopped: reached the maximum number of steps."


# ----------------------------------------------------------------- UI
st.set_page_config(page_title="Agentic AI Agent", page_icon="🤖")
st.title("🤖 Agentic AI Agent")
st.caption("Autonomously uses tools: calculator · date/time · Wikipedia · notes")

api_key = os.getenv("ANTHROPIC_API_KEY") or st.sidebar.text_input("Anthropic API key", type="password")
st.sidebar.markdown("**Try:** \n- What is 15% of 2450, and what day is it today? \n"
                    "- Summarise Alan Turing and save a note about him \n- Show my notes")

st.session_state.setdefault("api_messages", [])
st.session_state.setdefault("display", [])

for m in st.session_state.display:
    with st.chat_message(m["role"]):
        for step in m.get("trace", []):
            st.markdown(step)
        st.markdown(m["content"])

if prompt := st.chat_input("Give the agent a task..."):
    st.session_state.display.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    with st.chat_message("assistant"):
        if not api_key:
            answer, trace = "Please enter your Anthropic API key in the sidebar.", []
        else:
            import anthropic
            trace = []
            st.session_state.api_messages.append({"role": "user", "content": prompt})
            try:
                with st.spinner("Agent is working..."):
                    answer = run_agent(anthropic.Anthropic(api_key=api_key),
                                       st.session_state.api_messages, trace)
            except Exception as e:
                answer = f"Error: {e}"
        for step in trace:
            st.markdown(step)
        st.markdown(answer)
    st.session_state.display.append({"role": "assistant", "content": answer, "trace": trace})
