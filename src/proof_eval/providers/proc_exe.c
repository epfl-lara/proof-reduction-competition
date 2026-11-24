/* Compatibility only, never an access-control boundary.
 * The mount guard deliberately hides procfs. Dynamically linked native clients
 * can still ask libc for their own executable path using the kernel's AT_EXECFN.
 * No file is opened or made writable, and no other procfs path is emulated.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <sys/auxv.h>
#include <unistd.h>

static char executable[PATH_MAX];
static ssize_t (*original_readlink)(const char *, char *, size_t);
static ssize_t (*original_readlinkat)(int, const char *, char *, size_t);

__attribute__((constructor)) static void initialize(void) {
    original_readlink = dlsym(RTLD_NEXT, "readlink");
    original_readlinkat = dlsym(RTLD_NEXT, "readlinkat");
    const char *name = (const char *)getauxval(AT_EXECFN);
    if (!name || !*name) return;
    /* Resolve at process startup, before a client can change its working dir. */
    if (!realpath(name, executable)) executable[0] = '\0';
}

static int own_executable(const char *path) {
    return executable[0] &&
        (!strcmp(path, "/proc/self/exe") || !strcmp(path, "/proc/thread-self/exe"));
}

static ssize_t copy_executable(char *buffer, size_t size) {
    if (!size) { errno = EINVAL; return -1; }
    size_t length = strlen(executable);
    if (length > size) length = size;
    memcpy(buffer, executable, length);
    return (ssize_t)length;  /* readlink does not append a NUL. */
}

ssize_t readlink(const char *path, char *buffer, size_t size) {
    if (own_executable(path)) return copy_executable(buffer, size);
    if (!original_readlink) { errno = ENOSYS; return -1; }
    return original_readlink(path, buffer, size);
}

ssize_t readlinkat(int directory, const char *path, char *buffer, size_t size) {
    if (own_executable(path)) return copy_executable(buffer, size);
    if (!original_readlinkat) { errno = ENOSYS; return -1; }
    return original_readlinkat(directory, path, buffer, size);
}
