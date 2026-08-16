from typing import List, Tuple
from mcp.types import Prompt, PromptMessage, TextContent
from anthropic.types import MessageParam

from core.chat import Chat
from core.claude import Claude
from mcp_client import MCPClient
import json


class CliChat(Chat):
    def __init__(
        self,
        task_client: MCPClient,
        clients: dict[str, MCPClient],
        claude_service: Claude,
    ):
        super().__init__(clients=clients, claude_service=claude_service)

        self.task_client: MCPClient = task_client

    async def list_prompts(self) -> list[Prompt]:
        return await self.task_client.list_prompts() + [Prompt(name='resources', title='Fetch all available resources', description='List of all resources available'), 
                                                        Prompt(name='tools', title='Fetch all available tools', description='List of all tools available'), 
                                                        Prompt(name='prompts', title='Fetch all available prompts', description='List of all prompts available')]

    async def list_tasks(self) -> dict:
        return await self.task_client.read_resource("tasks://all")

    async def get_task_details(self, task_id: str) -> dict:
        return await self.task_client.read_resource(f"tasks://task/{task_id}")
    
    async def get_tasks_by_status(self, status: str) -> dict:
        return await self.task_client.read_resource(f"tasks://status/{status}")
    
    async def board_summary(self) -> str:
        return await self.task_client.read_resource("board://summary")
    
    async def get_prompt_standup(
            self, command: str
        ) -> list[PromptMessage]:
        return await self.task_client.get_prompt(command, args={})
    
    async def get_prompt_plan_task(
            self, command: str, task_id: str
        ) -> list[PromptMessage]:
        return await self.task_client.get_prompt(command, {"task_id": task_id})
    
    async def get_prompt_triage(
        self, command: str, tag: str
    ) -> list[PromptMessage]:
        return await self.task_client.get_prompt(command, {"tag": tag})

    async def _extract_resources(self, query: str) -> str:
        mentions = [word[1:] for word in query.split() if word.startswith("@")]

        task_ids = (await self.list_tasks())["tasks"]
        mentioned_tasks: list[Tuple[str, str]] = []

        for id in task_ids:
            if id in mentions or 'all' in mentions:
                task = await self.get_task_details(id)
                mentioned_tasks.append((id, task))

        return "".join(
            f'\n<task id="{task_id}">\n{content}\n</task>\n'
            for task_id, content in mentioned_tasks
        )

    async def _process_command(self, query: str) -> dict:
        if not query.startswith("/"):
            return {"success": False, "chat_loop": True}

        words = query.split()
        command = words[0].replace("/", "")

        if query.startswith('/tools'):
            for t in await self.task_client.list_tools():
                print(f"\n{t.name}: {t.description}")
                print(json.dumps(t.inputSchema, indent=2))
            return {'success': True, "chat_loop": False}
        if query.startswith('/resources'):
            resources = await self.task_client.list_resources()
            resources_template = await self.task_client.list_resources_template()
            
            for r in resources:
                print(f'\n URI: {r.uri} name: {r.name} mime_type: {r.mimeType} description: {r.description}')
                
            for r in resources_template:
                print(f'\n URI: {r.uriTemplate} name: {r.name} mime_type: {r.mimeType} description: {r.description}')
            
            return {'success': True, "chat_loop": False}
        if query.startswith('/prompts'):
            for t in await self.task_client.list_prompts():
                print(f"\n{t.name}: {t.description}")
                for a in t.arguments or []:
                    print(f'\n\t Argument name: {a.name} description: {a.description}')
            return {'success': True, "chat_loop": False}

        if command == 'standup':
            messages = await self.get_prompt_standup(command=command)
        elif command == 'plan_task':
            if len(words) < 2:
                print("Usage: /plan_task <task_id>")
                return {'success': True, "chat_loop": False}
            messages = await self.get_prompt_plan_task(command=command, task_id=words[1])
        elif command == 'triage':
            if len(words) < 2:
                print("Usage: /triage <tag>")
                return {'success': True, "chat_loop": False}
            messages = await self.get_prompt_triage(command=command, tag=words[1])
        else:
            print(f"Unknown command: /{command}")
            return {'success': True, "chat_loop": False}

        self.messages += convert_prompt_messages_to_message_params(messages)
        return {'success': True, "chat_loop": True}

    async def _process_query(self, query: str):
        result = await self._process_command(query)
        if result['success']:
            return {"chat_loop": result['chat_loop']}

        added_resources = await self._extract_resources(query)

        prompt = f"""
        The user has a question:
        <query>
        {query}
        </query>

        The following context may be useful in answering their question:
        <context>
        {added_resources}
        </context>

        Note the user's query might contain references to task ids like "@T-001". The "@" is only
        included as a way of mentioning the task. The actual id of the task would be "T-001".
        If the task details is included in this prompt, you don't need to use an additional tool to read the task.
        Answer the user's question directly and concisely. Start with the exact information they need. 
        Don't refer to or mention the provided context in any way - just use it to inform your answer.
        """

        self.messages.append({"role": "user", "content": prompt})
        return {"chat_loop": True}


def convert_prompt_message_to_message_param(
    prompt_message: "PromptMessage",
) -> MessageParam:
    role = "user" if prompt_message.role == "user" else "assistant"

    content = prompt_message.content

    # Check if content is a dict-like object with a "type" field
    if isinstance(content, dict) or hasattr(content, "__dict__"):
        content_type = (
            content.get("type", None)
            if isinstance(content, dict)
            else getattr(content, "type", None)
        )
        if content_type == "text":
            content_text = (
                content.get("text", "")
                if isinstance(content, dict)
                else getattr(content, "text", "")
            )
            return {"role": role, "content": content_text}

    if isinstance(content, list):
        text_blocks = []
        for item in content:
            # Check if item is a dict-like object with a "type" field
            if isinstance(item, dict) or hasattr(item, "__dict__"):
                item_type = (
                    item.get("type", None)
                    if isinstance(item, dict)
                    else getattr(item, "type", None)
                )
                if item_type == "text":
                    item_text = (
                        item.get("text", "")
                        if isinstance(item, dict)
                        else getattr(item, "text", "")
                    )
                    text_blocks.append({"type": "text", "text": item_text})

        if text_blocks:
            return {"role": role, "content": text_blocks}

    return {"role": role, "content": ""}


def convert_prompt_messages_to_message_params(
    prompt_messages: List[PromptMessage],
) -> List[MessageParam]:
    return [
        convert_prompt_message_to_message_param(msg) for msg in prompt_messages
    ]
