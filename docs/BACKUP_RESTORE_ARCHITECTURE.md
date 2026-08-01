# Backup, Export, Restore, and Verification Architecture

## Status

Planned for The Foreman v0.7.4.

This document defines the recovery contract before implementation begins.
Backup and restore must be deterministic, verifiable, and safe against
corruption, incompatible data, interrupted operations, and failed restores.

## Purpose

The Foreman is an external working memory and continuity system.

Its database preserves the operational state of Projects, Tasks, Inventory,
material requirements, migration history, responsibilities, and progress.
Creating a backup file is not sufficient. The Foreman must be able to prove
that the artifact is complete, internally consistent, compatible, and
restorable.

## Audit findings

The current authoritative application database is configured through
`FOREMAN_DATABASE_URL`.

The deployed default is:

`/data/foreman.db`

The database is stored in the Compose `foreman-data` volume.

The live v0.7.3 audit confirmed:

- SQLite journal mode: `delete`
- SQLite `user_version`: `2`
- Integrity check: `ok`
- Foreign-key violations: none
- No active WAL, shared-memory, or rollback-journal files
- No separate upload, attachment, image, or document storage

Current non-system tables are:

- `inventory_items`
- `inventory_migrations`
- `project_material_requirements`
- `project_migrations`
- `projects`
- `task_migrations`
- `tasks`

Migration tables are part of the authoritative database state and must be
preserved automatically.

## Browser-local state

Browser-local Project, Task, and Inventory records are retained only as legacy
migration sources.

Current operational authority belongs to the backend database. Browser-local
migration records and device-local migration provenance are not included in
an application backup.

The backup must not claim to preserve legacy browser records that have not
been migrated into the backend.

## Backup package format

Backup format version 1 uses:

`foreman-backup-YYYYMMDDTHHMMSSZ.zip`

The archive contains exactly:

- `manifest.json`
- `foreman.db`

Archive members must not contain absolute paths, parent-directory traversal,
symbolic links, duplicate names, or unexpected files.

## Manifest contract

The manifest must contain:

- `backupFormatVersion`
- `applicationName`
- `applicationVersion`
- `createdAt`
- `operationalFactSchemaVersion`
- `database`
- `recordCounts`

The database section must contain:

- `filename`
- `byteSize`
- `sha256`
- `userVersion`
- `integrityCheck`
- `foreignKeyViolationCount`
- `tables`

Requirements:

- Backup format version begins at numeric `1`.
- Creation time uses UTC ISO 8601.
- Database filename is exactly `foreman.db`.
- SHA-256 uses lowercase hexadecimal.
- Integrity must equal `ok`.
- Foreign-key violation count must equal zero.
- Table names and record-count keys use deterministic ordering.
- No credentials, host paths, volume names, IP addresses, or secrets appear
  in the manifest.

## Explicit exclusions

An application backup must not contain:

- `.env`
- credentials or authentication secrets
- TLS certificates or private keys
- Caddy private CA state
- Caddy configuration volumes
- Git repository data
- Docker images
- container logs
- temporary files
- browser-local migration sources
- browser-local migration provenance

Infrastructure recovery requires a separate HardHead server-recovery
procedure.

## Backup creation

The backend must not copy a live SQLite file directly.

Backup creation must:

1. Resolve the configured SQLite database.
2. Create work inside controlled temporary storage.
3. Use SQLite's supported online backup API.
4. Close the snapshot connection before packaging.
5. Run `PRAGMA integrity_check` against the snapshot.
6. Run `PRAGMA foreign_key_check` against the snapshot.
7. Read `PRAGMA user_version`.
8. Enumerate non-system tables deterministically.
9. Record deterministic table counts.
10. Calculate byte size and SHA-256.
11. Write the manifest.
12. Create a temporary ZIP package.
13. Reopen and independently verify the package.
14. Atomically rename it to the final filename.
15. Remove temporary files after success or failure.

A backup is not successful until independent verification passes.

## Verification

Package verification confirms:

- The archive is readable.
- Required members exist exactly once.
- No unsafe or unexpected members exist.
- The manifest is valid UTF-8 JSON.
- The backup format is supported.
- Declared file size matches.
- The database checksum matches.

Database verification confirms:

- SQLite can open the extracted database.
- Integrity check returns `ok`.
- Foreign-key check returns no rows.
- Database `user_version` is supported.
- Required tables exist.
- Manifest table names match the database.
- Manifest record counts match the database.

## Export

Export is separate from backup.

An export provides portable, human-readable JSON or CSV. It may omit migration
metadata or database-specific structure.

An export must never be presented as a complete restore artifact unless a
separate import workflow is explicitly designed and validated.

## Restore preflight

Restore must validate the candidate without modifying live state.

Preflight must:

1. Copy the selected package into controlled temporary storage.
2. Verify the archive and manifest.
3. Extract only approved members.
4. Verify the candidate database.
5. Check compatibility.
6. Apply supported schema upgrades only to a temporary candidate.
7. Reverify the upgraded candidate.
8. Present a deterministic restore summary.
9. Require explicit confirmation before activation.

The original backup artifact must remain unchanged.

## Pre-restore safety backup

Immediately before replacement, The Foreman must create and verify a backup of
the current live database.

The durable safety-backup workspace is derived from the live database path.
For the deployed `/data/foreman.db`, verified safety packages are retained in:

`/data/recovery/safety-backups/`

The `recovery` and `safety-backups` directories use mode `0700`. Published
safety-backup packages use mode `0600`. The workspace must be on the same
filesystem as the live database, and the package and containing directories
must be synchronized before activation may continue.

Restore must stop when that safety backup cannot be created, synchronized, and
independently verified.

## Maintenance boundary

Restore activation requires exclusive maintenance mode.

During maintenance:

- New database writes are rejected.
- Operational reads may return a stable maintenance response.
- Active database work finishes or is safely terminated.
- SQLAlchemy sessions are closed.
- Pooled connections are disposed.
- No request may reopen the old database during replacement.

## Atomic replacement and rollback

The verified candidate must be placed on the same filesystem as the active
database before activation.

Replacement must use an atomic filesystem operation.

After replacement, The Foreman must verify:

- Database initialization
- Integrity
- Foreign keys
- Required tables
- Record counts
- Health endpoint
- Operational-fact calculation

If activation or verification fails, The Foreman must atomically restore the
pre-restore database and verify the rollback.

Activation owns the exclusive maintenance boundary from the final candidate
check through post-replacement verification. The activated database must pass
schema initialization, integrity and foreign-key inspection, required-table
and record-count comparison, a direct database health probe, and operational-
fact calculation before normal access resumes.

If rollback also fails, the maintenance coordinator enters an emergency latch.
The latch keeps all database-backed routes unavailable after the restore call
returns. The durable safety package and activation workspace are retained for
explicit operator recovery; normal access cannot resume until the emergency
latch is deliberately cleared after repair.

## Compatibility

Compatibility must consider:

- Backup format version
- Database `user_version`
- Required tables
- Database integrity
- Foreign-key integrity
- Supported schema-upgrade path

A backup from an unsupported future database version must be rejected.

Operational facts are derived data. Their schema version may be recorded for
diagnostic context, but facts are not persisted in a backup table.

## Initial non-goals

v0.7.4 does not include:

- Cloud backup
- Off-site synchronization
- Continuous replication
- Multi-device database merging
- Encrypted account recovery
- Automatic conflict resolution
- Fact history
- AI interpretation
- Caddy private-CA recovery
- Operating-system recovery

## Implementation order

1. Architecture and recovery contract
2. Manifest and verification schemas
3. Pure package and checksum utilities
4. Consistent SQLite backup creation
5. Independent backup verification
6. Portable data export
7. Restore staging and compatibility validation
8. Maintenance boundary
9. Pre-restore safety backup
10. Atomic restoration and rollback
11. User interface
12. Destructive and browser validation
13. Release finalization

No destructive restore behavior may be exposed before the preceding safety
layers are complete and tested.
