#!/usr/bin/env bash
# Only run in the disposable GitHub Actions checkout, never a developer worktree.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == true && "${GITHUB_REPOSITORY:-}" == mizucopo/homebrew-tap ]]
[[ "${GITHUB_REF:-}" == refs/heads/main ]]

baseline="$(git rev-parse HEAD)"
for attempt in 1 2 3 4 5; do
  git fetch --no-tags origin main
  remote="$(git rev-parse origin/main)"
  # A concurrent code/configuration change needs a new workflow run and review.
  if ! git diff --quiet "$baseline" "$remote" -- automation .github; then
    echo '::error::Automation changed during this run. Rerun on the new main commit.'
    exit 1
  fi
  git reset --hard "$remote"
  python3 -m unittest discover -s automation/tests -v
  python3 automation/update_casks.py
  git diff --check
  python3 - <<'PY'
import subprocess
from pathlib import Path
from automation.update_casks import load_apps

allowed = {"Casks/" + app["token"] + ".rb" for app in load_apps(Path.cwd())}
changed = set(subprocess.check_output(["git", "diff", "--name-only"], text=True).splitlines())
if not changed <= allowed:
    raise SystemExit("Refusing to publish changes outside registered casks")
for path in sorted(changed):
    subprocess.run(["git", "add", "--", path], check=True)
PY
  if git diff --cached --quiet; then
    echo 'All registered casks are current.'
    exit 0
  fi
  git -c user.name='github-actions[bot]' \
      -c user.email='41898282+github-actions[bot]@users.noreply.github.com' \
      commit -m 'chore: update verified release casks'
  if git push origin HEAD:refs/heads/main; then
    exit 0
  fi
  git fetch --no-tags origin main
  if [[ "$(git rev-parse origin/main)" == "$remote" ]]; then
    echo '::error::Push failed without a concurrent main update. Check permissions/rules; do not bypass them.'
    exit 1
  fi
  sleep "$attempt"
done
echo '::error::Main kept changing. Rerun the updater; no force push was attempted.'
exit 1
