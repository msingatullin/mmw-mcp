"""Lightweight MCP introspection server for Glama Docker checks."""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field
from typing import Annotated

m = FastMCP("mmw", host="0.0.0.0", port=8000)

class RememberResult(BaseModel):
    id: str = Field(description="Unique identifier of the stored memory")
    status: str = Field(description="Verification status")

@m.tool(
    name="remember",
    description="Store a durable memory with provenance and an auditable trust status.",
    annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False)
)
def remember(
    content: Annotated[str, Field(description="Text content of the memory or fact to store")],
    workspace: Annotated[str, Field(default="default", description="Target workspace partitioning the memories")] = "default",
) -> RememberResult:
    """Store a memory fact."""
    return RememberResult(id="mock", status="verified")

@m.tool(
    name="search",
    description="Search memories across workspaces.",
    annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True)
)
def search(
    query: Annotated[str, Field(description="Search query")]
) -> list[dict]:
    """Search stored memories."""
    return []

if __name__ == "__main__":
    m.run(transport="streamable-http")
