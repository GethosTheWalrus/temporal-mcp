const test = require('node:test');
const assert = require('node:assert/strict');
const merge = require('./dependabot-auto-merge.cjs');

function fixture() {
  const fullName = 'owner/repo';
  const pull = {
    number: 83, user: { login: 'dependabot[bot]', type: 'Bot' },
    head: { sha: 'current-head', repo: { full_name: fullName } },
    base: { ref: 'main' }, state: 'open', draft: false,
  };
  const runs = ['test', 'lint', 'security', 'codeql', 'osv-scanner-scheduled', 'docker-scout']
    .map((name, id) => ({
      id, path: `.github/workflows/${name}.yml`,
      head_repository: { full_name: fullName }, status: 'completed', conclusion: 'success',
    }));
  const files = [{ filename: 'pyproject.toml' }];
  const merges = [];
  const warnings = [];
  const github = {
    rest: {
      pulls: {
        list: async () => [pull],
        get: async () => ({ data: pull }),
        listFiles: async () => files,
        merge: async (args) => {
          merges.push(args);
          return { data: { merged: true, sha: 'merged' } };
        },
      },
      actions: { listWorkflowRunsForRepo: async (args) => {
        assert.equal(args.head_sha, 'current-head');
        assert.equal(args.event, 'pull_request');
        return runs;
      } },
    },
    paginate: async (method, args) => method(args),
  };
  const options = {
    github, context: { repo: { owner: 'owner', repo: 'repo' } }, hasMergeToken: false,
    core: { info() {}, warning: (message) => warnings.push(message), setFailed: assert.fail },
  };
  return { pull, runs, files, merges, warnings, options };
}

test('merges a fully checked Dependabot head with SHA protection', async () => {
  const f = fixture();
  await merge(f.options);
  assert.equal(f.merges.length, 1);
  assert.equal(f.merges[0].sha, 'current-head');
  assert.equal(f.merges[0].merge_method, 'squash');
});

for (const conclusion of ['failure', 'cancelled', 'skipped', null]) {
  test(`blocks CI conclusion ${conclusion}`, async () => {
    const f = fixture();
    f.runs[0].conclusion = conclusion;
    await merge(f.options);
    assert.equal(f.merges.length, 0);
  });
}

test('blocks missing workflows and newer unfinished runs', async () => {
  for (const missing of [true, false]) {
    const f = fixture();
    if (missing) f.runs.pop();
    else f.runs.push({ ...f.runs[0], id: 100, status: 'in_progress' });
    await merge(f.options);
    assert.equal(f.merges.length, 0);
  }
});

test('ignores humans, forks, drafts, and closed PRs', async () => {
  for (const change of [
    (p) => { p.user.login = 'human'; },
    (p) => { p.head.repo.full_name = 'other/repo'; },
    (p) => { p.draft = true; },
    (p) => { p.state = 'closed'; },
  ]) {
    const f = fixture();
    change(f.pull);
    await merge(f.options);
    assert.equal(f.merges.length, 0);
  }
});

test('workflow updates need the dedicated token, including renamed files', async () => {
  for (const renamed of [true, false]) {
    for (const hasMergeToken of [true, false]) {
      const f = fixture();
      f.files[0][renamed ? 'previous_filename' : 'filename'] = '.github/workflows/test.yml';
      f.options.hasMergeToken = hasMergeToken;
      await merge(f.options);
      assert.equal(f.merges.length, hasMergeToken ? 1 : 0);
      assert.equal(f.warnings.length, hasMergeToken ? 0 : 1);
    }
  }
});
