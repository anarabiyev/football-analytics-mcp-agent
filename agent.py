import asyncio
import json

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

load_dotenv()  # reads OPENAI_API_KEY from a .env file in the project root


# a plain JSON schema, not a Pydantic class - so the structured response
# LangGraph stores between turns is just a dict, not a custom Python type
AGENT_RESPONSE_SCHEMA = {
    "title": "AgentResponse",
    "description": "The final response to the user.",
    "type": "object",
    "properties": {
        "needs_clarification": {"type": "boolean"},
        "message": {"type": "string"},
    },
    "required": ["needs_clarification", "message"],
}

SYSTEM_PROMPT = """You are a football analytics assistant. Answer questions
about match events using the tools available to you.

If the question is too vague to answer well (no match specified, or the
metric isn't clear), set needs_clarification=true and put your question
in message. Otherwise set needs_clarification=false and put your full
answer in message.

If the result is a ranking or a breakdown across several players/teams,
call build_chart to include a chart. Skip the chart for a single number.

Here's how the data is structured:

{schema}
"""

MCP_CONFIG = {
    "football": {
        "url": "http://127.0.0.1:8000/mcp",
        "transport": "streamable_http",
    }
}


async def build_agent():
    client = MultiServerMCPClient(MCP_CONFIG)
    tools = await client.get_tools()

    async with client.session("football") as session:
        schema_doc = await session.read_resource("statsbomb://schema")
        schema_text = schema_doc.contents[0].text

    model = ChatOpenAI(model="gpt-4.1-mini")
    checkpointer = InMemorySaver()
    return create_react_agent(
        model,
        tools,
        prompt=SYSTEM_PROMPT.format(schema=schema_text),
        response_format=AGENT_RESPONSE_SCHEMA,
        checkpointer=checkpointer,
    )


async def ask(agent, question, match_id, session_id):
    config = {"configurable": {"thread_id": session_id}}
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": f"match_id={match_id}. {question}"}]},
        config=config,
    )
    return extract_answer(result)


def extract_answer(result):
    """
    needs_clarification and message come from the structured final response,
    so the caller can tell a clarifying question apart from a real answer.
    The chart, if any, is pulled from the actual build_chart tool output
    (not the model's retelling of it) so the numbers are guaranteed correct.
    """
    structured = result["structured_response"]

    chart = None
    for message in result["messages"]:
        if getattr(message, "name", None) == "build_chart":
            chart = _parse_tool_content(message.content)

    return {
        "needs_clarification": structured["needs_clarification"],
        "message": structured["message"],
        "chart": chart,
    }


def _parse_tool_content(content):
    """
    MCP tools return their result wrapped as a list of content blocks,
    e.g. [{"type": "text", "text": "<json string>"}] - this unwraps that
    down to the actual dict, however it happens to arrive.
    """
    if isinstance(content, str):
        return json.loads(content)
    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and "text" in block:
                return json.loads(block["text"])
    return content


if __name__ == "__main__":
    async def main():
        agent = await build_agent()

        # Union Berlin vs Bayer Leverkusen, from step 1's explore.py
        match_id = 3895292
        session_id = "demo-session-1"

        print("\nQ: who's the best player of all time?")
        result = await ask(agent, "who's the best player of all time?", match_id, session_id)
        print(result)

        if result["needs_clarification"]:
            # same session_id - the agent still remembers the original question
            print("\nfollow-up: I mean in this match, based on match events")
            result = await ask(agent, "I mean in this match, based on match events", match_id, session_id)
            print(result)

        print("\nQ: how many passes did each team complete?")
        result = await ask(agent, "how many passes did each team complete?", match_id, "demo-session-2")
        print(result)

    asyncio.run(main())