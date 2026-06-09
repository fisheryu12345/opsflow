#!/usr/bin/env python
"""Batch i18n conversion for all remaining opsflow pages"""
import glob, re, sys, os
sys.stdout.reconfigure(encoding='utf-8')

# Files to process (already partially done ones excluded)
files = [
    # opsflow-template
    "src/views/apps/opsflow-template/index.vue",
    "src/views/apps/opsflow-template/schedule.vue",
    "src/views/apps/opsflow-template/components/ScheduleForm.vue",
    "src/views/apps/opsflow-template/components/ScheduleManager.vue",
    "src/views/apps/opsflow-template/components/ScheduleTable.vue",
    "src/views/apps/opsflow-template/components/VersionDialog.vue",
    # Other opsflow pages
    "src/views/apps/opsflow-approval/index.vue",
    "src/views/apps/opsflow-knowledge/index.vue",
    "src/views/apps/opsflow-log/index.vue",
    "src/views/apps/opsflow-project/index.vue",
    "src/views/apps/opsflow-webhook/index.vue",
    "src/views/apps/opsflow-dashboard/index.vue",
    "src/views/apps/opsflow-stats/index.vue",
    # Remaining opsflow sub-components
    "src/views/apps/opsflow/components/gates/ConditionDialog.vue",
    "src/views/apps/opsflow/components/gates/ConditionRow.vue",
    "src/views/apps/opsflow/components/badges/SubprocessStatusBadge.vue",
    "src/views/apps/opsflow/components/schemes/SchemeSelector.vue",
    "src/views/apps/opsflow/components/panels/VariableBrowser.vue",
    "src/views/apps/opsflow/components/panels/VariablePicker.vue",
    "src/views/apps/opsflow/components/dialogs/DryRunDialog.vue",
]

# Common replacement patterns that apply across all files
COMMON_REPLACEMENTS = [
    # Form labels used in many files
    ("label=\"Name\"", ":label=\"$t('message.common.name')\""),
    ("label=\"Status\"", ":label=\"$t('message.execution.status')\""),
    ("label=\"Description\"", ":label=\"$t('message.common.description')\""),
    ("label=\"Template\"", ":label=\"$t('message.execution.colTemplate')\""),
    ("label=\"ID\"", ":label=\"$t('message.execution.colId')\""),
    # Buttons
    (">Refresh<", ">{{ $t('message.common.refresh') }}<"),
    (">Edit<", ">{{ $t('message.common.edit') }}<"),
    (">Delete<", ">{{ $t('message.common.delete') }}<"),
    (">Cancel<", ">{{ $t('message.common.cancel') }}<"),
    (">Save<", ">{{ $t('message.common.save') }}<"),
    (">Create<", ">{{ $t('message.common.create') }}<"),
    (">Search<", ">{{ $t('message.common.search') }}<"),
    (">Import<", ">{{ $t('message.common.import') }}<"),
    (">Export<", ">{{ $t('message.common.export') }}<"),
    (">Close<", ">{{ $t('message.common.close') }}<"),
    # Tooltips
    ('content="Edit"', ':content="$t(\'message.common.edit\')"'),
    ('content="Delete"', ':content="$t(\'message.common.delete\')"'),
    # Common placeholders
    ("placeholder=\"Search...\"", ":placeholder=\"$t('message.common.search')\""),
    ("placeholder=\"Search\"", ":placeholder=\"$t('message.common.search')\""),
]

total_files = 0
for fp in files:
    abs_path = os.path.join(os.getcwd(), fp)
    if not os.path.exists(abs_path):
        print(f"SKIP {fp}: not found")
        continue
    with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    orig = content

    # Add useI18n import if needed and not already present
    if 'useI18n' not in content:
        content = re.sub(
            r'(import \{ ref, computed, watch, onMounted \})',
            r'import { useI18n } from \'vue-i18n\'\n\1',
            content,
            count=1
        )
        content = re.sub(
            r'(import \{ ref, computed, onMounted \})',
            r'import { useI18n } from \'vue-i18n\'\n\1',
            content,
            count=1
        )
        content = re.sub(
            r'(import \{ ref, computed \})',
            r'import { useI18n } from \'vue-i18n\'\n\1',
            content,
            count=1
        )
        content = re.sub(
            r'(import \{ ref \})',
            r'import { useI18n } from \'vue-i18n\'\n\1',
            content,
            count=1
        )

    # Add const { t } = useI18n() after store initialization
    content = re.sub(
        r'(const \w+Store = use\w+Store\(\))',
        r'\1\nconst { t } = useI18n()',
        content,
        count=1
    )
    # Or after defineProps/defineEmits
    if 'const { t }' not in content:
        content = re.sub(
            r'(\}\)\n\nconst \w+ = ref)',
            r'})\nconst { t } = useI18n()\n\n\1',
            content,
            count=1
        )

    # Apply common replacements
    for old, new in COMMON_REPLACEMENTS:
        content = content.replace(old, new)

    if content != orig:
        total_files += 1
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"FIXED {fp}")
    else:
        print(f"OK {fp}")

print(f"\nTotal files fixed: {total_files}")
