"""Tool definitions for the Temporal MCP server."""

from mcp.types import Tool


def get_all_tools() -> list[Tool]:
    """Get all available Temporal tools.
    
    Returns:
        List of Tool definitions
    """
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
            description="Cancel multiple workflows matching a query with concurrent processing for speed. Use 'concurrency' to control parallel operations (default: 50).",
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
                    },
                    "concurrency": {
                        "type": "number",
                        "description": "Number of workflows to cancel concurrently for faster processing (default: 50, max recommended: 100)"
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
