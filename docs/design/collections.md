# Collections — personal folders of rules and bundles

Private folders (only the owner sees them) where a user keeps rules and bundles
with **a note** (why I keep it), **a status** (to do / in progress / done) and
**a reminder** (a notification on the chosen day).

Use cases: "To fix" (a rule with a change request or a false positive, a
reminder to check the answer), "To test", "To review", "Reading list",
an incident or CVE working set (download the folder's rules in one click).

## Pieces
- Models `app/core/db_class/collection.py`: `UserCollection` (nested by
  `parent_id`, icon, color, position), `UserCollectionItem` (rule_id or
  bundle_id, note, status, remind_at, reminded_at). Migration `03d507bd10ab`.
- Logic `app/features/collection/collection_core.py`, routes
  `collection.py` (`/collection/api/*`, logged-in only, every
  query scoped to `current_user`).
- Setting `app/config/collection.json` (public): default folders created on the
  first visit, statuses, icons, colors, limits.
- Reminders: `fire_due_reminders()` called by the task-scheduler ticker
  (`scheduler_engine.tick`) — one `collection_reminder` notification, once;
  the link opens the folder with the item highlighted.
- Front end:
  - `static/js/components/CollectionPicker.js` — reusable "Add to folder"
    dialog (one rule/bundle: shows and edits its folders; several: bulk add).
    Used on the rule and bundle detail pages and as the "Add to folder" bulk
    action of the My rules lists.
  - `static/js/collection/` — `CollectionBrowser` (KPIs, smart views All /
    Reminders due / Upcoming, tree, filters, bulk status/move/remove),
    `CollectionTree` (recursive, drop an item on a folder to move it),
    `CollectionItem` (inline note / status / reminder / move), `FolderDialog`.
  - Only in the "My Folders" tab of My rules (`/rule/owner_rules?tab=folders`);
    `/collection/` redirects there (reminder links, old bookmarks). No menu entry.

## Later
Watch (alert when a kept rule changes), smart folders (saved filters),
dashboard widget for due reminders.
