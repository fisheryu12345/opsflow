#!/usr/bin/env python
"""Replace hardcoded English in opsflow-project/index.vue with $t() calls"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow-project/index.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

orig = content

# Hero
content = content.replace('<h1 class="pj-hero-title">Projects</h1>',
    '<h1 class="pj-hero-title">{{ $t("message.project.title") }}</h1>')
content = content.replace('<p class="pj-hero-subtitle">Multi-tenant isolation for OpsFlow workspaces</p>',
    '<p class="pj-hero-subtitle">{{ $t("message.opsflowPage.projectsSubtitle") }}</p>')
content = content.replace('placeholder="Search projects..."',
    ':placeholder="$t(\'message.opsflowPage.projectsSearch\')"')

# Stats
content = content.replace('<span class="pj-stat-label">Total</span>',
    '<span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatTotal") }}</span>')
content = content.replace('<span class="pj-stat-label">Active</span>',
    '<span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatActive") }}</span>')
content = content.replace('<span class="pj-stat-label">Templates</span>',
    '<span class="pj-stat-label">{{ $t("message.opsflowPage.projectsStatTemplates") }}</span>')

# Filter tabs
content = content.replace('/>All<', '/>{{ $t("message.opsflowPage.projectsFilterAll") }}<')
content = content.replace('/>Active<', '/>{{ $t("message.opsflowPage.projectsFilterActive") }}<')
content = content.replace('/>Inactive<', '/>{{ $t("message.opsflowPage.projectsFilterInactive") }}<')

# Buttons
content = content.replace('>Refresh<', '>{{ $t("message.common.refresh") }}<')
content = content.replace('>New Project<', '>{{ $t("message.opsflowPage.projectsNew") }}<')

# Card badges
content = content.replace("{{ p.is_active ? 'Active' : 'Inactive' }}",
    "{{ p.is_active ? $t('message.opsflowPage.projectsActive') : $t('message.opsflowPage.projectsInactive') }}")
content = content.replace("'No description'", "t('message.opsflowPage.projectsNoDesc')")

# Card stats
content = content.replace('<b>{{ p.template_count ?? 0 }}</b> templates',
    '<b>{{ p.template_count ?? 0 }}</b> {{ $t("message.opsflowPage.projectsTemplates") }}')
content = content.replace('<b>{{ p.execution_count ?? 0 }}</b> executions',
    '<b>{{ p.execution_count ?? 0 }}</b> {{ $t("message.opsflowPage.projectsExecutions") }}')

# Dialog titles
content = content.replace(":title=\"formId ? 'Edit Project' : 'New Project'\"",
    ":title=\"formId ? $t('message.opsflowPage.projectsEdit') : $t('message.opsflowPage.projectsNew')\"")

# Form labels
content = content.replace('label="Name"', ':label="$t(\'message.common.name\')"')
content = content.replace('label="Description"', ':label="$t(\'message.template.descLabel\')"')
content = content.replace('label="Active"', ':label="$t(\'message.opsflowPage.projectsActive\')"')
content = content.replace('label="Max Schedules"', ':label="$t(\'message.opsflowPage.projectsMaxSchedules\')"')

# Placeholders
content = content.replace('placeholder="Project name (unique)"', ':placeholder="$t(\'message.opsflowPage.projectsNamePlaceholder\')"')
content = content.replace('placeholder="Optional description..."', ':placeholder="$t(\'message.opsflowPage.projectsDescPlaceholder\')"')

content = content.replace('0 = unlimited', '{{ $t("message.opsflowPage.projectsUnlimited") }}')

# Footer buttons
content = content.replace('>Cancel<', '>{{ $t("message.common.cancel") }}<')
content = content.replace("{{ formId ? 'Update' : 'Create' }}",
    "{{ formId ? $t('message.opsflowPage.projectsUpdate') : $t('message.opsflowPage.projectsCreate') }}")

# Detail tabs
content = content.replace('label="Overview"', ':label="$t(\'message.opsflowPage.projectsOverview\')"')
content = content.replace('label="Members"', ':label="$t(\'message.opsflowPage.projectsMembers\')"')
content = content.replace('label="Plugins"', ':label="$t(\'message.opsflowPage.projectsPlugins\')"')
content = content.replace('label="Environment"', ':label="$t(\'message.opsflowPage.projectsEnvironment\')"')

# Detail card badges
content = content.replace("{{ detail.is_active ? 'Active' : 'Inactive' }}",
    "{{ detail.is_active ? $t('message.opsflowPage.projectsActive') : $t('message.opsflowPage.projectsInactive') }}")

# Detail labels (in template text)
content = content.replace('Owner:', '{{ $t("message.opsflowPage.projectsOwner") }}:')
content = content.replace('Created ', '{{ $t("message.opsflowPage.projectsCreated") }} ')

# Info grid labels - need careful handling
content = content.replace('<span class="pj-info-label">Desc</span>',
    '<span class="pj-info-label">{{ $t("message.opsflowPage.projectsDescLabel") }}</span>')
content = content.replace('<span class="pj-info-label">Templates</span>',
    '<span class="pj-info-label">{{ $t("message.opsflowPage.projectsTemplates") }}</span>')
content = content.replace('<span class="pj-info-label">Executions</span>',
    '<span class="pj-info-label">{{ $t("message.opsflowPage.projectsExecutions") }}</span>')
content = content.replace('<span class="pj-info-label">Schedule Limit</span>',
    '<span class="pj-info-label">{{ $t("message.opsflowPage.projectsScheduleLimit") }}</span>')
content = content.replace('Unlimited', '{{ $t("message.opsflowPage.projectsUnlimited") }}')

# Overview buttons
content = content.replace('>Edit<', '>{{ $t("message.common.edit") }}<')
content = content.replace('>Delete<', '>{{ $t("message.common.delete") }}<')
content = content.replace("title='Delete this project?'", ":title=\"$t('message.opsflowPage.projectsDeleteConfirm')\"")

# Members tab
content = content.replace('label="User"', ':label="$t(\'message.opsflowPage.projectsUser\')"')
content = content.replace('label="Role"', ':label="$t(\'message.opsflowPage.projectsRole\')"')
content = content.replace('placeholder="Select users..."', ':placeholder="$t(\'message.opsflowPage.projectsSelectUsers\')"')
content = content.replace('>Add<', '>{{ $t("message.opsflowPage.projectsAdd") }}<')

# Plugins tab
content = content.replace('Plugins for this project',
    '{{ $t("message.opsflowPage.projectsPluginsFor") }}')
content = content.replace('Toggle which plugins are available when designing pipelines in this project. When a plugin is switched off, it will not appear in the plugin picker for any template within this project.',
    '{{ $t("message.opsflowPage.projectsPluginsDesc") }}')
content = content.replace('>Manage Plugins<',
    '>{{ $t("message.opsflowPage.projectsManagePlugins") }}<')

# Script messages
content = content.replace("'No projects yet. Create one to get started.'",
    "t('message.opsflowPage.projectsNoProjects')")
content = content.replace("'Failed to load projects'",
    "t('message.opsflowPage.projectsLoadFailed')")
content = content.replace("'Project created'",
    "t('message.opsflowPage.projectsCreated')")
content = content.replace("'Project updated'",
    "t('message.opsflowPage.projectsUpdated')")
content = content.replace("'Project deleted'",
    "t('message.opsflowPage.projectsDeleted')")
content = content.replace("'Failed to save project'",
    "t('message.opsflowPage.projectsSaveFailed')")
content = content.replace("'Member added'",
    "t('message.opsflowPage.projectsMemberAdded')")
content = content.replace("'Member removed'",
    "t('message.opsflowPage.projectsMemberRemoved')")

# ElMessageBox confirm
content = content.replace("ElMessageBox.confirm('Delete this project?', 'Confirm')",
    "ElMessageBox.confirm(t('message.opsflowPage.projectsDeleteConfirm'), t('message.common.confirm'))")

if content != orig:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('projects index.vue: updated')
else:
    print('projects index.vue: no changes')
