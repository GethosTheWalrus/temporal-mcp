# Temporal MCP Server

## Overview

This is a Model Context Protocol (MCP) server that provides tools for interacting with Temporal workflow orchestration. It enables AI assistants and other MCP clients to manage Temporal workflows, schedules, and workflow executions through a standardized interface. The server supports both local and remote Temporal instances.

Read more on the [Temporal Code Exchange](https://temporal.io/code-exchange/temporal-mcp-server)

## Distributions
- PyPI   - https://pypi.org/project/temporal-mcp-server/
- Docker - https://hub.docker.com/r/mcp/temporal

## Tools

### Workflow Execution

- **`start_workflow`** - Start a new Temporal workflow execution with specified parameters, workflow ID, and task queue
- **`get_workflow_result`** - Retrieve the result of a completed workflow execution
- **`describe_workflow`** - Get detailed information about a workflow execution including status, timing, and metadata
- **`list_workflows`** - List workflow executions based on a query filter with pagination support (limit/skip)
- **`get_workflow_history`** - Retrieve the complete event history of a workflow execution
- **`get_workflow_event`** - Retrieve a single workflow history event with decoded payload fields when present

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
- **`describe_schedule`** - Get detailed configuration and runtime information about a schedule, including its spec, action, state, recent executions, and upcoming action times
- **`pause_schedule`** - Pause a schedule to temporarily stop workflow executions
- **`unpause_schedule`** - Resume a paused schedule
- **`delete_schedule`** - Permanently delete a schedule
- **`trigger_schedule`** - Manually trigger a scheduled workflow immediately

### Codec Authentication

Only listed when `--codec-token-cache` is set (see [Remote codec](#remote-codec)).

- **`codec_auth_status`** - Show whether the codec server login is valid
- **`codec_login`** - Refresh the codec server token, or start a device login that returns a URL and code to open in a browser

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
        "-e", "TEMPORAL_TLS_CLIENT_CERT_PATH",
        "-e", "TEMPORAL_TLS_CLIENT_KEY_PATH",
        "-e", "TEMPORAL_API_KEY",
        "mcp/temporal"
      ],
      "env": {
        "TEMPORAL_HOST": "localhost:7233",
        "TEMPORAL_NAMESPACE": "default",
        "TEMPORAL_TLS_ENABLED": "false",
        "TEMPORAL_TLS_CLIENT_CERT_PATH": "/path/to/client.pem",
        "TEMPORAL_TLS_CLIENT_KEY_PATH": "/path/to/client.key",
        "TEMPORAL_API_KEY": "your-api-key"
      }
    }
  }
}
```

### Python via uvx (CLI arguments)

Recommended when running from PyPI via [`uvx`](https://docs.astral.sh/uv/guides/tools/). No local install required — `uvx` fetches and runs the package automatically. Configuration is passed as CLI arguments.

```json
{
  "servers": {
    "temporal": {
      "command": "uvx",
      "args": [
        "temporal-mcp-server",
        "--host", "localhost:7233",
        "--namespace", "default",
        "--tls-enabled", "false",
        "--tls-cert", "/path/to/client.pem",
        "--tls-key", "/path/to/client.key",
        "--api-key", "your-api-key"
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
| Allowed namespaces | — | `TEMPORAL_ALLOWED_NAMESPACES` | configured namespace only |
| TLS | `--tls-enabled` | `TEMPORAL_TLS_ENABLED` | auto-detect |
| mTLS cert path | `--tls-cert` | `TEMPORAL_TLS_CLIENT_CERT_PATH` | — |
| mTLS key path | `--tls-key` | `TEMPORAL_TLS_CLIENT_KEY_PATH` | — |
| API key | `--api-key` | `TEMPORAL_API_KEY` | — |
| Codec server URL | `--codec-endpoint` | `TEMPORAL_CODEC_ENDPOINT` | — |
| Codec `Authorization` header | `--codec-auth` | `TEMPORAL_CODEC_AUTH` | — |
| Codec token cache file | `--codec-token-cache` | `TEMPORAL_CODEC_TOKEN_CACHE` | — |
| Codec OAuth server URL | `--codec-oauth-url` | `TEMPORAL_CODEC_OAUTH_URL` | — |
| Codec OAuth client ID | `--codec-oauth-client-id` | `TEMPORAL_CODEC_OAUTH_CLIENT_ID` | — |
| Codec OAuth audience | `--codec-oauth-audience` | `TEMPORAL_CODEC_OAUTH_AUDIENCE` | — |

CLI arguments take precedence over environment variables. When `TEMPORAL_API_KEY` is set, TLS is enabled automatically. When mTLS cert/key paths are provided, TLS is also enabled automatically.

Every tool accepts an optional `namespace` argument. If omitted, the server uses `--namespace`, then `TEMPORAL_NAMESPACE`, then `default`. Runtime overrides are disabled by default: set `TEMPORAL_ALLOWED_NAMESPACES` to a comma-separated allowlist such as `default,payments`, or set it to `*` to permit any namespace reachable through the configured Temporal host and credentials. A finite allowlist must include the configured default namespace.

### Remote codec

When payloads or failure messages are encrypted by a [codec server](https://docs.temporal.io/production-deployment/data-encryption), set `--codec-endpoint` and the server decodes them through it: `get_workflow_event` shows decoded inputs, results and failure details, and `get_workflow_history` shows decoded failure messages and stack traces, including every cause in the chain. The codec is also used for outbound data: workflow inputs and other values the server sends to Temporal are encoded through the codec server's `/encode` endpoint. The codec server must therefore expose both `/encode` and `/decode`. Without a codec nothing is decoded and no requests are made to a codec server.

`get_workflow_history` decodes failure messages and stack traces only. Workflow inputs, results and failure details in the history remain encoded; use `get_workflow_event` to see decoded inputs and results for a single event.

Each request carries the namespace in an `X-Namespace` header, and requests for other allowed namespaces use their own. Only `http` and `https` endpoints are accepted, and redirects are never followed, so credentials are not forwarded to another host.

Authenticate to the codec server in one of two ways:

- **Static header:** `--codec-auth "Bearer <token>"`. You are responsible for renewing it.
- **OAuth with a token cache:** set `--codec-token-cache` together with `--codec-oauth-url`, `--codec-oauth-client-id` and `--codec-oauth-audience`, all required. The server refreshes the access token itself and persists it to the cache file, which takes precedence over `--codec-auth`. This enables the `codec_login` and `codec_auth_status` tools: call `codec_login` to refresh silently, or to start a device-code login that returns a URL and code and completes in the background once you approve it in a browser. When no valid token is available, decoding reports an error pointing to `codec_login`.

The OAuth server must be Auth0-compatible: it needs to serve `/oauth/device/code` and `/oauth/token`, accept an `audience` parameter, and issue refresh tokens for the `offline_access` scope. The token cache is a JSON file with `access_token`, `refresh_token`, `token_type` and `expires_at` (RFC 3339). Its directory must be writable, because the file is replaced atomically. Refresh tokens may rotate, so do not share one cache file between this server and another client.

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
