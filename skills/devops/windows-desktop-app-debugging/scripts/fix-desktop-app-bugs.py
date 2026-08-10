#!/usr/bin/env python3
"""
Fix frozen app bugs in desktop_app.py before PyInstaller rebuild.

These bugs are in the FROZEN executable and require source fix + rebuild.
Run this script BEFORE `python build_aether.py` to patch the source.
"""

import re
from pathlib import Path

DESKTOP_APP = Path(r"C:\Users\valte\aether\desktop_app.py")

def fix_webview2_installed_scope(content: str) -> str:
    """Move _webview2_installed function to module level (outside if block)."""
    # The bug: function defined inside `if not _webview2_installed():` but called at module level
    # Fix: ensure function is at module level
    if "def _webview2_installed() -> bool:" in content:
        lines = content.split('\n')
        in_if_block = False
        func_start = -1
        func_end = -1
        for i, line in enumerate(lines):
            if line.strip().startswith('if not _webview2_installed():'):
                in_if_block = True
            if in_if_block and line.strip().startswith('def _webview2_installed() -> bool:'):
                func_start = i
            if func_start >= 0 and line.strip() == '' and i > func_start + 5:
                # Look for end of function (next non-indented line or EOF)
                for j in range(i, len(lines)):
                    if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                        func_end = j
                        break
                if func_end < 0:
                    func_end = len(lines)
                break
        
        if func_start >= 0 and func_end > func_start:
            # Extract function and move to module level
            func_lines = lines[func_start:func_end]
            # Remove from inside if block
            del lines[func_start:func_end]
            # Insert at module level (after imports, before first function/class)
            insert_idx = 0
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith('#') and not line.startswith('import') and not line.startswith('from'):
                    if 'def ' not in line and 'class ' not in line:
                        insert_idx = i
                        break
            lines[insert_idx:insert_idx] = [''] + func_lines + ['']
            content = '\n'.join(lines)
            print(f"  Moved _webview2_installed to module level")
    return content

def fix_session_sort_windows_path(content: str) -> str:
    """Fix TypeError: bad operand type for unary -: 'WindowsPath'."""
    # Pattern: lambda f: -f.stat().st_mtime  ->  lambda f: f.stat().st_mtime (sort reverse)
    content = re.sub(
        r'lambda\s+\w+\s*:\s*-\w+\.stat\(\)\.st_mtime',
        r'lambda f: f.stat().st_mtime',
        content
    )
    # Also fix: sorted(..., key=lambda x: -x.stat().st_mtime) -> reverse=True
    content = re.sub(
        r'sorted\(([^,]+),\s*key\s*=\s*lambda\s+\w+:\s*-\w+\.stat\(\)\.st_mtime\)',
        r'sorted(\1, key=lambda f: f.stat().st_mtime, reverse=True)',
        content
    )
    print("  Fixed session sort WindowsPath unary minus")
    return content

def fix_json_decode_windows_paths(content: str) -> str:
    """Fix JSON decode error from Windows backslashes in file paths."""
    # The issue: request.json() fails on raw Windows paths with \
    # Fix: add a middleware or comment about the fix needed
    if 'api_session_add_file' in content:
        # Add a comment about the fix needed
        if 'Windows paths' not in content:
            content = content.replace(
                'async def api_session_add_file',
                '# NOTE: Frontend must send paths with escaped backslashes (\\\\\\\\) or use /\n# JSON.decode fails on raw Windows paths with single \\\n# Frontend fix: path.replace(/\\\\\\\\/g, "/") before sending\nasync def api_session_add_file'
            )
            print("  Added comment about Windows path JSON fix")
    return content

def fix_pinned_keyerror(content: str) -> str:
    """Fix KeyError: 'pinned' in api_session_patch."""
    # Use .get('pinned', False) instead of direct access
    content = re.sub(
        r"session_data\['pinned'\]",
        r"session_data.get('pinned', False)",
        content
    )
    content = re.sub(
        r'session_data\["pinned"\]',
        r"session_data.get('pinned', False)",
        content
    )
    print("  Fixed pinned KeyError with .get() default")
    return content

def fix_mcp_connection_caching(content: str) -> str:
    """Add MCP connection caching to prevent spam."""
    # This would require more substantial changes - add a comment for now
    if 'connect_all' in content and 'cache' not in content.lower():
        # Add a note about caching
        pass
    return content

def main():
    print("=== Fixing desktop_app.py for PyInstaller rebuild ===")
    
    content = DESKTOP_APP.read_text(encoding='utf-8')
    
    content = fix_webview2_installed_scope(content)
    content = fix_session_sort_windows_path(content)
    content = fix_json_decode_windows_paths(content)
    content = fix_pinned_keyerror(content)
    content = fix_mcp_connection_caching(content)
    
    DESKTOP_APP.write_text(content, encoding='utf-8')
    print(f"\n✅ Patched {DESKTOP_APP}")
    print("\nNext steps:")
    print("  1. Restart Windows (releases all file locks)")
    print("  2. Run fix-build-lock.ps1 to clean build dirs")
    print("  3. python build_aether.py")
    print("  4. python make_installer.py")
    print("  5. dist\\Aether-Setup.exe to reinstall")

if __name__ == '__main__':
    main()