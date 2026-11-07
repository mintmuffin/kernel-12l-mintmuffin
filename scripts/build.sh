#!/usr/bin/env bash
#
# build.sh - end to end build: fetch the PE12 kernel tree, integrate BakaSU +
#            SUSFS, compile, and package flashable artifacts.
#
# This is what CI runs, and it is meant to be runnable locally too.
#
# Usage:
#   scripts/build.sh --device starlte [options]
#
# Options:
#   --device <name>       starlte (Galaxy S9, SM-G960F)       (default: starlte)
#                         add the board to the DEVICES list below to support more
#   --workdir <dir>       Where the kernel tree is cloned   (default: ./work)
#   --jobs <n>            Parallel make jobs                (default: nproc)
#   --root-solution <n>   bakasu | none                     (default: bakasu)
#   --no-package          Stop after compiling
#
# Environment:
#   CROSS_COMPILE         Toolchain prefix (default: aarch64-linux-gnu-)
#   KERNEL_REPO/KERNEL_REF  Kernel source (default: PixelExperience twelve)
#   BAKASU_SRC / BAKASU_COMMIT  See scripts/integrate.sh
#   KERNEL_SRC            Use an existing kernel tree instead of cloning
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

KERNEL_REPO="${KERNEL_REPO:-https://github.com/PixelExperience-Devices/kernel_samsung_exynos9810.git}"
KERNEL_REF="${KERNEL_REF:-twelve}"
CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}"
export CROSS_COMPILE

DEVICE="starlte"
WORKDIR="$REPO_DIR/work"
JOBS="$(nproc)"
ROOT_SOLUTION="bakasu"
DO_PACKAGE="yes"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
	case "$1" in
		--device)        DEVICE="$2"; shift 2 ;;
		--workdir)       WORKDIR="$2"; shift 2 ;;
		--jobs)          JOBS="$2"; shift 2 ;;
		--root-solution) ROOT_SOLUTION="$2"; shift 2 ;;
		--no-package)    DO_PACKAGE="no"; shift ;;
		-h|--help)       sed -n '2,26p' "$0"; exit 0 ;;
		*)               die "unknown argument: $1" ;;
	esac
done

# Board -> defconfig board name. Only the S9 is shipped; add another entry
# (e.g. star2lte / crownlte) here and in scripts/package.sh if that changes.
DEVICES="starlte"
case "$DEVICE" in
	starlte) ;;
	*) die "unsupported device '$DEVICE' (supported: $DEVICES)" ;;
esac

for tool in make git python3 "${CROSS_COMPILE}gcc"; do
	command -v "$tool" >/dev/null || die "missing build dependency: $tool"
done
"${CROSS_COMPILE}gcc" --version | head -1

# ------------------------------------------------------------- kernel tree
if [ -n "${KERNEL_SRC:-}" ]; then
	KERNEL_DIR="$(cd "$KERNEL_SRC" && pwd)"
	log "Using existing kernel tree at $KERNEL_DIR"
elif [ -d "$WORKDIR/kernel_src/.git" ]; then
	KERNEL_DIR="$WORKDIR/kernel_src"
	log "Reusing kernel tree at $KERNEL_DIR"
else
	mkdir -p "$WORKDIR"
	KERNEL_DIR="$WORKDIR/kernel_src"
	log "Cloning $KERNEL_REPO ($KERNEL_REF)"
	if ! git clone --depth=1 --single-branch --branch "$KERNEL_REF" "$KERNEL_REPO" "$KERNEL_DIR"; then
		# The repo is ~1 GB; a flaky connection should not kill the build.
		warn "git clone failed, falling back to a tarball download"
		rm -rf "$KERNEL_DIR" "$WORKDIR/ksrc.tar.gz"
		curl -L --retry 5 --retry-all-errors -o "$WORKDIR/ksrc.tar.gz" \
			"${KERNEL_TARBALL:-$(echo "$KERNEL_REPO" | sed -e 's|\.git$||' -e 's|github.com|codeload.github.com|')/tar.gz/refs/heads/$KERNEL_REF}"
		mkdir -p "$KERNEL_DIR"
		tar xzf "$WORKDIR/ksrc.tar.gz" -C "$KERNEL_DIR" --strip-components=1
	fi
fi

log "Kernel: $(make -s -C "$KERNEL_DIR" kernelversion 2>/dev/null || echo unknown)"

# --------------------------------------------------------------- integrate
"$SCRIPT_DIR/integrate.sh" --kernel-dir "$KERNEL_DIR" \
	--root-solution "$ROOT_SOLUTION" --susfs yes --green-screen yes --board "$DEVICE"

# ------------------------------------------------------------------- build
# Modern GCC is much stricter than the 2017/2018 toolchain this tree was
# written for. -Werror is stripped by integrate.sh; these -Wno flags cover the
# remaining noisy-but-harmless warnings.
KCFLAGS_COMMON="-Wno-error -Wno-format -Wno-error=format -Wno-nonnull \
-Wno-implicit-fallthrough -Wno-unused-const-variable -Wno-maybe-uninitialized \
-Wno-array-bounds -Wno-stringop-overflow -Wno-misleading-indentation \
-Wno-missing-attributes -Wno-packed-not-aligned -Wno-restrict \
-Wno-format-overflow -Wno-enum-conversion"

build_one() { # build_one <device>
	local device="$1"
	local defconfig="exynos9810-${device}_defconfig"
	local out="$KERNEL_DIR/out"

	[ -f "$KERNEL_DIR/arch/arm64/configs/$defconfig" ] || die "missing defconfig $defconfig"

	log "Configuring $defconfig"
	rm -rf "$out"
	make -C "$KERNEL_DIR" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" O="$out" "$defconfig"

	# Fail loudly if Kconfig silently dropped our options.
	for opt in CONFIG_KSU CONFIG_KSU_SUSFS CONFIG_KSU_SUSFS_SUS_PATH CONFIG_THREAD_INFO_IN_TASK; do
		grep -q "^${opt}=y" "$out/.config" || die "$opt did not survive Kconfig for $device"
	done
	log "KernelSU + SUSFS enabled for $device"

	log "Compiling $device ($JOBS jobs)"
	make -C "$KERNEL_DIR" ARCH=arm64 CROSS_COMPILE="$CROSS_COMPILE" O="$out" \
		KCFLAGS="$KCFLAGS_COMMON" -j"$JOBS" Image dtbs

	[ -f "$out/arch/arm64/boot/Image" ] || die "no Image produced for $device"
	log "Built $device: $(du -h "$out/arch/arm64/boot/Image" | cut -f1) Image"
}

package_one() { # package_one <device>
	local device="$1"
	local tag="pe12-bakasu-susfs"
	[ "$ROOT_SOLUTION" = "none" ] && tag="pe12-greenfix"
	"$SCRIPT_DIR/package.sh" --kernel-dir "$KERNEL_DIR" --device "$device" \
		--out "$REPO_DIR/dist" --tag "$tag"
}

devices="$DEVICE"

for device in $devices; do
	build_one "$device"
	if [ "$DO_PACKAGE" = "yes" ]; then
		package_one "$device"
	fi
done

log "Done"
