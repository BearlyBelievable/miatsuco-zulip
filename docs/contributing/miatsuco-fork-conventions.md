# MiAtSu.Co fork conventions

This is MiAtSu.Co's fork of Zulip. We track upstream release tags and rebase
our features on top of each new release instead of merging. Read this page
before contributing, on top of [Contributing to Zulip](contributing.md). It
only covers what differs in this fork. Zulip's standards for commit format,
PR structure, code style, and review apply as-is.

Every rebase replays our commits on top of upstream's latest code. That stays
low-friction only if our additions stay out of upstream's way. Reusing a field
name, migration number, or CSS class that upstream also uses turns a
mechanical rebase into a debugging session, so the conventions below exist to
prevent those collisions.

## Contributing a feature

1. Get the latest upstream state and branch off it.

   ```bash
   git fetch origin && git checkout -b my-feature origin/main
   ```

2. Build the feature on that branch. Keep it to one feature per branch so it
   can be reviewed and rebased independently, and follow the naming,
   upstream-file, and migration conventions below.
3. Add tests, then run the backend suite, the frontend suite, and the linters
   locally.
4. Push the branch and open a PR against `main`. CI must be green.

## Fork naming conventions

Two kinds of names matter in this fork, the names in code and the names we
use to talk about features. They follow different rules, so this describes
those rules, and the [fork feature index](miatsuco-feature-index.md) connects
them together.

### Naming features and improvements

Pick one name for each feature or improvement, the way you would describe it
to someone who has never seen the code. Use that name for the help section and
in the fork feature index, so a search for it finds everything the change
touches.

### Naming things in code

Once you've picked a name for the feature or improvement, you'll need to be
mindful that the code itself will often need to keep names consistent with
upstream choices. However, this depends on where the code actually lives and
what it does.

New files that the fork owns should use the `miatsuco_` prefix, for example
`miatsuco_collapsed_media.ts` or `zerver/tests/test_miatsuco_dm_restrict.py`.
Classes, functions, and variables inside these fork-owned files can be named
whatever reads best, since the prefix already marks them as ours.

When you add something to a model, setting, or dict that upstream owns, such
as a `Realm` field or a `property_types` key, prefix the name with
`miatsuco_` and follow the existing naming patterns. Upstream could add a name
that collides with yours later, so the prefix keeps the two apart. Leave names
alone when the fork only reads or extends something from upstream, as those
names belong to upstream.

## Maintaining upstream files

We try to keep fork content out of files upstream might also edit. Where
practical, fork-specific docs and tests get dedicated files instead of being
added to a file upstream maintains.

- **User-facing docs:** Fork-specific behavior is documented in the upstream help article it
  belongs to, in a self-contained section under a dedicated heading, so the
  help center matches what the fork does. Leave the upstream text around the
  section alone, which keeps rebases onto new upstream releases easy. A feature's
  rationale and full behavior belong there once, and the code can leave them
  out.
- **Contributor-facing docs:** Pages like this one live in
  `docs/contributing/`, alongside Zulip's pages, and are linked from the
  toctree in `docs/contributing/index.md`.
- **API documentation:** A genuinely new endpoint is tagged
  `intentionally_undocumented` in `zproject/urls.py`, and its OpenAPI content
  is drafted in
  [`miatsuco-upstream-api-drafts.md`](miatsuco-upstream-api-drafts.md)
  instead of `zerver/openapi/zulip.yaml`. That lasts until the endpoint has
  been through upstream's [API change process](../processes/api-design.md)
  and `tools/merge-api-changelogs` assigns a real `API_FEATURE_LEVEL`. A new
  field on an already-documented endpoint is documented normally, using
  `**Changes**: New in Miatsuco X.Y-dev.` in place of a real feature level.
- **Tests:** Each fork feature gets a dedicated module,
  `zerver/tests/test_miatsuco_<feature>.py` for the backend and
  `web/tests/miatsuco_<feature>.test.cjs` for the frontend, since a shared
  test file would conflict across feature branches. The test runners collect
  these automatically, so a new module needs no registration step. Shared
  helpers live in `MiatsucoMarkdownTestMixin` in
  `zerver/lib/test_miatsuco.py`, following upstream's convention of keeping
  test base classes out of the test modules the backend runner discovers.

This isn't a hard rule. A bug fix to existing upstream behavior has to edit
the file that behavior lives in, and that's fine. The goal is to remove
unnecessary shared-file surface area, and editing zero upstream files isn't
required.

When fork code does land inline in an upstream file, the
[fork feature index](miatsuco-feature-index.md) connects each feature to its
code names, so a search for those names finds the edit. Comments there follow
upstream's style and cover behavior that contradicts what a reader would
expect.

## Migrations

Fork migrations live in `zerver/migrations/`, named
`miatsuco_NNNN_description.py`. A fork feature that needs a wholly new table
can use a separate Django app instead, which never touches `zerver`'s
migration graph at all. We prefer that when it's an option.

For a field added to an existing upstream model, the migration's `zerver`
dependency has to be re-pointed at the current tip on every rebase onto a new
upstream tag. Django builds its migration graph from what's on disk, so a
`miatsuco_*` migration that still depends on a stale `zerver` migration
leaves the graph with multiple heads once upstream ships new migrations. Run
`./manage.py check_miatsuco_migrations` as part of the rebase checklist, and
again whenever you touch a migration. CI runs the same check through
`tools/test-migrations`.

## Signaling fork features

Upstream owns and increments `zulip_feature_level`, so the fork can't reuse
it to signal fork-specific features to a client without risking a future
collision. Instead, `zerver/lib/miatsuco.py` defines `MIATSUCO_VERSION` (a
fork-owned release number) and `MIATSUCO_FEATURE_LEVEL` (an integer that
works like upstream's). Both are advertised in `POST /register` and
`GET /server_settings` as `miatsuco_version` and `miatsuco_feature_level`.

Raise `MIATSUCO_FEATURE_LEVEL` by one in each PR that changes the fork's API,
such as a new realm setting, field, event, or endpoint. Mark what the PR added
with a **Changes** note reading `New in Miatsuco 1.0 (feature level N)`, and add
a row to the feature level table in the [fork feature
index](miatsuco-feature-index.md). A client that needs a specific change
compares `miatsuco_feature_level` with the level in that note.

## Passing CI

Most of what CI enforces is upstream Zulip's tooling, which is already
documented well elsewhere. Read those pages and run the same commands,
particularly [Linters](../testing/linters.md) (`./tools/lint -m`, `--fix`,
`--verbose`), [Testing with Django](../testing/testing-with-django.md) (the
100% line-coverage requirement, `test-backend --coverage`, `# nocoverage`),
and [Continuous integration](../testing/continuous-integration.md).

CI runs the linters with `--skip=gitlint`, so pass the same flag locally to
match. Write commit messages following [commit
discipline](commit-discipline.md).

One check applies only to this fork. `zerver/lib/test_miatsuco.py` is a
helper mixin that stays uncovered until a feature's tests exercise it, so it
needs `# nocoverage` as the exact first line of the file. You drop the line
once every helper is covered through a real caller.

`./tools/setup-git-repo` installs a fork `pre-push` hook that runs frontend
lint, backend lint, and node tests with coverage, and blocks the push if any
fail. The backend suite is opt-in with `RUN_BACKEND=1 git push`, since it
needs a provisioned database. The hook also reminds you to browser-test when
a push touches rendering or media paths.

## Pull requests

In addition to Zulip's [review guide](review-process.md), follow this
checklist.

1. Confirm your branch applies cleanly by itself against the current base
   release tag.
2. If your change should be independent of other in-flight fork features,
   verify it applies correctly in either order relative to them, with an
   identical resulting tree. If it has a genuine, intentional dependency,
   confirm it fails clearly and immediately without that dependency present.
3. Run the test suite after rebasing. A clean rebase only means the text
   merged, so it doesn't show that the feature still behaves correctly.

## Releases

Releases are numbered by `MIATSUCO_VERSION`, independent of
`ZULIP_VERSION`. Until the first release, `main` carries `1.0.0-dev`, meaning
work toward 1.0.0. That release will detail the features this fork adds on top
of upstream Zulip. The `-dev` suffix stays until a release is cut, and after
each release `main` moves to the next version with a `-dev` suffix.

A release is a known-good snapshot, meaning a tag where `main` sat at a
specific upstream base plus a specific feature set, with CI green and the
result deployed and verified. Cut one when a meaningful change has landed and
been confirmed working, and skip the merges in between.

`MAJOR.MINOR.PATCH` carries fork-specific meaning.

- **Major:** A stable-substrate milestone, or a break to the fork-specific
  API.
- **Minor:** A release that adds fork features.
- **Patch:** A release with only fixes to existing features.

## Upstreaming a fork feature

Some fork features are improvements Zulip itself should have. These follow a
separate process once they're ready to send upstream.

1. Once a feature is proven stable and worth sending upstream, build a
   second, independent implementation that targets current upstream `main`
   directly. It branches from a real upstream commit (since our `main` always
   carries fork-only commits), uses no `miatsuco_` prefix, follows upstream
   conventions throughout, and stays rebased on upstream's tip while the PR
   is open. Our fork keeps running the custom version regardless of that PR's
   status.
2. Once the PR is accepted, we reconcile during the periodic rebase onto a new
   upstream stable release. At that point we drop the custom implementation
   and adopt the version that arrives with the release.

## Questions

If something here is unclear, or you've hit a case this page doesn't cover,
that's a documentation bug. Please raise it instead of guessing, as this page
is expected to evolve. If a convention here turns out to be wrong, we want to
fix the convention and this page together, in the same commit.
