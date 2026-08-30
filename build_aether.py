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
    import shutil as _shutil
    pkg_dst = os.path.join(HERE, "chromadb_pkg")
    if not os.path.isdir(pkg_dst):
        try:
            import chromadb
            pkg_src = os.path.dirname(chromadb.__file__)
            _shutil.copytree(pkg_src, pkg_dst)
        except Exception as e:
            print(f"[notice] Using bundled/vendored chromadb_pkg: {e}")

    out_dir = os.path.join(HERE, "dist_build", "Aether")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "Aether",
        "--icon", os.path.join(HERE, "desktop_ui", "logo.ico"),
        "--paths", HERE,
        # UI assets the app serves at runtime
        "--add-data", os.path.join(HERE, "desktop_ui") + os.pathsep + "desktop_ui",
        # Hidden imports for Aether engine & dependencies
        "--hidden-import", "aether",
        "--hidden-import", "aether.config",
        "--hidden-import", "aether.agent",
        "--hidden-import", "aether.tools",
        "--hidden-import", "aether.skills",
        "--hidden-import", "aether.rag",
        "--hidden-import", "aether.memory",
        "--hidden-import", "aether.orchestrator",
        "--hidden-import", "aether.burr_orchestrator",
        "--hidden-import", "aether.gateway_ctl",
        "--hidden-import", "aether.telegram",
        "--hidden-import", "aether.pdf_store",
        "--hidden-import", "aether.compression",
        "--hidden-import", "aether.provider",
        "--hidden-import", "aether.mcp",
        "--hidden-import", "openai",
        "--hidden-import", "httpx",
        "--hidden-import", "pypdf",
        "--hidden-import", "dotenv",
        "--hidden-import", "webview",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "win32com",
        "--hidden-import", "win32com.client",
        "--hidden-import", "winshell",
        # chromadb: bundle the WHOLE package (incl. native rust bindings +
        # telemetry submodules) as data so no dynamically-imported submodule
        # is missed at runtime (RAG mode needs them all).
        "--add-data", os.path.join(HERE, "chromadb_pkg") + os.pathsep + "chromadb",
        "--hidden-import", "chromadb_rust_bindings",
        "--hidden-import", "tokenizers",
        "--hidden-import", "onnxruntime",
        # Heavy ML packages pulled in transitively (docling/huggingface hooks) but
        # NOT used by our runtime path. Excluding them shrinks the build from
        # ~700MB to a sane size and avoids the Inno bootloader 0xc0000005 crash
        # triggered by the huge file tree.
        # NOTE: tokenizers/onnxruntime are NOT excluded — chromadb's rust index
        # API imports them at runtime (RAG mode needs them).
        "--exclude-module", "torch",
        "--exclude-module", "torchvision",
        "--exclude-module", "torchaudio",
        "--exclude-module", "transformers",
        "--exclude-module", "safetensors",
        "--exclude-module", "sentencepiece",
        "--exclude-module", "huggingface_hub",
        "--exclude-module", "timm",
        "--exclude-module", "accelerate",
        "--exclude-module", "cv2",
        "--exclude-module", "scipy",
        "--exclude-module", "pandas",
        "--exclude-module", "sklearn",
        "--exclude-module", "scikit_learn",
        "--exclude-module", "matplotlib",
        "--exclude-module", "docling_parse",
        "--exclude-module", "docling",
        "--exclude-module", "sympy",
        "--exclude-module", "IPython",
        "--exclude-module", "ipykernel",
        "--distpath", os.path.join(HERE, "dist_build"),
        "--workpath", os.path.join(HERE, "build_aether"),
        os.path.join(HERE, "desktop_app.py"),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)
    print(f"Built onedir app at: {out_dir}")


if __name__ == "__main__":
    main()
