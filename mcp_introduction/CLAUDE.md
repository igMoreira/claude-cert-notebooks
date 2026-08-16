# MCP Introduction — Practice Project

A hands-on project to exercise **both sides of the Model Context Protocol**: an MCP **server**
that exposes tools, resources, and prompts, and an MCP **client** that discovers and consumes
them inside a Claude-powered chat loop.

Reference course: <https://anthropic-partners.skilljar.com/introduction-to-model-context-protocol/296689>

> The features are intentionally small. The point is to practice the MCP concepts — schema
> generation, URI/templated resources, prompt discovery, and the client wiring — not to build a
> production application.

---

## 1. Project idea — "TaskBoard"

A tiny in-memory task tracker. Everything lives in a Python dict on the server; no database, no
persistence (an optional JSON file is a stretch goal). The domain is deliberately boring so all
the interesting work is protocol work.

A task looks like:

```python
{
    "id": "T-001",
    "title": "Write the MCP server",
    "status": "todo",          # todo | in_progress | done
    "tags": ["mcp", "python"],
    "notes": "",
}
```

### Why this domain works for MCP

| Primitive | Controlled by | TaskBoard example |
| --- | --- | --- |
| **Tool** | The model | `create_task` — Claude decides to call it mid-conversation |
| **Resource** | The client app | `tasks://all` — the app pulls it to autocomplete a `@mention` |
| **Prompt** | The user | `/standup` — the user explicitly triggers a canned workflow |

Keep that table in mind: choosing the right primitive for a feature is the main skill being
practiced here.

---

## 2. Deliverables

### 2.1 Tools (model-controlled)

Defined with `@mcp.tool`. Use **type hints + `pydantic.Field(description=...)`** so the JSON
schema is generated for you — never hand-write a schema.

| Tool | Signature | Behaviour |
| --- | --- | --- |
| `create_task` | `(title: str, tags: list[str] = [])` | Creates a task, auto-assigns the next `T-00N` id, returns the id |
| `update_task_status` | `(task_id: str, status: str)` | Moves a task between `todo`/`in_progress`/`done`; raise `ValueError` on unknown id or invalid status |
| `append_task_note` | `(task_id: str, note: str)` | Appends a line to the task's notes |
| `search_tasks` | `(query: str)` | Case-insensitive substring match over title, tags, and notes; returns matching tasks |
| `delete_task` | `(task_id: str)` | Removes a task; returns a confirmation string |

**Practice points**
- Every parameter gets a `Field` description — inspect the generated schema with
  `client.list_tools()` and confirm the descriptions made it across the wire.
- Raise `ValueError` for bad input and observe how the error surfaces as a tool result with
  `isError=True` rather than crashing the server.
- Deliberately write one tool with a vague description, then a precise one, and note how Claude's
  choice of tool changes.

### 2.2 Resources (app-controlled)

Defined with `@mcp.resource`, with an explicit `mime_type`.

| URI | MIME type | Returns |
| --- | --- | --- |
| `tasks://all` | `application/json` | List of every task id — the "directory listing" a client uses for autocomplete |
| `tasks://task/{task_id}` | `application/json` | A single full task object (**templated resource**) |
| `tasks://status/{status}` | `application/json` | All tasks in a given status (second templated resource, different shape) |
| `board://summary` | `text/plain` | A human-readable board summary: counts per status + the in-progress titles |

**Practice points**
- Build at least one **static** and two **templated** resources so both discovery paths get
  exercised (`list_resources` vs. `list_resource_templates`).
- Return both `application/json` and `text/plain` so the client's MIME handling has to branch.
- Note the key distinction from tools: a resource is read *by the application*, not decided on by
  the model.

### 2.3 Prompts (user-controlled)

Defined with `@mcp.prompt`, returning `list[base.Message]`.

| Prompt | Args | Purpose |
| --- | --- | --- |
| `standup` | none | "Summarise the board as a standup update: done yesterday, in progress, blocked." Instructs Claude to read `board://summary` / call `search_tasks` first |
| `plan_task` | `task_id` | "Break this task into 3–5 concrete subtasks and create each one with `create_task`, tagged with the parent id." |
| `triage` | `tag` | "Review every task with this tag, propose a priority order, and update statuses accordingly." |

**Practice points**
- A prompt is a *reusable, high-quality instruction*, not a chat message — write it as if handing
  the workflow to a colleague.
- Have at least one prompt whose text explicitly directs Claude to use specific tools, and confirm
  the tool chain actually fires.

### 2.4 Client

A CLI chat app that connects to the server over **stdio**, wires everything into the Anthropic
Messages API, and exposes MCP features to the user:

- `list_tools()` → converted into the `tools` parameter for the Claude API; `call_tool()` on
  every `tool_use` block, results fed back as `tool_result`.
- `@task-id` / `@all` mentions → the client reads the matching resource and injects the content
  into the conversation *before* calling Claude.
- `/prompt-name arg` commands → `get_prompt()` and seed the conversation with the returned
  messages.
- `/tools`, `/resources`, `/prompts` → print raw discovery output. Useful for seeing what the
  protocol actually carries.

---

## 3. Layout

```
mcp_introduction/
├── CLAUDE.md              # this file
├── README.md              # setup + usage, written at the end
├── pyproject.toml         # deps: mcp[cli], anthropic, python-dotenv, prompt-toolkit
├── .env.example           # ANTHROPIC_API_KEY=
├── mcp_server.py          # tools + resources + prompts, mcp.run(transport="stdio")
├── mcp_client.py          # MCPClient wrapper over ClientSession
├── main.py                # entrypoint: wires client + chat loop
└── core/
    ├── claude.py          # thin Anthropic API wrapper
    ├── chat.py            # base chat loop (message list, tool-use loop)
    ├── cli_chat.py        # adds @mention + /prompt handling
    └── cli.py             # prompt-toolkit input with autocompletion
```

Deps go in `pyproject.toml`, managed with `uv` (`uv run mcp_server.py`). Python ≥ 3.10.

---

## 4. Milestones

Each milestone ends with something runnable. Don't skip the verification step — the whole point is
seeing the protocol behave.

**M1 — Server skeleton + first tool**
Create the project, `FastMCP("TaskBoard")`, the in-memory `tasks` dict, and `create_task`.
✅ Verify: `uv run mcp dev mcp_server.py` opens the MCP Inspector; call the tool from the browser.

**M2 — Remaining tools**
Add `update_task_status`, `append_task_note`, `search_tasks`, `delete_task`.
✅ Verify: in the Inspector, confirm each schema shows your `Field` descriptions, and that a bad
`task_id` returns an error result instead of killing the server.

**M3 — Resources**
Add all four resources.
✅ Verify: Inspector's Resources tab lists `tasks://all` and `board://summary`; the templated ones
resolve when you supply a parameter.

**M4 — Prompts**
Add `standup`, `plan_task`, `triage`.
✅ Verify: Inspector's Prompts tab renders each with its arguments filled in.

**M5 — Client connection**
Write `MCPClient` (`connect`, `list_tools`, `call_tool`, `list_prompts`, `get_prompt`,
`read_resource`, `cleanup`) as an async context manager over `stdio_client` + `ClientSession`.
✅ Verify: a `main()` that prints `list_tools()` output and exits cleanly.

**M6 — Chat loop with tool use**
Convert MCP tools to Anthropic tool definitions, run the tool-use loop until Claude stops
requesting tools.
✅ Verify: "Create a task to buy milk, then mark it done" completes end to end.

**M7 — Resources in the client**
`@mention` handling: read the resource, branch on MIME type (`json.loads` for JSON, raw text
otherwise), inject as context. Autocomplete `@` from `tasks://all`.
✅ Verify: `Summarise @T-001` works without Claude calling any tool.

**M8 — Prompts in the client**
`/standup` etc. discovered via `list_prompts()`, autocompleted, and expanded via `get_prompt()`.
✅ Verify: `/plan_task T-001` causes Claude to create subtasks via `create_task`.

**M9 — Connect to Claude Code / Claude Desktop**
Register the server in `.mcp.json` (or `claude mcp add`) and use the same tools from a real host.
✅ Verify: `/mcp` in Claude Code lists TaskBoard's tools, resources, and prompts.

---

## 5. Stretch goals

- Persist tasks to `tasks.json` so state survives restarts.
- Add a second server (e.g. a `notes` server) and connect the client to both — practice
  namespacing and routing a tool call to the right session.
- Swap stdio for **HTTP/SSE** transport and observe that nothing about the tool/resource/prompt
  definitions changes. That's the transport-agnostic claim, tested.
- Add structured output types (Pydantic models as tool return types) and compare the result shape.

---

## 6. Concept checkpoints

Answer these in your own words as you go — they're the actual learning objectives:

1. Why is `search_tasks` a tool but `tasks://all` a resource? What breaks if you swap them?

Answer: search_tasks is used by the model whenever querying tasks is required. tasks://all is Used by the application frontend to show all the avaialable task resources. If you swap them the CLI suggestion will no longer work.

2. What exactly does `list_tools()` return, and how does it map onto the Anthropic API's `tools`
   parameter?


Answer: A list of all tools provided by the MCP server with their schema. That response is provided to authropic's client so the model knows all the available tools and their schemas.


3. What's the difference between a resource and a resource *template* at the protocol level?

Answer: The former is a static resource, no dynamic value provided in the URI. The later provides a dynamic value in the URI that is used as input for the resource function.

4. Why does a prompt return a list of messages rather than a string?

Answer: The prompt may send multiple blocks with tool use, or tool response.

5. Where does the tool-execution burden sit in MCP, and what does that buy you compared to
   defining tools directly in your client app?

Answer: The tool execution cost goes to the server rather than in the application (client) that would normally implement and perform the action in the case of providing tools directly.