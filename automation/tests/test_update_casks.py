import copy
import hashlib
import io
import json
from pathlib import Path
import plistlib
import re
import stat
import struct
import tempfile
import unittest
from unittest.mock import patch
import urllib.request
import zipfile

from automation.update_casks import (
    GitHub, SafeRedirect, cask_state, load_apps, reconcile, release_asset,
    validate_zip, version_key,
)

ROOT = Path(__file__).resolve().parents[2]
APP = load_apps(ROOT)[0]


def make_zip(version="0.8.0", cpu=0x0100000C, app=None, extra=None, info_changes=None):
    app = app or APP
    info = {
        "CFBundleIdentifier": app["bundle_id"], "CFBundleShortVersionString": version,
        "CFBundlePackageType": "APPL", "CFBundleExecutable": "mizu-pairrank",
    }
    info.update(info_changes or {})
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(app["app"] + "/Contents/Info.plist", plistlib.dumps(info))
        executable = zipfile.ZipInfo(app["app"] + "/Contents/MacOS/mizu-pairrank")
        executable.external_attr = (stat.S_IFREG | 0o755) << 16
        archive.writestr(executable, struct.pack("<IIIIIIII", 0xFEEDFACF, cpu, 0, 2, 0, 0, 0, 0))
        if extra:
            archive.writestr(*extra)
    return output.getvalue()


def make_release(data, version="0.8.0", app=None):
    app = app or APP
    tag = app["tag_prefix"] + version
    base = "https://github.com/" + app["repository"] + "/releases"
    name = app["asset"].format(version=version)
    return {
        "id": 123, "tag_name": tag, "draft": False, "prerelease": False,
        "published_at": "2026-10-01T12:00:00Z", "html_url": base + "/tag/" + tag,
        "assets": [{"id": 456, "name": name, "state": "uploaded", "size": len(data),
                    "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
                    "browser_download_url": base + "/download/" + tag + "/" + name}],
    }


class FakeGitHub:
    def __init__(self, data, release, fresh=None):
        self.data, self.release, self.fresh = data, release, fresh
        self.reads = self.downloads = 0

    def get(self, repository, endpoint):
        self.reads += 1
        return self.fresh if self.fresh is not None and self.reads > 1 else self.release

    def download(self, asset, path):
        self.downloads += 1
        path.write_bytes(self.data)
        return hashlib.sha256(self.data).hexdigest()


class TestUpdater(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "automation").mkdir()
        (self.root / "automation/apps.json").write_text(json.dumps({"apps": [APP]}))
        (self.root / "Casks").mkdir()
        self.cask = self.root / "Casks" / (APP["token"] + ".rb")
        self.original = (ROOT / "Casks" / (APP["token"] + ".rb")).read_text()
        # Keep fixtures stable after the real registered version advances.
        self.original = re.sub(r'^  version "[^"]+"$', '  version "0.7.0"', self.original, flags=re.M)
        self.original = re.sub(r'^  sha256 "[^"]+"$', '  sha256 "' + "0" * 64 + '"', self.original, flags=re.M)
        self.cask.write_text(self.original)

    def validate(self, data, version="0.8.0"):
        path = self.root / "asset.zip"
        path.write_bytes(data)
        validate_zip(path, APP, version)

    def test_numeric_version_order(self):
        self.assertGreater(version_key("0.10.0"), version_key("0.9.0"))
        for value in ("0.8.0-rc.1", "v0.8.0", "01.2.3", "1.2.3+build", "1.2.3\n", '1.2.3";system("x")'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                version_key(value)

    def test_manifest_allowlist(self):
        for key, value in (("repository", "someone-else/app"), ("token", "../../other"),
                           ("asset", "https://evil.test/{version}"), ("app", "../other.app")):
            app = dict(APP, **{key: value})
            (self.root / "automation/apps.json").write_text(json.dumps({"apps": [app]}))
            with self.subTest(key=key), self.assertRaises(ValueError):
                load_apps(self.root)

    def test_duplicate_manifest(self):
        (self.root / "automation/apps.json").write_text(json.dumps({"apps": [APP, APP]}))
        with self.assertRaises(ValueError):
            load_apps(self.root)

    def test_cask_contract_is_checked(self):
        self.cask.write_text(self.original.replace("depends_on arch: :arm64", "depends_on arch: :intel"))
        with self.assertRaises(ValueError):
            cask_state(self.root, APP)

    def test_valid_zip(self):
        self.validate(make_zip())

    def test_wrong_architecture(self):
        with self.assertRaises(ValueError):
            self.validate(make_zip(cpu=0x01000007))

    def test_wrong_bundle_or_version(self):
        for changes in ({"CFBundleIdentifier": "invalid.app"}, {"CFBundleShortVersionString": "0.9.0"},
                        {"CFBundleExecutable": "../bad"}, {"CFBundlePackageType": "FMWK"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.validate(make_zip(info_changes=changes))

    def test_unsafe_paths(self):
        for name in ("../outside", "/absolute", "other.app/Contents/file", "mizu-pairrank.app/../outside",
                     "mizu-pairrank.app/./file", "mizu-pairrank.app\\outside", "mizu-pairrank.app/Contents//file"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.validate(make_zip(extra=(name, b"data")))

    def test_symbolic_link_rejected(self):
        link = zipfile.ZipInfo(APP["app"] + "/Contents/link")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with self.assertRaises(ValueError):
            self.validate(make_zip(extra=(link, b"../../outside")))

    def test_duplicate_zip_entry_rejected(self):
        with self.assertWarns(UserWarning):
            data = make_zip(extra=(APP["app"] + "/Contents/Info.plist", b"second"))
        with self.assertRaises(ValueError):
            self.validate(data)

    def test_macos_case_collision_rejected(self):
        with self.assertRaisesRegex(ValueError, "collide"):
            self.validate(make_zip(extra=(APP["app"] + "/Contents/info.plist", b"different")))

    def test_missing_app(self):
        path = self.root / "asset.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("__MACOSX/._data", b"data")
        with self.assertRaises(KeyError):
            validate_zip(path, APP, "0.8.0")

    def test_uncompressed_limit(self):
        with patch("automation.update_casks.MAX_UNPACKED", 1), self.assertRaises(ValueError):
            self.validate(make_zip())

    def test_stable_published_release_required(self):
        release = make_release(make_zip())
        for field, value in (("draft", True), ("prerelease", True), ("published_at", None),
                             ("tag_name", "0.8.0-rc.1"), ("html_url", "https://evil.test/tag/0.8.0")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                release_asset(APP, dict(release, **{field: value}))

    def test_exact_asset_required(self):
        original = make_release(make_zip())
        for field, value in (("state", "new"), ("size", 0), ("digest", None),
                             ("digest", "sha256:not-a-hash"), ("browser_download_url", "https://evil.test/app.zip")):
            release = copy.deepcopy(original)
            release["assets"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                release_asset(APP, release)
        for assets in ([], original["assets"] * 2):
            with self.assertRaises(ValueError):
                release_asset(APP, dict(original, assets=assets))

    def test_only_two_lines_change(self):
        data = make_zip()
        self.assertEqual(reconcile(self.root, FakeGitHub(data, make_release(data))), 1)
        after = self.cask.read_text().splitlines()
        before = self.original.splitlines()
        self.assertEqual([i for i, pair in enumerate(zip(before, after)) if pair[0] != pair[1]], [1, 2])
        self.assertIn('  version "0.8.0"', after)
        self.assertIn(f'  sha256 "{hashlib.sha256(data).hexdigest()}"', after)

    def test_check_does_not_write(self):
        data = make_zip()
        self.assertEqual(reconcile(self.root, FakeGitHub(data, make_release(data)), check=True), 1)
        self.assertEqual(self.cask.read_text(), self.original)

    def test_repeat_is_noop(self):
        data = make_zip()
        release = make_release(data)
        reconcile(self.root, FakeGitHub(data, release))
        once = self.cask.read_text()
        self.assertEqual(reconcile(self.root, FakeGitHub(data, release)), 0)
        self.assertEqual(self.cask.read_text(), once)

    def test_no_downgrade(self):
        data = make_zip("0.6.0")
        github = FakeGitHub(data, make_release(data, "0.6.0"))
        self.assertEqual(reconcile(self.root, github), 0)
        self.assertEqual(github.downloads, 0)
        self.assertEqual(self.cask.read_text(), self.original)

    def test_same_version_replacement_rejected(self):
        data = make_zip("0.7.0")
        with self.assertRaisesRegex(ValueError, "existing version"):
            reconcile(self.root, FakeGitHub(data, make_release(data, "0.7.0")))
        self.assertEqual(self.cask.read_text(), self.original)

    def test_release_changed_during_download(self):
        data = make_zip()
        first = make_release(data)
        second = copy.deepcopy(first)
        second["assets"][0]["id"] += 1
        with self.assertRaisesRegex(ValueError, "changed during"):
            reconcile(self.root, FakeGitHub(data, first, second))
        self.assertEqual(self.cask.read_text(), self.original)

    def test_redirect_restrictions(self):
        handler = SafeRedirect()
        req = urllib.request.Request("https://github.com/mizucopo/mizu-pairrank/releases/download/0.8.0/app.zip")
        for url in ("http://github.com/file", "https://evil.test/file", "https://github.com:8443/file",
                    "https://user:password@github.com/file", "file:///tmp/file"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(req, None, 302, "Found", {}, url)
        redirected = handler.redirect_request(req, None, 302, "Found", {},
                                             "https://release-assets.githubusercontent.com/file")
        self.assertEqual(redirected.full_url, "https://release-assets.githubusercontent.com/file")

    def test_download_byte_digest_and_size(self):
        data = make_zip()
        asset = make_release(data)["assets"][0]
        client = GitHub()
        with patch.object(client.asset_opener, "open", return_value=io.BytesIO(data)):
            self.assertEqual(client.download(asset, self.root / "a.zip"), hashlib.sha256(data).hexdigest())
        for bad in (dict(asset, size=len(data) - 1), dict(asset, size=len(data) + 1),
                    dict(asset, digest="sha256:" + "0" * 64)):
            with patch.object(client.asset_opener, "open", return_value=io.BytesIO(data)), self.assertRaises(ValueError):
                client.download(bad, self.root / "b.zip")


if __name__ == "__main__":
    unittest.main()
