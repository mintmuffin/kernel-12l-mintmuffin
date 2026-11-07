#!/usr/bin/env python3
"""Strip -Werror (and -Werror=foo) from every makefile in a kernel tree.

Android 12 era Exynos/Samsung trees carry -Werror in a few subdirectory
Makefiles. Modern GCC (>= 11) trips over pre-existing warnings that the
original 2017/2018 toolchain ignored, and -Werror turns those into hard build
failures. The shipped defconfigs are unchanged by this, it only relaxes the
warning policy so the tree compiles with a current compiler.
"""
import os
import re
import sys


def main() -> int:
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    count = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in (".git", "out", ".repo")]
        for name in files:
            if not (name.startswith("Makefile") or name.startswith("Kbuild")
                    or name.endswith(".mk")):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", errors="ignore") as fh:
                    content = fh.read()
            except OSError:
                continue
            if "-Werror" not in content:
                continue
            with open(path, "w") as fh:
                fh.write(re.sub(r"-Werror[=a-zA-Z0-9_-]*", "", content))
            count += 1
    print("   -Werror stripped from %d makefiles" % count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
