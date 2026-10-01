#!/usr/bin/env python3
"""Reconcile allowlisted public releases without extracting or executing assets."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import plistlib
import re
import stat
import struct
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile

OWNER = "mizucopo"
MAX_DOWNLOAD = 128 * 1024 * 1024
MAX_UNPACKED = 512 * 1024 * 1024
STABLE = r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)"
SHA = r"[0-9a-f]{64}"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def version_key(value):
    require(isinstance(value, str) and re.fullmatch(STABLE, value),
            "Only numeric, stable major.minor.patch versions are supported")
    return tuple(map(int, value.split(".")))


def load_apps(root):
    data = json.loads((root / "automation/apps.json").read_text())
    require(set(data) == {"apps"} and isinstance(data["apps"], list)
            and 0 < len(data["apps"]) <= 100, "Invalid app manifest")
    tokens, repositories = set(), set()
    for app in data["apps"]:
        require(set(app) == {"token", "repository", "tag_prefix", "asset", "app", "bundle_id"},
                "Unexpected manifest fields")
        require(all(isinstance(v, str) for v in app.values()), "Manifest values must be strings")
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", app["token"]), "Invalid cask token")
        require(re.fullmatch(OWNER + r"/[a-z0-9][a-z0-9._-]*", app["repository"]),
                "Source repository is outside the owner allowlist")
        require(app["token"] not in tokens and app["repository"] not in repositories,
                "Duplicate app registration")
        tokens.add(app["token"])
        repositories.add(app["repository"])
        require(app["tag_prefix"] in ("", "v"), "Unsupported tag prefix")
        require(re.fullmatch(r"[a-zA-Z0-9._-]+-\{version\}-macos-arm64\.zip", app["asset"]),
                "Only versioned macOS ARM64 ZIP assets are supported")
        require(re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*\.app", app["app"]), "Invalid app name")
        require(re.fullmatch(r"[a-zA-Z0-9]+(?:[.-][a-zA-Z0-9]+)+", app["bundle_id"]),
                "Invalid bundle identifier")
    return data["apps"]


def cask_state(root, app):
    path = root / "Casks" / (app["token"] + ".rb")
    require(not path.is_symlink(), "Cask must not be a symbolic link")
    text = path.read_text()
    versions = re.findall(r'^  version "(' + STABLE + r')"$', text, re.M)
    hashes = re.findall(r'^  sha256 "(' + SHA + r')"$', text, re.M)
    require(len(versions) == len(hashes) == 1, "Cask needs one literal version and SHA-256")
    url = ("https://github.com/" + app["repository"] + "/releases/download/"
           + app["tag_prefix"] + "#{version}/" + app["asset"].replace("{version}", "#{version}"))
    for expected in (f'cask "{app["token"]}" do', f'  url "{url}"',
                     f'  app "{app["app"]}"', '  depends_on arch: :arm64', '  depends_on :macos'):
        require(text.splitlines().count(expected) == 1, "Cask no longer matches its registered contract")
    return path, text, versions[0], hashes[0]


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        require(parsed.scheme == "https" and parsed.port in (None, 443)
                and parsed.username is None and parsed.password is None
                and parsed.hostname in {"github.com", "release-assets.githubusercontent.com",
                                        "objects.githubusercontent.com"},
                "Unexpected asset redirect destination")
        # Downloads are always anonymous; never forward an API credential.
        require("Authorization" not in req.headers, "Credentials cannot follow redirects")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("GitHub API redirects are not accepted")


class GitHub:
    def __init__(self):
        self.api_opener = urllib.request.build_opener(NoRedirect())
        self.asset_opener = urllib.request.build_opener(SafeRedirect())

    def get(self, repository, endpoint):
        url = f"https://api.github.com/repos/{repository}/{endpoint}"
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
                   "User-Agent": "mizucopo-homebrew-updater"}
        token = os.environ.get("GH_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        for attempt in range(3):
            try:
                with self.api_opener.open(urllib.request.Request(url, headers=headers), timeout=30) as response:
                    data = response.read(2 * 1024 * 1024 + 1)
                require(len(data) <= 2 * 1024 * 1024, "Oversized API response")
                return json.loads(data)
            except urllib.error.HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 2:
                    raise
            except (urllib.error.URLError, TimeoutError):
                if attempt == 2:
                    raise
            time.sleep(2 ** attempt)

    def download(self, asset, destination):
        request = urllib.request.Request(asset["browser_download_url"],
                                         headers={"User-Agent": "mizucopo-homebrew-updater"})
        digest, size = hashlib.sha256(), 0
        with self.asset_opener.open(request, timeout=60) as response, destination.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                require(size <= MAX_DOWNLOAD and size <= asset["size"], "Oversized asset download")
                output.write(chunk)
                digest.update(chunk)
        require(size == asset["size"], "Asset download size mismatch")
        require("sha256:" + digest.hexdigest() == asset["digest"], "Asset digest mismatch")
        return digest.hexdigest()


def release_asset(app, release):
    require(isinstance(release, dict) and release.get("draft") is False
            and release.get("prerelease") is False and bool(release.get("published_at")),
            "Release must be published and stable")
    tag = release.get("tag_name", "")
    require(isinstance(tag, str) and tag.startswith(app["tag_prefix"]), "Unexpected release tag")
    version = tag[len(app["tag_prefix"]):]
    version_key(version)
    require(type(release.get("id")) is int and release["id"] > 0, "Invalid release ID")
    base = f'https://github.com/{app["repository"]}/releases'
    require(release.get("html_url") == base + "/tag/" + tag, "Unexpected release URL")
    name = app["asset"].format(version=version)
    assets = [asset for asset in release.get("assets", []) if asset.get("name") == name]
    require(len(assets) == 1, "Expected exactly one registered release asset")
    asset = assets[0]
    require(type(asset.get("id")) is int and asset["id"] > 0
            and asset.get("state") == "uploaded"
            and type(asset.get("size")) is int and 0 < asset["size"] <= MAX_DOWNLOAD,
            "Release asset is incomplete or oversized")
    require(asset.get("browser_download_url") == base + "/download/" + tag + "/" + name,
            "Asset URL does not match the allowlisted repository, version and filename")
    require(isinstance(asset.get("digest"), str) and re.fullmatch("sha256:" + SHA, asset["digest"]),
            "GitHub must supply a SHA-256 asset digest")
    return version, asset


def validate_zip(path, app, version):
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        require(0 < len(entries) <= 10000 and sum(i.file_size for i in entries) <= MAX_UNPACKED,
                "ZIP exceeds the entry or uncompressed-size limit")
        names = [entry.filename for entry in entries]
        require(len(names) == len(set(names)), "Duplicate ZIP entries")
        mac_names = [unicodedata.normalize("NFD", name.rstrip("/")).casefold() for name in names]
        require(len(mac_names) == len(set(mac_names)), "ZIP paths collide on a macOS filesystem")
        for entry in entries:
            name = entry.filename
            parts = PurePosixPath(name).parts
            require(name and not name.startswith("/") and "\\" not in name and "\x00" not in name
                    and ".." not in parts and "." not in name.split("/")
                    and parts[0] in (app["app"], "__MACOSX"), "Unexpected or unsafe ZIP path")
            require(entry.orig_filename == name
                    and name.rstrip("/") == PurePosixPath(name).as_posix(), "Non-canonical ZIP path")
            mode = entry.external_attr >> 16
            require(stat.S_IFMT(mode) in (0, stat.S_IFREG, stat.S_IFDIR),
                    "ZIP links and special files are not accepted")
            require(not entry.flag_bits & 1, "Encrypted ZIP entries are not accepted")
        info_name = app["app"] + "/Contents/Info.plist"
        info_entry = archive.getinfo(info_name)
        require(info_entry.file_size <= 1024 * 1024, "Oversized Info.plist")
        info = plistlib.loads(archive.read(info_entry))
        require(info.get("CFBundleIdentifier") == app["bundle_id"]
                and info.get("CFBundleShortVersionString") == version
                and info.get("CFBundlePackageType") == "APPL", "App identity or version mismatch")
        binary = info.get("CFBundleExecutable", "")
        require(isinstance(binary, str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", binary),
                "Invalid executable name")
        executable = archive.getinfo(app["app"] + "/Contents/MacOS/" + binary)
        require(executable.file_size >= 32 and bool((executable.external_attr >> 16) & 0o111),
                "Expected an executable Mach-O file")
        with archive.open(executable) as stream:
            header = stream.read(32)
        magic, cpu, _, filetype = struct.unpack("<IIII", header[:16])
        require(magic == 0xFEEDFACF and cpu == 0x0100000C and filetype == 2,
                "Expected a thin ARM64 Mach-O executable")
        require(archive.testzip() is None, "ZIP integrity check failed")


def fingerprint(release, asset):
    return (release["id"], release["tag_name"], asset["id"], asset["size"],
            asset["digest"], asset["browser_download_url"])


def reconcile(root, github, check=False):
    changes = []
    for app in load_apps(root):
        path, text, current, current_sha = cask_state(root, app)
        release = github.get(app["repository"], "releases/latest")
        version, asset = release_asset(app, release)
        if version_key(version) < version_key(current):
            print(f'{app["token"]}: keep newer registered version {current}')
            continue
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "asset.zip"
            digest = github.download(asset, archive)
            validate_zip(archive, app, version)
        # Refuse an asset replacement or latest-release change during validation.
        fresh = github.get(app["repository"], "releases/latest")
        _, fresh_asset = release_asset(app, fresh)
        require(fingerprint(fresh, fresh_asset) == fingerprint(release, asset),
                "Release changed during verification; rerun the updater")
        if version == current:
            require(digest == current_sha, "An existing version's asset changed; manual review required")
            print(f'{app["token"]}: {current} already verified')
            continue
        updated = text.replace(f'  version "{current}"\n', f'  version "{version}"\n', 1)
        updated = updated.replace(f'  sha256 "{current_sha}"\n', f'  sha256 "{digest}"\n', 1)
        require(updated != text, "Cask update produced no change")
        changes.append((path, updated))
        print(f'{app["token"]}: {current} -> {version}')
    # Validate every app before writing any file, so failures are fail-closed.
    if not check:
        for path, content in changes:
            path.write_text(content)
    return len(changes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify releases without writing casks")
    args = parser.parse_args()
    try:
        reconcile(Path(__file__).resolve().parent.parent, GitHub(), args.check)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, plistlib.InvalidFileException) as error:
        raise SystemExit(f"Cask update stopped: {error}") from error
