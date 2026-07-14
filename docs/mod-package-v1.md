# MOD package format v1

A `.modpkg` is a ZIP archive. Version 1 requires these exact metadata files:

- `plugin.json`
- `files.json`
- `plugin.sig`

Every other regular file must be listed in `files.json` with a SHA-256 digest.
Paths are POSIX-style, case-insensitively unique, relative, and must not contain
Windows reserved names, alternate data stream separators, symbolic links, or
executable installer formats.

`plugin.sig` is an Ed25519 signature over this exact byte sequence:

```text
"MediaManager-MOD-v1\\0"
+ uint64_be(len(plugin.json)) + raw_plugin_json_bytes
+ uint64_be(len(files.json))  + raw_files_json_bytes
```

The raw bytes are signed; producers must not reformat either JSON file after
signing. Public keys are raw 32-byte Ed25519 keys encoded as Base64, optionally
prefixed with `ed25519:`. Signatures may be raw 64-byte values or Base64 text.

Executable plugins must declare a relative `.py` entry point included in
`files.json`. A `data-only` plugin must use an empty `entry_point`.

Installation is allowed in `NORMAL` and `SAFE_MODE`, always disabled by default.
`BLOCKED` mode rejects installation. Enabling requires `NORMAL` and repeats the
signature, manifest, declared-file, symlink, and undeclared-file checks.
The installer rejects packages whose `minimum_core_version` / `maximum_core_version`
range does not include the running core version. Every ID in `dependencies` must
already be installed; version-constrained dependency resolution is not part of v1.
## Updates

An update must keep the same plugin ID and publisher, use a SemVer version newer
than the installed version, pass the complete install verification again, and
receive explicit approval for its resulting permission set. The running plugin
is stopped first. The previous version is moved atomically to
`mod/backups/<plugin-id>/<version>`; a failed filesystem or Registry transaction
restores it. A successful update remains disabled until explicitly enabled.
## Interrupted transaction recovery

Before replacing an installed directory, update and rollback operations persist an
`UPDATE` or `ROLLBACK` journal state. On the next startup, MediaManager verifies
the registered version and restores it as the safe baseline. An interrupted new
version is retained as a backup. Ambiguous, missing, tampered, or path-escaping
state cannot be guessed safely and changes the application security mode to
`BLOCKED` before any plugin can start.
## Removal and permanent cleanup

Normal removal is reversible: the disabled plugin is moved to
`mod/quarantine/removed/<plugin-id>/<version>` and its Registry row remains in
`REMOVE` state. Permanent cleanup is a separate, explicit trusted-UI action with
an irreversible confirmation. It can delete one retained backup, or delete a
removed plugin together with all of its backups.

Full cleanup uses a `PURGE` journal and atomically stages data under
`mod/quarantine/purge/<sha256(plugin-id)>` before deleting the Registry row. If
startup finds an active `PURGE` row, it restores staged data and returns the row
to reversible `REMOVE` state. A staging directory without a Registry row means
the commit completed and is erased as orphaned cleanup data.

## Declarative MOD pages

An enabled plugin may include `ui.json` in its signed `files.json` inventory. The
trusted UI renders it only inside the plugin manager's `MOD pages` tab. Schema v1
accepts an exact object containing `schema_version`, `page_id`, `title`, and up to
40 static `heading`, `text`, or `status` blocks. HTML, URLs, scripts, Qt objects,
and callback declarations are not accepted. The complete installed plugin is
verified again immediately before the descriptor is read and rendered.
