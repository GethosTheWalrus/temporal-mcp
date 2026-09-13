"""Main MCP Server for Temporal workflow orchestration."""

import json
import sys
from typing import Any, Optional, Sequence

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolRequestParams, CallToolResult, ContentBlock, ListToolsResult, TextContent

from .client import TemporalClientManager
from .tools.tool_definitions import get_all_tools
from .utils.exceptions import format_connection_error, format_error_response

# Import all handlers
from .handlers import workflow_handlers
from .handlers import query_handlers
from .handlers import batch_handlers
from .handlers import schedule_handlers
from .handlers import activity_handlers


class TemporalMCPServer:
    """MCP Server that provides tools for interacting with Temporal."""

    def __init__(
        self,
        temporal_host: str = "localhost:7233",
        namespace: str = "default",
        tls_enabled: Optional[bool] = None,
        tls_client_cert_path: Optional[str] = None,
        tls_client_key_path: Optional[str] = None,
        api_key: Optional[str] = None,
        allowed_namespaces: Optional[Sequence[str]] = None,
    ):
        """Initialize the Temporal MCP server.

        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
            tls_client_cert_path: Path to the TLS client certificate file (for mTLS / Temporal Cloud)
            tls_client_key_path: Path to the TLS client private key file (for mTLS / Temporal Cloud)
            api_key: API key for Temporal Cloud authentication
            allowed_namespaces: Namespaces callers may select. None permits only the
                configured default; ["*"] permits any namespace.
        """
        self.client_manager = TemporalClientManager(
            temporal_host=temporal_host,
            namespace=namespace,
            tls_enabled=tls_enabled,
            tls_client_cert_path=tls_client_cert_path,
            tls_client_key_path=tls_client_key_path,
            api_key=api_key,
            allowed_namespaces=allowed_namespaces,
        )
        self.server = Server(
            "temporal-mcp-server",
            on_list_tools=self._list_tools,
            on_call_tool=self._call_tool,
        )

    async def _list_tools(self, context: Any, params: Any) -> ListToolsResult:
        """List available Temporal tools."""
        return ListToolsResult(tools=get_all_tools(self.client_manager.allowed_namespaces))

    async def _call_tool(self, context: Any, params: CallToolRequestParams) -> CallToolResult:
        """Handle tool execution requests."""
        content = list(await self._execute_tool(params.name, params.arguments or {}))
        return CallToolResult(content=content)

    async def _execute_tool(self, name: str, arguments: Any) -> Sequence[ContentBlock]:
        """Execute a Temporal tool by name."""
        handler_arguments = dict(arguments)
        requested_namespace = handler_arguments.pop("namespace", None)

        try:
            namespace = self.client_manager.resolve_namespace(requested_namespace)
        except Exception as e:
            print(f"Rejected tool {name} namespace={requested_namespace!r}: {e}", file=sys.stderr)
            return format_error_response(e, name)

        try:
            client = await self.client_manager.get_client(namespace)
        except Exception as e:
            print(f"Connection failed for tool {name} namespace={namespace}: {e}", file=sys.stderr)
            return format_connection_error(e)

        print(f"Executing tool {name} namespace={namespace}", file=sys.stderr)
        try:
            # Workflow operations
            if name == "start_workflow":
                return await workflow_handlers.start_workflow(client, handler_arguments)
            elif name == "cancel_workflow":
                return await workflow_handlers.cancel_workflow(client, handler_arguments)
            elif name == "terminate_workflow":
                return await workflow_handlers.terminate_workflow(client, handler_arguments)
            elif name == "get_workflow_result":
                return await workflow_handlers.get_workflow_result(client, handler_arguments)
            elif name == "describe_workflow":
                return await workflow_handlers.describe_workflow(client, handler_arguments)
            elif name == "list_workflows":
                return await workflow_handlers.list_workflows(client, handler_arguments)
            elif name == "get_workflow_history":
                return await workflow_handlers.get_workflow_history(client, handler_arguments)
            elif name == "get_workflow_event":
                return await workflow_handlers.get_workflow_event(client, handler_arguments)

            # Standalone activity operations
            elif name == "start_activity":
                return await activity_handlers.start_activity(client, handler_arguments)
            elif name == "execute_activity":
                return await activity_handlers.execute_activity(client, handler_arguments)
            elif name == "get_activity_result":
                return await activity_handlers.get_activity_result(client, handler_arguments)
            elif name == "describe_activity":
                return await activity_handlers.describe_activity(client, handler_arguments)
            elif name == "list_activities":
                return await activity_handlers.list_activities(client, handler_arguments)
            elif name == "count_activities":
                return await activity_handlers.count_activities(client, handler_arguments)
            elif name == "cancel_activity":
                return await activity_handlers.cancel_activity(client, handler_arguments)
            elif name == "terminate_activity":
                return await activity_handlers.terminate_activity(client, handler_arguments)

            # Query and signal operations
            elif name == "query_workflow":
                return await query_handlers.query_workflow(client, handler_arguments)
            elif name == "signal_workflow":
                return await query_handlers.signal_workflow(client, handler_arguments)
            elif name == "continue_as_new":
                return await query_handlers.continue_as_new(client, handler_arguments)

            # Batch operations
            elif name == "batch_signal":
                return await batch_handlers.batch_signal(client, handler_arguments)
            elif name == "batch_cancel":
                return await batch_handlers.batch_cancel(client, handler_arguments)
            elif name == "batch_terminate":
                return await batch_handlers.batch_terminate(client, handler_arguments)
            elif name == "batch_cancel_activities":
                return await batch_handlers.batch_cancel_activities(client, handler_arguments)
            elif name == "batch_terminate_activities":
                return await batch_handlers.batch_terminate_activities(client, handler_arguments)

            # Schedule operations
            elif name == "create_schedule":
                return await schedule_handlers.create_schedule(client, handler_arguments)
            elif name == "list_schedules":
                return await schedule_handlers.list_schedules(client, handler_arguments)
            elif name == "pause_schedule":
                return await schedule_handlers.pause_schedule(client, handler_arguments)
            elif name == "unpause_schedule":
                return await schedule_handlers.unpause_schedule(client, handler_arguments)
            elif name == "delete_schedule":
                return await schedule_handlers.delete_schedule(client, handler_arguments)
            elif name == "trigger_schedule":
                return await schedule_handlers.trigger_schedule(client, handler_arguments)
            elif name == "describe_schedule":
                return await schedule_handlers.describe_schedule(client, handler_arguments)

            else:
                return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}", "type": "unknown_tool"}, indent=2))]

        except Exception as e:
            print(f"Tool failed: {name} namespace={namespace}", file=sys.stderr)
            return format_error_response(e, name)

    async def run(self):
        """Run the MCP server."""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
        finally:
            await self.client_manager.disconnect()
