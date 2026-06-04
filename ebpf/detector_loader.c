#include <errno.h>
#include <signal.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <bpf/bpf.h>
#include <bpf/libbpf.h>

#include "ransomware_detector.skel.h"

static volatile sig_atomic_t exiting = 0;

static void sig_handler(int sig)
{
    (void)sig;
    exiting = 1;
}

static int open_unix_socket(const char *path)
{
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    if (fd < 0)
        return -1;

    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path, sizeof(addr.sun_path) - 1);

    if (connect(fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(fd);
        return -1;
    }

    return fd;
}

static int handle_event(void *ctx, void *data, size_t data_sz)
{
    (void)data_sz;
    int *sock_fd = (int *)ctx;
    const struct file_event *ev = (const struct file_event *)data;

    char line[1024];
    int n = snprintf(
        line,
        sizeof(line),
        "{\"pid\":%u,\"uid\":%u,\"timestamp\":%.6f,\"comm\":\"%s\",\"filename\":\"%s\",\"op_type\":%u}\n",
        ev->pid,
        ev->uid,
        (double)ev->timestamp_ns / 1000000000.0,
        ev->comm,
        ev->filename,
        ev->op_type);

    if (n <= 0)
        return 0;

    if (*sock_fd >= 0) {
        ssize_t w = write(*sock_fd, line, (size_t)n);
        if (w < 0)
            *sock_fd = -1;
    }

    return 0;
}

int main(void)
{
    struct ransomware_detector_bpf *skel = NULL;
    struct ring_buffer *rb = NULL;
    int err = 0;

    signal(SIGINT, sig_handler);
    signal(SIGTERM, sig_handler);

    skel = ransomware_detector_bpf__open_and_load();
    if (!skel) {
        fprintf(stderr, "failed to open/load BPF skeleton\n");
        return 1;
    }

    err = ransomware_detector_bpf__attach(skel);
    if (err) {
        fprintf(stderr, "failed to attach BPF skeleton: %d\n", err);
        goto cleanup;
    }

    int sock_fd = open_unix_socket("/tmp/cis_ebpf_events.sock");
    rb = ring_buffer__new(bpf_map__fd(skel->maps.rb), handle_event, &sock_fd, NULL);
    if (!rb) {
        fprintf(stderr, "failed to create ring buffer\n");
        err = 1;
        goto cleanup;
    }

    while (!exiting) {
        err = ring_buffer__poll(rb, 100);
        if (err == -EINTR)
            break;
        if (err < 0) {
            fprintf(stderr, "ring buffer polling error: %d\n", err);
            break;
        }
    }

cleanup:
    ring_buffer__free(rb);
    ransomware_detector_bpf__destroy(skel);
    return err < 0 ? 1 : 0;
}
