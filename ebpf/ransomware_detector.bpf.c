// SPDX-License-Identifier: GPL-2.0
#include <linux/bpf.h>
#include <linux/fcntl.h>
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>
#include <bpf/bpf_tracing.h>

char LICENSE[] SEC("license") = "GPL";

struct {
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

struct file_event {
    __u32 pid;
    __u32 uid;
    __u64 timestamp_ns;
    char comm[16];
    char filename[256];
    __u32 op_type; // 1=read,2=write,4=unlink
    __u32 flags;
};

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_openat(struct trace_event_raw_sys_enter *ctx)
{
    __u64 id = bpf_get_current_pid_tgid();
    __u32 pid = id >> 32;

    struct file_event *ev = bpf_ringbuf_reserve(&rb, sizeof(*ev), 0);
    if (!ev)
        return 0;

    ev->pid = pid;
    ev->uid = bpf_get_current_uid_gid() & 0xFFFFFFFF;
    ev->timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&ev->comm, sizeof(ev->comm));

    const char *filename_ptr = (const char *)ctx->args[1];
    bpf_probe_read_user_str(&ev->filename, sizeof(ev->filename), filename_ptr);

    int flags = (int)ctx->args[2];
    if ((flags & O_WRONLY) || (flags & O_RDWR))
        ev->op_type = 2;
    else
        ev->op_type = 1;

    ev->flags = (__u32)flags;
    bpf_ringbuf_submit(ev, 0);
    return 0;
}

SEC("tracepoint/syscalls/sys_enter_unlinkat")
int trace_unlinkat(struct trace_event_raw_sys_enter *ctx)
{
    __u64 id = bpf_get_current_pid_tgid();
    __u32 pid = id >> 32;

    struct file_event *ev = bpf_ringbuf_reserve(&rb, sizeof(*ev), 0);
    if (!ev)
        return 0;

    ev->pid = pid;
    ev->uid = bpf_get_current_uid_gid() & 0xFFFFFFFF;
    ev->timestamp_ns = bpf_ktime_get_ns();
    bpf_get_current_comm(&ev->comm, sizeof(ev->comm));
    ev->op_type = 4;
    ev->flags = 0;

    const char *filename_ptr = (const char *)ctx->args[1];
    bpf_probe_read_user_str(&ev->filename, sizeof(ev->filename), filename_ptr);

    bpf_ringbuf_submit(ev, 0);
    return 0;
}
