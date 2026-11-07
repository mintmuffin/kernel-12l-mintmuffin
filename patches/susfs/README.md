# SUSFS v2.3.0 for Linux 4.9 (non-GKI), rebased for the Exynos 9810 tree

| file | what it is |
|------|------------|
| `50_add_susfs_in_kernel-4.9.patch` | the patch we actually apply, already rebased onto `PixelExperience-Devices/kernel_samsung_exynos9810 @ twelve` (Linux 4.9.319) |
| `fs/susfs.c`, `include/linux/susfs.h`, `include/linux/susfs_def.h` | SUSFS kernel-side sources copied into the tree verbatim |
| `upstream/50_add_susfs_in_kernel-4.9.patch` | the untouched upstream patch, reference only, **not applied** |

## Where it comes from

* SUSFS itself: <https://gitlab.com/simonpunk/susfs4ksu> — `SUSFS_VERSION "v2.3.0"`.
* The Linux 4.9 non-GKI port of it: <https://github.com/wxx9248/susfs4ksu>,
  branch `kernel-4.9-v2`, commit `71345ded5af28f55d76ebcdc7a9df9cea56111e1`
  ("feat: v2.3.0 port").

The port is needed because simonpunk's own `kernel-4.9` branch stopped at
v1.5.5 (Feb 2025) while the 4.9-capable root solutions moved on to the v2
SUSFS API (`susfs_add_sus_map`, `susfs_set_batch_sid`,
`susfs_get_enabled_features`, ...). v1.5.5 cannot compile against a current
BakaSU/KernelSU-Next driver.

## What was rebased

The upstream patch targets a mainline 4.9 tree. On this Samsung tree it leaves
17 rejects; all of them are context drift (Samsung added `CONFIG_RKP_NS_PROT`,
`task_integrity.h`, `sec_debug.h`, dropped `mm_inline.h`, rewrote
`generic_readlink()`, and has no `proc_command_line`/bootconfig plumbing).
Those hunks are pre-applied in our patch, plus one real API difference:

* `fs/exec.c` — upstream assumes SukiSU's `ksu_su_compat_enabled` is a plain
  `bool`. BakaSU (like KernelSU >= 4.3 kernels) uses a `struct static_key_true`,
  so the hook uses `static_branch_unlikely(&ksu_su_compat_enabled)`.

The patch applies with `-F0` (no fuzz) on a pristine tree and leaves no rejects.

## How to update SUSFS

1. Fetch the new `kernel-4.9` patch from the port repository (or `kernel-4.9`
   of upstream if it ever resumes) and drop it over
   `upstream/50_add_susfs_in_kernel-4.9.patch`.
2. Copy the matching `fs/susfs.c` + `include/linux/susfs*.h`.
3. `patch -p1 -F0` it onto a pristine `twelve` tree, collect the rejects, and
   re-apply them by hand where Samsung diverges — the hunks listed above are
   the only ones that ever conflict.
4. Re-generate our rebased patch (`diff -u` of the touched files) and rebuild.
   `scripts/integrate.sh` fails loudly if the patch stops applying cleanly, so
   a broken update cannot slip into a release silently.
