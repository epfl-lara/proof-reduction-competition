# Container setup

The Dockerfile uses a pinned public NVIDIA CUDA 12.9.1 / Ubuntu 24.04 base.
It needs no EPFL registry credentials. Setup installs the pinned Python serving
and harness environments, Lean toolchains and public assets.

## Build

On a Linux x86-64 Docker host:

```bash
git clone --depth 1 https://github.com/epfl-lara/proof-reduction-competition.git
cd proof-reduction-competition
docker build --platform linux/amd64 -t epfl-lara-submission .
```

## CPU setup

Choose a writable shared filesystem with roughly 500 GB free. These examples
use `/shared`; replace it consistently if your cluster uses another path.

```bash
mkdir -p /shared/arena-home
docker run --rm -it --ipc=host \
  --user "$(id -u):$(id -g)" \
  --security-opt seccomp=unconfined --security-opt apparmor=unconfined \
  -e HOME=/shared/arena-home -v /shared:/shared \
  epfl-lara-submission bash
```

Inside the container, run the host check and setup commands in the
[README](../README.md#setup). The outer container policy must permit nested
user/mount namespaces and the guard's syscalls. A site-approved profile that
permits those operations can replace the two `unconfined` settings. The native
client's filesystem, signal and memory restrictions remain enabled. Run the
check on the actual compute node; a login-node check is insufficient.

## GPU search

Use the same image, shared mount and user identity in a four-GPU allocation.
Add `--gpus all` to the command above, then run:

```bash
bash run-namespace.sh /shared/arena-work /shared/arena-output
```

This requires an NVIDIA driver compatible with CUDA 12.9. Model loading precedes
the saved `MODEL_SEARCH_STARTED` boundary. Search uses all four GPUs on one node;
it has no multi-node MPI requirement.

CPU cleanup runs by default after the server stops. An inline run retains its
GPU reservation through cleanup. To release it earlier, use `--no-cleanup`, end
the GPU allocation, and run the README's separate cleanup command in a CPU
container with the same image and paths.

For Podman or a cluster container runtime, preserve the same user identity,
shared paths and namespace permissions. The host check determines whether that
runtime provides the required protections; see [host requirements](HOST_REQUIREMENTS.md).
