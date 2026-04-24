# Tile Deletion / Rebuild Issue

## Current problem

We currently mix two different concepts:

1. deleting a rendered tile from the graph UI
2. deleting or invalidating the underlying domain result represented by that tile

That creates unstable behavior, especially for non-administration norm addressees and for downstream tiles that depend on an intermediate tile.

## Confirmed implementation mismatch

- Deleting a tile in the graph removes rows only for the selected `(session_id, norm_addressee)` in `tiles` and `links`.
- The session menu action `Kacheln dieser Session neu laden` previously called `rebuildTiles(appSessionId)` without passing `norm_addressee`.
- Backend `/tiles/rebuild` defaults to `administration` when `norm_addressee` is missing.

Result: rebuilding from business or citizens view could rebuild the wrong tile set.

## Short-term stabilization

- Pass the selected `norm_addressee` in frontend rebuild calls.
- Keep backend tile rebuild scoped to the requested norm addressee.
- Disable tile deletion in the UI for now.

Reason: the expected semantics of deleting an intermediate tile are not defined well enough yet.

## Open product / workflow questions

1. Is tile deletion only a visual hide action, or should it remove the underlying result?
2. If an intermediate tile is deleted, should downstream tiles be deleted as well?
3. Should session reload always restore all derivable tiles from DB state?
4. Should rerun / recompute recreate deleted tiles automatically?
5. Do we want separate actions for:
   - hide tile
   - delete derived result
   - rerun from this step

## Recommended next design step

Design tile lifecycle explicitly before re-enabling deletion:

- define whether tiles are views or editable data artifacts
- define cascade behavior for dependent tiles
- define how rebuild, rerun, and undo interact with deleted or hidden tiles
- then re-enable deletion with tests for all norm addressees
