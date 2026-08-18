#!/usr/bin/env python3
"""
comfyui_desktop.orphan_reap
Re-exports orphan_reap functions for package access.
"""
from orphan_reap import (
    COMFY_PORT,
    SENTINEL,
    pid_on_port,
    image_name,
    parent_pid_of,
    pid_alive,
    read_sentinel,
    write_sentinel,
    clear_sentinel,
    reap_orphan_8188,
    reap_if_orphan,
    WindowsJobObject,
    reap_process_tree,
)

