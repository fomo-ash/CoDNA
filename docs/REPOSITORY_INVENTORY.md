# Repository Inventory and File Discovery

> **Status:** Current implementation
> **Last reviewed:** 2026-07-20

## Purpose

Inventory is the first persisted analysis stage after cloning. It provides a safe, owner-scoped file catalog and the change signal that drives incremental parsing, knowledge extraction, and chunk rebuilding.

## Runtime role

```text
Celery index task
  ↓
Clone repository
  ↓
Discover safe files and calculate hashes
  ↓
Synchronize repository_files and repository_statistics
  ↓
Determine changed and removed paths
  ↓
Parse changed supported files
  ↓
Rebuild knowledge, chunks, and relationships for affected paths
```

Inventory is not the final stage. The same indexing worker continues into parsing, knowledge extraction, semantic chunks, history refresh, and—when configured—a separate embedding job.

## Persisted records

`repository_files` stores one row for each discovered file:

- repository-relative path, filename, extension, language hint;
- size, SHA-256 hash, and binary flag;
- discovery and update timestamps.

`repository_statistics` stores the latest aggregate counts for a repository: total files, source files, binary files, total bytes, language counts, and last scan time. Statistics are persisted instead of recomputed for every request.

The inventory model is linked to parse, knowledge, and chunk records through `repository_file_id` where applicable.

## Discovery policy

Discovery ignores VCS, dependency, generated-output, editor, and virtual-environment directories, including `.git`, `node_modules`, `dist`, `build`, `.next`, `coverage`, `__pycache__`, `venv`, `.venv`, `.idea`, `.vscode`, `target`, and `vendor`.

Known binary assets and archives are skipped. Other binary files can be inventoried with `is_binary=true` but are not parsed as source. Secret-like environment files and symlinks are excluded. The default maximum scanned file size is 10 MiB, controlled by `REPOSITORY_FILE_MAX_BYTES`.

The discovery layer is filesystem-only; persistence remains in the inventory service. That keeps discovery reusable and prevents file-walking code from owning database policy.

## API

All inventory endpoints require the caller to own the repository.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/repositories/{repository_id}/files` | Paginated file catalog |
| `GET /api/v1/repositories/{repository_id}/stats` | Persisted aggregate inventory statistics |

The file endpoint supports `page`, `page_size`, `language`, `extension`, and `path_prefix`. It returns metadata only: it never exposes worker clone paths or source file contents.

## Incremental behavior

Each scan compares the discovered state with persisted inventory. Changed hashes and removed paths identify work that must be rebuilt. Relationship edges can add known dependent paths to the affected set before chunk rebuilding.

An unchanged re-index does not recreate every parse, knowledge item, or chunk. This makes re-indexing cheaper while retaining a complete persisted catalog.

## Related layers

- [API.md](API.md) documents list, filter, and response contracts.
- [ARCHITECTURE.md](ARCHITECTURE.md) describes the complete worker pipeline.
- [REPOSITORY_REGISTRATION.md](REPOSITORY_REGISTRATION.md) describes ownership and job creation.
