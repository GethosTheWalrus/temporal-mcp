# Dependabot auto-merge

The auto-merge workflow waits for Tests, Lint & Type Check, Security, CodeQL,
OSV-Scanner, and Docker Scout to succeed on the current PR head, then squash
merges same-repository Dependabot PRs. It does not require branch protection,
so the release workflow can continue pushing version commits to `main`.
Keep the workflow triggers and the script's required workflow paths in sync
when changing CI. A newer pending or failed run blocks merging.

## Workflow-file updates

Create a fine-grained personal access token restricted to this repository with:

- Actions: read (to inspect CI runs)
- Contents: read and write (to merge)
- Pull requests: read and write
- Workflows: read and write (to merge GitHub Actions dependency updates)

Store it as the **Actions** repository secret `DEPENDABOT_MERGE_TOKEN` in
Settings → Secrets and variables → Actions. Do not commit the token.
The workflow runs from the default branch via `workflow_run`, so this is an
Actions secret, not a Dependabot secret. Renew it before it expires.

Without this secret, ordinary dependency PRs use `GITHUB_TOKEN`; workflow-file
updates remain open with a warning. Merges using `GITHUB_TOKEN` do not trigger
push workflows, including Release. The dedicated token enables those triggers.

After installing the workflow on `main` and adding the secret, use Actions →
Dependabot Auto-merge → Run workflow to process existing PRs. Subsequent CI
completions automatically retry open Dependabot PRs.

The privileged job only checks out the default-branch commit and reads GitHub
API metadata. It never executes code or downloads artifacts from a PR, and
merges with an expected head SHA to reject concurrent updates.
