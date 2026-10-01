// Keep this list aligned with the PR CI workflows and workflow_run triggers.
const requiredWorkflows = [
  '.github/workflows/test.yml',
  '.github/workflows/lint.yml',
  '.github/workflows/security.yml',
  '.github/workflows/codeql.yml',
  '.github/workflows/osv-scanner-scheduled.yml',
  '.github/workflows/docker-scout.yml',
];

module.exports = async ({ github, context, core, hasMergeToken }) => {
  const { owner, repo } = context.repo;
  const pulls = await github.paginate(github.rest.pulls.list, {
    owner, repo, state: 'open', base: 'main', per_page: 100,
  });

  for (const candidate of pulls) {
    const { data: pull } = await github.rest.pulls.get({
      owner, repo, pull_number: candidate.number,
    });
    if (pull.user.login !== 'dependabot[bot]' || pull.user.type !== 'Bot' ||
        pull.head.repo?.full_name !== `${owner}/${repo}` ||
        pull.base.ref !== 'main' || pull.state !== 'open' || pull.draft) continue;

    // Query the current head, not the possibly stale workflow_run event SHA.
    const runs = await github.paginate(github.rest.actions.listWorkflowRunsForRepo, {
      owner, repo, event: 'pull_request', head_sha: pull.head.sha, per_page: 100,
    });
    const pending = requiredWorkflows.filter((path) => {
      const latest = runs.filter((run) => run.path === path &&
        run.head_repository?.full_name === `${owner}/${repo}`)
        .sort((a, b) => b.id - a.id)[0];
      return !latest || latest.status !== 'completed' || latest.conclusion !== 'success';
    });
    if (pending.length) {
      core.info(`#${pull.number}: waiting for successful CI: ${pending.join(', ')}`);
      continue;
    }

    const files = await github.paginate(github.rest.pulls.listFiles, {
      owner, repo, pull_number: pull.number, per_page: 100,
    });
    if (!hasMergeToken && files.some((file) =>
      [file.filename, file.previous_filename].some((name) => name?.startsWith('.github/workflows/')))) {
      core.warning(`#${pull.number}: add the DEPENDABOT_MERGE_TOKEN Actions secret with Workflows write permission to merge workflow updates.`);
      continue;
    }

    // GitHub rejects the merge if Dependabot has pushed a new, untested head.
    const { data: result } = await github.rest.pulls.merge({
      owner, repo, pull_number: pull.number, sha: pull.head.sha, merge_method: 'squash',
    });
    if (!result.merged) {
      core.setFailed(`#${pull.number}: ${result.message}`);
      continue;
    }
    core.info(`Merged #${pull.number}: ${result.sha}`);
  }
};
