#!/usr/bin/env python
"""Replace hardcoded English in opsflow-webhook/index.vue"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow-webhook/index.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()
orig = content

# Imports
content = content.replace(
    'import { ref, computed, onMounted } from \'vue\'',
    'import { useI18n } from \'vue-i18n\'\nimport { ref, computed, onMounted } from \'vue\''
)
content = content.replace(
    "import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'",
    "import ProjectSwitcher from '/@/views/apps/opsflow/components/common/ProjectSwitcher.vue'\nconst { t } = useI18n()"
)

# Hero
content = content.replace('<h1 class="wh-hero-title">Webhook</h1>',
    '<h1 class="wh-hero-title">{{ $t("message.opsflowPage.webhookTitle") }}</h1>')
content = content.replace('<p class="wh-hero-subtitle">HTTP callback notifications for pipeline events</p>',
    '<p class="wh-hero-subtitle">{{ $t("message.opsflowPage.webhookSubtitle") }}</p>')
content = content.replace('placeholder="Search webhooks..."',
    ':placeholder="$t(\'message.opsflowPage.webhookSearch\')"')
content = content.replace('<span class="wh-stat-label">Total</span>',
    '<span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatTotal") }}</span>')
content = content.replace('<span class="wh-stat-label">Active</span>',
    '<span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatActive") }}</span>')
content = content.replace('<span class="wh-stat-label">Err</span>',
    '<span class="wh-stat-label">{{ $t("message.opsflowPage.webhookStatErr") }}</span>')

# Filter tabs
content = content.replace('/>All<', '/>{{ $t("message.opsflowPage.webhookFilterAll") }}<')
content = content.replace('/>Completed<', '/>{{ $t("message.execution.statCompleted") }}<')
content = content.replace('/>Failed<', '/>{{ $t("message.execution.statFailed") }}<')
content = content.replace('>Refresh<', '>{{ $t("message.common.refresh") }}<')
content = content.replace('>Add Webhook<', '>{{ $t("message.opsflowPage.webhookAdd") }}<')

# Card badges
content = content.replace("{{ w.enabled ? 'Active' : 'Paused' }}",
    "{{ w.enabled ? $t('message.opsflowPage.webhookActive') : $t('message.opsflowPage.webhookPaused') }}")
content = content.replace('\U0001f510 Signed',
    '\U0001f510 {{ $t("message.opsflowPage.webhookSigned") }}')
content = content.replace('>Retry <',
    '>{{ $t("message.opsflowPage.webhookRetry") }} <')

# Dialog
content = content.replace(":title=\"formId ? 'Edit Webhook' : 'Add Webhook'\"",
    ":title=\"formId ? $t('message.opsflowPage.webhookEdit') : $t('message.opsflowPage.webhookAdd')\"")
content = content.replace('label="Name"', ':label="$t(\'message.common.name\')"')
content = content.replace('placeholder="Webhook name"', ':placeholder="$t(\'message.opsflowPage.webhookNamePlaceholder\')"')
content = content.replace('placeholder="https://example.com/callback"', ':placeholder="$t(\'message.opsflowPage.webhookUrlPlaceholder\')"')
content = content.replace('placeholder="HMAC signing key (optional)"', ':placeholder="$t(\'message.opsflowPage.webhookSecretPlaceholder\')"')

content = content.replace('value="completed" size="small">completed</el-checkbox>',
    'value="completed" size="small">{{ $t("message.execution.statCompleted") }}</el-checkbox>')
content = content.replace('value="failed" size="small">failed</el-checkbox>',
    'value="failed" size="small">{{ $t("message.execution.statFailed") }}</el-checkbox>')

content = content.replace('>Cancel<', '>{{ $t("message.common.cancel") }}<')
content = content.replace("{{ formId ? 'Update' : 'Create' }}",
    "{{ formId ? $t('message.opsflowPage.webhookUpdate') : $t('message.opsflowPage.webhookCreate') }}")

# Detail
content = content.replace("{{ detail.enabled ? 'Active' : 'Paused' }}",
    "{{ detail.enabled ? $t('message.opsflowPage.webhookActive') : $t('message.opsflowPage.webhookPaused') }}")
content = content.replace('✓ Configured',
    '{{ $t("message.opsflowPage.webhookConfigured") }}')
content = content.replace('Delivery Logs',
    '{{ $t("message.opsflowPage.webhookDeliveryLogs") }}')
content = content.replace('"No delivery logs"',
    't("message.opsflowPage.webhookNoLogs")')

content = content.replace("title='Delete this webhook?'",
    ":title=\"$t('message.opsflowPage.webhookDeleteConfirm')\"")

content = content.replace(">Edit<", ">{{ $t(\"message.common.edit\") }}<")
content = content.replace(">Delete<", ">{{ $t(\"message.common.delete\") }}<")

# Script messages
content = content.replace("'No webhooks configured yet. Create one to receive HTTP callbacks.'",
    "t('message.opsflowPage.webhookEmptyText')")
content = content.replace("'Failed to load webhooks'",
    "t('message.opsflowPage.webhookLoadFailed')")
content = content.replace("'Webhook updated'",
    "t('message.opsflowPage.webhookUpdated')")
content = content.replace("'Webhook created'",
    "t('message.opsflowPage.webhookCreated')")
content = content.replace("'Webhook deleted'",
    "t('message.opsflowPage.webhookDeleted')")
content = content.replace("'Save failed'",
    "t('message.opsflowPage.webhookSaveFailed')")
content = content.replace("'Delete failed'",
    "t('message.opsflowPage.webhookDeleteFailed')")
content = content.replace("ElMessage.warning('Name, URL, and Template are required')",
    "ElMessage.warning(t('message.opsflowPage.webhookRequired'))")

if content != orig:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('webhooks index.vue: updated')
else:
    print('no changes')
