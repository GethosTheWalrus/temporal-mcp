"""Main MCP Server for Temporal workflow orchestration."""

import json
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .client import TemporalClientManager
from .tools.tool_definitions import get_all_tools
from .utils.exceptions import format_connection_error, format_error_response

# Import all handlers
from .handlers import workflow_handlers
from .handlers import query_handlers
from .handlers import batch_handlers
from .handlers import schedule_handlers


class TemporalMCPServer:
    """MCP Server that provides tools for interacting with Temporal."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
        namespace: str = "default",
        tls_enabled: Optional[bool] = None
    ):
        """Initialize the Temporal MCP server.
        
        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
        """
        self.client_manager = TemporalClientManager(
            temporal_host=temporal_host,
            namespace=namespace,
            tls_enabled=tls_enabled
        )
        self.server = Server("temporal-mcp-server")
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available Temporal tools."""
            return get_all_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool execution requests."""
            # Ensure connection
            try:
                await self.client_manager.connect()
            except Exception as e:
                return format_connection_error(e)
            
            # Route to appropriate handler
            try:
                client = self.client_manager.ensure_connected()
                
                # Workflow operations
                if name == "start_workflow":
                    return await workflow_handlers.start_workflow(client, arguments)
                elif name == "cancel_workflow":
                    return await workflow_handlers.cancel_workflow(client, arguments)
                elif name == "terminate_workflow":
                    return await workflow_handlers.terminate_workflow(client, arguments)
                elif name == "get_workflow_result":
                    return await workflow_handlers.get_workflow_result(client, arguments)
                elif name == "describe_workflow":
                    return await workflow_handlers.describe_workflow(client, arguments)
                elif name == "list_workflows":
                    return await workflow_handlers.list_workflows(client, arguments)
                elif name == "get_workflow_history":
                    return await workflow_handlers.get_workflow_history(client, arguments)
                
                # Query and signal operations
                elif name == "query_workflow":
                    return await query_handlers.query_workflow(client, arguments)
                elif name == "signal_workflow":
                    return await query_handlers.signal_workflow(client, arguments)
                elif name == "continue_as_new":
                    return await query_handlers.continue_as_new(client, arguments)
                
                # Batch operations
                elif name == "batch_signal":
                    return await batch_handlers.batch_signal(client, arguments)
                elif name == "batch_cancel":
                    return await batch_handlers.batch_cancel(client, arguments)
                elif name == "batch_terminate":
                    return await batch_handlers.batch_terminate(client, arguments)
                
                # Schedule operations
                elif name == "create_schedule":
                    return await schedule_handlers.create_schedule(client, arguments)
                elif name == "list_schedules":
                    return await schedule_handlers.list_schedules(client, arguments)
                elif name == "pause_schedule":
                    return await schedule_handlers.pause_schedule(client, arguments)
                elif name == "unpause_schedule":
                    return await schedule_handlers.unpause_schedule(client, arguments)
                elif name == "delete_schedule":
                    return await schedule_handlers.delete_schedule(client, arguments)
                elif name == "trigger_schedule":
                    return await schedule_handlers.trigger_schedule(client, arguments)
                
                else:
                    return [TextContent(
                        type="text",
                        text=json.dumps({
                            "error": f"Unknown tool: {name}",
                            "type": "unknown_tool"
                        }, indent=2)
                    )]
            
            except Exception as e:
                return format_error_response(e, name)

    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.client_manager.disconnect()
