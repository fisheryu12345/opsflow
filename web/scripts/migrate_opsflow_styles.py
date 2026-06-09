#!/usr/bin/env python
"""Move opsflow-global.scss and opsflow-variables.scss to web/src/styles/"""

import glob
import os
import re
import shutil

SRC = "src/views/apps/opsflow/styles"
DST = "src/styles"

def main():
    # Step 1: Copy files
    for fname in ["opsflow-global.scss", "opsflow-variables.scss"]:
        shutil.copy2(f"{SRC}/{fname}", f"{DST}/{fname}")
        print(f"[OK] Copied {fname} -> {DST}/")

    # Step 2: Update internal comment in opsflow-global.scss
    path = f"{DST}/opsflow-global.scss"
    with open(path, "r", encoding="utf-8") as fh:
        content = fh.read()
    content = content.replace(
        "// Import via: @use '../styles/opsflow-global' as *;",
        "// Import via: @use 'opsflow-global' as *;"
    )
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    print("[OK] Updated internal comment")

    # Step 3: Find all files that reference these
    files = {}
    for pattern in ["**/*.vue", "**/*.scss"]:
        for fp in glob.glob(f"src/**/{pattern}", recursive=True):
            if "node_modules" in fp:
                continue
            with open(fp, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            if "opsflow-global" in text or "opsflow-variables" in text:
                files[fp] = text

    print(f"\nFound {len(files)} files to update")

    # Step 4: For each file, calculate correct relative path
    root = os.path.abspath("src")
    for fp in sorted(files.keys()):
        content = files[fp]
        original = content

        # Get file's parent directory relative to src/
        abs_fp = os.path.abspath(fp)
        parent = os.path.dirname(abs_fp)
        # Walk up from parent to find how many steps to reach src/
        rel = os.path.relpath(parent, root)
        # Number of "../" needed
        up_count = len(rel.split(os.sep))

        # Build the relative prefix
        prefix = "../" * up_count

        # Replace opsflow-global refs
        for tgt in ["opsflow-global", "opsflow-variables"]:
            # Match any @use '...tgt' as *; pattern
            pattern = r"@use\s+'[^']*" + re.escape(tgt) + r"[^']*'\s+as\s+\*;"
            replacement = f"@use '{prefix}{tgt}' as *;"
            content = re.sub(pattern, replacement, content)

        if content != original:
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"  [OK] {fp}")
        else:
            print(f"  [--] {fp}")

    print("\n[DONE] Migration complete")


if __name__ == "__main__":
    main()
