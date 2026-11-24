# Read-only mount protection

The namespace backend uses Bubblewrap to create a recursively read-only view
of the filesystem, with writable binds for the approved workspace and native
profile/cache paths. Trusted source and measurement paths cannot overlap these
writable roots. It provides a private device directory, hides host procfs behind
an empty read-only mount, drops capabilities and enables `no_new_privs`.

Before executing the client, the trusted entry installs an inherited seccomp
filter that denies `unshare`, `setns` and namespace flags on `clone`. `clone3`
returns `ENOSYS` so libc uses the checked `clone` interface. Ordinary processes
and threads remain available. The entry verifies actual namespace denial before
releasing the client. Hidden procfs prevents access through another process's
`/proc/PID/root` or `/proc/PID/fd`; procfs-based commands may be unavailable.

The pinned dynamically linked client needs `/proc/self/exe` during startup.
A small compatibility library answers libc `readlink`/`readlinkat` requests for
that executable path using kernel-provided `AT_EXECFN`. Other calls pass through.
Procfs remains hidden. This library is not the write guard: removing it cannot
remove the mount restrictions.

The signal broker stays outside the mount view, in the same PID namespace, and
authorizes exact descendant PID/start-time pairs. The namespace guard retains
the original signal/pidfd and ptrace restrictions while allowing additive
listenerless `prctl` filters. The direct `seccomp` syscall remains denied, so
the client cannot create a new notification listener. Additive filters cannot
relax the inherited restrictions. Hard memory limits propagate to descendants.

## Included checks

`check-host.sh --backend readonly-mounts` checks the actual container's mutation
denials, approved writes, hidden procfs, namespace/capability restrictions,
signal ownership and inherited limits. Native preflight repeats checks inside
the selected boundary before model loading. Runtime receipts bind the backend,
launcher and probe identities, and audits reject changed guard evidence.

The `tests/check_namespace_syscalls.py`, `tests/check_signal_filter_layers.py`
and `tests/check_native_protocol.py` utilities cover Linux syscall restrictions
and real native-client/tool integration. The protocol fixture uses fixed local
HTTP responses; it is not a model benchmark. These checks establish the tested
properties on the host where they run. Run the host check in each intended
compute environment before a benchmark run.
