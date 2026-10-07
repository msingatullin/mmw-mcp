"""Lightweight MCP introspection stub for Glama Docker checks.

It only describes the tool surface of the real server (https://mcp.mmwhub.tech/mcp) so a catalog can list it;
it stores nothing. Tool names and descriptions mirror the production server.
"""
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

m = FastMCP("mmw", host="0.0.0.0", port=8000)


@m.tool(name="remember", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        description="Save a note, fact, or decision to memory so it can be recalled in future conversations. Saving never "
                    "deletes or overwrites existing memories. Records with the same fact_key that disagree are flagged as a conflict.")
def remember(content: Annotated[str, Field(description="Text of the memory")],
             workspace: Annotated[str, Field(description="Workspace")] = "default",
             fact_key: Annotated[str | None, Field(description="Canonical key; versions of one fact share it")] = None,
             source_id: Annotated[str | None, Field(description="Source document, file or session")] = None,
             source_hash: Annotated[str | None, Field(description="Hash of the source, used to detect stale records")] = None) -> dict:
    return {"id": "stub", "status": "unverified"}


@m.tool(name="search", annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        description="Search memories and annotate provenance, stale and conflict status. The newest version of a fact comes first.")
def search(query: Annotated[str, Field(description="Query text")],
           workspace: Annotated[str, Field(description="Workspace")] = "default",
           limit: Annotated[int, Field(description="1-50")] = 10) -> list[dict]:
    return []


@m.tool(name="forget", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=True, idempotentHint=True),
        description="Soft-delete a memory by memory_id or all memories from a source_id, cleaning up graph edges.")
def forget(memory_id: Annotated[str | None, Field(description="Memory to delete")] = None,
           source_id: Annotated[str | None, Field(description="Delete every memory of this source")] = None) -> dict:
    return {"forgotten": False}


@m.tool(name="validate_memory", annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
        description="Validate one source against its current hash and report stale and conflicting memories.")
def validate_memory(source_id: Annotated[str, Field(description="Source to check")],
                    current_source_hash: Annotated[str, Field(description="Current hash of the source")]) -> dict:
    return {"checked": 0, "stale": [], "conflicts": []}


@m.tool(name="gateway_call", annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        description="Call a tool on an integration the user connected to the project (for example GitHub). Integration secrets stay on the server.")
def gateway_call(server: Annotated[str, Field(description="Integration")],
                 tool: Annotated[str, Field(description="Tool name")],
                 arguments: Annotated[dict, Field(description="Tool arguments")]) -> dict:
    return {}


if __name__ == "__main__":
    m.run(transport="streamable-http")
