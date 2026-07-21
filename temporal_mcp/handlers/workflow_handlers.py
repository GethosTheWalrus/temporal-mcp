"""Handlers for workflow operations."""

import asyncio
import json
import sys
from typing import Any

from mcp.types import TextContent
from temporalio.client import Client
from temporalio.api.common.v1 import Payloads
from temporalio.api.enums.v1 import EventType, RetryState, StartChildWorkflowExecutionFailedCause, TimeoutType, WorkflowExecutionStatus
from temporalio.api.failure.v1 import Failure


async def start_workflow(client: Client, args: dict) -> list[TextContent]:
    """Start a new workflow execution.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_name, workflow_id, task_queue, and optional args

    Returns:
        Success response with workflow details
    """
    workflow_name = args["workflow_name"]
    workflow_id = args["workflow_id"]
    task_queue = args["task_queue"]
    workflow_args = args.get("args", {})

    handle = await client.start_workflow(
        workflow_name,
        workflow_args,
        id=workflow_id,
        task_queue=task_queue,
    )

    result = {"workflow_id": handle.id, "run_id": handle.result_run_id, "status": "started"}
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def cancel_workflow(client: Client, args: dict) -> list[TextContent]:
    """Cancel a workflow execution.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id

    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]

    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()

    return [TextContent(type="text", text=json.dumps({"status": "cancelled", "workflow_id": workflow_id}, indent=2))]


async def terminate_workflow(client: Client, args: dict) -> list[TextContent]:
    """Terminate a workflow execution.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional reason

    Returns:
        Success response
    """
    workflow_id = args["workflow_id"]
    reason = args.get("reason", "Terminated via MCP")

    handle = client.get_workflow_handle(workflow_id)
    await handle.terminate(reason)

    return [TextContent(type="text", text=json.dumps({"status": "terminated", "workflow_id": workflow_id, "reason": reason}, indent=2))]


async def get_workflow_result(client: Client, args: dict) -> list[TextContent]:
    """Get the result of a workflow execution.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional timeout

    Returns:
        Workflow result or timeout error
    """
    workflow_id = args["workflow_id"]
    timeout = args.get("timeout")

    handle = client.get_workflow_handle(workflow_id)

    try:
        if timeout:
            result = await asyncio.wait_for(handle.result(), timeout=timeout)
        else:
            result = await handle.result()

        return [TextContent(type="text", text=json.dumps({"result": result, "workflow_id": workflow_id}, indent=2, default=str))]
    except asyncio.TimeoutError:
        return [
            TextContent(
                type="text",
                text=json.dumps(
                    {
                        "error": f"Timeout waiting for workflow result after {timeout} seconds",
                        "type": "timeout",
                        "workflow_id": workflow_id,
                        "note": "Workflow may still be running. Use describe_workflow to check status.",
                    },
                    indent=2,
                ),
            )
        ]


async def describe_workflow(client: Client, args: dict) -> list[TextContent]:
    """Get detailed information about a workflow.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id

    Returns:
        Workflow description
    """
    workflow_id = args["workflow_id"]

    handle = client.get_workflow_handle(workflow_id)
    description = await handle.describe()

    status_name = WorkflowExecutionStatus.Name(int(description.status)) if description.status is not None else "UNKNOWN"  # type: ignore[arg-type]

    info = {
        "workflow_id": description.id,
        "run_id": description.run_id,
        "workflow_type": description.workflow_type,
        "status": status_name,
        "status_code": description.status,
        "start_time": str(description.start_time),
        "execution_time": str(description.execution_time) if description.execution_time else None,
        "close_time": str(description.close_time) if description.close_time else None,
    }

    return [TextContent(type="text", text=json.dumps(info, indent=2))]


async def list_workflows(client: Client, args: dict) -> list[TextContent]:
    """List workflow executions with skip-based pagination support.

    Args:
        client: Connected Temporal client
        args: Arguments containing optional query, limit, and skip

    Returns:
        List of workflows with pagination info
    """
    query = args.get("query", "")
    limit = args.get("limit", 100)
    skip = args.get("skip", 0)

    workflows = []
    count = 0
    total_fetched = 0

    async for workflow in client.list_workflows(query):
        # Skip the first 'skip' results
        if count < skip:
            count += 1
            continue

        workflows.append(
            {
                "workflow_id": workflow.id,
                "run_id": workflow.run_id,
                "workflow_type": workflow.workflow_type,
                "status": WorkflowExecutionStatus.Name(int(workflow.status)) if workflow.status is not None else "UNKNOWN",  # type: ignore[arg-type]
                "status_code": workflow.status,
                "start_time": str(workflow.start_time),
            }
        )
        count += 1
        total_fetched += 1

        if total_fetched >= limit:
            break

    # Check if there are more results
    has_more = False
    try:
        async for _ in client.list_workflows(query):
            if count < skip + limit:
                count += 1
                continue
            has_more = True
            break
    except Exception as e:
        print(f"Warning: Error checking for more workflows: {e}", file=sys.stderr)

    result = {"workflows": workflows, "count": len(workflows), "skip": skip, "limit": limit}

    if has_more:
        result["has_more"] = True
        result["next_skip"] = skip + limit
        result["message"] = f"Showing {len(workflows)} workflows (skipped {skip}). More results available. Use skip={skip + limit} to get the next page."
    else:
        result["has_more"] = False
        result["message"] = f"Showing all {len(workflows)} workflows (skipped {skip}). No more results."

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def get_workflow_history(client: Client, args: dict) -> list[TextContent]:
    """Get workflow execution history.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id and optional limit

    Returns:
        Workflow history events
    """
    workflow_id = args["workflow_id"]
    limit = args.get("limit", 1000)

    handle = client.get_workflow_handle(workflow_id)

    events = []
    scheduled_activities: dict[int, dict[str, Any]] = {}
    initiated_child_workflows: dict[int, dict[str, Any]] = {}
    count = 0
    async for event in handle.fetch_history_events():
        attributes_type = event.WhichOneof("attributes")
        if attributes_type == "activity_task_scheduled_event_attributes":
            scheduled_attrs = event.activity_task_scheduled_event_attributes
            scheduled_activities[event.event_id] = {
                "activity_id": scheduled_attrs.activity_id,
                "activity_type": scheduled_attrs.activity_type.name,
            }
        elif attributes_type == "start_child_workflow_execution_initiated_event_attributes":
            initiated_attrs = event.start_child_workflow_execution_initiated_event_attributes
            initiated_child_workflows[event.event_id] = {
                "workflow_id": initiated_attrs.workflow_id,
                "workflow_type": initiated_attrs.workflow_type.name,
            }

        events.append(_workflow_history_event_to_dict(event, scheduled_activities, initiated_child_workflows))
        count += 1
        if count >= limit:
            break

    return [TextContent(type="text", text=json.dumps({"workflow_id": workflow_id, "events": events, "count": len(events)}, indent=2))]


def _workflow_history_event_to_dict(event: Any, scheduled_activities: dict[int, dict[str, Any]], initiated_child_workflows: dict[int, dict[str, Any]]) -> dict[str, Any]:
    event_info = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_type_name": _enum_name(EventType, event.event_type),
        "event_time": str(event.event_time),
        "attributes": {},
    }

    attributes_type = event.WhichOneof("attributes")
    if attributes_type == "activity_task_scheduled_event_attributes":
        attrs = event.activity_task_scheduled_event_attributes
        event_info["attributes"] = {
            "activity": {
                "activity_id": attrs.activity_id,
                "activity_type": attrs.activity_type.name,
            }
        }
    elif attributes_type == "activity_task_failed_event_attributes":
        attrs = event.activity_task_failed_event_attributes
        event_info["attributes"] = {
            "scheduled_event_id": attrs.scheduled_event_id,
            "started_event_id": attrs.started_event_id,
            "activity": scheduled_activities.get(attrs.scheduled_event_id),
            "retry_state": attrs.retry_state,
            "retry_state_name": _enum_name(RetryState, attrs.retry_state),
            "failure": _failure_to_metadata(attrs.failure),
        }
    elif attributes_type == "start_child_workflow_execution_initiated_event_attributes":
        attrs = event.start_child_workflow_execution_initiated_event_attributes
        event_info["attributes"] = {
            "workflow_task_completed_event_id": attrs.workflow_task_completed_event_id,
            "workflow": {
                "workflow_id": attrs.workflow_id,
                "workflow_type": attrs.workflow_type.name,
            },
        }
    elif attributes_type in {
        "child_workflow_execution_started_event_attributes",
        "child_workflow_execution_completed_event_attributes",
        "child_workflow_execution_failed_event_attributes",
        "child_workflow_execution_canceled_event_attributes",
        "child_workflow_execution_terminated_event_attributes",
    }:
        attrs = getattr(event, attributes_type)
        workflow = _child_workflow_metadata(attrs)
        initiated_workflow = initiated_child_workflows.get(attrs.initiated_event_id)
        if initiated_workflow:
            workflow = {**initiated_workflow, **workflow}

        child_attrs: dict[str, Any] = {
            "initiated_event_id": attrs.initiated_event_id,
            "started_event_id": getattr(attrs, "started_event_id", None),
            "workflow": workflow,
        }
        if attributes_type == "child_workflow_execution_failed_event_attributes":
            child_attrs.update(
                {
                    "retry_state": attrs.retry_state,
                    "retry_state_name": _enum_name(RetryState, attrs.retry_state),
                    "failure": _failure_to_metadata(attrs.failure),
                }
            )
        event_info["attributes"] = child_attrs
    elif attributes_type == "start_child_workflow_execution_failed_event_attributes":
        attrs = event.start_child_workflow_execution_failed_event_attributes
        event_info["attributes"] = {
            "initiated_event_id": attrs.initiated_event_id,
            "workflow_task_completed_event_id": attrs.workflow_task_completed_event_id,
            "cause": attrs.cause,
            "cause_name": _enum_name(StartChildWorkflowExecutionFailedCause, attrs.cause),
            "workflow": {
                "workflow_id": attrs.workflow_id,
                "workflow_type": attrs.workflow_type.name,
            },
        }

    return event_info


def _child_workflow_metadata(attrs: Any) -> dict[str, Any]:
    workflow_execution = attrs.workflow_execution
    return {
        "workflow_id": workflow_execution.workflow_id,
        "run_id": workflow_execution.run_id,
        "workflow_type": attrs.workflow_type.name,
    }


def _failure_to_metadata(failure: Failure) -> dict[str, Any]:
    failure_type = failure.WhichOneof("failure_info")
    result: dict[str, Any] = {
        "message": failure.message,
        "source": failure.source,
        "stack_trace": failure.stack_trace,
        "type": failure_type.replace("_info", "") if failure_type else None,
    }

    if failure_type == "application_failure_info":
        application_info = failure.application_failure_info
        result["application_failure"] = {
            "type": application_info.type,
            "non_retryable": application_info.non_retryable,
        }
    elif failure_type == "timeout_failure_info":
        timeout_info = failure.timeout_failure_info
        result["timeout_failure"] = {
            "timeout_type": timeout_info.timeout_type,
            "timeout_type_name": _enum_name(TimeoutType, timeout_info.timeout_type),
        }
    elif failure_type == "server_failure_info":
        result["server_failure"] = {"non_retryable": failure.server_failure_info.non_retryable}
    elif failure_type == "activity_failure_info":
        activity_info = failure.activity_failure_info
        result["activity_failure"] = {
            "scheduled_event_id": activity_info.scheduled_event_id,
            "started_event_id": activity_info.started_event_id,
            "identity": activity_info.identity,
            "activity_id": activity_info.activity_id,
            "activity_type": activity_info.activity_type.name,
            "retry_state": activity_info.retry_state,
            "retry_state_name": _enum_name(RetryState, activity_info.retry_state),
        }
    elif failure_type == "child_workflow_execution_failure_info":
        child_workflow_info = failure.child_workflow_execution_failure_info
        result["child_workflow_failure"] = {
            "initiated_event_id": child_workflow_info.initiated_event_id,
            "started_event_id": child_workflow_info.started_event_id,
            "workflow": {
                "workflow_id": child_workflow_info.workflow_execution.workflow_id,
                "run_id": child_workflow_info.workflow_execution.run_id,
                "workflow_type": child_workflow_info.workflow_type.name,
            },
            "retry_state": child_workflow_info.retry_state,
            "retry_state_name": _enum_name(RetryState, child_workflow_info.retry_state),
        }

    result["cause"] = _failure_to_metadata(failure.cause) if failure.HasField("cause") else None
    return result


async def get_workflow_event(client: Client, args: dict) -> list[TextContent]:
    """Get a single workflow history event with decoded payload fields.

    Args:
        client: Connected Temporal client
        args: Arguments containing workflow_id, event_id, and optional run_id

    Returns:
        Workflow history event with decoded payload fields when present
    """
    workflow_id = args["workflow_id"]
    event_id = int(args["event_id"])
    run_id = args.get("run_id")

    handle = client.get_workflow_handle(workflow_id, run_id=run_id)

    scheduled_activities: dict[int, dict[str, Any]] = {}
    async for event in handle.fetch_history_events():
        if event.WhichOneof("attributes") == "activity_task_scheduled_event_attributes":
            attrs = event.activity_task_scheduled_event_attributes
            scheduled_activities[event.event_id] = {
                "activity_id": attrs.activity_id,
                "activity_type": attrs.activity_type.name,
            }

        if event.event_id == event_id:
            result = {
                "workflow_id": workflow_id,
                "run_id": run_id,
                "event": await _workflow_event_to_dict(client, event, scheduled_activities),
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    return [
        TextContent(
            type="text",
            text=json.dumps(
                {
                    "error": f"Event {event_id} not found in workflow history",
                    "type": "not_found",
                    "workflow_id": workflow_id,
                    "run_id": run_id,
                    "event_id": event_id,
                },
                indent=2,
            ),
        )
    ]


async def _workflow_event_to_dict(client: Client, event: Any, scheduled_activities: dict[int, dict[str, Any]]) -> dict[str, Any]:
    event_info = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_type_name": _enum_name(EventType, event.event_type),
        "event_time": str(event.event_time),
        "attributes": {},
    }

    attributes_type = event.WhichOneof("attributes")
    if attributes_type == "workflow_execution_started_event_attributes":
        attrs = event.workflow_execution_started_event_attributes
        event_info["attributes"] = {
            "workflow_type": attrs.workflow_type.name,
            "input": await _decode_payloads(client, attrs.input, collapse_single=False),
        }
    elif attributes_type == "activity_task_scheduled_event_attributes":
        attrs = event.activity_task_scheduled_event_attributes
        event_info["attributes"] = {
            "activity": {
                "activity_id": attrs.activity_id,
                "activity_type": attrs.activity_type.name,
            },
            "input": await _decode_payloads(client, attrs.input, collapse_single=False),
        }
    elif attributes_type == "activity_task_completed_event_attributes":
        attrs = event.activity_task_completed_event_attributes
        event_info["attributes"] = {
            "scheduled_event_id": attrs.scheduled_event_id,
            "started_event_id": attrs.started_event_id,
            "activity": scheduled_activities.get(attrs.scheduled_event_id),
            "result": await _decode_payloads(client, attrs.result, collapse_single=True),
        }
    elif attributes_type == "activity_task_failed_event_attributes":
        attrs = event.activity_task_failed_event_attributes
        event_info["attributes"] = {
            "scheduled_event_id": attrs.scheduled_event_id,
            "started_event_id": attrs.started_event_id,
            "activity": scheduled_activities.get(attrs.scheduled_event_id),
            "retry_state": attrs.retry_state,
            "retry_state_name": _enum_name(RetryState, attrs.retry_state),
            "failure": await _decode_failure(client, attrs.failure),
        }
    elif attributes_type == "workflow_execution_failed_event_attributes":
        attrs = event.workflow_execution_failed_event_attributes
        event_info["attributes"] = {
            "retry_state": attrs.retry_state,
            "retry_state_name": _enum_name(RetryState, attrs.retry_state),
            "failure": await _decode_failure(client, attrs.failure),
        }

    return event_info


async def _decode_payloads(client: Client, payloads: Payloads, *, collapse_single: bool) -> dict[str, Any]:
    payload_list = list(payloads.payloads)
    try:
        values = await client.data_converter.decode(payload_list)
        return {
            "decoded": True,
            "value": values[0] if collapse_single and len(values) == 1 else values,
            "payload_count": len(payload_list),
        }
    except Exception as e:
        return {
            "decoded": False,
            "error": str(e),
            "error_type": type(e).__name__,
            "payload_count": len(payload_list),
        }


async def _decode_failure(client: Client, failure: Failure) -> dict[str, Any]:
    try:
        decoded_failure = await client.data_converter.decode_failure(failure)
        return {
            "decoded": True,
            "message": getattr(decoded_failure, "message", str(decoded_failure)),
            "type": type(decoded_failure).__name__,
            "details": list(getattr(decoded_failure, "details", [])),
        }
    except Exception as e:
        return {
            "decoded": False,
            "message": failure.message,
            "source": failure.source,
            "stack_trace": failure.stack_trace,
            "error": str(e),
            "error_type": type(e).__name__,
        }


def _enum_name(enum_type: Any, value: Any) -> str:
    try:
        return str(enum_type.Name(int(value)))
    except Exception:
        return str(value)
