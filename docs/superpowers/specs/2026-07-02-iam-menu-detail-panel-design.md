# IAM Menu Detail Panel — Design Spec

## Context

The IAM page's Menu tab currently has a left-side tree (MenuTreeCom) but the right panel is empty — it shows only a placeholder message saying button permission management was migrated to IAM role assignment. Users can add/edit menus via a drawer form, but there is no way to view a selected menu's details or toggle its status/visibility without opening the full edit form.

**Goal**: Replace the empty right panel with a read-while-editable detail panel that shows all menu fields, with inline toggle switches for boolean fields and quick access to edit/delete/sort.

## Approach

Single Vue component (`MenuDetailPanel`) with inline edit capability — no new backend APIs needed. The existing `GET /api/iam/menu/{id}/` returns all fields via `MenuSerializer` (`fields = "__all__"`), and `PUT /api/iam/menu/{id}/` already handles partial updates.

## Architecture

### Components

```
web/src/views/apps/iam/admin/menu/
  index.vue                           ← Modify: replace empty right panel with MenuDetailPanel
  components/
    MenuTreeCom/index.vue             ← Unchanged (already emits treeClick with full record)
    MenuFormCom/index.vue             ← Unchanged (existing drawer form)
    MenuDetailPanel/
      index.vue                       ← NEW: detail panel component
```

### Data Flow

```
Tree node click
  → MenuTreeCom @treeClick(record) emits full MenuTreeItemType
  → index.vue handleTreeClick(record) sets selectedMenu ref
  → MenuDetailPanel receives :menu="selectedMenu" prop
  → User clicks inline toggle/icon/edit/delete
  → MenuDetailPanel emits event or calls API directly
  → On success, notify parent to refresh tree
```

### MenuDetailPanel Sections

Each section is a card with header and content:

| Section | Fields | Edit Mode |
|---|---|---|
| **Header** | Icon (large), name (zh), name (en), Edit button, Delete button | Edit opens drawer; Icon click → IconSelector |
| **Basic Info** | Icon preview + name tag, name_en, parent, sort | Sort ↑↓ buttons; Icon → IconSelector |
| **Route & Component** | web_path, component, component_name, link_url | Read-only (edit via drawer) |
| **Toggles** | status, visible, cache, is_catalog, is_link, is_iframe | **Inline el-switch** — click to toggle, auto-save via PATCH |
| **Description** | description text | Read-only (edit via drawer) |

### Inline Toggle Save Strategy

Each `el-switch` change triggers a debounced PATCH call:

```
PATCH /api/iam/menu/{id}/
{ "status": true }   // or whichever field changed
```

On success → update local data, show success toast.
On failure → revert switch to previous value, show error toast.

This avoids the overhead of opening the drawer for simple boolean toggles.

### States

| State | Behavior |
|---|---|
| **No menu selected** | Show `el-empty` with prompt "Select a menu from the tree" |
| **Loading** | Show `v-loading` on detail panel while fetching (for first load only) |
| **Selected + data loaded** | Show all sections as designed |
| **Toggle save in progress** | Disable the switch being saved; show loading indicator on it |
| **Delete success** | Clear detail panel, refresh tree |
| **Edit success (drawer)** | Refresh tree and detail panel with new data |

## Files to Modify / Create

### New files
1. `web/src/views/apps/iam/admin/menu/components/MenuDetailPanel/index.vue`
   - The new detail panel component
   - Props: `menu: MenuTreeItemType | null`
   - Emits: `refresh` (after toggle/edit/delete to refresh tree)

### Modified files
2. `web/src/views/apps/iam/admin/menu/index.vue`
   - Replace `el-empty` in right `el-col` with `<MenuDetailPanel>`
   - Wire `handleTreeClick` to pass selected menu data
   - Pass `handleDrawerClose` as refresh callback
   - Import `GetObj`, `UpdateObj`, `DelObj` from `../../api`

### No changes needed
3. `backend/iam/views/menu.py` — All needed endpoints exist
4. `backend/iam/models/page_config.py` — Model unchanged
5. `MenuTreeCom/index.vue` — Already works correctly
6. `MenuFormCom/index.vue` — Already works correctly
7. `web/src/views/apps/iam/admin/menu/api.ts` — All needed API calls exist

## Verification

1. Open IAM page → Menus tab
2. Right panel shows "Select a menu from the tree" prompt when nothing selected
3. Click a menu in tree → right panel shows all details
4. Toggle "status" switch → menu status changes in DB; tree node updates appearance
5. Toggle "sidebar visible" → sidebar reflects change on page refresh
6. Click edit button → drawer opens pre-filled with current data
7. Click delete → confirmation → menu removed; tree refreshes
8. Sort ↑↓ arrows reorder menus within their parent level
9. Click header icon → IconSelector opens → pick new icon → saves immediately
