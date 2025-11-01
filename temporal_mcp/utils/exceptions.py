"""Exception handling and error formatting utilities."""

import json
import sys
import traceback
from typing import Any

from mcp.types import TextContent
from temporalio.client import RPCError
from temporalio.service import RPCStatusCode
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.client import ScheduleAlreadyRunningError


def format_connection_error(error: Exception) -> list[TextContent]:
    """Format a connection error response.
    
    Args:
        error: The connection exception
        
    Returns:
        List containing error message as TextContent
    """
    error_msg = f"Failed to connect to Temporal server: {type(error).__name__}: {str(error)}"
    print(error_msg, file=sys.stderr)
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": error_msg,
            "type": "connection_error"
        }, indent=2)
    )]


def format_error_response(error: Exception, tool_name: str) -> list[TextContent]:
    """Format an error response based on the exception type.
    
    Args:
        error: The exception that occurred
        tool_name: Name of the tool that encountered the error
        
    Returns:
        List containing formatted error as TextContent
    """
    if isinstance(error, KeyError):
        return _format_key_error(error, tool_name)
    elif isinstance(error, RPCError):
        return _format_rpc_error(error, tool_name)
    elif isinstance(error, WorkflowAlreadyStartedError):
        return _format_workflow_already_started_error(tool_name)
    elif isinstance(error, ScheduleAlreadyRunningError):
        return _format_schedule_already_exists_error(tool_name)
    else:
        return _format_generic_error(error, tool_name)


def _format_key_error(error: KeyError, tool_name: str) -> list[TextContent]:
    """Format a KeyError (missing parameter).
    
    Args:
        error: The KeyError exception
        tool_name: Name of the tool
        
    Returns:
        Formatted error response
    """
    error_msg = f"Missing required parameter: {str(error)}"
    print(f"KeyError in {tool_name}: {error_msg}", file=sys.stderr)
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": error_msg,
            "type": "missing_parameter",
            "tool": tool_name
        }, indent=2)
    )]


def _format_rpc_error(error: RPCError, tool_name: str) -> list[TextContent]:
    """Format an RPC error from Temporal.
    
    Args:
        error: The RPCError exception
        tool_name: Name of the tool
        
    Returns:
        Formatted error response
    """
    error_msg = str(error)
    error_type = "rpc_error"
    
    if error.status == RPCStatusCode.NOT_FOUND:
        error_type = "not_found"
        error_msg = f"Resource not found: {str(error)}"
    elif error.status == RPCStatusCode.ALREADY_EXISTS:
        error_type = "already_exists"
        error_msg = f"Resource already exists: {str(error)}"
    
    print(f"RPCError in {tool_name}: {error_msg}", file=sys.stderr)
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": error_msg,
            "type": error_type,
            "tool": tool_name
        }, indent=2)
    )]


def _format_workflow_already_started_error(tool_name: str) -> list[TextContent]:
    """Format a workflow already started error.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Formatted error response
    """
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": "Workflow with this ID already exists",
            "type": "workflow_already_started",
            "tool": tool_name
        }, indent=2)
    )]


def _format_schedule_already_exists_error(tool_name: str) -> list[TextContent]:
    """Format a schedule already exists error.
    
    Args:
        tool_name: Name of the tool
        
    Returns:
        Formatted error response
    """
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": "Schedule with this ID already exists",
            "type": "schedule_already_exists",
            "tool": tool_name
        }, indent=2)
    )]


def _format_generic_error(error: Exception, tool_name: str) -> list[TextContent]:
    """Format a generic error.
    
    Args:
        error: The exception
        tool_name: Name of the tool
        
    Returns:
        Formatted error response
    """
    error_msg = f"Error executing {tool_name}: {type(error).__name__}: {str(error)}"
    print(error_msg, file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    return [TextContent(
        type="text",
        text=json.dumps({
            "error": str(error),
            "error_type": type(error).__name__,
            "tool": tool_name
        }, indent=2)
    )]
