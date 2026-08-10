# Eclipse Java Project Silent Failure — Reproduction and Fix

## Symptom
- Right-click Java file → "Run As Java Application" → `Error occurred during initialization of boot layer` / `java.lang.module.FindException: Module X not found`
- Or: `bin/` directory is empty after a build (Eclipse produces no `.class` files)
- Or: `.classpath` shows red "JRE System Library [JavaSE-26]" (unbound container)

## Root Cause
Eclipse stores compiler target version in **two** config files — both must match the available JRE:

1. **`.classpath`** — `JRE_CONTAINER` path must reference a JRE that exists
2. **`.settings/org.eclipse.jdt.core.prefs`** — `source`, `targetPlatform`, `compliance` must all be ≤ the available JRE's major version

If either is set higher than what's available (e.g. JavaSE-26 when only JRE 21 is bundled), the compiler silently produces no bytecode and `bin/` stays empty.

## Diagnostic Checklist

1. `.classpath` → check `JRE_CONTAINER` path for version number
2. `.settings/org.eclipse.jdt.core.prefs` → grep for `source`, `targetPlatform`, `compliance`
3. Check if source files are empty (`find src -name "*.java" -empty`)
4. Check `module-info.java` if present — module name must match Eclipse's run config

## Fix (example: change from 26 to 21)

Edit `.settings/org.eclipse.jdt.core.prefs`:
- `org.eclipse.jdt.core.compiler.codegen.targetPlatform=26` → `=21`
- `org.eclipse.jdt.core.compiler.compliance=26` → `=21`
- `org.eclipse.jdt.core.compiler.source=26` → `=21`

Also fix `.classpath`:
- `JRE_CONTAINER/.../JavaSE-26` → `JavaSE-21`

## Pitfall: Duplicate Keys in `.prefs`
Java `.prefs` files use **last-wins** semantics. If a duplicate `source=26` appears AFTER your fix `source=21`, the 26 wins silently. Always grep the entire file for all occurrences of the key.