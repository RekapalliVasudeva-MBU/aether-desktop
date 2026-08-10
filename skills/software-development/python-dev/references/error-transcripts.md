# Error Transcripts — Python Env Troubleshooting

## Read-Only Conda Env — Full Error

```
EnvironmentNotWritableError: The current user does not have write permissions to the target environment.
  environment location: C:\ProgramData\anaconda3\envs\ai_env
```

Folder permissions: `BUILTIN\Users:(I)(OI)(CI)(RX)` — read+execute only, no write.

**Fix**: `python -m pip install --user <package>` → installs to `%APPDATA%\Python\Python314\site-packages`

---

## pyzmq DLL Load Failure — Full Traceback

```
File "...\zmq\backend\cython\__init__.py", line 6, in <module>
    from . import _zmq
ImportError: DLL load failed while importing _zmq: The specified module could not be found.
```

`libzmq.dll` and `_zmq.pyd` both existed on disk. The pyd was compiled against a different libzmq version.

**Fix**: `python -m pip install --user --force-reinstall pyzmq`

---

## HFValidationError for Local Path

```
huggingface_hub.errors.HFValidationError: Repo id must use alphanumeric chars, '-', '_' or '.'. 
The name cannot start or end with '-' or '.' and the maximum length is 96: './saved_summary_model'.
```

**Cause**: Relative path `./saved_summary_model` fails HF's repo ID validation.

**Fix**: Use `os.path.abspath()` or `os.path.dirname(os.path.abspath(__file__))` to build absolute paths.

---

## Git Commit Message with Spaces — Full Error

```
error: pathspec 'commit:' did not match any file(s) known to git
error: pathspec 'T5' did not match any file(s) known to git
```

**Cause**: `subprocess.run(["git", "commit", "-m", "message with spaces"])` — subprocess splits on spaces when shell=False.

**Fix**: Use `shell=True` or avoid spaces in the message.
