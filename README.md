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

## VS Code MCP Config

Add a `.vscode/mcp.json` file to your workspace. Choose the approach that fits your setup.

### Docker (environment variables)

Recommended when running via Docker. Configuration is passed through environment variables.

```json
{
  "servers": {
    "temporal": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TEMPORAL_HOST",
        "-e", "TEMPORAL_NAMESPACE",
        "-e", "TEMPORAL_TLS_ENABLED",
        "mcp/temporal"
      ],
      "env": {
        "TEMPORAL_HOST": "localhost:7233",
        "TEMPORAL_NAMESPACE": "default",
        "TEMPORAL_TLS_ENABLED": "false"
      }
    }
  }
}
```

### Python (CLI arguments)

Recommended when running from a local Python environment (e.g. installed via [PyPI](https://pypi.org/project/temporal-mcp-server/)). Configuration is passed as CLI arguments.

```json
{
  "servers": {
    "temporal": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "-m", "temporal_mcp",
        "--host", "localhost:7233",
        "--namespace", "default",
        "--tls-enabled", "false"
      ]
    }
  }
}
```

### Configuration Options

| Option | CLI Argument | Environment Variable | Default |
|--------|-------------|----------------------|---------|
| Temporal host | `--host` | `TEMPORAL_HOST` | `localhost:7233` |
| Namespace | `--namespace` | `TEMPORAL_NAMESPACE` | `default` |
| TLS | `--tls-enabled` | `TEMPORAL_TLS_ENABLED` | auto-detect |
| mTLS cert path | `--tls-cert` | `TEMPORAL_TLS_CLIENT_CERT_PATH` | — |
| mTLS key path | `--tls-key` | `TEMPORAL_TLS_CLIENT_KEY_PATH` | — |
| API key | `--api-key` | `TEMPORAL_API_KEY` | — |

CLI arguments take precedence over environment variables. When `TEMPORAL_API_KEY` is set, TLS is enabled automatically. When mTLS cert/key paths are provided, TLS is also enabled automatically.

## Development

### Running Tests

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest test.py -v
```

### Building the Docker Image

```bash
docker build -t mcp/temporal:latest .
```
