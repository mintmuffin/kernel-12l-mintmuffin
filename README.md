# kernel-12l-mintmuffin

Clean Android 12L (PixelExperience 12.1 / ArrowOS 12.1 / AOSP) kernel for the
Samsung Galaxy S9 / S9+ / Note9 (Exynos 9810), with the AMOLED green-screen
recovery patch and a **current** KernelSU-lineage root solution plus SUSFS.

| | |
|---|---|
| Base tree | `PixelExperience-Devices/kernel_samsung_exynos9810` @ `twelve` (Linux 4.9.319) |
| Device | `starlte` - Galaxy S9 (SM-G960F) |
| Root | **BakaSU** @ `516d3e8` — KernelSU fork, formerly ReSukiSU, from the SukiSU-Ultra family |
| Hiding | **SUSFS v2.3.0**, Linux 4.9 non-GKI port |
| Hook mode | SUSFS inline hooks (no KPROBES on this kernel, no manual hook patches to maintain) |
| Display | AMOLED green-screen recovery: native ALPM hardware reset + forced 2-nit sequence |
| Branding | `-mintmuffin-mafushii` |
| Toolchain | Linaro GCC 6.4.1 aarch64 (pinned) |

---

## Why this root solution

The obvious candidates do not work on a Linux 4.9 non-GKI kernel any more:

* **KernelSU (tiann) v3.x** is GKI-only. Non-GKI support was dropped in v1.0
  (commit `898e9d4`), and the old v1.0.3 + `revert_898` + hand-rolled manual
  hooks recipe that used to live in this repo cannot be combined with the v2
  SUSFS API.
* **SukiSU-Ultra** `builtin` no longer compiles below Linux 4.14 — this tree is
  4.9.
* **SUSFS** `kernel-4.9` stopped at v1.5.5; current drivers expect the v2 API.

So the stack is **BakaSU** (KernelSU fork that still carries a 3.4+ compat
layer, with a built-in SUSFS inline-hook mode) plus the **v2.3.0 Linux 4.9
port** of SUSFS. That is the combination the port author recommends, everything
is pinned by commit, and the whole thing is compiled in CI on every change.

## Repository layout

```
patches/
  green_screen_fix.patch                  AMOLED green-screen recovery
  susfs/50_add_susfs_in_kernel-4.9.patch  SUSFS v2.3.0, rebased for this tree
  susfs/fs/, susfs/include/linux/         SUSFS kernel sources
  susfs/upstream/                         pristine upstream patch (reference)
scripts/
  integrate.sh        patch a pristine kernel tree: SUSFS + BakaSU + green fix
  build.sh            clone tree -> integrate -> build -> package
  package.sh          boot.img / dt.img / AnyKernel3 zip / Odin tar
  mkbootimg.py        Android boot image + Samsung DTBH packing
  strip_werror.py     modern-GCC build hygiene
tools/pe12_ramdisk.cpio.gz  stock PE12 ramdisk used by the standalone boot.img
```

## Build

### CI (recommended)

Actions -> **Build PE12 kernel (BakaSU + SUSFS + green screen fix)** ->
*Run workflow* (it builds `starlte`, the Galaxy S9). Artifacts:

```
anykernel3-starlte-pe12-bakasu-susfs.zip      flash in TWRP / FKM / EX Kernel Manager
boot_starlte_pe12_bakasu_susfs.img            standalone boot image
boot-starlte-pe12-bakasu-susfs-ODIN.tar       Odin AP slot
```

A second workflow, **… (green screen fix only, no root)**, builds the same
kernel without KernelSU/SUSFS. Both workflows are `starlte`-only; adding
another board means extending the device list in `scripts/build.sh` and
`scripts/package.sh` (the DTB is selected by the board's defconfig).

### Locally

```sh
# aarch64 GCC >= 5.1; the pinned Linaro 6.4.1 prebuilt is what CI uses
git clone --depth=1 -b lineage-19.1 \
  https://github.com/LineageOS/android_prebuilts_gcc_linux-x86_aarch64_aarch64-linux-gnu-6.4.1.git ~/gcc64
export PATH="$HOME/gcc64/bin:$PATH"
sudo apt install bc bison flex libssl-dev libelf-dev dwarves zip device-tree-compiler

./scripts/build.sh --device starlte --jobs "$(nproc)"
# artifacts land in dist/
```

`scripts/build.sh` clones the kernel tree into `work/`, patches it, verifies
that `CONFIG_KSU` / `CONFIG_KSU_SUSFS` survived Kconfig, builds `Image dtbs`
and packages the result. To reuse an existing tree:
`KERNEL_SRC=/path/to/tree ./scripts/build.sh --device starlte`.

BakaSU is linked into the tree (`drivers/kernelsu -> ../KernelSU/kernel`) rather
than copied, because its Kbuild derives the driver version from git and hard
errors on a copied tree. That is the same layout BakaSU's own `setup.sh` uses.

### Verified build

The current recipe is built and checked against `twelve` (`4.9.319`), device
`starlte`, with the pinned GCC 6.4.1:

```
-- BakaSU version code: 35257
-- BakaSU version name: v4.2.0-rc3-516d3e87
-- BakaSU: using SuSFS Inline hook
-- BakaSU/susfs_inline: ksu_handle_setresuid/-execveat/-faccessat/-sys_read/-stat/-sys_reboot/-input_handle_event found
Image         31078408 bytes
boot.img      32749568 bytes  (kernel + stock ramdisk + 303104 byte DTBH)
```

## Flash

1. Install the **BakaSU manager** APK that matches this kernel build (BakaSU
   releases / CI build for the same commit). The official KernelSU manager and
   KOWSU also work — BakaSU is multi-manager. The manager bundles the matching
   `ksu_susfs` userspace tool (v2.3.0). Do **not** use the v1.5.5 `ksu_susfs`
   from the old `susfs4ksu` `kernel-4.9` branch, it is incompatible.
2. Flash `anykernel3-*.zip` in TWRP (or with a kernel manager). AnyKernel3
   keeps your device's own boot image layout, ramdisk and cmdline, so it is
   the safe path. `boot-*-ODIN.tar` is for Odin (`AP`), brute force recovery.
3. After boot, verify:

```sh
su -c 'cat /proc/version'          # -mintmuffin-mafushii
su -c 'ksu_susfs show version'     # v2.3.0
```

4. Optional SUSFS hardening from a module `service.sh` or a root shell:

```sh
ksu_susfs hide_sus_mnts_for_non_su_procs 1
```

## Notes and limitations

* `CONFIG_KSU_SUSFS_SUS_MAP`, `SUS_PATH`, `SUS_MOUNT`, `SUS_KSTAT`,
  `OPEN_REDIRECT`, `SPOOF_UNAME`, `SPOOF_CMDLINE_OR_BOOTCONFIG` and symbol
  hiding are all enabled; see `scripts/integrate.sh` for the exact block that
  is appended to the defconfigs.
* SUSFS hides paths/mounts for non-root app processes only — grant root to the
  app that is supposed to see them (e.g. file managers, banking apps).
* The tree builds everything built-in (no loadable modules), so there is no
  vermagic/module mismatch with the vendor partitions after flashing.
* The stock DVFS tables and thermal governors are untouched.
* Updating: bump `BAKASU_COMMIT` in `scripts/integrate.sh` (or set it in the
  environment) and see `patches/susfs/README.md` for SUSFS.
