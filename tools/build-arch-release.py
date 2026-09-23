#!/usr/bin/env python3
"""Create reproducible local Arch release inputs for Boreal."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import tomllib


SOURCE_DIRS = (".github", "boreal", "docs", "integration", "packaging", "po", "tests", "tools")
SOURCE_FILES = (
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "README.en.md",
    "README.md",
    "SECURITY.md",
    "install-local.py",
    "pyproject.toml",
    "setup-kraken-access.sh",
)
IGNORED_PARTS = {"__pycache__", ".pytest_cache", ".mypy_cache", "build", "dist"}
IGNORED_SUFFIXES = (".pyc", ".pyo", "~")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def included_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for name in SOURCE_FILES:
        candidate = source / name
        if not candidate.is_file():
            raise SystemExit(f"Missing release file: {candidate}")
        files.append(candidate)
    for name in SOURCE_DIRS:
        directory = source / name
        if not directory.is_dir():
            raise SystemExit(f"Missing release directory: {directory}")
        for candidate in directory.rglob("*"):
            relative = candidate.relative_to(source)
            if candidate.is_file() and not (set(relative.parts) & IGNORED_PARTS):
                if not candidate.name.endswith(IGNORED_SUFFIXES):
                    files.append(candidate)
    return sorted(set(files), key=lambda item: item.relative_to(source).as_posix())


def create_source_archive(source: Path, target: Path, version: str) -> None:
    prefix = Path(f"boreal-cooling-{version}")
    with target.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as archive:
                directories: set[Path] = {Path(".")}
                files = included_files(source)
                for candidate in files:
                    relative = candidate.relative_to(source)
                    directories.update(relative.parents)
                for relative in sorted(directories, key=lambda item: (len(item.parts), item.as_posix())):
                    if relative == Path("."):
                        continue
                    info = tarfile.TarInfo((prefix / relative).as_posix())
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = 0
                    archive.addfile(info)
                for candidate in files:
                    relative = candidate.relative_to(source)
                    payload = candidate.read_bytes()
                    info = tarfile.TarInfo((prefix / relative).as_posix())
                    info.size = len(payload)
                    info.mode = 0o755 if candidate.stat().st_mode & 0o111 else 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = "root"
                    info.mtime = 0
                    archive.addfile(info, io.BytesIO(payload))


def write_checksums(output: Path) -> None:
    candidates = sorted(
        path
        for path in output.iterdir()
        if path.is_file()
        and path.name != "SHA256SUMS"
        and (
            path.name in {"PKGBUILD", "boreal-cooling.install"}
            or path.name.endswith((".tar.gz", ".pkg.tar.zst"))
        )
    )
    lines = [f"{sha256(path)}  {path.name}" for path in candidates]
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    source = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((source / "pyproject.toml").read_text(encoding="utf-8"))
    version = metadata["project"]["version"]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)

    archive = output / f"boreal-cooling-{version}.tar.gz"
    create_source_archive(source, archive, version)
    archive_hash = sha256(archive)

    template = (source / "packaging/arch/PKGBUILD.in").read_text(encoding="utf-8")
    if template.count("@VERSION@") != 1 or template.count("@SHA256@") != 1:
        raise SystemExit("PKGBUILD template placeholders are invalid")
    pkgbuild = template.replace("@VERSION@", version).replace("@SHA256@", archive_hash)
    (output / "PKGBUILD").write_text(pkgbuild, encoding="utf-8")
    shutil.copyfile(source / "packaging/arch/boreal-cooling.install", output / "boreal-cooling.install")
    write_checksums(output)

    print(archive)
    print(output / "PKGBUILD")
    print(output / "SHA256SUMS")


if __name__ == "__main__":
    main()
