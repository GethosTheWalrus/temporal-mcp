# CHANGELOG

<!-- version list -->

## v1.9.1 (2026-08-20)

### Bug Fixes

- Resolve container scan findings ([#66](https://github.com/GethosTheWalrus/temporal-mcp/pull/66),
  [`ca5c2f9`](https://github.com/GethosTheWalrus/temporal-mcp/commit/ca5c2f9c01adf1e10784ee8031121d397fec8b92))

### Chores

- **deps**: Bump actions/download-artifact from 4 to 8
  ([#61](https://github.com/GethosTheWalrus/temporal-mcp/pull/61),
  [`a958b04`](https://github.com/GethosTheWalrus/temporal-mcp/commit/a958b0491c5bd0b52de6b175dedec70a0cc1bb4d))

- **deps**: Bump actions/github-script from 8 to 9
  ([#60](https://github.com/GethosTheWalrus/temporal-mcp/pull/60),
  [`9d6b7b9`](https://github.com/GethosTheWalrus/temporal-mcp/commit/9d6b7b94b7d067208e3df605fa01232d9e040589))

- **deps**: Bump google/osv-scanner-action/.github/workflows/osv-scanner-reusable-pr.yml
  ([#64](https://github.com/GethosTheWalrus/temporal-mcp/pull/64),
  [`ec64dbf`](https://github.com/GethosTheWalrus/temporal-mcp/commit/ec64dbf85c53337c3cd0e1bb321b806d7f481074))

- **deps-dev**: Update filelock requirement from >=3.32.0 to >=3.32.2
  ([#59](https://github.com/GethosTheWalrus/temporal-mcp/pull/59),
  [`bb6c1a7`](https://github.com/GethosTheWalrus/temporal-mcp/commit/bb6c1a76f266fcf9bea8ed34a9f2300cbf7ae974))

- **deps-dev**: Update filelock requirement from >=3.32.2 to >=3.32.3
  ([#63](https://github.com/GethosTheWalrus/temporal-mcp/pull/63),
  [`c19f8e6`](https://github.com/GethosTheWalrus/temporal-mcp/commit/c19f8e6bcfcb33a96c21cae541585e76daf595fc))

- **deps-dev**: Update pre-commit requirement from >=4.6.1 to >=4.6.2
  ([#62](https://github.com/GethosTheWalrus/temporal-mcp/pull/62),
  [`9dc40ee`](https://github.com/GethosTheWalrus/temporal-mcp/commit/9dc40ee32dfd4ae58d1ad45b541d367c77fbb513))


## v1.9.0 (2026-07-29)

### Chores

- Rerun checks ([#54](https://github.com/GethosTheWalrus/temporal-mcp/pull/54),
  [`d3aebdf`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d3aebdfe14a465407878dabf8f3bec839f32b02c))

- Trigger updated security workflows
  ([#54](https://github.com/GethosTheWalrus/temporal-mcp/pull/54),
  [`d3aebdf`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d3aebdfe14a465407878dabf8f3bec839f32b02c))

### Continuous Integration

- Add consolidated security PR comment
  ([`4ea2bed`](https://github.com/GethosTheWalrus/temporal-mcp/commit/4ea2bedb99a361e1f8ebd63aed2941aef5cd73ce))

- Scan fork PR images with Docker Scout
  ([`7acdfef`](https://github.com/GethosTheWalrus/temporal-mcp/commit/7acdfeff631037b508452448d34c2db41e632b9d))

- Skip Docker Scout when PR secrets are unavailable
  ([`a76fd6a`](https://github.com/GethosTheWalrus/temporal-mcp/commit/a76fd6a307aaaee7a90358b4f976602882e0c007))

### Features

- Add optional run_id to get_workflow_history
  ([#54](https://github.com/GethosTheWalrus/temporal-mcp/pull/54),
  [`d3aebdf`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d3aebdfe14a465407878dabf8f3bec839f32b02c))


## v1.8.0 (2026-07-28)

### Bug Fixes

- Satisfy MCP 2 type checks
  ([`85cac11`](https://github.com/GethosTheWalrus/temporal-mcp/commit/85cac112eee043cecec4742cc7a57fc16c7d03ac))

- Use MCP content block types
  ([`1965fe1`](https://github.com/GethosTheWalrus/temporal-mcp/commit/1965fe11d6f3d0aefb95c145b82f724ec26003cb))

### Features

- Support MCP SDK 2.0
  ([`d051e43`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d051e43a4a40d974f14240996edd4e661b6cda44))


## v1.7.1 (2026-07-28)

### Bug Fixes

- Cap MCP SDK below 2.0
  ([`18f75fd`](https://github.com/GethosTheWalrus/temporal-mcp/commit/18f75fd035ef628f6f968ea64e666af3db1abf43))

### Chores

- **deps**: Bump actions/setup-python from 6 to 7
  ([#51](https://github.com/GethosTheWalrus/temporal-mcp/pull/51),
  [`ba305e9`](https://github.com/GethosTheWalrus/temporal-mcp/commit/ba305e921d84432d11009e854f1f8c7acb9dc131))

- **deps-dev**: Update filelock requirement from >=3.31.0 to >=3.32.0
  ([#53](https://github.com/GethosTheWalrus/temporal-mcp/pull/53),
  [`a2412bf`](https://github.com/GethosTheWalrus/temporal-mcp/commit/a2412bf4c566a06d5eeba48bdac85f7b43a313cd))

- **deps-dev**: Update pre-commit requirement from >=4.6.0 to >=4.6.1
  ([#52](https://github.com/GethosTheWalrus/temporal-mcp/pull/52),
  [`1b2d4c0`](https://github.com/GethosTheWalrus/temporal-mcp/commit/1b2d4c0a3eb2a13fb5d67381208402a53ff78ab5))


## v1.7.0 (2026-07-21)

### Continuous Integration

- Consolidate OSV scanning workflow
  ([`7523f01`](https://github.com/GethosTheWalrus/temporal-mcp/commit/7523f01d3da305ccd7f12d09f872645972b314ee))

### Features

- Expand schedule descriptions
  ([`d59d30c`](https://github.com/GethosTheWalrus/temporal-mcp/commit/d59d30cdfdec1b7a3b36714d4d0f139c8d9e7511))


## v1.6.0 (2026-07-21)

### Chores

- **deps**: Bump actions/checkout from 4 to 7
  ([#44](https://github.com/GethosTheWalrus/temporal-mcp/pull/44),
  [`f183bdb`](https://github.com/GethosTheWalrus/temporal-mcp/commit/f183bdb212c58ca023a46aad52ed3dd031726459))

- **deps-dev**: Update filelock requirement from >=3.20.3 to >=3.31.0
  ([#45](https://github.com/GethosTheWalrus/temporal-mcp/pull/45),
  [`b9f4e0e`](https://github.com/GethosTheWalrus/temporal-mcp/commit/b9f4e0ef5be911ba83fedb8b3d9438f98df98dfc))

- **deps-dev**: Update mypy requirement from >=2.2.0 to >=2.3.0
  ([#46](https://github.com/GethosTheWalrus/temporal-mcp/pull/46),
  [`103ee29`](https://github.com/GethosTheWalrus/temporal-mcp/commit/103ee29cc59c2da4161099fb8903f332ba3fbfc8))

### Features

- Enrich workflow history metadata
  ([`43d16c1`](https://github.com/GethosTheWalrus/temporal-mcp/commit/43d16c102fad9f96867a363ab3f6ea21a9015717))


## v1.5.0 (2026-07-18)

### Chores

- Raise vulnerable dependency floors
  ([`1cd7f6b`](https://github.com/GethosTheWalrus/temporal-mcp/commit/1cd7f6b89421e6a0fbcd77bc70d203b746110ab9))

- **deps-dev**: Update mypy requirement from >=2.1.0 to >=2.2.0
  ([#37](https://github.com/GethosTheWalrus/temporal-mcp/pull/37),
  [`90440a1`](https://github.com/GethosTheWalrus/temporal-mcp/commit/90440a181692f67f567558eeb8fc28dadea7bf41))

### Continuous Integration

- Add Docker Scout scanning
  ([`de391d4`](https://github.com/GethosTheWalrus/temporal-mcp/commit/de391d469253a26539631c698406244a6f30f067))

- Add security scanning workflows
  ([`cf579c3`](https://github.com/GethosTheWalrus/temporal-mcp/commit/cf579c3a0e0dee65c580b38870e5def6d468ee43))

- Fix OSV PR workflow syntax
  ([`895f0b4`](https://github.com/GethosTheWalrus/temporal-mcp/commit/895f0b4693aef239d296dc0b79a97507f9ab3302))

- Make OSV PR comparison advisory
  ([`fd536ab`](https://github.com/GethosTheWalrus/temporal-mcp/commit/fd536abb54da52f9699155daac636dd524021f1a))

- Report OSV PR findings without blocking
  ([`3a8834c`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3a8834c69a8b047eecc8c7f6507025b8eb2c1b8d))

- Require Docker Scout credentials
  ([`6d84126`](https://github.com/GethosTheWalrus/temporal-mcp/commit/6d841262f7e0585038255154dc1f53026a1756fa))

### Features

- Add workflow event payload tool
  ([`aef620f`](https://github.com/GethosTheWalrus/temporal-mcp/commit/aef620fce7d517c2523ce17251eefa226a7833b1))

### Testing

- Fix async mock warnings
  ([`b28e46a`](https://github.com/GethosTheWalrus/temporal-mcp/commit/b28e46ac6807274d0c5e6587fbf9a4b759909bc5))

- Fix async mock warnings
  ([`8e4cbf0`](https://github.com/GethosTheWalrus/temporal-mcp/commit/8e4cbf081b5629c6586cf4ca7e199b0e0925c780))


## v1.4.0 (2026-06-27)

### Chores

- **deps**: Bump actions/checkout from 6 to 7
  ([#33](https://github.com/GethosTheWalrus/temporal-mcp/pull/33),
  [`e13b806`](https://github.com/GethosTheWalrus/temporal-mcp/commit/e13b806dd3bc8626fb8b717393e93ca2f17f65f9))

- **deps-dev**: Update black requirement from >=26.5.0 to >=26.5.1
  ([#28](https://github.com/GethosTheWalrus/temporal-mcp/pull/28),
  [`0ac9ef3`](https://github.com/GethosTheWalrus/temporal-mcp/commit/0ac9ef3f57019f994ceb69810619fe093b19f5e6))

- **deps-dev**: Update pytest requirement from >=9.0.3 to >=9.1.0
  ([#32](https://github.com/GethosTheWalrus/temporal-mcp/pull/32),
  [`858efce`](https://github.com/GethosTheWalrus/temporal-mcp/commit/858efce07786c9b7558b441ff05270d6cfe58bfd))

- **deps-dev**: Update pytest requirement from >=9.1.0 to >=9.1.1
  ([#34](https://github.com/GethosTheWalrus/temporal-mcp/pull/34),
  [`bbe92eb`](https://github.com/GethosTheWalrus/temporal-mcp/commit/bbe92ebc4375aff5e5efff6ffd7b69db8956d92b))

- **deps-dev**: Update pytest-asyncio requirement
  ([#30](https://github.com/GethosTheWalrus/temporal-mcp/pull/30),
  [`223b20c`](https://github.com/GethosTheWalrus/temporal-mcp/commit/223b20c568a43a4e21089855ab3f2c7d01a043e0))

### Documentation

- Document describe_schedule tool in README
  ([`05fede3`](https://github.com/GethosTheWalrus/temporal-mcp/commit/05fede3621e2cf7ad80333951f56c293b8250154))

### Features

- Add describe_schedule tool
  ([`f15984a`](https://github.com/GethosTheWalrus/temporal-mcp/commit/f15984a10d04829c89648b9c8e10194a595936b8))


## v1.3.0 (2026-05-19)

### Bug Fixes

- Resolve mypy enum typing in activity status helper
  ([`3c8a955`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3c8a9558557eb8caa2298c041fecc3f91e5660f8))

### Continuous Integration

- Add Python 3.14 coverage to workflows
  ([`6e9cd0c`](https://github.com/GethosTheWalrus/temporal-mcp/commit/6e9cd0cb398b5158f682421cdae4297f31eb95f2))

### Features

- Add standalone activity tools and batch operations
  ([`5985722`](https://github.com/GethosTheWalrus/temporal-mcp/commit/5985722953fac0e687ffe7e39b1a144f7f51ecfd))


## v1.2.0 (2026-05-19)

### Chores

- **deps**: Bump actions/download-artifact from 4 to 8
  ([`4043d7f`](https://github.com/GethosTheWalrus/temporal-mcp/commit/4043d7f0cdb028e63ca8cded14d6990f943a3d57))

- **deps**: Bump actions/upload-artifact from 4 to 7
  ([#15](https://github.com/GethosTheWalrus/temporal-mcp/pull/15),
  [`5f382a0`](https://github.com/GethosTheWalrus/temporal-mcp/commit/5f382a0bd0c6ee6e252b95917f2e34ccd27153bf))

- **deps-dev**: Update black requirement from >=25.0.0 to >=26.3.1
  ([#21](https://github.com/GethosTheWalrus/temporal-mcp/pull/21),
  [`93ce21d`](https://github.com/GethosTheWalrus/temporal-mcp/commit/93ce21d37a64bbcccdc209fde979ca57bebe3ee0))

- **deps-dev**: Update black requirement from >=26.3.1 to >=26.5.0
  ([#25](https://github.com/GethosTheWalrus/temporal-mcp/pull/25),
  [`289b087`](https://github.com/GethosTheWalrus/temporal-mcp/commit/289b087cff37e0a537883633e26b7d49034b17d1))

- **deps-dev**: Update flake8 requirement from >=6.0.0 to >=7.3.0
  ([#17](https://github.com/GethosTheWalrus/temporal-mcp/pull/17),
  [`2f9b35e`](https://github.com/GethosTheWalrus/temporal-mcp/commit/2f9b35eb0a0f872840ced4e13520403ef005a455))

- **deps-dev**: Update mypy requirement from >=1.0.0 to >=1.20.2
  ([#20](https://github.com/GethosTheWalrus/temporal-mcp/pull/20),
  [`bb1d51e`](https://github.com/GethosTheWalrus/temporal-mcp/commit/bb1d51eb405a9a38b0ca158872879a64d4662f1f))

- **deps-dev**: Update mypy requirement from >=1.20.2 to >=2.0.0
  ([#23](https://github.com/GethosTheWalrus/temporal-mcp/pull/23),
  [`3628bc8`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3628bc8ef1d1b5935ab7a0a09de350073de034dd))

- **deps-dev**: Update mypy requirement from >=2.0.0 to >=2.1.0
  ([#24](https://github.com/GethosTheWalrus/temporal-mcp/pull/24),
  [`ed2539f`](https://github.com/GethosTheWalrus/temporal-mcp/commit/ed2539f3507842ca1706a5504ce560aef9dd639c))

- **deps-dev**: Update pre-commit requirement from >=4.0.0 to >=4.6.0
  ([#19](https://github.com/GethosTheWalrus/temporal-mcp/pull/19),
  [`5a54093`](https://github.com/GethosTheWalrus/temporal-mcp/commit/5a540939d4882f310dc154f1bf1197dc90b34bf6))

- **deps-dev**: Update pytest requirement from >=7.0.0 to >=9.0.3
  ([#22](https://github.com/GethosTheWalrus/temporal-mcp/pull/22),
  [`47cdee8`](https://github.com/GethosTheWalrus/temporal-mcp/commit/47cdee88b021885a64292d81d4a645ebc3c14a97))

- **deps-dev**: Update pytest-asyncio requirement
  ([#18](https://github.com/GethosTheWalrus/temporal-mcp/pull/18),
  [`886e14a`](https://github.com/GethosTheWalrus/temporal-mcp/commit/886e14a23423eaa5d9d0c38b9c89fa1652298409))

### Documentation

- Add distribution options to the README
  ([`e9e6736`](https://github.com/GethosTheWalrus/temporal-mcp/commit/e9e673635131f5deb9ee751e4a161b1a60928479))

- Fix indentation in README
  ([`dc107ff`](https://github.com/GethosTheWalrus/temporal-mcp/commit/dc107ffac6fb6a85aaa6676a2787373463959c5a))

### Features

- Harden Docker image with multi-stage Alpine build
  ([`e14debe`](https://github.com/GethosTheWalrus/temporal-mcp/commit/e14debe360f4f2842a7c0b9f2f682961bdb5ab68))


## v1.1.1 (2026-02-24)

### Bug Fixes

- Remove redundant publish.yml now that release.yml handles PyPI publish directly
  ([`1a022f1`](https://github.com/GethosTheWalrus/temporal-mcp/commit/1a022f1250628712762fcb5026aa7e487d04fa57))

### Continuous Integration

- Add pypi environment to publish job for OIDC trusted publisher
  ([`400c733`](https://github.com/GethosTheWalrus/temporal-mcp/commit/400c73320638ed5e5ad42820324fb2d5f871a169))

- Publish to PyPI directly from release workflow to avoid GITHUB_TOKEN trigger limitation
  ([`3e39132`](https://github.com/GethosTheWalrus/temporal-mcp/commit/3e39132f7b4150087073f0206efcbf71d0126ba9))

### Documentation

- Update Python MCP config example to use uvx
  ([`21bab91`](https://github.com/GethosTheWalrus/temporal-mcp/commit/21bab9108fb6515d328484410ae8f78d7411f9d0))


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
