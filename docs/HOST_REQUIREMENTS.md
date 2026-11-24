# Host requirements

Use Linux x86-64 with the supplied Ubuntu 24.04 userland, Python 3.12 and
glibc 2.39 or newer. Model search uses four A100 80 GB GPUs on one node, with
an NVIDIA driver compatible with CUDA 12.9. Setup and separate CPU cleanup need
no GPUs. All phases need the same writable shared paths and public HTTPS access.

The full-benchmark model run requests 64 CPU cores and 512 GB RAM, without an
explicit container RAM limit. Short workflow checks also pass with a 256 GB cap;
they do not establish the full benchmark's peak memory. Separate cleanup uses
32 workers on a CPU allocation requesting 64 cores and 256 GB RAM.

## Read-only mounts (recommended entry points)

`setup-namespace.sh` and `run-namespace.sh` select this backend explicitly. It
requires nested user and mount namespaces, seccomp user notification and pidfd
operations. Container seccomp or AppArmor policies can block these operations
even when the host kernel supports them. See [container setup](IMAGE.md).

Inside the intended compute container:

```bash
bash check-host.sh --backend readonly-mounts --directory /shared/arena-guard-checks
```

This downloads nothing and makes no model or Lean calls. It creates owned test
files and checks write/truncate restrictions, approved workspace writes, hidden
procfs, namespace restrictions, signal confinement and inherited memory limits.
Exit 0 reports `readonly_mounts_protections_verified`; exit 2 means this runtime
cannot enforce the backend. Keep the resulting JSON and evidence directory.

Use the same host policy for setup and execution. Separate cleanup and finalize
commands also need `PROOF_EVAL_FILESYSTEM_BACKEND=readonly-mounts`. The wrappers
set it automatically for their phases. Do not change backend within a prepared
run: preparation binds the trusted launcher and guard identities.

## Landlock (alternative entry points)

The ordinary `setup.sh` and `run.sh` use Landlock by default. This requires actual
Landlock ABI 3 or newer: mainline Linux 6.2+ or an equivalent backport, with
Landlock built, enabled and allowed by the container syscall policy.

```bash
bash check-host.sh
bash setup.sh /shared/arena-work
bash run.sh /shared/arena-work /shared/arena-output
```

The ABI query is read-only. ABI 3 is required for the
[file-truncation restriction](https://docs.kernel.org/6.8/userspace-api/landlock.html#file-truncation-abi-3).
A failed query stops execution; it does not silently select another backend.
Changing the container image cannot add a missing host-kernel feature.

## Native client limits

Both backends restrict file writes and signals from native clients and their
tools. Each guarded process inherits a 4 GiB DATA limit, a 32 GiB address-space
limit and disabled core dumps. These are **per-process limits**; the trusted
host verifier and model server are outside them. They are not the job's total
RAM limit. See [namespace implementation](NAMESPACE_VALIDATION.md) for the
read-only mount boundary and its checks.
