# CHANGELOG

<!-- version list -->

## v1.1.0 (2026-02-24)

### Continuous Integration

- Auto-merge dependabot PRs once checks pass
  ([`1bfdc32`](https://github.com/GethosTheWalrus/temporal-mcp/commit/1bfdc32016702d5a7f48652063fdd9e987671688))

### Documentation

- Add per-client examples for TEMPORAL_API_KEY and mTLS env vars
  ([`d83631d`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d83631d530706a7353e9c29afde35cf563350b3a))

- Consolidate VS Code MCP config examples for env vars and CLI args
  ([`34463d2`](https://github.com/GethosTheWalrus/temporal-mcp/commit/34463d23f1946c4e7b16a7932b989907414b341e))

- Show all config options in VS Code MCP config examples
  ([`3a0c796`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3a0c796d76fc643f96be0380c3d78235e8abcd11))

### Features

- Add CLI argument support for server configuration
  ([`3295a1e`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3295a1eed7970b30e81122f4defb0421e85de12c))

### Testing

- Add tests for CLI arg parsing, env var fallback, and arg precedence
  ([`bfe9d91`](https://github.com/GethosTheWalrus/temporal-mcp/commit/bfe9d91198deff55c0e27f17c1b894175a5ba444))


## v1.0.1 (2026-02-22)

### Bug Fixes

- Pass --repo to gh label create to avoid git context requirement
  ([`28ec118`](https://github.com/GethosTheWalrus/temporal-mcp/commit/28ec1186e25b6d8002848f6fa792bb0328987e90))

### Continuous Integration

- Add label setup workflow and fix dependabot label config
  ([`d7a8e49`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d7a8e49b796cd13247b955f6b7020cf05c46cbc3))

- Only run label sync on manual dispatch
  ([`ef0694b`](https://github.com/GethosTheWalrus/temporal-mcp/commit/ef0694baa53afb767879346db8e82996fba0e84e))

- Trigger label sync on every push to main
  ([`130e464`](https://github.com/GethosTheWalrus/temporal-mcp/commit/130e4647b82fc0382645c5ecdafd527392a7a8a1))


## v1.0.0 (2026-02-22)

- Initial Release
