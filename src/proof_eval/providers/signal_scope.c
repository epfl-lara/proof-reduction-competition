/* Model-free prototype. Not installed in a production runtime.
 * Linux x86-64 only: inherited seccomp notifications constrain signal targets.
 * The broker uses pidfds rather than continuing a checked numeric kill PID.
 * This is a signal boundary, not a general-purpose security sandbox.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <linux/audit.h>
#include <linux/filter.h>
#include <linux/seccomp.h>
#include <pthread.h>
#include <signal.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/prctl.h>
#include <sys/socket.h>
#include <sys/syscall.h>
#include <sys/wait.h>
#include <unistd.h>

#if !defined(__x86_64__)
#error "This prototype has only an x86-64 syscall/architecture gate"
#endif

static int proc_info(pid_t pid, pid_t *parent, pid_t *group) {
    char path[64], buf[4096], state;
    snprintf(path, sizeof(path), "/proc/%d/stat", pid);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    char *line = fgets(buf, sizeof(buf), f);
    fclose(f);
    if (!line) return -1;
    char *end = strrchr(buf, ')');
    return end && sscanf(end + 1, " %c %d %d", &state, parent, group) == 3 ? 0 : -1;
}

static pid_t thread_group(pid_t tid) {
    char path[64], line[256];
    snprintf(path, sizeof(path), "/proc/%d/status", tid);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    pid_t result = -1;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "Tgid: %d", &result) == 1) break;
    }
    fclose(f);
    return result;
}

/* Only the listener thread writes this bounded trace for one notification. */
static pid_t delivered_targets[4096];
static int delivered_count;

static int owned(pid_t pid, pid_t root) {
    pid_t broker = getpid();
    if (pid == broker) return 0;  /* The trusted broker is never a signal target. */
    for (int depth = 0; depth < 4096 && pid > 1; depth++) {
        if (pid == root || pid == broker) return 1;
        pid_t parent, group;
        if (proc_info(pid, &parent, &group) || parent == pid) return 0;
        pid = parent;
    }
    return 0;
}

static int pinned_signal(pid_t target, int sig, pid_t root) {
    int fd = (int)syscall(SYS_pidfd_open, target, 0);
    if (fd < 0) return errno;
    int error = EPERM;
    if (owned(target, root)) {
        error = syscall(SYS_pidfd_send_signal, fd, sig, NULL, 0) ? errno : 0;
    }
    close(fd);
    return error;
}

static int group_signal(pid_t group, int sig, pid_t root) {
    if (group <= 0) return EPERM;
    DIR *directory = opendir("/proc");
    if (!directory) return errno;
    int fds[4096], count = 0, error = 0;
    pid_t targets[4096];
    struct dirent *entry;
    while ((entry = readdir(directory))) {
        char *end;
        long value = strtol(entry->d_name, &end, 10);
        if (!value || *end || value > INT32_MAX) continue;
        pid_t parent, pgid;
        if (proc_info((pid_t)value, &parent, &pgid) || pgid != group) continue;
        int fd = (int)syscall(SYS_pidfd_open, (pid_t)value, 0);
        if (fd < 0 && errno == ESRCH) continue;
        if (fd < 0) { error = errno; break; }
        if (!owned((pid_t)value, root) || count == 4096) {
            close(fd);
            error = EPERM;
            break;
        }
        targets[count] = (pid_t)value;
        fds[count++] = fd;
    }
    closedir(directory);
    /* No kernel group kill: every delivered target has its own pinned pidfd.
     * Newly forked members can be missed; no unverified member is signalled.
     */
    if (!error) {
        int sent = 0;
        for (int i = 0; i < count; i++) {
            if (!syscall(SYS_pidfd_send_signal, fds[i], sig, NULL, 0)) {
                sent++;
                delivered_targets[delivered_count++] = targets[i];
            }
            else if (errno != ESRCH) { error = errno; break; }
        }
        if (!error && !sent) error = ESRCH;
    }
    for (int i = 0; i < count; i++) close(fds[i]);
    return error;
}

static pid_t pidfd_target(pid_t caller, int fd) {
    char path[96], line[256];
    snprintf(path, sizeof(path), "/proc/%d/fdinfo/%d", caller, fd);
    FILE *f = fopen(path, "r");
    if (!f) return -1;
    pid_t target = -1;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "Pid: %d", &target) == 1) break;
    }
    fclose(f);
    return target;
}

#define NOTIFY(number) \
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (number), 0, 1), \
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_USER_NOTIF)
#define DENY(number) \
    BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, (number), 0, 1), \
    BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM)

static int install_filter(void) {
    struct sock_filter filter[] = {
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, arch)),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, AUDIT_ARCH_X86_64, 1, 0),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | ENOSYS),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, nr)),
        BPF_JUMP(BPF_JMP | BPF_JGE | BPF_K, 0x40000000, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | ENOSYS),
        NOTIFY(SYS_kill), NOTIFY(SYS_tkill), NOTIFY(SYS_tgkill),
        NOTIFY(SYS_rt_sigqueueinfo), NOTIFY(SYS_rt_tgsigqueueinfo),
        NOTIFY(SYS_pidfd_send_signal),
        DENY(SYS_ptrace), DENY(SYS_process_vm_writev), DENY(SYS_pidfd_getfd),
        /* An untrusted later USER_NOTIF filter must not supersede this one. */
        DENY(SYS_seccomp),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, SYS_prctl, 0, 3),
        BPF_STMT(BPF_LD | BPF_W | BPF_ABS, offsetof(struct seccomp_data, args[0])),
        BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, PR_SET_SECCOMP, 0, 1),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ERRNO | EPERM),
        BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW)
    };
    struct sock_fprog program = { .len = sizeof(filter) / sizeof(filter[0]), .filter = filter };
    if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)) return -1;
    return (int)syscall(SYS_seccomp, SECCOMP_SET_MODE_FILTER,
                        SECCOMP_FILTER_FLAG_NEW_LISTENER |
                        SECCOMP_FILTER_FLAG_WAIT_KILLABLE_RECV, &program);
}

static int transfer_fd(int socket, int fd) {
    char value = 'F', control[CMSG_SPACE(sizeof(int))];
    struct iovec io = { .iov_base = &value, .iov_len = 1 };
    struct msghdr message = { .msg_iov = &io, .msg_iovlen = 1,
        .msg_control = control, .msg_controllen = sizeof(control) };
    memset(control, 0, sizeof(control));
    struct cmsghdr *header = CMSG_FIRSTHDR(&message);
    header->cmsg_level = SOL_SOCKET; header->cmsg_type = SCM_RIGHTS;
    header->cmsg_len = CMSG_LEN(sizeof(int));
    memcpy(CMSG_DATA(header), &fd, sizeof(fd));
    return sendmsg(socket, &message, 0) == 1 ? 0 : -1;
}

static int receive_fd(int socket) {
    char value, control[CMSG_SPACE(sizeof(int))];
    struct iovec io = { .iov_base = &value, .iov_len = 1 };
    struct msghdr message = { .msg_iov = &io, .msg_iovlen = 1,
        .msg_control = control, .msg_controllen = sizeof(control) };
    if (recvmsg(socket, &message, MSG_CMSG_CLOEXEC) != 1 || value != 'F') return -1;
    struct cmsghdr *header = CMSG_FIRSTHDR(&message);
    if (!header || header->cmsg_level != SOL_SOCKET || header->cmsg_type != SCM_RIGHTS ||
        header->cmsg_len != CMSG_LEN(sizeof(int))) return -1;
    int fd; memcpy(&fd, CMSG_DATA(header), sizeof(fd)); return fd;
}

static void decide(struct seccomp_notif *request, struct seccomp_notif_resp *response, pid_t root) {
    delivered_count = 0;
    int number = request->data.nr;
    int32_t first = (int32_t)request->data.args[0];
    int error = EPERM;
    pid_t caller_group = thread_group((pid_t)request->pid);
    if (caller_group <= 0 || !owned(caller_group, root)) goto done;
    if (number == SYS_kill) {
        int sig = (int32_t)request->data.args[1];
        if (first == caller_group) {
            /* The blocked caller anchors its own TGID. Deliver self-signals
             * through the original syscall, not through a second signaler.
             */
            response->flags = SECCOMP_USER_NOTIF_FLAG_CONTINUE;
            error = 0;
        }
        else if (first > 0) error = pinned_signal(first, sig, root);
        else if (first != -1 && first != INT32_MIN) {
            pid_t group, parent;
            if (first == 0 && proc_info((pid_t)request->pid, &parent, &group)) error = ESRCH;
            else error = group_signal(first ? -first : group, sig, root);
        }
    } else if (number == SYS_pidfd_send_signal) {
        pid_t target = pidfd_target((pid_t)request->pid, first);
        if (request->data.args[2] || request->data.args[3]) error = EPERM;
        else if (target > 0) error = pinned_signal(target, (int32_t)request->data.args[1], root);
        else error = ESRCH;
    } else {
        /* CONTINUE only when the fixed target is the blocked caller's own
         * live process. tgkill also checks the TID's group in the kernel.
         * Cross-process queued signals are deliberately unsupported here.
         */
        int safe = (number == SYS_tgkill || number == SYS_rt_tgsigqueueinfo ||
                    number == SYS_rt_sigqueueinfo) && first == caller_group;
        if (number == SYS_tkill)
            safe = first == (pid_t)request->pid || first == caller_group;
        if (safe) { response->flags = SECCOMP_USER_NOTIF_FLAG_CONTINUE; error = 0; }
    }
done:
    response->id = request->id;
    response->val = 0;
    response->error = -error;
}

struct service {
    int listener;
    int audit;
    pid_t root;
};

static void *notifications(void *argument) {
    struct service *service = argument;
    struct seccomp_notif_sizes sizes;
    if (syscall(SYS_seccomp, SECCOMP_GET_NOTIF_SIZES, 0, &sizes)) _exit(77);
    struct seccomp_notif *request = calloc(1, sizes.seccomp_notif);
    struct seccomp_notif_resp *response = calloc(1, sizes.seccomp_notif_resp);
    if (!request || !response) _exit(77);
    for (;;) {
        memset(request, 0, sizes.seccomp_notif);
        if (ioctl(service->listener, SECCOMP_IOCTL_NOTIF_RECV, request)) {
            if (errno == EINTR || errno == ENOENT) continue;
            _exit(77);
        }
        if (ioctl(service->listener, SECCOMP_IOCTL_NOTIF_ID_VALID, &request->id)) continue;
        memset(response, 0, sizes.seccomp_notif_resp);
        decide(request, response, service->root);
        dprintf(service->audit, "{\"id\":%llu,\"caller\":%u,\"caller_tgid\":%d,\"syscall\":%d,\"target_arg\":%d,\"error\":%d,\"continued\":%s,\"signal_number\":%d,\"delivered_targets\":[",
                (unsigned long long)request->id, request->pid, thread_group((pid_t)request->pid), request->data.nr,
                (int32_t)request->data.args[0], -response->error,
                response->flags ? "true" : "false",
                (int32_t)request->data.args[(request->data.nr == SYS_tgkill ||
                                           request->data.nr == SYS_rt_tgsigqueueinfo) ? 2 : 1]);
        for (int i = 0; i < delivered_count; i++)
            dprintf(service->audit, "%s%d", i ? "," : "", delivered_targets[i]);
        dprintf(service->audit, "]}\n");
        if (fsync(service->audit)) _exit(77);
        if (ioctl(service->listener, SECCOMP_IOCTL_NOTIF_SEND, response) && errno != ENOENT) _exit(77);
    }
}

int main(int argc, char **argv) {
    if (argc < 5 || strcmp(argv[1], "--audit") || strcmp(argv[3], "--")) {
        fprintf(stderr, "usage: signal-scope --audit NEW_FILE -- COMMAND [ARGS...]\n");
        return 64;
    }
    int audit = open(argv[2], O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (audit < 0) { perror("audit"); return 77; }
    if (prctl(PR_SET_DUMPABLE, 0)) { perror("dumpable"); return 77; }
    if (prctl(PR_SET_CHILD_SUBREAPER, 1)) { perror("subreaper"); return 77; }
    int pair[2];
    if (socketpair(AF_UNIX, SOCK_SEQPACKET | SOCK_CLOEXEC, 0, pair)) return 77;
    pid_t root = fork();
    if (root < 0) return 77;
    if (!root) {
        close(pair[0]); close(audit);
        int listener = install_filter();
        if (listener < 0 || transfer_fd(pair[1], listener)) {
            perror("signal scope filter: refusing unrestricted execution"); _exit(77);
        }
        close(listener); close(pair[1]);
        execvp(argv[4], argv + 4); perror("exec"); _exit(127);
    }
    close(pair[1]);
    int listener = receive_fd(pair[0]); close(pair[0]);
    if (listener < 0) { int status; waitpid(root, &status, 0); return 77; }
    struct service service = { .listener = listener, .audit = audit, .root = root };
    pthread_t thread;
    if (pthread_create(&thread, NULL, notifications, &service)) return 77;
    int status = 0;
    for (;;) {
        int child_status = 0;
        pid_t exited = waitpid(-1, &child_status, 0);
        if (exited == root) { status = child_status; break; }
        if (exited < 0 && errno != EINTR) return 77;
        /* Reap only adopted descendants of this one guard's filtered root. */
    }
    /* Returning exits the whole broker, including the blocking listener
     * thread. Do not close/reuse its FDs concurrently before exit_group.
     * Descendants retain the filter; a missing listener fails signal syscalls
     * closed. Production integration still needs explicit orphan fencing.
     */
    return WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
}
