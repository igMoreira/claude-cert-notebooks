from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts import base
from typing import Literal, get_args
from pydantic import Field
import json

Status = Literal["todo","in_progress", "done"]

class Task:
    def __init__(self, id:str, title:str, status:Status, tags:list[str], notes:str):
        self.id = id
        self.title = title
        self.status = status
        self.tags = tags
        self.notes = notes


__tasks:list[Task] = []

mcp = FastMCP("Demo")


@mcp.tool(
    name="create_task",
    description="Creates a task, auto-assigns the next `T-00N` id, returns the id"
)
def create_task(
        title:str = Field(description="Title of the task"),
        tags:list[str] = Field(description="A list of tags associated with the task. This will allow grouping similar tasks.")
    ):
    if not title:
        raise ValueError("Title cannot be empty")
    if not __tasks:
        last_id = 0
    else:
        last_task = __tasks[-1]
        last_id = int(last_task.id[2:])
    id = f'T-{(last_id+1):03d}'
    __tasks.append(Task(id, title, 'todo', tags, notes=""))
    
    
@mcp.tool(
    name="update_task_status",
    description="Moves a task between `todo`/`in_progress`/`done`"
)
def update_task_status(
        task_id:str = Field(description="Id of the task to change status"),
        status:str = Field(description="Status to change the task to")
    ):
    if not task_id:
        raise ValueError("task_id cannot be empty")
    if not status or status not in get_args(Status):
        raise ValueError("invalid status")
    task = next((t for t in __tasks if t.id == task_id), None)
    if not task:
        raise ValueError('task_id not found')
    task.status = status

@mcp.tool(
    name="append_task_note",
    description="Appends a line to the task's notes"
)    
def append_task_note(
    task_id:str = Field(description="Id of the task to add a note"), 
    note:str = Field(description="A one line note for the task")):
    if not task_id:
        raise ValueError("task_id cannot be empty")
    if not note:
        raise ValueError("not cannot be empty")
    task = next((t for t in __tasks if t.id == task_id), None)
    if not task:
        raise ValueError('task_id not found')
    task.notes = note
    

@mcp.tool(
    name="search_tasks",
    description="Case-insensitive substring match over title, tags, and notes; returns matching tasks"
)    
def search_tasks(query:str = Field(description="Search query containing a substring of title, tags, or notes")):
    if not query:
        raise ValueError("Query cannot be empty")
    tasks = []
    for t in __tasks:
        if query.casefold() in t.title.casefold() or query.casefold() in t.notes.casefold() or query.casefold() in [ c.casefold() for c in t.tags]:
            tasks.append(t)
    return json.dumps({
        "count": len(tasks),
        "tasks": [t.__dict__ for t in tasks]
        })
    

@mcp.tool(
    name="delete_task",
    description="Removes a task; returns a confirmation string"
)
def delete_task(task_id:str = Field(description="Id of the ask to be deleted")):
    if not task_id:
        raise ValueError("task_id cannot be empty")
    global __tasks
    __tasks = [t for t in __tasks if t.id != task_id]
    
    
@mcp.resource(uri='tasks://all', 
              name='list_tasks', 
              title='List all tasks', 
              description='ist of every task id — the "directory listing" a client uses for autocomplete', 
              mime_type='application/json'
              )
def list_tasks():
    return json.dumps({
            "count": len(__tasks),
            "tasks": [t.id for t in __tasks]
            })
    
    
@mcp.resource(uri='tasks://task/{task_id}',
              name='get_task',
              title='Get a single task details',
              description='A single full task object',
              mime_type='application/json')
def get_task(task_id:str):
    task = next(t for t in __tasks if t.id == task_id)
    if not task:
        raise ValueError('task_id not found')
    return json.dumps(task.__dict__)

@mcp.resource(uri='tasks://status/{status}',
              name='list_tasks_by_status',
              title='List all tasks by status',
              description='All tasks in a given status',
              mime_type='application/json')
def list_tasks_by_status(status:str):
    if not status or status not in get_args(Status):
        raise ValueError('Invalid status value')
    tasks = [t for t in __tasks if t.status == status]
    return json.dumps({
            "count": len(tasks),
            "tasks": [t.id for t in tasks]
            })
    
@mcp.resource(uri='board://summary',
              name='tasks_summary',
              title='Summary of the current tasks',
              description='A human-readable board summary: counts per status + the in-progress titles',
              mime_type='text/plain')
def tasks_summary():
    todo = [t.title for t in __tasks if t.status == 'todo']
    in_progress = [t.title for t in __tasks if t.status == 'in_progress']
    done = [t.title for t in __tasks if t.status == 'done']
    unordered_list = '\n\t'.join(f'- "{t}"' for t in in_progress)
    return f"""
    Total number of tasks: {len(__tasks)}
    
        Total to-do tasks: {len(todo)}
        Total in-progress tasks: {len(in_progress)}
        Total done tasks: {len(done)}
        
    Summary of in-progress tasks: 
        {unordered_list}
    """
    
@mcp.prompt(name='standup',
            description="Summarise the board as a standup update: done yesterday, in progress, blocked.")
def standup() -> list[base.Message]:
    prompt = f"""
    Your goal is to summarise the existing board to simulate a standup.
    You need to include
    - tasks done yesterday
    - tasks that are in progress
    - and any task blockers
    
    For the sake of example you may pick random done tasks, you don't need dates to calculate 'yesterday'
    
    Create example blockers for the tasks. Not all, but handful random tasks.
    
    Use the 'board://summary' resource and call 'search_tasks' first.
    """
    return [ base.UserMessage(prompt)]

@mcp.prompt(name='plan_task',
            description='Break this task into 3–5 concrete subtasks')
def plan_task(task_id:str = Field(description='Id of the task to break into subtasks')) -> list[base.Message]:
        prompt = f"""
        Break task with id {task_id} into 3–5 concrete subtasks and create each one with `create_task` tool, tagged with the parent id.
        Use 'tasks://task/{task_id}' to get the task details and 'append_task_note' to add a note to the parent task notifying the user it is a parent task.
        """
        return [base.UserMessage(prompt)]
    
@mcp.prompt(name='triage',
            description="Review every task with this tag, propose a priority order, and update statuses accordingly.")
def triage(tag:str = Field(description='Tag to be searched')) -> list[base.Message]:
    prompt = f"""
    Review every task with tag {tag}.
    Use 'search_tasks' tool to find all tasks with this tag.
    Propose a priority order, and update statuses accordingly.
    Note: You may come up with a dummy proposal just for the sake of example.
    """
    return [base.UserMessage(prompt)]


if __name__ == "__main__":
    mcp.run(transport="stdio")