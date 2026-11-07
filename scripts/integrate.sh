#!/usr/bin/env bash
#
# integrate.sh - turn a pristine Exynos 9810 (Linux 4.9) kernel tree into a
#                BakaSU + SUSFS v2.3.0 kernel with the AMOLED green-screen fix.
#
# Everything this script touches is patched in place and is idempotent: running
# it twice on the same tree is a no-op (it detects already applied steps).
#
# Usage:
#   scripts/integrate.sh --kernel-dir <path> [options]
#
# Options:
#   --kernel-dir <dir>      Kernel source tree (required)
#   --root-solution <name>  bakasu | none            (default: bakasu)
#   --susfs <yes|no>        Kernel-side SUSFS patch  (default: yes)
#   --green-screen <yes|no> AMOLED green-screen fix  (default: yes)
#   --board <name>          Defconfig board to tune: starlte|star2lte|crownlte|all
#                           (default: all, i.e. every exynos9810-*_defconfig)
#   --no-defconfig          Do not touch the defconfigs
#
# Environment overrides:
#   BAKASU_REPO     git URL of the root solution      (default: BakaSU)
#   BAKASU_COMMIT   pinned commit/tag to check out    (default: pinned below)
#   BAKASU_SRC      existing BakaSU checkout to reuse (skips the clone)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---------------------------------------------------------------- pinned deps
# BakaSU (formerly ReSukiSU, a SukiSU-Ultra downstream) - the active KernelSU
# fork whose compat layer still targets Linux 3.4+, which is the only way to run
# a current KernelSU-lineage driver on this 4.9 tree. SukiSU-Ultra's own
# `builtin` branch stopped compiling below 4.14.
BAKASU_REPO="${BAKASU_REPO:-https://github.com/Baka-SU/BakaSU.git}"
BAKASU_COMMIT="${BAKASU_COMMIT:-516d3e87fbc986ccefdde2c2765f1700612441a9}"
BAKASU_BRANCH="${BAKASU_BRANCH:-main}"

# SUSFS v2.3.0 kernel-side port for Linux 4.9 non-GKI
# (wxx9248/susfs4ksu @ kernel-4.9-v2, upstream: simonpunk/susfs4ksu).
SUSFS_VERSION="v2.3.0"

KERNEL_DIR=""
ROOT_SOLUTION="bakasu"
USE_SUSFS="yes"
GREEN_SCREEN="yes"
BOARD="all"
DO_DEFCONFIG="yes"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

while [ $# -gt 0 ]; do
	case "$1" in
		--kernel-dir)     KERNEL_DIR="$2"; shift 2 ;;
		--root-solution)  ROOT_SOLUTION="$2"; shift 2 ;;
		--susfs)          USE_SUSFS="$2"; shift 2 ;;
		--green-screen)   GREEN_SCREEN="$2"; shift 2 ;;
		--board)          BOARD="$2"; shift 2 ;;
		--no-defconfig)   DO_DEFCONFIG="no"; shift ;;
		-h|--help)        sed -n '2,32p' "$0"; exit 0 ;;
		*)                die "unknown argument: $1" ;;
	esac
done

[ -n "$KERNEL_DIR" ] || die "--kernel-dir is required"
[ -d "$KERNEL_DIR" ] || die "no such kernel tree: $KERNEL_DIR"
KERNEL_DIR="$(cd "$KERNEL_DIR" && pwd)"

for d in fs drivers include/linux arch/arm64; do
	[ -d "$KERNEL_DIR/$d" ] || die "$KERNEL_DIR does not look like a kernel tree (missing $d)"
done

# ------------------------------------------------------------------- helpers
apply_patch() { # apply_patch <root> <patch> [extra patch args...]
	local root="$1" patch_file="$2"; shift 2
	( cd "$root" && patch -p1 -N -F0 --no-backup-if-mismatch "$@" < "$patch_file" )
}

SUSFS_PATCH="$REPO_DIR/patches/susfs/50_add_susfs_in_kernel-4.9.patch"

# ===================================================================== 0. info
log "Kernel tree: $KERNEL_DIR"
KVER="$(make -s -C "$KERNEL_DIR" kernelversion 2>/dev/null || true)"
[ -n "$KVER" ] || KVER="$(awk '/^VERSION =/{v=$3}/^PATCHLEVEL =/{p=$3}/^SUBLEVEL =/{s=$3}END{print v"."p"."s}' "$KERNEL_DIR/Makefile")"
log "Kernel version: $KVER"
case "$KVER" in
	4.9.*) ;;
	*) die "this integration targets Linux 4.9 (got $KVER)" ;;
esac

# ================================================================ 1. SUSFS
if [ "$USE_SUSFS" = "yes" ]; then
	log "Installing SUSFS $SUSFS_VERSION (Linux 4.9 non-GKI port)"

	cp -f "$REPO_DIR/patches/susfs/fs/susfs.c"                    "$KERNEL_DIR/fs/susfs.c"
	cp -f "$REPO_DIR/patches/susfs/include/linux/susfs.h"         "$KERNEL_DIR/include/linux/susfs.h"
	cp -f "$REPO_DIR/patches/susfs/include/linux/susfs_def.h"     "$KERNEL_DIR/include/linux/susfs_def.h"

	if grep -q 'CONFIG_KSU_SUSFS' "$KERNEL_DIR/fs/namespace.c" 2>/dev/null && \
	   grep -q "CL_COPY_MNT_NS" "$KERNEL_DIR/fs/pnode.h" 2>/dev/null; then
		warn "SUSFS core hooks already present, skipping kernel patch"
	else
		log "Applying the SUSFS $SUSFS_VERSION kernel patch (fuzz 0)"
		apply_patch "$KERNEL_DIR" "$SUSFS_PATCH"
		if ( cd "$KERNEL_DIR" && find . -name '*.rej' | grep -q . ); then
			die "SUSFS patch did not apply cleanly.
The kernel tree must be PixelExperience-Devices/kernel_samsung_exynos9810 @ twelve."
		fi
	fi
else
	log "SUSFS disabled, skipping kernel-side patch"
fi

# ======================================================== 2. root solution
case "$ROOT_SOLUTION" in
	bakasu)
		log "Installing BakaSU ($BAKASU_COMMIT)"
		if [ -e "$KERNEL_DIR/drivers/kernelsu" ]; then
			warn "drivers/kernelsu already exists, keeping it"
		else
			if [ -n "${BAKASU_SRC:-}" ]; then
				src="$BAKASU_SRC"
				[ -d "$src/kernel" ] || die "BAKASU_SRC=$src does not look like a BakaSU checkout"
			else
				src="$KERNEL_DIR/KernelSU"
				if [ -d "$src/.git" ]; then
					log "Reusing existing BakaSU checkout at $src"
				else
					git clone --quiet --single-branch --branch "$BAKASU_BRANCH" \
						"$BAKASU_REPO" "$src"
				fi
				git -C "$src" checkout --quiet "$BAKASU_COMMIT"
			fi

			# BakaSU's Kbuild derives the driver version from git and hard
			# errors when the driver is not a git work tree, so link it in
			# exactly like BakaSU's own setup.sh does instead of copying.
			ln -sfn "$(realpath --relative-to="$KERNEL_DIR/drivers" "$src/kernel")" \
				"$KERNEL_DIR/drivers/kernelsu"
			log "BakaSU linked at drivers/kernelsu -> $(readlink "$KERNEL_DIR/drivers/kernelsu")"
			log "BakaSU commit: $(git -C "$src" rev-parse HEAD 2>/dev/null || echo external checkout)"
		fi

		if ! grep -q "kernelsu" "$KERNEL_DIR/drivers/Makefile"; then
			printf '\nobj-$(CONFIG_KSU) += kernelsu/\n' >> "$KERNEL_DIR/drivers/Makefile"
		fi
		if ! grep -q 'drivers/kernelsu/Kconfig' "$KERNEL_DIR/drivers/Kconfig"; then
			printf '\nsource "drivers/kernelsu/Kconfig"\n' >> "$KERNEL_DIR/drivers/Kconfig"
		fi
		;;
	none)
		log "No root solution requested"
		;;
	*)
		die "unsupported --root-solution '$ROOT_SOLUTION' (bakasu|none)"
		;;
esac

# ==================================================== 3. green screen fix
if [ "$GREEN_SCREEN" = "yes" ]; then
	if grep -q "panel_green_screen_recovery" \
		"$KERNEL_DIR/drivers/video/fbdev/exynos/panel/panel_drv.c" 2>/dev/null; then
		warn "green-screen fix already applied, skipping"
	else
		log "Applying AMOLED green-screen recovery patch"
		apply_patch "$KERNEL_DIR" "$REPO_DIR/patches/green_screen_fix.patch"
	fi
fi

# ======================================= 4. build hygiene for modern GCC
log "Kernel build hygiene (modern GCC compatibility)"
# drivers/video/fbdev/exynos/dpu_9810 declares a table of doubles; GCC >= 8
# refuses float in kernel space. The sibling dpu/ driver already uses the same
# table with unsigned long, so mirror that.
sed -i 's/const double decon_clocks_table/const unsigned long decon_clocks_table/g' \
	"$KERNEL_DIR/drivers/video/fbdev/exynos/dpu_9810/decon_reg.c" 2>/dev/null || true

python3 "$SCRIPT_DIR/strip_werror.py" "$KERNEL_DIR"

# ============================================================== 5. defconfig
if [ "$DO_DEFCONFIG" = "yes" ]; then
	log "Enabling KernelSU + SUSFS in the defconfigs"

	# SUSFS feature set. Every KSU_SUSFS_* option in BakaSU's Kconfig is
	# default-y, they are listed explicitly so the config is self documenting.
	read -r -d '' KSU_CONFIG <<-'EOF' || true
	#
	# --- BakaSU + SUSFS (added by kernel-12l-mintmuffin) ---
	CONFIG_KALLSYMS_ALL=y
	CONFIG_KSU=y
	CONFIG_KSU_SUSFS=y
	CONFIG_KSU_SUSFS_SUS_PATH=y
	CONFIG_KSU_SUSFS_SUS_MOUNT=y
	CONFIG_KSU_SUSFS_SUS_KSTAT=y
	CONFIG_KSU_SUSFS_SPOOF_UNAME=y
	CONFIG_KSU_SUSFS_ENABLE_LOG=y
	CONFIG_KSU_SUSFS_HIDE_KSU_SUSFS_SYMBOLS=y
	CONFIG_KSU_SUSFS_SPOOF_CMDLINE_OR_BOOTCONFIG=y
	CONFIG_KSU_SUSFS_OPEN_REDIRECT=y
	CONFIG_KSU_SUSFS_SUS_MAP=y
	EOF

	case "$BOARD" in
		all)     defconfigs=$(ls "$KERNEL_DIR"/arch/arm64/configs/exynos9810-*_defconfig) ;;
		starlte|star2lte|crownlte)
		         defconfigs="$KERNEL_DIR/arch/arm64/configs/exynos9810-${BOARD}_defconfig" ;;
		*)       die "unknown --board '$BOARD'" ;;
	esac

	for defconfig in $defconfigs; do
		[ -f "$defconfig" ] || die "missing defconfig: $defconfig"
		if grep -q '^CONFIG_KSU=y' "$defconfig"; then
			warn "$(basename "$defconfig") already carries the KSU config"
			continue
		fi
		sed -i 's/^CONFIG_LOCALVERSION=.*/CONFIG_LOCALVERSION="-mintmuffin-mafushii"/' "$defconfig"
		# Drop any pre-existing definition of the symbols we set, otherwise
		# kconfig warns about overrides and the last line wins by accident.
		while IFS='=' read -r key _; do
			case "$key" in
				CONFIG_*) [ -n "$key" ] && sed -i "/^${key}=/d; /^# ${key} is not set/d" "$defconfig" ;;
			esac
		done <<-EOF
		$KSU_CONFIG
		EOF
		printf '%s\n' "$KSU_CONFIG" >> "$defconfig"
		log "patched $(basename "$defconfig")"
	done
fi

log "Integration complete"
