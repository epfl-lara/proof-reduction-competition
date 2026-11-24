"""Entry points keep imports and prepared paths coherent across directory aliases."""

import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT if (ROOT / "setup.sh").is_file() else ROOT / "submission"
ENTRIES = [
    name
    for name in ("setup", "run", "search", "cleanup")
    if (SCRIPTS / f"{name}.sh").is_file()
]


@pytest.mark.parametrize("entry", ENTRIES)
@pytest.mark.parametrize("bundle_alias", [False, True])
def test_entry_points_resolve_shared_directory_aliases(tmp_path, entry, bundle_alias):
    work = tmp_path / "physical work"
    work.mkdir()
    alias = tmp_path / "shared work alias"
    alias.symlink_to(work, target_is_directory=True)
    bundle = tmp_path / "physical bundle" if bundle_alias else work / "bundle"
    package = bundle / "src/proof_eval/interfaces"
    package.mkdir(parents=True)
    (package.parent / "__init__.py").write_text("")
    (package / "__init__.py").write_text("")
    (package / "submission.py").write_text(
        "import json, os, sys\nfrom pathlib import Path\n"
        "root = Path(__file__).resolve().parents[3]\n"
        "Path(__file__).relative_to(root)\n"
        "Path(os.environ['ENTRYPOINT_CAPTURE']).write_text(json.dumps("
        "{'argv': sys.argv[1:], 'pythonpath': os.environ['PYTHONPATH']}))\n"
    )
    if bundle_alias:
        (work / "bundle").symlink_to(bundle, target_is_directory=True)
    shutil.copyfile(SCRIPTS / "toolchain-env.sh", bundle / "toolchain-env.sh")
    (work / "elan").mkdir()
    (work / "elan-home.txt").write_text(str(work / "elan") + "\n")
    for env in ("harness", "serving"):
        binaries = work / "envs" / env / "bin"
        binaries.mkdir(parents=True)
        python = binaries / "python"
        python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
        python.chmod(0o755)
    vllm = work / "envs/serving/bin/vllm"
    vllm.write_text("#!/bin/sh\nexit 0\n")
    vllm.chmod(0o755)
    commands = tmp_path / "provided commands"
    commands.mkdir()
    for name in ("git", "lake", "lean", "elan", "taskset", "rg"):
        command = commands / name
        command.write_text("#!/bin/sh\nexit 0\n")
        command.chmod(0o755)
    source = tmp_path / "source" if SCRIPTS == ROOT else bundle
    source.mkdir(exist_ok=True)
    shutil.copyfile(SCRIPTS / f"{entry}.sh", source / f"{entry}.sh")
    shutil.copyfile(SCRIPTS / "toolchain-env.sh", source / "toolchain-env.sh")
    source_alias = tmp_path / "source alias"
    source_alias.symlink_to(source, target_is_directory=True)
    capture = tmp_path / "captured.json"
    args = ["/bin/bash", str(source_alias / f"{entry}.sh"), str(alias)]
    if entry != "setup":
        args.append(str(tmp_path / "output"))
    result = subprocess.run(
        args,
        cwd=tmp_path,
        env={
            **os.environ,
            "ELAN_HOME": str(work / "elan"),
            "PATH": str(commands) + os.pathsep + os.environ["PATH"],
            "PYTHONPATH": "",
            "ENTRYPOINT_CAPTURE": str(capture),
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(capture.read_text())
    argv = observed["argv"]
    assert argv[0] == entry
    assert argv[argv.index("--work") + 1] == str(work)
    assert argv[argv.index("--bundle") + 1] == str(bundle)
    assert observed["pythonpath"] == str(bundle / "src")
