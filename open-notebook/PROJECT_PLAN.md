# Project Plan

Date: 2026-06-23

## Overhaul Goals

- Fix the most important backend safety and reliability issues.
- Restore useful command and agent management behavior.
- Align the frontend with a NotebookLM-inspired research workspace.
- Remove visible English residue from the primary UI.
- Restore a reliable build path for the desktop EXE.

## Work Items

### Backend

1. Implement real command job listing from SurrealDB.
2. Make command cancellation explicit and truthful.
3. Improve command-module import logging.
4. Harden build-task execution to avoid arbitrary shell execution.
5. Use constant-time password comparison in auth.
6. Make auth behavior explicit when no password is configured.
7. Fix MoneyPrinterTurbo launch and health handling.
8. Close the MPT log file handle after spawn.
9. Repair or align the PyInstaller spec with current assets.

### Frontend

10. Simplify the global app shell into a calm NotebookLM-like workspace.
11. Update sidebar hierarchy and spacing.
12. Make the page header lighter and more paper-like.
13. Rework the most visible pages for consistency.
14. Replace visible English labels in the dashboard surface.
15. Make settings and tool pages visually consistent with the main workspace.

### Validation

16. Add or update targeted tests for command, auth, and agent flows.
17. Run frontend lint and build checks.
18. Run backend test subsets around the changed services.

## Notes

- The multi-agent persistence layer is intentionally not part of this pass.
- The visual target is NotebookLM-inspired, not a literal clone.
- Existing unrelated worktree changes should be preserved.
