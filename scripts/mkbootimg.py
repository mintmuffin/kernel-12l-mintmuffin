#!/usr/bin/env python3
"""Package an Exynos 9810 (samsung/universal9810) kernel build into flashable images.

Produces, in --out:
  Image-dtb                        kernel with the device DTBs appended (AnyKernel3)
  dt.img                           Samsung DTBH blob (AnyKernel3 / boot.img DT area)
  boot_<device>_<tag>.img          standalone Android boot image
  boot-<device>-<tag>-ODIN.tar     the same boot.img in a tar for Odin

The Android header values and the DTBH layout below are the ones the stock
PE12/ArrowOS boot image for these devices uses; do not "clean them up" without
re-checking them against a dump of a stock boot.img.

Usage:
  mkbootimg.py --image out/arch/arm64/boot/Image \
               --dtb-dir out/arch/arm64/boot/dts/exynos \
               --device starlte --ramdisk tools/pe12_ramdisk.cpio.gz \
               --out dist --tag pe12-bakasu-susfs
"""
import argparse
import glob
import os
import struct
import sys
import tarfile

PAGE_SIZE = 2048

# Android boot image header (v0) values used by the stock Samsung boot.img.
KERNEL_ADDR = 268468224    # 0x10008000
RAMDISK_ADDR = 285212672   # 0x11000000
TAGS_ADDR = 268435712      # 0x10000100
OS_VERSION = 402653547     # 0x1800000B
CMDLINE = b"buildvariant=userdebug\x00"

# Samsung DTBH blob header ("DTBH", version 2.1) for a single eur_open_26 DTB.
DTBH_MAGIC = b"DTBH"
DTBH_VERSION = 2
DTBH_ENTRY_1 = 0x50A6
DTBH_ENTRY_2 = 0x217584DA
DTBH_BOARD_ID = 0x2652
DTBH_VERSION_2 = 26


def pad(data, align):
    rem = len(data) % align
    return data + b"\x00" * (align - rem) if rem else data


def pick_dtb(dtb_dir, device):
    """Prefer the eur_open_26 DTB, exactly like the stock image ships it."""
    preferred = os.path.join(dtb_dir, "exynos9810-%s_eur_open_26.dtb" % device)
    if os.path.exists(preferred):
        return preferred
    cands = sorted(glob.glob(os.path.join(dtb_dir, "exynos9810-%s*.dtb" % device)))
    if not cands:
        sys.exit("no DTBs for %s in %s - did `make dtbs` run?" % (device, dtb_dir))
    return cands[0]


def build_dt_img(dtb_path):
    with open(dtb_path, "rb") as fh:
        dtb = fh.read()

    hdr = bytearray(PAGE_SIZE)
    struct.pack_into("<4sIII", hdr, 0, DTBH_MAGIC, DTBH_VERSION, 1, DTBH_BOARD_ID)
    struct.pack_into("<IIIIII", hdr, 16, DTBH_ENTRY_1, DTBH_ENTRY_2,
                     DTBH_VERSION_2, 255, PAGE_SIZE, len(dtb))
    hdr[40] = 0x20
    return bytes(hdr) + pad(dtb, PAGE_SIZE)


def build_image_dtb(image_path, dtb_dir, device):
    with open(image_path, "rb") as fh:
        out = fh.read()
    appneded = 0
    for dtb in sorted(glob.glob(os.path.join(dtb_dir, "exynos9810-%s*.dtb" % device))):
        with open(dtb, "rb") as fh:
            out += fh.read()
        appneded += 1
    return out, appneded


def build_boot_img(kernel, ramdisk, dt):
    if len(DTBH_MAGIC) != 4:
        raise AssertionError
    hdr = bytearray(PAGE_SIZE)
    struct.pack_into("<8sIIIIIIIIII", hdr, 0,
                     b"ANDROID!", len(kernel), KERNEL_ADDR,
                     len(ramdisk), RAMDISK_ADDR,
                     0, 0, TAGS_ADDR,
                     PAGE_SIZE, len(dt), OS_VERSION)
    hdr[64:64 + len(CMDLINE)] = CMDLINE
    return bytes(hdr) + pad(kernel, PAGE_SIZE) + pad(ramdisk, PAGE_SIZE) + dt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="out/arch/arm64/boot/Image")
    ap.add_argument("--dtb-dir", required=True, help="out/arch/arm64/boot/dts/exynos")
    ap.add_argument("--device", required=True, help="starlte (Galaxy S9, SM-G960F)")
    ap.add_argument("--ramdisk", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="pe12-bakasu-susfs")
    ap.add_argument("--no-bootimg", action="store_true",
                    help="only write Image-dtb and dt.img (AnyKernel3 builds)")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    device, tag = args.device, args.tag

    dtb_path = pick_dtb(args.dtb_dir, device)
    dt = build_dt_img(dtb_path)
    with open(os.path.join(args.out, "dt.img"), "wb") as fh:
        fh.write(dt)
    print("  dt.img         %8d bytes  (%s)" % (len(dt), os.path.basename(dtb_path)))

    image_dtb, count = build_image_dtb(args.image, args.dtb_dir, device)
    with open(os.path.join(args.out, "Image-dtb"), "wb") as fh:
        fh.write(image_dtb)
    print("  Image-dtb      %8d bytes  (%d DTBs appended)" % (len(image_dtb), count))

    if args.no_bootimg:
        return 0

    with open(args.image, "rb") as fh:
        kernel = fh.read()
    with open(args.ramdisk, "rb") as fh:
        ramdisk = fh.read()

    boot = build_boot_img(kernel, ramdisk, dt)
    boot_name = "boot_%s_%s.img" % (device, tag.replace("-", "_"))
    boot_path = os.path.join(args.out, boot_name)
    with open(boot_path, "wb") as fh:
        fh.write(boot)
    print("  %-14s %8d bytes" % (boot_name, len(boot)))

    tar_name = "boot-%s-%s-ODIN.tar" % (device, tag)
    tar_path = os.path.join(args.out, tar_name)
    with tarfile.open(tar_path, "w") as tar:
        tar.add(boot_path, arcname="boot.img")
    print("  %-14s %8d bytes" % (tar_name, os.path.getsize(tar_path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
