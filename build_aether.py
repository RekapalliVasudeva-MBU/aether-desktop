"""PyInstaller build for the frozen Aether desktop app (--onedir, windowed).

--onedir (not --onefile) is intentional: a onefile build unpacks to a random
%TEMP%\_MEIxxxx folder at every launch, which antivirus (Defender) frequently
blocks/quarantines -> "0xc0000142 / application was unable to start". With
--onedir the files live permanently in the install dir, so there is no
runtime temp-unpack step and no AV trigger. Inno Setup packages this folder.

Build:
    python build_aether.py
Produces: dist/Aether/  (Aether.exe + all DLLs/support files)
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    out_dir = os.path.join(HERE, "dist_build", "Aether")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "Aether",
        "--paths", HERE,
        # UI assets the app serves at runtime
        "--add-data", os.path.join(HERE, "desktop_ui") + os.pathsep + "desktop_ui",
        # Typical hidden imports for this stack
        "--hidden-import", "webview",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "winshell",
        # Heavy ML packages pulled in transitively (docling/huggingface hooks) but
        # NOT used by our runtime path. Excluding them shrinks the build from
        # ~700MB to a sane size and avoids the Inno bootloader 0xc0000005 crash
        # triggered by the huge file tree.
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "torchaudio",
        "--exclude-module", "transformers",
        "--exclude-module", "tokenizers",
        "--exclude-module", "safetensors",
        "--exclude-module", "sentencepiece",
        "--exclude-module", "huggingface_hub",
        "--exclude-module", "timm",
        "--exclude-module", "accelerate",
        "--exclude-module", "cv2",
        "--exclude-module", "onnxruntime",
        "--distpath", os.path.join(HERE, "dist_build"),
        "--workpath", os.path.join(HERE, "build_aether"),
        os.path.join(HERE, "build_entry.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Built onedir app at: {out_dir}")


if __name__ == "__main__":
    main()
