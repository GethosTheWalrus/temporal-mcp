# Temporal MCP Server

## Overview

This is a Model Context Protocol (MCP) server that provides tools for interacting with Temporal workflow orchestration. It enables AI assistants and other MCP clients to manage Temporal workflows, schedules, and workflow executions through a standardized interface. The server supports both local and remote Temporal instances.

## Tools

### Workflow Execution

- **`start_workflow`** - Start a new Temporal workflow execution with specified parameters, workflow ID, and task queue
- **`get_workflow_result`** - Retrieve the result of a completed workflow execution
- **`describe_workflow`** - Get detailed information about a workflow execution including status, timing, and metadata
- **`list_workflows`** - List workflow executions based on a query filter with pagination support (limit/skip)
- **`get_workflow_history`** - Retrieve the complete event history of a workflow execution

### Workflow Control

- **`query_workflow`** - Query a running workflow for its current state without affecting execution
- **`signal_workflow`** - Send a signal to a running workflow to change its behavior or provide data
- **`cancel_workflow`** - Request cancellation of a running workflow execution
- **`terminate_workflow`** - Forcefully terminate a workflow execution with a reason
- **`continue_as_new`** - Signal a workflow to continue as new (restart with new inputs while preserving history link)

### Batch Operations

- **`batch_signal`** - Send a signal to multiple workflows matching a query (configurable batch size)
- **`batch_cancel`** - Cancel multiple workflows matching a query (configurable batch size)
- **`batch_terminate`** - Terminate multiple workflows matching a query with a specified reason (configurable batch size)

### Schedule Management

- **`create_schedule`** - Create a new schedule for periodic workflow execution using cron expressions
- **`list_schedules`** - List all schedules with pagination support (limit/skip)
- **`pause_schedule`** - Pause a schedule to temporarily stop workflow executions
- **`unpause_schedule`** - Resume a paused schedule
- **`delete_schedule`** - Permanently delete a schedule
- **`trigger_schedule`** - Manually trigger a scheduled workflow immediately

## Temporal Documentation

For more information about Temporal, refer to the official Temporal documentation:

- **Temporal Documentation**: https://docs.temporal.io/
- **Workflows**: https://docs.temporal.io/workflows
- **Activities**: https://docs.temporal.io/activities
- **Python SDK**: https://docs.temporal.io/dev-guide/python

## MCP Client Config Examples

### OpenCode

Add to your OpenCode settings (`~/.config/opencode/opencode.json`):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "temporal": {
      "type": "local",
      "command": [
        "docker", "run", "-i", "--rm", "--network", "host",
        "-e", "TEMPORAL_HOST=192.168.69.98:7233",
        "-e", "TEMPORAL_NAMESPACE=default",
        "-e", "TEMPORAL_TLS_ENABLED=false",
        "temporal-mcp-server:latest"
      ],
      "enabled": true
    }
  }
}
```

### VS Code (Copilot MCP)

Add to your VS Code settings (`.vscode/mcp.json` or global settings):

```json
{
  "mcp.servers": {
    "temporal": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--network", "host",
        "-e", "TEMPORAL_HOST=192.168.69.98:7233",
        "-e", "TEMPORAL_NAMESPACE=default",
        "-e", "TEMPORAL_TLS_ENABLED=false",
        "temporal-mcp-server:latest"
      ]
    }
  }
}
```

### Cursor

Add to your Cursor MCP settings (`~/.cursor/mcp.json` on macOS/Linux or `%APPDATA%\Cursor\mcp.json` on Windows):

```json
{
  "mcpServers": {
    "temporal": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--network", "host",
        "-e", "TEMPORAL_HOST=192.168.69.98:7233",
        "-e", "TEMPORAL_NAMESPACE=default",
        "-e", "TEMPORAL_TLS_ENABLED=false",
        "temporal-mcp-server:latest"
      ]
    }
  }
}
```

### Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "temporal": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm", "--network", "host",
        "-e", "TEMPORAL_HOST=192.168.69.98:7233",
        "-e", "TEMPORAL_NAMESPACE=default",
        "-e", "TEMPORAL_TLS_ENABLED=false",
        "temporal-mcp-server:latest"
      ]
    }
  }
}
```

### Configuration Notes

- **TEMPORAL_HOST**: Set to your Temporal server address (default: `localhost:7233`)
- **TEMPORAL_NAMESPACE**: Set to your Temporal namespace (default: `default`)
- **TEMPORAL_TLS_ENABLED**: Set to `true` for remote servers, `false` for local, or omit for auto-detection
- Replace `192.168.69.98:7233` with your actual Temporal server address
- For local development, you can use `localhost:7233` or `host.docker.internal:7233` (when running in Docker)
