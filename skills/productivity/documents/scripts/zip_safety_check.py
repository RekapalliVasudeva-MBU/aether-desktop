#!/usr/bin/env python3
"""Safety-check a zip file before extraction.

Usage:
    python zip_safety_check.py <path_to_zip>

Exit codes:
    0 = safe (no threats found)
    1 = threats detected
    2 = error opening zip
"""

import sys
import zipfile

DANGEROUS_EXTS = (
    ".exe", ".bat", ".cmd", ".ps1", ".vbs", ".js", ".msi",
    ".dll", ".scr", ".com", ".wsf", ".hta", ".cpl", ".inf", ".reg",
)

def check_zip(path: str) -> list[str]:
    """Return list of threat descriptions. Empty = safe."""
    threats = []
    try:
        with zipfile.ZipFile(path, "r") as z:
            total_uncompressed = 0
            for info in z.infolist():
                total_uncompressed += info.file_size
                fn = info.filename
                # Path traversal
                if fn.startswith("..") or (len(fn) > 1 and fn[1] == ":"):
                    threats.append(f"PATH TRAVERSAL: {fn}")
                # Zip bomb (extreme compression ratio)
                if info.file_size > 0 and info.compress_size / info.file_size < 0.03:
                    threats.append(f"ZIP BOMB SUSPECT: {fn} (ratio {info.compress_size/info.file_size:.4f})")
                # Executables
                if fn.lower().endswith(DANGEROUS_EXTS):
                    threats.append(f"EXECUTABLE [{fn.rsplit('.', 1)[1].upper()}]: {fn} ({info.file_size} bytes)")
            # Final summary
            print(f"Files: {len(z.namelist())}")
            print(f"Uncompressed size: {total_uncompressed / 1024 / 1024:.1f} MB")
    except zipfile.BadZipFile:
        threats.append("BAD ZIP FILE — cannot open")
    except Exception as e:
        threats.append(f"ERROR: {e}")
    return threats


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <zip_path>")
        sys.exit(2)
    threat_list = check_zip(sys.argv[1])
    if threat_list:
        print("THREATS FOUND:")
        for t in threat_list:
            print(f"  - {t}")
        sys.exit(1)
    else:
        print("SAFE — no threats detected")
        sys.exit(0)
