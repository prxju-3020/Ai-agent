# Agentic AI Agent

DA-III: AI-Agent Development — Option (i) Agentic Agent

An autonomous agent built on the Claude API. Given a task, it decides which tools to use, runs them, reads the results, and repeats until it can give a final answer. Every tool call is shown in the chat so you can see its reasoning steps.

## Tools the agent can use
| Tool | What it does |
|---|---|
| `calculator` | Safely evaluates math expressions |
| `get_datetime` | Returns current date and time |
| `wikipedia_summary` | Fetches a topic summary from Wikipedia |
| `save_note` / `list_notes` | Stores and reads notes (`notes.json`) |

## How it works (agent loop)
1. User gives a task
2. Claude decides: answer directly, or call a tool
3. The tool runs and the result goes back to Claude
4. Repeat (max 6 steps) until Claude gives the final answer

## Run it
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here   # Windows: set ANTHROPIC_API_KEY=your_key_here
streamlit run app.py
```
(Or paste the key into the app's sidebar.)

## Example tasks
- "What is 15% of 2450, and what day is it today?"
- "Summarise Alan Turing and save a note about him"
- "Show my notes"

## Files
- `app.py` – the agent and UI
- `requirements.txt` – dependencies
- `schema.md` – architecture / schema
