"""MCP Server for Temporal workflow orchestration."""

import asyncio
import base64
import json
import os
import sys
import traceback
from typing import Any, Optional
from datetime import timedelta

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from temporalio.client import Client, TLSConfig, Schedule, ScheduleActionStartWorkflow, ScheduleSpec, ScheduleIntervalSpec

#"TEMPORAL_HOST": "host.docker.internal:7233"
#"TEMPORAL_HOST": "temporal.dev.use2.hscp-workload-dev.aws.paylocity.private:7233"

class TemporalMCPServer:
    """MCP Server that provides tools for interacting with Temporal."""

    def __init__(self, temporal_host: str = "localhost:7233", namespace: str = "default", 
                 tls_enabled: Optional[bool] = None):
        """Initialize the Temporal MCP server.
        
        Args:
            temporal_host: The Temporal server host and port
            namespace: The Temporal namespace to use
            tls_enabled: Whether to use TLS for connection (None = auto-detect, True = force enable, False = force disable)
        """
        self.temporal_host = temporal_host
        self.namespace = namespace
        self.tls_enabled = tls_enabled
        self.client: Optional[Client] = None
        self.server = Server("temporal-mcp-server")
        self._setup_handlers()

    async def connect(self):
        """Connect to Temporal server."""
        if not self.client:
            # Determine if we need TLS
            # Priority: explicit tls_enabled setting > auto-detect from hostname
            tls_config = None
            
            if self.tls_enabled is True:
                # Explicitly enabled
                tls_config = TLSConfig()
                print(f"Connecting to {self.temporal_host} with TLS enabled (explicit)", file=sys.stderr)
            elif self.tls_enabled is False:
                # Explicitly disabled
                tls_config = None
                print(f"Connecting to {self.temporal_host} without TLS (explicit)", file=sys.stderr)
            elif (
                "localhost" not in self.temporal_host and 
                "127.0.0.1" not in self.temporal_host and
                "host.docker.internal" not in self.temporal_host
            ):
                # Auto-detect: enable TLS for remote connections
                tls_config = TLSConfig()
                print(f"Connecting to {self.temporal_host} with TLS enabled (auto-detected for remote host)", file=sys.stderr)
            else:
                # Auto-detect: disable TLS for local connections
                print(f"Connecting to {self.temporal_host} without TLS (auto-detected for local host)", file=sys.stderr)
            
            print(f"Namespace: {self.namespace}", file=sys.stderr)
            print(f"TLS Enabled: {tls_config is not None}", file=sys.stderr)
            
            try:
                self.client = await Client.connect(
                    self.temporal_host,
                    namespace=self.namespace,
                    tls=tls_config,
                )
                print(f"Successfully connected to Temporal at {self.temporal_host}", file=sys.stderr)
            except Exception as e:
                print(f"Failed to connect to Temporal at {self.temporal_host}: {type(e).__name__}: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                raise

    async def disconnect(self):
        """Disconnect from Temporal server."""
        if self.client:
            await self.client.close()
            self.client = None

    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List available Temporal tools."""
            return [
                Tool(
                    name="start_workflow",
                    description="Start a new Temporal workflow execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_name": {
                                "type": "string",
                                "description": "The name of the workflow to start"
                            },
                            "workflow_id": {
                                "type": "string",
                                "description": "Unique identifier for the workflow execution"
                            },
                            "task_queue": {
                                "type": "string",
                                "description": "The task queue to use for this workflow"
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments to pass to the workflow (as JSON object)"
                            }
                        },
                        "required": ["workflow_name", "workflow_id", "task_queue"]
                    }
                ),
                Tool(
                    name="query_workflow",
                    description="Query a running workflow for its current state",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID to query"
                            },
                            "query_name": {
                                "type": "string",
                                "description": "The name of the query to execute"
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments for the query (as JSON object)"
                            }
                        },
                        "required": ["workflow_id", "query_name"]
                    }
                ),
                Tool(
                    name="signal_workflow",
                    description="Send a signal to a running workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID to signal"
                            },
                            "signal_name": {
                                "type": "string",
                                "description": "The name of the signal to send"
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments for the signal (as JSON object)"
                            }
                        },
                        "required": ["workflow_id", "signal_name"]
                    }
                ),
                Tool(
                    name="cancel_workflow",
                    description="Cancel a running workflow execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID to cancel"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                ),
                Tool(
                    name="get_workflow_result",
                    description="Get the result of a completed workflow",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                ),
                Tool(
                    name="describe_workflow",
                    description="Get detailed information about a workflow execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID to describe"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                ),
                Tool(
                    name="list_workflows",
                    description="List workflow executions based on a query. Specify 'limit' to control the number of results (default: 100, max recommended: 1000). Use 'skip' to paginate through results.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "List filter query (e.g., 'WorkflowType=\"MyWorkflow\"')"
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of results to return (default: 100, increase for more results)"
                            },
                            "skip": {
                                "type": "number",
                                "description": "Number of results to skip for pagination (default: 0)"
                            }
                        }
                    }
                ),
                Tool(
                    name="terminate_workflow",
                    description="Forcefully terminate a workflow execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID to terminate"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for termination"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                ),
                Tool(
                    name="get_workflow_history",
                    description="Get the complete event history of a workflow execution. Specify 'limit' to control the number of events (default: 1000).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow execution ID"
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of history events to return (default: 1000)"
                            }
                        },
                        "required": ["workflow_id"]
                    }
                ),
                Tool(
                    name="batch_signal",
                    description="Send a signal to multiple workflows matching a query. Specify 'limit' to control batch size (default: 100).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query to select workflows"
                            },
                            "signal_name": {
                                "type": "string",
                                "description": "The signal name to send"
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments for the signal"
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of workflows to signal (default: 100)"
                            }
                        },
                        "required": ["query", "signal_name"]
                    }
                ),
                Tool(
                    name="batch_cancel",
                    description="Cancel multiple workflows matching a query. Specify 'limit' to control batch size (default: 100).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query to select workflows to cancel"
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of workflows to cancel (default: 100)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="batch_terminate",
                    description="Terminate multiple workflows matching a query. Specify 'limit' to control batch size (default: 100).",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Query to select workflows to terminate"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for termination"
                            },
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of workflows to terminate (default: 100)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="create_schedule",
                    description="Create a new schedule for periodic workflow execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "string",
                                "description": "Unique identifier for the schedule"
                            },
                            "workflow_name": {
                                "type": "string",
                                "description": "Name of the workflow to schedule"
                            },
                            "task_queue": {
                                "type": "string",
                                "description": "Task queue for the workflow"
                            },
                            "cron": {
                                "type": "string",
                                "description": "Cron expression (e.g., '0 12 * * *')"
                            },
                            "args": {
                                "type": "object",
                                "description": "Arguments for the workflow"
                            }
                        },
                        "required": ["schedule_id", "workflow_name", "task_queue", "cron"]
                    }
                ),
                Tool(
                    name="list_schedules",
                    description="List all schedules. Specify 'limit' to control the number of results (default: 100). Use 'skip' to paginate through results.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "number",
                                "description": "Maximum number of schedules to return (default: 100)"
                            },
                            "skip": {
                                "type": "number",
                                "description": "Number of results to skip for pagination (default: 0)"
                            }
                        }
                    }
                ),
                Tool(
                    name="pause_schedule",
                    description="Pause a schedule",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "string",
                                "description": "The schedule ID to pause"
                            },
                            "note": {
                                "type": "string",
                                "description": "Note explaining why the schedule was paused"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                ),
                Tool(
                    name="unpause_schedule",
                    description="Resume a paused schedule",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "string",
                                "description": "The schedule ID to unpause"
                            },
                            "note": {
                                "type": "string",
                                "description": "Note explaining why the schedule was resumed"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                ),
                Tool(
                    name="delete_schedule",
                    description="Delete a schedule",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "string",
                                "description": "The schedule ID to delete"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                ),
                Tool(
                    name="trigger_schedule",
                    description="Manually trigger a scheduled workflow immediately",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "schedule_id": {
                                "type": "string",
                                "description": "The schedule ID to trigger"
                            }
                        },
                        "required": ["schedule_id"]
                    }
                ),
                Tool(
                    name="continue_as_new",
                    description="Signal a workflow to continue as new (restart with new inputs while preserving history link)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "workflow_id": {
                                "type": "string",
                                "description": "The workflow ID to continue as new"
                            },
                            "signal_name": {
                                "type": "string",
                                "description": "The signal name to send (must be handled by the workflow to trigger continue-as-new)"
                            },
                            "signal_args": {
                                "type": "object",
                                "description": "Arguments for the signal that will trigger continue-as-new"
                            }
                        },
                        "required": ["workflow_id", "signal_name"]
                    }
                )
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Any) -> list[TextContent]:
            """Handle tool execution requests."""
            await self.connect()
            
            try:
                if name == "start_workflow":
                    return await self._start_workflow(arguments)
                elif name == "query_workflow":
                    return await self._query_workflow(arguments)
                elif name == "signal_workflow":
                    return await self._signal_workflow(arguments)
                elif name == "cancel_workflow":
                    return await self._cancel_workflow(arguments)
                elif name == "get_workflow_result":
                    return await self._get_workflow_result(arguments)
                elif name == "describe_workflow":
                    return await self._describe_workflow(arguments)
                elif name == "list_workflows":
                    return await self._list_workflows(arguments)
                elif name == "terminate_workflow":
                    return await self._terminate_workflow(arguments)
                elif name == "get_workflow_history":
                    return await self._get_workflow_history(arguments)
                elif name == "batch_signal":
                    return await self._batch_signal(arguments)
                elif name == "batch_cancel":
                    return await self._batch_cancel(arguments)
                elif name == "batch_terminate":
                    return await self._batch_terminate(arguments)
                elif name == "create_schedule":
                    return await self._create_schedule(arguments)
                elif name == "list_schedules":
                    return await self._list_schedules(arguments)
                elif name == "pause_schedule":
                    return await self._pause_schedule(arguments)
                elif name == "unpause_schedule":
                    return await self._unpause_schedule(arguments)
                elif name == "delete_schedule":
                    return await self._delete_schedule(arguments)
                elif name == "trigger_schedule":
                    return await self._trigger_schedule(arguments)
                elif name == "continue_as_new":
                    return await self._continue_as_new(arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    async def _start_workflow(self, args: dict) -> list[TextContent]:
        """Start a new workflow execution."""
        workflow_name = args["workflow_name"]
        workflow_id = args["workflow_id"]
        task_queue = args["task_queue"]
        workflow_args = args.get("args", {})

        # Note: This is a generic implementation. In practice, you would need
        # to have the workflow class registered and imported
        handle = await self.client.start_workflow(
            workflow_name,
            workflow_args,
            id=workflow_id,
            task_queue=task_queue,
        )

        result = {
            "workflow_id": handle.id,
            "run_id": handle.result_run_id,
            "status": "started"
        }
        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _query_workflow(self, args: dict) -> list[TextContent]:
        """Query a workflow execution."""
        workflow_id = args["workflow_id"]
        query_name = args["query_name"]
        query_args = args.get("args")

        handle = self.client.get_workflow_handle(workflow_id)
        result = await handle.query(query_name, query_args)
        
        return [TextContent(
            type="text",
            text=json.dumps({"query_result": result}, indent=2)
        )]

    async def _signal_workflow(self, args: dict) -> list[TextContent]:
        """Send a signal to a workflow."""
        workflow_id = args["workflow_id"]
        signal_name = args["signal_name"]
        signal_args = args.get("args")

        handle = self.client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name, signal_args)
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "signal_sent"}, indent=2)
        )]

    async def _cancel_workflow(self, args: dict) -> list[TextContent]:
        """Cancel a workflow execution."""
        workflow_id = args["workflow_id"]

        handle = self.client.get_workflow_handle(workflow_id)
        await handle.cancel()
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "cancelled"}, indent=2)
        )]

    async def _get_workflow_result(self, args: dict) -> list[TextContent]:
        """Get the result of a workflow execution."""
        workflow_id = args["workflow_id"]

        handle = self.client.get_workflow_handle(workflow_id)
        result = await handle.result()
        
        return [TextContent(
            type="text",
            text=json.dumps({"result": result}, indent=2)
        )]

    async def _describe_workflow(self, args: dict) -> list[TextContent]:
        """Get detailed information about a workflow."""
        workflow_id = args["workflow_id"]

        handle = self.client.get_workflow_handle(workflow_id)
        description = await handle.describe()
        
        info = {
            "workflow_id": description.id,
            "run_id": description.run_id,
            "workflow_type": description.workflow_type,
            "status": str(description.status),
            "start_time": str(description.start_time),
            "execution_time": str(description.execution_time) if description.execution_time else None,
            "close_time": str(description.close_time) if description.close_time else None,
        }
        
        return [TextContent(type="text", text=json.dumps(info, indent=2))]

    async def _list_workflows(self, args: dict) -> list[TextContent]:
        """List workflow executions with skip-based pagination support."""
        query = args.get("query", "")
        limit = args.get("limit", 100)
        skip = args.get("skip", 0)

        workflows = []
        count = 0
        total_fetched = 0
        
        async for workflow in self.client.list_workflows(query):
            # Skip the first 'skip' results
            if count < skip:
                count += 1
                continue
            
            workflows.append({
                "workflow_id": workflow.id,
                "run_id": workflow.run_id,
                "workflow_type": workflow.workflow_type,
                "status": str(workflow.status),
                "start_time": str(workflow.start_time),
            })
            count += 1
            total_fetched += 1
            
            if total_fetched >= limit:
                break
        
        # Check if there are more results by trying to fetch one more
        has_more = False
        try:
            async for _ in self.client.list_workflows(query):
                if count < skip + limit:
                    count += 1
                    continue
                has_more = True
                break
        except:
            pass
        
        result = {
            "workflows": workflows,
            "count": len(workflows),
            "skip": skip,
            "limit": limit
        }
        
        if has_more:
            result["has_more"] = True
            result["next_skip"] = skip + limit
            result["message"] = f"Showing {len(workflows)} workflows (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
        else:
            result["has_more"] = False
            result["message"] = f"Showing all {len(workflows)} workflows (skipped {skip}). No more results."
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    async def _terminate_workflow(self, args: dict) -> list[TextContent]:
        """Terminate a workflow execution."""
        workflow_id = args["workflow_id"]
        reason = args.get("reason", "Terminated via MCP")

        handle = self.client.get_workflow_handle(workflow_id)
        await handle.terminate(reason)
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "terminated", "reason": reason}, indent=2)
        )]

    async def _get_workflow_history(self, args: dict) -> list[TextContent]:
        """Get workflow execution history."""
        workflow_id = args["workflow_id"]
        limit = args.get("limit", 1000)

        handle = self.client.get_workflow_handle(workflow_id)
        
        events = []
        async for event in handle.fetch_history():
            events.append({
                "event_id": event.event_id,
                "event_type": event.event_type,
                "event_time": str(event.event_time),
            })
            if len(events) >= limit:
                break
        
        return [TextContent(
            type="text",
            text=json.dumps({"workflow_id": workflow_id, "events": events, "count": len(events)}, indent=2)
        )]

    async def _batch_signal(self, args: dict) -> list[TextContent]:
        """Send signal to multiple workflows."""
        query = args["query"]
        signal_name = args["signal_name"]
        signal_args = args.get("args")
        limit = args.get("limit", 100)

        workflows_signaled = []
        async for workflow in self.client.list_workflows(query):
            if len(workflows_signaled) >= limit:
                break
            
            try:
                handle = self.client.get_workflow_handle(workflow.id)
                await handle.signal(signal_name, signal_args)
                workflows_signaled.append(workflow.id)
            except Exception as e:
                workflows_signaled.append(f"{workflow.id} (error: {str(e)})")
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "signal_name": signal_name,
                "workflows_signaled": workflows_signaled,
                "count": len(workflows_signaled)
            }, indent=2)
        )]

    async def _batch_cancel(self, args: dict) -> list[TextContent]:
        """Cancel multiple workflows."""
        query = args["query"]
        limit = args.get("limit", 100)

        workflows_cancelled = []
        async for workflow in self.client.list_workflows(query):
            if len(workflows_cancelled) >= limit:
                break
            
            try:
                handle = self.client.get_workflow_handle(workflow.id)
                await handle.cancel()
                workflows_cancelled.append(workflow.id)
            except Exception as e:
                workflows_cancelled.append(f"{workflow.id} (error: {str(e)})")
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "workflows_cancelled": workflows_cancelled,
                "count": len(workflows_cancelled)
            }, indent=2)
        )]

    async def _batch_terminate(self, args: dict) -> list[TextContent]:
        """Terminate multiple workflows."""
        query = args["query"]
        reason = args.get("reason", "Batch termination via MCP")
        limit = args.get("limit", 100)

        workflows_terminated = []
        async for workflow in self.client.list_workflows(query):
            if len(workflows_terminated) >= limit:
                break
            
            try:
                handle = self.client.get_workflow_handle(workflow.id)
                await handle.terminate(reason)
                workflows_terminated.append(workflow.id)
            except Exception as e:
                workflows_terminated.append(f"{workflow.id} (error: {str(e)})")
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "reason": reason,
                "workflows_terminated": workflows_terminated,
                "count": len(workflows_terminated)
            }, indent=2)
        )]

    async def _create_schedule(self, args: dict) -> list[TextContent]:
        """Create a new workflow schedule."""
        schedule_id = args["schedule_id"]
        workflow_name = args["workflow_name"]
        task_queue = args["task_queue"]
        cron = args["cron"]
        workflow_args = args.get("args", {})

        try:
            await self.client.create_schedule(
                schedule_id,
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        workflow_name,
                        workflow_args,
                        id=f"{schedule_id}-workflow",
                        task_queue=task_queue,
                    ),
                    spec=ScheduleSpec(cron_expressions=[cron]),
                ),
            )
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "status": "created",
                    "schedule_id": schedule_id,
                    "cron": cron
                }, indent=2)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2)
            )]

    async def _list_schedules(self, args: dict) -> list[TextContent]:
        """List all schedules with skip-based pagination."""
        limit = args.get("limit", 100)
        skip = args.get("skip", 0)

        schedules = []
        count = 0
        total_fetched = 0
        
        async for schedule in self.client.list_schedules():
            # Skip the first 'skip' results
            if count < skip:
                count += 1
                continue
                
            schedules.append({
                "schedule_id": schedule.id,
                "state": str(schedule.info.paused) if schedule.info else "unknown",
            })
            count += 1
            total_fetched += 1
            
            if total_fetched >= limit:
                break
        
        # Check if there are more results
        has_more = False
        try:
            async for _ in self.client.list_schedules():
                if count < skip + limit:
                    count += 1
                    continue
                has_more = True
                break
        except:
            pass
        
        result = {
            "schedules": schedules,
            "count": len(schedules),
            "skip": skip,
            "limit": limit
        }
        
        if has_more:
            result["has_more"] = True
            result["next_skip"] = skip + limit
            result["message"] = f"Showing {len(schedules)} schedules (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
        else:
            result["has_more"] = False
            result["message"] = f"Showing all {len(schedules)} schedules (skipped {skip}). No more results."
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]

    async def _pause_schedule(self, args: dict) -> list[TextContent]:
        """Pause a schedule."""
        schedule_id = args["schedule_id"]
        note = args.get("note", "Paused via MCP")

        handle = self.client.get_schedule_handle(schedule_id)
        await handle.pause(note=note)
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "paused", "schedule_id": schedule_id}, indent=2)
        )]

    async def _unpause_schedule(self, args: dict) -> list[TextContent]:
        """Resume a schedule."""
        schedule_id = args["schedule_id"]
        note = args.get("note", "Resumed via MCP")

        handle = self.client.get_schedule_handle(schedule_id)
        await handle.unpause(note=note)
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "unpaused", "schedule_id": schedule_id}, indent=2)
        )]

    async def _delete_schedule(self, args: dict) -> list[TextContent]:
        """Delete a schedule."""
        schedule_id = args["schedule_id"]

        handle = self.client.get_schedule_handle(schedule_id)
        await handle.delete()
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "deleted", "schedule_id": schedule_id}, indent=2)
        )]

    async def _trigger_schedule(self, args: dict) -> list[TextContent]:
        """Manually trigger a schedule."""
        schedule_id = args["schedule_id"]

        handle = self.client.get_schedule_handle(schedule_id)
        await handle.trigger()
        
        return [TextContent(
            type="text",
            text=json.dumps({"status": "triggered", "schedule_id": schedule_id}, indent=2)
        )]

    async def _continue_as_new(self, args: dict) -> list[TextContent]:
        """Signal a workflow to continue as new.
        
        Note: This sends a signal to the workflow. The workflow itself must be
        designed to call workflow.continue_as_new() when it receives this signal.
        This is just a helper to trigger that behavior via signal.
        """
        workflow_id = args["workflow_id"]
        signal_name = args["signal_name"]
        signal_args = args.get("signal_args", {})
        
        handle = self.client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name, signal_args)
        
        return [TextContent(
            type="text",
            text=json.dumps({
                "status": "signal_sent",
                "workflow_id": workflow_id,
                "signal_name": signal_name,
                "note": "Workflow must implement continue-as-new logic in signal handler"
            }, indent=2)
        )]

    async def run(self):
        """Run the MCP server."""
        try:
            # The actual server running is handled by the MCP framework
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            await self.disconnect()


async def main():
    """Main entry point for the MCP server."""
    temporal_host = os.environ.get("TEMPORAL_HOST", "localhost:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    
    # Parse TLS setting: None (auto-detect), True (force enable), False (force disable)
    tls_env = os.environ.get("TEMPORAL_TLS_ENABLED", "").lower()
    if tls_env == "true":
        tls_enabled = True
    elif tls_env == "false":
        tls_enabled = False
    else:
        tls_enabled = None  # Auto-detect
    
    print(f"Starting MCP server with TEMPORAL_HOST={temporal_host}, TLS={tls_enabled}", file=sys.stderr)
    
    server = TemporalMCPServer(
        temporal_host=temporal_host,
        namespace=namespace,
        tls_enabled=tls_enabled
    )
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
