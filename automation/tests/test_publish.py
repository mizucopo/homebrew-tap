"""Exercise normal pushes, idempotence and real Git races using local repositories."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class TestPublish(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.remote = self.directory / "remote.git"
        self.work = self.directory / "work"
        self.other = self.directory / "other"
        self.git("init", "--bare", "--initial-branch=main", str(self.remote), cwd=self.directory)
        self.git("clone", str(self.remote), str(self.work), cwd=self.directory)
        (self.work / "automation/tests").mkdir(parents=True)
        (self.work / "Casks").mkdir()
        (self.work / ".github").mkdir()
        shutil.copy(ROOT / "automation/publish.sh", self.work / "automation/publish.sh")
        (self.work / ".github/config").write_text("trusted\n")
        (self.work / "automation/tests/test_fixture.py").write_text(
            'import unittest\nfrom pathlib import Path\n'
            'class FixtureCheck(unittest.TestCase):\n'
            '    def test_fixture_is_valid_python(self):\n'
            '        compile(Path("automation/update_casks.py").read_text(), "fixture", "exec")\n'
        )
        (self.work / "Casks/example.rb").write_text('version "0.7.0"\n')
        # The publisher is tested independently of HTTP/ZIP validation (covered separately).
        (self.work / "automation/update_casks.py").write_text('''
import os
from pathlib import Path
import subprocess

def load_apps(root):
    return [{"token": "example"}]

if __name__ == "__main__":
    Path("Casks/example.rb").write_text('version "0.8.0"\\n')
    other = os.environ.get("TEST_RACE_WORKTREE")
    marker = os.environ.get("TEST_RACE_MARKER")
    if other and not Path(marker).exists():
        Path(marker).touch()
        target = Path(other) / os.environ.get("TEST_RACE_PATH", "README.md")
        target.write_text("Concurrent maintainer change\\n")
        subprocess.run(["git", "add", "."], cwd=other, check=True)
        subprocess.run(["git", "-c", "user.name=test", "-c", "user.email=test@example.test",
                        "commit", "-m", "Concurrent change"], cwd=other, check=True)
        subprocess.run(["git", "push", "origin", "main"], cwd=other, check=True)
''')
        self.git("add", ".")
        self.git("-c", "user.name=test", "-c", "user.email=test@example.test", "commit", "-m", "Initial fixture")
        self.git("push", "origin", "main")
        self.git("clone", str(self.remote), str(self.other), cwd=self.directory)

    def git(self, *args, cwd=None):
        return subprocess.check_output(["git", *args], cwd=cwd or self.work,
                                       stderr=subprocess.STDOUT, text=True).strip()

    def publish(self, **env):
        return subprocess.run(["bash", "automation/publish.sh"], cwd=self.work,
                              env=dict(os.environ, GITHUB_ACTIONS="true",
                                       GITHUB_REPOSITORY="mizucopo/homebrew-tap",
                                       GITHUB_REF="refs/heads/main", **env),
                              capture_output=True, text=True, timeout=20)

    def test_publish_and_noop(self):
        first = self.publish()
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(self.git("show", "main:Casks/example.rb", cwd=self.remote), 'version "0.8.0"')
        head = self.git("rev-parse", "main", cwd=self.remote)
        second = self.publish()
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(self.git("rev-parse", "main", cwd=self.remote), head)

    def test_concurrent_commit_is_preserved(self):
        result = self.publish(TEST_RACE_WORKTREE=str(self.other),
                              TEST_RACE_MARKER=str(self.directory / "raced"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git("show", "main:README.md", cwd=self.remote), "Concurrent maintainer change")
        self.assertEqual(self.git("show", "main:Casks/example.rb", cwd=self.remote), 'version "0.8.0"')

    def test_concurrent_automation_change_stops(self):
        result = self.publish(TEST_RACE_WORKTREE=str(self.other), TEST_RACE_PATH=".github/config",
                              TEST_RACE_MARKER=str(self.directory / "raced"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Automation changed", result.stdout)
        self.assertEqual(self.git("show", "main:Casks/example.rb", cwd=self.remote), 'version "0.7.0"')

    def test_push_denial_stops_without_force(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Push failed without a concurrent main update", result.stdout)
        self.assertEqual(self.git("show", "main:Casks/example.rb", cwd=self.remote), 'version "0.7.0"')


if __name__ == "__main__":
    unittest.main()
