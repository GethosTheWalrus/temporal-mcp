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
  const dispatches = [];
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
      }, createWorkflowDispatch: async (args) => {
        assert.ok(merges.length > 0, 'Release must follow a successful merge');
        dispatches.push(args);
      } },
    },
    paginate: async (method, args) => method(args),
  };
  const options = {
    github, context: { repo: { owner: 'owner', repo: 'repo' } },
    core: { info() {}, warning: (message) => warnings.push(message), setFailed: assert.fail },
  };
  return { pull, runs, files, merges, warnings, dispatches, options };
}

test('merges a fully checked Dependabot head with SHA protection', async () => {
  const f = fixture();
  await merge(f.options);
  assert.equal(f.merges.length, 1);
  assert.equal(f.merges[0].sha, 'current-head');
  assert.equal(f.merges[0].merge_method, 'squash');
  assert.deepEqual(f.dispatches, [{
    owner: 'owner', repo: 'repo', workflow_id: 'release.yml', ref: 'main',
  }]);
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

test('workflow updates require manual merging, including renamed files', async () => {
  for (const renamed of [true, false]) {
    const f = fixture();
    f.files[0][renamed ? 'previous_filename' : 'filename'] = '.github/workflows/test.yml';
    await merge(f.options);
    assert.equal(f.merges.length, 0);
    assert.equal(f.dispatches.length, 0);
    assert.equal(f.warnings.length, 1);
  }
});

test('does not dispatch Release when merging is refused or throws', async () => {
  for (const throws of [true, false]) {
    const f = fixture();
    const failures = [];
    f.options.core.setFailed = (message) => failures.push(message);
    f.options.github.rest.pulls.merge = async () => {
      if (throws) throw new Error('Head changed');
      return { data: { merged: false, message: 'Merge refused' } };
    };
    if (throws) await assert.rejects(merge(f.options), /Head changed/);
    else {
      await merge(f.options);
      assert.deepEqual(failures, ['#83: Merge refused']);
    }
    assert.equal(f.dispatches.length, 0);
  }
});

test('reports manual recovery when Release dispatch fails after a merge', async () => {
  const f = fixture();
  const failures = [];
  f.options.core.setFailed = (message) => failures.push(message);
  f.options.github.rest.actions.createWorkflowDispatch = async () => {
    throw new Error('API unavailable');
  };
  await merge(f.options);
  assert.equal(f.merges.length, 1);
  assert.equal(failures.length, 1);
  assert.match(failures[0], /Run the Release workflow manually on main/);
});
