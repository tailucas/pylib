---
paths:
  - "pyproject.toml"
  - "uv.lock"
  - "Makefile"
  - "README.md"
---

# Dependency Upgrade Standard (tailucas-pylib)

`uv.lock` is the single source of truth for resolved versions and `uv` is the
only tool that writes it. Downstream apps depend on this package with `>=`
bounds, so a dependency upgrade must leave the lockfile, the build backend, the
declared bounds and the package version mutually consistent.

## One-Prompt Procedure

When asked to "upgrade dependencies", run this end to end and report the
result; do not stop at the first command.

```sh
# 1. Re-resolve every package: core deps, all extras, all groups
uv lock --upgrade

# 2. Install what the new resolution defines
uv sync --all-extras --all-groups

# 3. Assert lockfile <-> pyproject and env <-> lockfile consistency
uv lock --check
uv sync --check --all-extras --all-groups

# 4. Assert the package still builds with the pinned build backend
uv build
```

`make update` runs steps 1-4. Steps 5-7 are then required to close the change:

```sh
# 5. Review what actually moved, per package, against the committed lock
git show HEAD:uv.lock > /tmp/uv.lock.head   # diff name/version pairs, not the whl lists

# 6. Close any gap the lock cannot cross (see Guardrails below), bump the
#    patch version in pyproject.toml, then re-run 1-4

# 7. Validation gate - both suites must pass, not just the core one
uv run ruff check src/
uv run ruff format --check src/
uv run mypy src/tailucas_pylib/
uv run --group test pytest
uv run --group test --extra aws --extra creds --extra monitoring --extra mq pytest
```

`make test-all` (the Hatch extras matrix) is optional for a dependency-only
change: it re-runs the live 1Password tests 32 times and is rate-limited, so an
occasional `RateLimitExceeded` there is transient rather than a regression.

## Command Reference

The resolution step is where the options matter. All forms still require
steps 2-4 afterwards.

| Goal | Command |
| --- | --- |
| Upgrade everything | `uv lock --upgrade` |
| Upgrade one package | `uv lock --upgrade-package boto3` |
| Upgrade one dependency group (`lint`, `test`, `dev`) | `uv lock --upgrade-group test` |
| Preview without writing | `uv lock --upgrade --dry-run` |
| Ignore cached index data | `uv lock --upgrade --refresh` (or `--no-cache`) |
| Allow pre-releases | `uv lock --upgrade --prerelease allow` (`UV_PRERELEASE=allow`) |
| Prefer oldest resolvable versions (lower-bound audit only, `--dry-run`; oldest releases fail to build on 3.14) | `uv lock --upgrade --resolution lowest-direct --dry-run` |
| Freeze to a release date | `uv lock --upgrade --exclude-newer 2026-10-01` |
| Upgrade the uv CLI itself | `uv self update` |

Group and extra names come from `[dependency-groups]` and
`[project.optional-dependencies]`: groups are `lint`, `test`, `dev`; extras are
`aws`, `creds`, `monitoring`, `mq`. `uv` fails on an unknown name, so never
copy a stale extra name (for example `dto`) into a command or a rule file.

## Guardrails

1. **Bounds cap the upgrade.** `uv lock --upgrade` cannot cross a bound in
   `[project]` / `[project.optional-dependencies]`. Widen the floor in the same
   change (for example `boto3>=1.43.123`) when a newer release is excluded,
   otherwise that dependency silently stops moving. Do not add upper bounds
   without a reason, and never pin an exact version.
2. **The build backend is not locked.** `uv_build` in `[build-system]` is
   resolved only at build time and never appears in `uv.lock`, so it must be
   bumped by hand to the current uv release line and re-verified with
   `uv build` *and* the publish path:
   `uvx --from build pyproject-build --outdir dist .` (the release workflow
   builds with `python -m build`, i.e. pip + build isolation).
   Verify backend bumps in a throwaway copy first, and compare the built
   wheel's file list and `METADATA` against the previous backend.
3. **Never hand-edit `uv.lock`, and never bypass uv.** No
   `pip install --upgrade`, no `uv pip install --upgrade` inside the project
   environment; those desynchronise the lockfile from the venv.
4. **Bump the package version.** Dependency-only changes get a patch bump
   (`0.8.4` -> `0.8.5`); a breaking dependency change needs a minor bump plus a
   note, because downstream apps use `>=` bounds.
5. **Report the deltas.** Summarise `<package>: <old> -> <new>` for the direct
   dependencies, plus any package that appeared or disappeared transitively,
   and state explicitly whether anything was already current.
6. **Conservative posture.** One upgrade per change; keep unrelated refactors
   out. If the upgrade surfaces a pre-existing defect (missing optional-dep
   guard, stale extra name in a command), report it separately instead of
   silently folding the fix into a dependency bump.

## Common Failures

- `uv lock --check` fails after editing `pyproject.toml` by hand: re-run
  `uv lock` (bounds changed, resolution must move with it).
- `uv build` fails right after a backend bump: the pinned `uv_build` requires
  a newer uv CLI (`uv self update`) or a wheel is missing for the platform.
- A newer version exists on PyPI but the lock will not take it: the bound in
  `pyproject.toml` is the cause, not the cache.
- `uv lock --upgrade --resolution lowest-direct` fails building `coverage==3.0`
  (or another ancient release): the `lint`, `test` and `dev` groups are
  intentionally unpinned, so lowest-resolution selects pre-2020 versions. Keep
  it a `--dry-run` lower-bound audit, never an upgrade path.
