<template>
  <!-- Designer view -->
  <Designer v-if="designerMode" :workflow-id="designerWorkflowId" @back="onCloseDesigner" />
  <!-- List view -->
  <div v-else class="itsm-page">
    <!-- ===== Hero Section ===== -->
    <div class="itsm-hero">
      <div class="itsm-hero-bg" />
      <div class="itsm-hero-inner">
        <div class="itsm-hero-left">
          <h1 class="itsm-hero-title">ITSM</h1>
          <p class="itsm-hero-subtitle">{{ $t('message.itsmPage.subtitle') }}</p>
        </div>
        <div ref="heroSearchRef" class="itsm-hero-search" />
        <div class="itsm-hero-stats">
          <template v-for="(stat, i) in heroStats" :key="i">
            <div v-if="i > 0" class="itsm-stat-divider" />
            <div class="itsm-stat-item">
              <span class="itsm-stat-value">{{ stat.value }}</span>
              <span class="itsm-stat-label">{{ stat.label }}</span>
            </div>
          </template>
        </div>
      </div>
      <!-- Hero tabs -->
      <div class="itsm-hero-tabs">
        <div v-for="tab in pageConfig?.tabs" :key="tab.key"
          class="itsm-hero-tab"
          :class="{ active: activeTab === tab.key, locked: !tab.has_access }"
          @click="onTabClick(tab)">
          <el-icon><component :is="iconMap[tab.icon]" /></el-icon>
          {{ isEn ? tab.label_en : tab.label_zh }}
          <span v-if="!tab.has_access" class="tab-lock">🔒</span>
        </div>
      </div>
    </div>

    <!-- ===== Body ===== -->
    <div class="itsm-body">

      <!-- ==================== TAB: {{ $t('message.itsmPage.tabDashboard') }} ==================== -->
      <div v-if="isVisited('dashboard')" v-show="activeTab === 'dashboard'" class="itsm-section g-fade-in-up">
        <Dashboard :tickets="tickets" :active="activeTab === 'dashboard'" @view-ticket="onViewTicket" @switch-tab="activeTab = $event" />
      </div>

      <!-- ==================== TAB: 服务市场 ==================== -->
      <div v-if="isVisited('service-market')" v-show="activeTab === 'service-market'" class="itsm-section g-fade-in-up">
        <ServiceMarket :active="activeTab === 'service-market'" @goTicket="onGoTicket" />
      </div>

      <!-- ==================== TAB: 服务目录管理 ==================== -->
      <div v-if="isVisited('service-admin')" v-show="activeTab === 'service-admin'" class="itsm-section g-fade-in-up">
        <ServiceAdmin :active="activeTab === 'service-admin'" />
      </div>

      <!-- ==================== TAB: 我的工单 ==================== -->
      <div v-if="isVisited('tickets')" v-show="activeTab === 'tickets'" class="itsm-section g-fade-in-up">
        <!-- Filter bar -->
        <div class="itsm-filter-bar">
          <div class="itsm-filter-tabs">
            <div class="itsm-tab" :class="{ active: ticketFilter === '' }" @click="ticketFilter = ''; loadTickets()">
              <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterAll') }}
            </div>
            <div class="itsm-tab" :class="{ active: ticketFilter === 'draft' }" @click="ticketFilter = 'draft'; loadTickets()">
              <span class="itsm-tab-dot" style="background:#E6A23C" />{{ $t('message.itsmPage.filterDraft') }}
            </div>
            <div class="itsm-tab" :class="{ active: ticketFilter === 'running' }" @click="ticketFilter = 'running'; loadTickets()">
              <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterRunning') }}
            </div>
            <div class="itsm-tab" :class="{ active: ticketFilter === 'finished' }" @click="ticketFilter = 'finished'; loadTickets()">
              <span class="itsm-tab-dot" style="background:#67C23A" />{{ $t('message.itsmPage.filterFinished') }}
            </div>
          </div>
          <div class="itsm-filter-actions">
            <el-button :icon="Refresh" size="small" text @click="loadTickets" :loading="loadingTickets">{{ $t('message.itsmPage.refresh') }}</el-button>
          </div>
        </div>

        <div class="itsm-table-card">
          <el-table :data="tickets" v-loading="loadingTickets" stripe style="width:100%" size="small"
            :empty-text="loadingTickets ? $t('message.itsmPage.loading') : $t('message.itsmPage.noTickets')">
            <el-table-column prop="sn" :label="$t('message.itsmPage.colSn')" width="160" />
            <el-table-column prop="title" :label="$t('message.itsmPage.colTitle')" min-width="200" show-overflow-tooltip />
            <el-table-column :label="$t('message.itsmPage.colType')" width="90">
              <template #default="{ row }">
                <el-tag :type="row.itsm_type === 'incident' ? 'danger' : row.itsm_type === 'change' ? 'warning' : ''" size="small">
                  {{ row.itsm_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colStatus')" width="100">
              <template #default="{ row }">
                <span class="itsm-status-badge" :class="'it-status-' + row.current_status">
                  <span class="itsm-status-dot" />{{ statusLabel(row.current_status) }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colSla')" width="100">
              <template #default="{ row }">
                <span v-if="row.sla_info" :class="'sla-badge sla-' + row.sla_info.sla_status">
                  {{ row.sla_info.remaining_seconds != null ? formatSla(row.sla_info.remaining_seconds) : '-' }}
                </span>
                <span v-else style="font-size:12px;color:#C0C4CC">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80">
              <template #default="{ row }">
                <span class="itsm-prio-badge" :class="'it-prio-' + (row.priority || 'p3').toLowerCase()">{{ row.priority }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colCreator')" width="120">
              <template #default="{ row }">
                {{ row.creator_name || row.creator || '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="create_datetime" :label="$t('message.itsmPage.colCreateTime')" width="170" />
            <el-table-column :label="$t('message.itsmPage.colAssignee')" width="140">
              <template #default="{ row }">
                <template v-if="row.meta?.assignee">
                  <span style="font-size:13px;color:#606266">{{ row.meta.assignee.name }}</span>
                  <el-tag v-if="row.meta.assignee.group" size="small" style="margin-left:4px">{{ row.meta.assignee.group }}</el-tag>
                </template>
                <span v-else-if="row.meta?.assign_group" style="font-size:12px;color:#909399">
                  组: {{ row.meta.assign_group.name }}
                </span>
                <span v-else style="font-size:12px;color:#C0C4CC">{{ $t('message.itsmPage.pendingAssignee') }}</span>
              </template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colActions')" width="280" fixed="right">
              <template #default="{ row }">
                <el-button v-if="row.current_status === 'draft'" size="small" text v-can="'itsm:ticket:create'" @click="onSubmitTicket(row)">
                  <el-icon><Select /></el-icon> {{ $t('message.itsmPage.submit') }}
                </el-button>
                <el-button size="small" text @click="onViewTicket(row)">
                  <el-icon><Search /></el-icon> {{ $t('message.itsmPage.detail') }}
                </el-button>
                <el-button v-if="row.meta?.assignee && row.current_status !== 'finished' && row.current_status !== 'terminated'" size="small" text type="warning" v-can="'itsm:ticket:assign'" @click="ticketAssign(row)">
                  <el-icon><User /></el-icon> {{ $t('message.itsmPage.transfer') }}
                </el-button>
                <el-button v-else-if="!row.meta?.assignee && row.current_status !== 'finished' && row.current_status !== 'terminated'" size="small" text type="primary" v-can="'itsm:ticket:assign'" @click="ticketAssign(row)">
                  <el-icon><User /></el-icon> {{ $t('message.itsmPage.assign') }}
                </el-button>
                <el-button v-if="row.current_status === 'running'" size="small" text type="danger" v-can="'itsm:ticket:close'" @click="onCloseTicket(row)">
                  <el-icon><CircleClose /></el-icon> {{ $t('message.itsmPage.close') }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- ==================== TAB: 流程模板 ==================== -->
      <div v-if="isVisited('workflows')" v-show="activeTab === 'workflows'" class="itsm-section g-fade-in-up">
        <div class="itsm-filter-bar">
          <div class="itsm-filter-tabs">
            <div class="itsm-tab" :class="{ active: wfFilter === '' }" @click="wfFilter = ''; loadWorkflows()">
              <span class="itsm-tab-dot" style="background:#409EFF" />{{ $t('message.itsmPage.filterAll') }}
            </div>
            <div class="itsm-tab" :class="{ active: wfFilter === 'change' }" @click="wfFilter = 'change'; loadWorkflows()">
              <span class="itsm-tab-dot" style="background:#E6A23C" />{{ $t('message.itsmPage.changes') }}
            </div>
            <div class="itsm-tab" :class="{ active: wfFilter === 'incident' }" @click="wfFilter = 'incident'; loadWorkflows()">
              <span class="itsm-tab-dot" style="background:#F56C6C" />{{ $t('message.itsmPage.incidents') }}
            </div>
          </div>
          <div class="itsm-filter-actions">
            <el-button v-can="'itsm:workflow:create'" size="small" type="primary" @click="showAICreate = true">
              <el-icon><MagicStick /></el-icon> {{ $t('message.itsmPage.aiCreate') }}
            </el-button>
            <el-button :icon="Refresh" size="small" text @click="loadWorkflows" :loading="loadingWf">{{ $t('message.itsmPage.refresh') }}</el-button>
          </div>
        </div>

        <div class="itsm-wf-grid">
          <div v-for="wf in workflows" :key="wf.id" class="itsm-wf-card">
            <div class="itsm-wf-card-inner">
              <div class="itsm-wf-card-header">
                <span class="itsm-wf-type-tag" :class="'wf-type-' + wf.itsm_type">{{ wf.itsm_type }}</span>
                <el-tag v-if="wf.is_draft" size="small" type="warning">{{ $t('message.itsmPage.filterDraft') }}</el-tag>
                <el-tag v-else size="small" type="success">{{ $t('message.itsmPage.published') }}</el-tag>
              </div>
              <div class="itsm-wf-name">{{ wf.name }}</div>
              <div class="itsm-wf-desc" v-if="wf.description">{{ wf.description }}</div>
              <div class="itsm-wf-meta">
                <span>{{ wf.created_by || '-' }}</span>
                <span>{{ wf.create_datetime || '' }}</span>
              </div>
              <div class="itsm-wf-actions">
<el-button v-if="wf.is_draft" v-can="'itsm:workflow:deploy'" size="small" text type="success" @click="onDeployWorkflow(wf)">
                  <el-icon><Upload /></el-icon> {{ $t('message.itsmPage.deploy') }}
                </el-button>
                <el-button v-can="'itsm:workflow:design'" size="small" text @click="onOpenDesigner(wf.id)">
                  <el-icon><Setting /></el-icon> {{ $t('message.itsmPage.design') }}
                </el-button>
                <el-button size="small" text @click="onOpenVersions(wf)">
                  <el-icon><Clock /></el-icon> {{ $t('message.itsmPage.version') }}
                </el-button>
                <el-button v-can.admin="'itsm:workflow:delete'" size="small" text type="danger" @click="onDeleteWorkflow(wf)">
                  <el-icon><Delete /></el-icon> {{ $t('message.itsmPage.delete') }}
                </el-button>
              </div>
            </div>
          </div>
          <div v-if="!workflows.length && !loadingWf" class="itsm-wf-empty">
            <el-empty :description="$t('message.itsmPage.noWorkflows')" :image-size="50" />
          </div>
        </div>
      </div>


      <!-- ==================== TAB: SLA 策略 ==================== -->
      <div v-if="isVisited('sla')" v-show="activeTab === 'sla'" class="itsm-section g-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">{{ $t('message.itsmPage.slaPolicies') }}</span>
          </div>
          <el-table :data="slaPolicies" v-loading="loadingSla" stripe style="width:100%" size="small"
            :empty-text="loadingSla ? $t('message.itsmPage.loading') : $t('message.itsmPage.noSla')">
            <el-table-column prop="name" :label="$t('message.itsmPage.colSLAPolicy')" min-width="160" />
            <el-table-column prop="priority" :label="$t('message.ticketCreate.priority')" width="80" />
            <el-table-column prop="response_minutes" :label="$t('message.itsmPage.colResponseMin')" width="140" />
            <el-table-column prop="resolve_minutes" :label="$t('message.itsmPage.colResolveMin')" width="140" />
            <el-table-column prop="is_active" :label="$t('message.itsmPage.colEnabled')" width="80" align="center">
              <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="onSlaToggle(row)" /></template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colActions')" width="80" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text v-can="'itsm:sla:edit'" @click="onSlaEdit(row)">{{ $t('message.common.edit') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- SLA Edit Dialog -->
        <el-dialog v-model="showSlaEdit" :title="$t('message.itsmPage.editSlaPolicy')" width="440px" top="15vh" destroy-on-close append-to-body>
          <el-form :model="slaForm" label-width="120px" size="small">
            <el-form-item :label="$t('message.itsmPage.colSLAPolicy')"><el-input v-model="slaForm.name" /></el-form-item>
            <el-form-item :label="$t('message.ticketCreate.priority')" v-if="!slaForm.id">
              <el-select v-model="slaForm.priority" style="width:100%">
                <el-option label="P1" value="P1" /><el-option label="P2" value="P2" />
                <el-option label="P3" value="P3" /><el-option label="P4" value="P4" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('message.ticketCreate.priority')" v-else>
              <span style="font-weight:600">{{ slaForm.priority }}</span>
            </el-form-item>
            <el-form-item :label="$t('message.itsmPage.responseMinLabel')"><el-input-number v-model="slaForm.response_minutes" :min="1" :max="10080" style="width:160px" /></el-form-item>
            <el-form-item :label="$t('message.itsmPage.resolveMinLabel')"><el-input-number v-model="slaForm.resolve_minutes" :min="1" :max="43200" style="width:160px" /></el-form-item>
            <el-form-item :label="$t('message.itsmPage.colEnabled')"><el-switch v-model="slaForm.is_active" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showSlaEdit = false">{{ $t('message.common.cancel') }}</el-button>
            <el-button type="primary" :loading="savingSla" @click="onSlaSave">{{ $t('message.common.save') }}</el-button>
          </template>
        </el-dialog>
      </div>

      <!-- ==================== TAB: 审批委托 ==================== -->
      <div v-if="isVisited('delegation')" v-show="activeTab === 'delegation'" class="itsm-section g-fade-in-up">
        <Delegation :active="activeTab === 'delegation'" />
      </div>

      <!-- ==================== TAB: 升级层级 ==================== -->
      <div v-if="isVisited('escalation')" v-show="activeTab === 'escalation'" class="itsm-section g-fade-in-up">
        <div class="itsm-table-card">
          <div class="itsm-table-header">
            <span class="itsm-table-title">{{ $t('message.escalation.title') }}</span>
            <el-button size="small" type="primary" v-can="'itsm:escalation:manage'" @click="onEscalationCreate">
              <el-icon><Plus /></el-icon> {{ $t('message.common.create') }}
            </el-button>
          </div>
          <el-table :data="escalationLevels" v-loading="loadingEsc" stripe style="width:100%" size="small"
            :empty-text="loadingEsc ? $t('message.itsmPage.loading') : $t('message.escalation.noData')">
            <el-table-column prop="level" :label="$t('message.escalation.level')" width="70" />
            <el-table-column prop="name" :label="$t('message.escalation.name')" min-width="160" />
            <el-table-column prop="timeout_minutes" :label="$t('message.escalation.timeoutLabel')" width="150" />
            <el-table-column prop="action" :label="$t('message.escalation.action')" width="140">
              <template #default="{ row }">{{ escActionLabel(row.action) }}</template>
            </el-table-column>
            <el-table-column prop="is_active" :label="$t('message.itsmPage.colEnabled')" width="80" align="center">
              <template #default="{ row }"><el-switch v-model="row.is_active" size="small" @change="onEscToggle(row)" /></template>
            </el-table-column>
            <el-table-column :label="$t('message.itsmPage.colActions')" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" text v-can="'itsm:escalation:manage'" @click="onEscEdit(row)">{{ $t('message.common.edit') }}</el-button>
                <el-button size="small" text type="danger" v-can="'itsm:escalation:manage'" @click="onEscDelete(row)">{{ $t('message.common.delete') }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- Escalation Edit Dialog -->
        <el-dialog v-model="showEscEdit" :title="escForm.id ? $t('message.escalation.editEscalation') : $t('message.escalation.createEscalation')" width="480px" top="15vh" destroy-on-close append-to-body>
          <el-form :model="escForm" label-width="130px" size="small">
            <el-form-item :label="$t('message.escalation.levelNumber')"><el-input-number v-model="escForm.level" :min="1" :max="10" style="width:100%" /></el-form-item>
            <el-form-item :label="$t('message.escalation.name')"><el-input v-model="escForm.name" /></el-form-item>
            <el-form-item :label="$t('message.escalation.timeoutLabel')"><el-input-number v-model="escForm.timeout_minutes" :min="1" :max="43200" style="width:100%" /></el-form-item>
            <el-form-item :label="$t('message.escalation.action')">
              <el-select v-model="escForm.action" style="width:100%">
                <el-option :label="$t('message.escalation.notifyOnly')" value="notify_only" />
                <el-option :label="$t('message.escalation.transferLeader')" value="transfer_leader" />
                <el-option :label="$t('message.escalation.transferNext')" value="transfer_next" />
                <el-option :label="$t('message.escalation.notifyUsers')" value="notify_users" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('message.escalation.notifyUsersLabel')">
              <el-select v-model="escNotifyUsers" multiple filterable remote :remote-method="loadEscUsers"
                :loading="escUsersLoading" style="width:100%" :placeholder="$t('message.designer.searchUserPlaceholder')"
                @change="syncEscNotifyUsersStr">
                <el-option v-for="u in escUserOptions" :key="u.value" :label="u.label" :value="u.value" />
              </el-select>
            </el-form-item>
            <el-form-item :label="$t('message.itsmPage.colEnabled')"><el-switch v-model="escForm.is_active" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="showEscEdit = false">{{ $t('message.common.cancel') }}</el-button>
            <el-button type="primary" :loading="savingEsc" @click="onEscSave">{{ escForm.id ? $t('message.common.save') : $t('message.common.create') }}</el-button>
          </template>
        </el-dialog>
      </div>
    </div>

    <!-- ===== AI 创建流程 ===== -->
    <el-dialog v-model="showAICreate" :title="$t('message.aiCreate.title')" width="620px" top="5vh" class="itsm-dialog">
      <el-form label-position="top">
        <el-form-item :label="$t('message.aiCreate.descLabel')">
          <el-input v-model="aiDescription" type="textarea" :rows="4"
            :placeholder="$t('message.aiCreate.descPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('message.ticketCreate.itsmType')">
          <el-select v-model="aiType" style="width:100%">
            <el-option :label="$t('message.ticketCreate.changeRequest')" value="change" />
            <el-option :label="$t('message.ticketCreate.eventTicket')" value="incident" />
            <el-option :label="$t('message.ticketCreate.serviceRequest')" value="request" />
            <el-option :label="$t('message.ticketCreate.problem')" value="problem" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="aiResult" class="itsm-ai-preview g-fade-in-up">
        <div class="itsm-ai-preview-header">{{ $t('message.aiCreate.generatePreview') }}</div>
        <div class="itsm-ai-flow">
          <span v-for="(s, idx) in aiResult.states?.filter((s: any) => s.type !== 'START' && s.type !== 'END') || []" :key="idx" class="itsm-ai-node">
            <span class="itsm-ai-node-badge" :class="'node-' + (s.type || '').toLowerCase()">{{ s.type }}</span>
            {{ s.name }}
            <el-icon v-if="Number(idx) < arrowCount(aiResult)"><ArrowRight /></el-icon>
          </span>
        </div>
      </div>
      <template #footer>
        <el-button @click="showAICreate = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button v-if="!aiResult" type="primary" :loading="aiLoading" @click="onAIGenerate">
          <el-icon><MagicStick /></el-icon> {{ $t('message.aiCreate.oneClick') }}
        </el-button>
        <el-button v-else type="success" :loading="savingWf" @click="onSaveAIWorkflow">
          <el-icon><Check /></el-icon> {{ $t('message.aiCreate.saveTemplate') }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== 工单分派对话框 ===== -->
    <el-dialog v-model="assignTicketVisible" :title="$t('message.assignment.title')" width="380px" top="25vh" destroy-on-close>
      <el-form label-position="top">
        <el-form-item :label="$t('message.assignment.selectUser')">
          <el-select v-model="assignUserId" filterable size="small" style="width:100%"
            :loading="usersLoading" :placeholder="$t('message.assignment.searchUser')">
            <el-option v-for="u in filteredUserOptions" :key="u.id" :label="`${u.name} (${u.username})`" :value="u.id" />
          </el-select>
        </el-form-item>
        <div v-if="assignTicketRow" style="font-size:12px;color:#909399;margin-top:-8px;margin-bottom:8px">
          {{ $t('message.assignment.ticketPrefix') }}: <b>{{ assignTicketRow.sn }} - {{ assignTicketRow.title }}</b>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="assignTicketVisible = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="primary" :disabled="!assignUserId" @click="confirmAssignTicket">{{ $t('message.assignment.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== 版本历史对话框 ===== -->
    <el-dialog v-model="showVersionDialog" :title="$t('message.itsmPage.versionHistory', { name: versionDialogWf?.name || '' })" width="520px" top="10vh" destroy-on-close @closed="onVersionDialogClosed">
      <div v-loading="versionLoading" style="min-height: 80px;">
        <div v-if="!versionLoading && !versionList.length" style="text-align:center;padding:24px;color:#909399;">{{ $t('message.itsmPage.noVersions') }}</div>
        <div v-for="ver in versionList" :key="ver.id" style="display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid #f0f0f0;">
          <div>
            <el-tag size="small" type="info" style="margin-right:8px;">v{{ ver.version }}</el-tag>
            <span style="font-size:12px;color:#909399;">{{ ver.create_datetime }}</span>
          </div>
          <div>
            <el-button size="small" text type="warning" @click="onRollbackClick(ver)">{{ $t('message.itsmPage.rollback') }}</el-button>
            <el-button size="small" text type="danger" @click="onDeleteVersion(ver)">{{ $t('message.itsmPage.delete') }}</el-button>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showVersionDialog = false">{{ $t('message.itsmPage.close') }}</el-button>
      </template>
    </el-dialog>

    <!-- ===== 版本回滚确认对话框 ===== -->
    <el-dialog v-model="showRollbackDialog" :title="$t('message.itsmPage.rollbackConfirm')" width="440px" top="25vh" destroy-on-close>
      <div style="padding: 8px 0; font-size: 14px;">
        <p style="margin-bottom: 12px;">{{ $t('message.itsmPage.rollbackToVersion', { version: rollbackTarget?.version }) }}</p>
        <p style="color: #909399; font-size: 12px; margin-bottom: 0;">{{ $t('message.itsmPage.rollbackHint') }}</p>
      </div>
      <template #footer>
        <el-button @click="showRollbackDialog = false">{{ $t('message.common.cancel') }}</el-button>
        <el-button type="warning" :loading="rollbackLoading" @click="confirmRollback">{{ $t('message.itsmPage.confirmRollback') }}</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, watch } from 'vue'
import { useTabLazyLoad } from '/@/composables/useTabLazyLoad'
import { useHeroProvider, type HeroStatItem } from '/@/composables/useHeroProvider'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { request } from '/@/utils/service'
import Designer from './designer/index.vue'
import { useI18n } from 'vue-i18n'
import { usePermissionStore } from '/@/stores/permission'
import Dashboard from './Dashboard.vue'
import Delegation from './Delegation.vue'
import ServiceMarket from './catalog/ServiceMarket.vue'
import ServiceAdmin from './catalog/ServiceAdmin.vue'
import {
  WarningFilled, Edit, Message, QuestionFilled, Clock,
  Plus, Refresh, User, Finished, CircleClose, Select, Close,
  List, Setting, MagicStick, ArrowRight, Check, Collection, DataAnalysis,
  Search, Delete, Upload, Lock,
} from '@element-plus/icons-vue'
import {
  slaPolicyApi,
  workflowApi, workflowVersionApi, stateApi, transitionApi, ticketApi,
  DeployWorkflow, SubmitTicket,
  CloseTicket,
  AIGenerateWorkflow,
  AssignTicket, RollbackVersion,
  escalationApi,
} from '/@/api/itsm/index'

// ===== Page Config (data-driven tabs) =====
const pageConfig = ref<any>(null)
const userPerms = ref<string[]>([])
const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))

const permissionStore = usePermissionStore()

function getTab(key: string) {
  return pageConfig.value?.tabs?.find((t: any) => t.key === key)
}

async function loadPageConfig() {
  try {
    const res = await request({ url: '/api/iam/page-permissions/', params: { app: 'itsm' } })
    pageConfig.value = res.data
    userPerms.value = res.data.user_permissions || []
    const defaultTab = res.data.tabs.find((t: any) => t.is_default) || res.data.tabs[0]
    if (defaultTab) activeTab.value = defaultTab.key
    // Check sessionStorage for tab override (set by TicketDetail back button)
    const savedTab = sessionStorage.getItem('itsm_active_tab')
    if (savedTab && getTab(savedTab)) {
      activeTab.value = savedTab
      sessionStorage.removeItem('itsm_active_tab')
    }
  } catch { /* show empty */ }
}

const iconMap: Record<string, any> = {
  DataAnalysis, List, Setting, WarningFilled, Edit, Clock, User, Collection,
}

function onTabClick(tab: any) {
  if (!tab.has_access) {
    permissionStore.requestPerm(tab.label_zh, tab.required_perm)
    return
  }
  activeTab.value = tab.key
}

// ===== Tab state =====
const activeTab = ref('tickets')
const designerMode = ref(false)
const designerWorkflowId = ref(0)

function onOpenDesigner(wfId?: number) {
  designerWorkflowId.value = wfId || 0
  designerMode.value = true
}
function arrowCount(aiResult: any): number { return ((aiResult.states?.filter((s: any) => s.type !== 'START' && s.type !== 'END') || []).length || 1) - 1 }

function onCloseDesigner() {
  designerMode.value = false
  loadWorkflows()
}

// ===== Tickets (pipeline-driven) =====
const loadingTickets = ref(false)
const tickets = ref<any[]>([])
const ticketFilter = ref('')
const router = useRouter()

async function loadTickets() {
  loadingTickets.value = true
  try {
    const params: any = {}
    if (ticketFilter.value) params.current_status = ticketFilter.value
    const res = await ticketApi.list(params)
    tickets.value = res?.results || res?.data || res || []
    reportInlineStats()
  } finally { loadingTickets.value = false }
}
// ===== 工单分派 =====
const assignTicketVisible = ref(false)
const assignUserId = ref<number | null>(null)
const assignTicketRow = ref<any>(null)
const userOptions = ref<any[]>([])
const usersLoading = ref(false)

const filteredUserOptions = computed(() => userOptions.value)

async function loadAllUsers() {
  usersLoading.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = ((res as any).data || []).map((item: any) => ({
      id: item.value,
      name: item.label,
    }))
  } catch { userOptions.value = [] }
  usersLoading.value = false
}
async function ticketAssign(row: any) {
  assignTicketRow.value = row
  assignUserId.value = null
  if (!userOptions.value.length) await loadAllUsers()
  assignTicketVisible.value = true
}
async function confirmAssignTicket() {
  if (!assignTicketRow.value || !assignUserId.value) return
  try {
    await AssignTicket(assignTicketRow.value.id, assignUserId.value)
    ElMessage.success('工单已分派')
    assignTicketVisible.value = false
    assignTicketRow.value = null
    assignUserId.value = null
    await loadTickets()
  } catch { ElMessage.error('分派失败') }
}

// 从服务市场提交后跳转到工单详情页进行填单
function onGoTicket(ticketId: number) {
  router.push('/apps/itsm/ticket/' + ticketId)
}

async function onSubmitTicket(row: any) {
  if (!row?.id) { ElMessage.error('无效工单'); return }
  try {
    await SubmitTicket(row.id)
    ElMessage.success('工单已提交，pipeline 已启动')
    await loadTickets()
  } catch (e: any) {
    ElMessage.error(e?.msg || e?.message || '提交失败')
  }
}

function onViewTicket(row: any) {
  if (row?.id) router.push('/apps/itsm/ticket/' + row.id)
}

async function onCloseTicket(row: any) {
  try {
    await CloseTicket(row.id)
    ElMessage.success('工单已关闭')
    await loadTickets()
  } catch (e: any) {
    ElMessage.error(e?.msg || '关闭失败')
  }
}

// ===== Workflows (pipeline templates) =====
const loadingWf = ref(false)
const workflows = ref<any[]>([])
const wfFilter = ref('')
const showAICreate = ref(false)
const aiDescription = ref('')
const aiType = ref('change')
const aiLoading = ref(false)
const aiResult = ref<any>(null)
const savingWf = ref(false)
// Version dialog state
const showVersionDialog = ref(false)
const versionDialogWf = ref<any>(null)
const versionList = ref<any[]>([])
const versionLoading = ref(false)
// Rollback dialog state
const showRollbackDialog = ref(false)
const rollbackTarget = ref<any>(null)
const rollbackLoading = ref(false)

async function loadWorkflows() {
  loadingWf.value = true
  try {
    const params: any = {}
    if (wfFilter.value) params.itsm_type = wfFilter.value
    const res = await workflowApi.list(params)
    workflows.value = res?.results || res?.data || res || []
    reportInlineStats()
  } finally { loadingWf.value = false }
}

async function onDeployWorkflow(wf: any) {
  const msg = await ElMessageBox.prompt('版本说明（可选）', '部署流程').catch(() => null)
  if (msg === null) return
  try {
    await DeployWorkflow(wf.id, msg?.value || '')
    ElMessage.success('部署成功')
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '部署失败')
  }
}

async function onOpenVersions(wf: any) {
  versionDialogWf.value = wf
  versionList.value = []
  versionLoading.value = true
  showVersionDialog.value = true
  try {
    const res = await workflowVersionApi.list({ workflow: wf.id })
    versionList.value = res?.results || res?.data || []
  } catch { versionList.value = [] }
  finally { versionLoading.value = false }
}
function onVersionDialogClosed() {
  versionDialogWf.value = null
  versionList.value = []
}
function onRollbackClick(ver: any) {
  rollbackTarget.value = ver
  showRollbackDialog.value = true
}
async function confirmRollback() {
  if (!rollbackTarget.value) return
  rollbackLoading.value = true
  try {
    await RollbackVersion(rollbackTarget.value.id)
    ElMessage.success('已回滚并创建新版本')
    showRollbackDialog.value = false
    // Refresh the version list in the dialog
    if (versionDialogWf.value) {
      versionLoading.value = true
      const res = await workflowVersionApi.list({ workflow: versionDialogWf.value.id })
      versionList.value = res?.results || res?.data || []
      versionLoading.value = false
    }
  } catch { ElMessage.error('回滚失败') }
  finally { rollbackLoading.value = false }
}
async function onDeleteVersion(ver: any) {
  try {
    await workflowVersionApi.delete(ver.id)
    ElMessage.success("版本已删除")
    // Refresh the version list in the dialog
    if (versionDialogWf.value) {
      versionLoading.value = true
      const res = await workflowVersionApi.list({ workflow: versionDialogWf.value.id })
      versionList.value = res?.results || res?.data || []
      versionLoading.value = false
    }
  } catch { ElMessage.error("删除失败") }
}
async function onDeleteWorkflow(wf: any) {
  try {
    await ElMessageBox.confirm(
      `确定要删除流程模板「${wf.name}」吗？此操作不可恢复。`,
      '删除确认',
      { confirmButtonText: '确认删除', cancelButtonText: '取消', type: 'warning' }
    )
  } catch {
    return // user cancelled
  }
  try {
    await workflowApi.delete(wf.id)
    ElMessage.success('流程模板已删除')
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '删除失败')
  }
}

function showWfDetail(wf: any) {
  ElMessage.info(`模板: ${wf.name}\n类型: ${wf.itsm_type}\n状态: ${wf.is_draft ? '草稿' : '已发布'}`)
}

async function onAIGenerate() {
  if (!aiDescription.value) {
    ElMessage.warning('请输入审批需求描述')
    return
  }
  aiLoading.value = true
  aiResult.value = null
  try {
    const res = await AIGenerateWorkflow(aiDescription.value, aiType.value)
    aiResult.value = res.data || res
  } catch (e: any) {
    ElMessage.error(e?.msg || '生成失败')
  } finally { aiLoading.value = false }
}

async function onSaveAIWorkflow() {
  if (!aiResult.value) return
  savingWf.value = true
  try {
    const wfData = aiResult.value.workflow || {}
    const res = await workflowApi.create({
      name: wfData.name || `AI-${aiType.value}-${Date.now()}`,
      itsm_type: aiType.value,
      description: wfData.description || aiDescription.value,
    })
    const wf = res.data?.data || res.data || res
    // Create states via state API
    for (const state of aiResult.value.states || []) {
      await stateApi.create({ ...state, workflow: wf.id })
    }
    // Create transitions via transition API
    for (const trans of aiResult.value.transitions || []) {
      await transitionApi.create({ ...trans, workflow: wf.id })
    }
    ElMessage.success('流程模板已创建，可在「流程模板」中查看并部署')
    showAICreate.value = false
    aiResult.value = null
    aiDescription.value = ''
    await loadWorkflows()
  } catch (e: any) {
    ElMessage.error(e?.msg || '保存失败')
  } finally { savingWf.value = false }
}

// ===== SLA =====
const loadingSla = ref(false)
const slaPolicies = ref<any[]>([])
async function loadSla() {
  loadingSla.value = true
  try { const res = await slaPolicyApi.list(); slaPolicies.value = res?.results || res?.data || res || []; reportInlineStats() } finally { loadingSla.value = false }
}

// ===== SLA Edit =====
const showSlaEdit = ref(false)
const savingSla = ref(false)
const slaForm = ref<any>({ name: '', priority: 'P3', response_minutes: 60, resolve_minutes: 480, is_active: true })

function onSlaEdit(row: any) {
  slaForm.value = { ...row }
  showSlaEdit.value = true
}

async function onSlaSave() {
  savingSla.value = true
  try {
    const { id, name, response_minutes, resolve_minutes, is_active } = slaForm.value
    await slaPolicyApi.update(id, { name, response_minutes, resolve_minutes, is_active })
    ElMessage.success('保存成功')
    showSlaEdit.value = false
    await loadSla()
  } catch { ElMessage.error('保存失败') }
  savingSla.value = false
}

async function onSlaToggle(row: any) {
  try { await slaPolicyApi.update(row.id, { is_active: row.is_active }) } catch { row.is_active = !row.is_active }
}

// ===== Utility =====
function statusLabel(s: string) {
  const m: Record<string, string> = {
    draft: t('message.itsmPage.statusDraft'),
    assigned: t('message.itsmPage.statusAssigned'),
    receiving: t('message.itsmPage.statusReceiving'),
    running: t('message.itsmPage.statusRunning'),
    escalated: t('message.itsmPage.statusEscalated'),
    suspended: t('message.itsmPage.statusSuspended'),
    finished: t('message.itsmPage.statusFinished'),
    terminated: t('message.itsmPage.statusTerminated'),
    failed: t('message.itsmPage.statusFailed'),
    success: '成功', firing: '触发中', acknowledged: '已确认', resolved: '已恢复',
  }
  return m[s] || s || t('message.common.empty') || ''
}

function formatSla(seconds: number): string {
  if (seconds <= 0) return t('message.itsmPage.slaOverdue')
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const hr = t('message.itsmPage.slaHours')
  const mi = t('message.itsmPage.slaMinutes')
  if (h > 0) return `${h}${hr}${m}${mi}`
  return `${m}${mi}`
}

// ===== Escalation Levels =====
const loadingEsc = ref(false)
const escalationLevels = ref<any[]>([])
const showEscEdit = ref(false)
const savingEsc = ref(false)
const escForm = ref<any>({ level: 1, name: '', timeout_minutes: 60, action: 'notify_only', notify_users: '', is_active: true })
const escNotifyUsers = ref<string[]>([])
const escUserOptions = ref<any[]>([])
const escUsersLoading = ref(false)

function escActionLabel(action: string): string {
  const m: Record<string, string> = { notify_only: '仅通知', transfer_leader: '转给组长', transfer_next: '升级到下一级', notify_users: '通知用户' }
  return m[action] || action
}

function escExtractUsername(label: string): string {
  const m = label.match(/\((\w+)\)$/)
  return m ? m[1] : label
}

async function loadEscUsers() {
  escUsersLoading.value = true
  try {
    const { request } = await import('/@/utils/service')
    const res = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 10000 } })
    escUserOptions.value = ((res as any).data || []).map((item: any) => ({
      value: escExtractUsername(item.label),
      label: item.label,
    }))
  } catch { escUserOptions.value = [] }
  escUsersLoading.value = false
}

// Sync escForm.notify_users ↔ escNotifyUsers
function syncEscNotifyUsers() {
  const us = escForm.value.notify_users ? escForm.value.notify_users.split(',').filter(Boolean) : []
  escNotifyUsers.value = escUserOptions.value
    .filter(o => us.includes(o.value))
    .map(o => o.value)
}
function syncEscNotifyUsersStr() {
  escForm.value.notify_users = escNotifyUsers.value.join(',')
}

async function loadEscalation() {
  loadingEsc.value = true
  try { const res = await escalationApi.list(); escalationLevels.value = res?.results || res?.data || res || []; reportInlineStats() } finally { loadingEsc.value = false }
}

function onEscalationCreate() {
  escForm.value = { level: 1, name: '', timeout_minutes: 60, action: 'notify_only', notify_users: '', is_active: true }
  escNotifyUsers.value = []
  showEscEdit.value = true
  loadEscUsers()
}

async function onEscEdit(row: any) {
  escForm.value = { ...row }
  showEscEdit.value = true
  await loadEscUsers()
  syncEscNotifyUsers()
}

async function onEscSave() {
  savingEsc.value = true
  try {
    const data = { ...escForm.value }
    if (data.id) {
      await escalationApi.update(data.id, data)
    } else {
      await escalationApi.create(data)
    }
    ElMessage.success('保存成功')
    showEscEdit.value = false
    await loadEscalation()
  } catch { ElMessage.error('保存失败') }
  savingEsc.value = false
}

async function onEscDelete(row: any) {
  try {
    await ElMessageBox.confirm(`确定删除升级级别「${row.name}」吗？`, '删除确认', { type: 'warning' })
    await escalationApi.delete(row.id)
    ElMessage.success('已删除')
    await loadEscalation()
  } catch { /* cancelled */ }
}

async function onEscToggle(row: any) {
  try { await escalationApi.update(row.id, { is_active: row.is_active }) } catch { row.is_active = !row.is_active }
}

// ===== Project change trigger (replaces window event listener) =====
const projectChangedTrigger = ref(0)
function onProjectChanged() { projectChangedTrigger.value++ }

// ===== Tab lazy loading =====
const { isVisited } = useTabLazyLoad({
  tabs: ['dashboard', 'service-market', 'service-admin', 'tickets', 'workflows', 'sla', 'delegation', 'escalation'],
  activeTab,
  onTabActivated: (tab, firstVisit) => {
    if (!firstVisit) return
    // Inline tabs: manually trigger data load on first visit
    if (tab === 'tickets') loadTickets()
    else if (tab === 'workflows') loadWorkflows()
    else if (tab === 'sla') loadSla()
    else if (tab === 'escalation') loadEscalation()
    // Component tabs (dashboard/service-market/service-admin/delegation):
    // their own onMounted fires automatically when v-if becomes true
  },
  resetOn: projectChangedTrigger,
})

// ===== Hero stats provider =====
const { stats: heroStats, searchRef: heroSearchRef, updateStats } = useHeroProvider()

// Initialize default stats (replaced by sub-tab reportStats when data loads)
updateStats([
  { value: 0, label: '工单' },
  { value: 0, label: '流程' },
  { value: 0, label: 'SLA' },
])

// Watch activeTab: reset stats to tab-appropriate defaults when switching
watch(activeTab, (tab) => {
  if (tab === 'dashboard') {
    updateStats([
      { value: '-', label: '待处理' },
      { value: '-', label: '已逾期' },
      { value: '-', label: '今日解决' },
      { value: '-', label: '平均解决(h)' },
    ])
  } else if (tab === 'service-market') {
    updateStats([
      { value: '-', label: '服务总数' },
      { value: '-', label: '流程模式' },
      { value: '-', label: '轻量模式' },
    ])
  } else if (tab === 'service-admin') {
    updateStats([
      { value: '-', label: '服务总数' },
      { value: '-', label: '已启用' },
      { value: '-', label: '已禁用' },
    ])
  } else if (tab === 'tickets') {
    updateStats([
      { value: '-', label: '工单总数' },
      { value: '-', label: '处理中' },
      { value: '-', label: '草稿' },
      { value: '-', label: '已完成' },
    ])
  } else if (tab === 'workflows') {
    updateStats([
      { value: '-', label: '模板总数' },
      { value: '-', label: '已发布' },
      { value: '-', label: '草稿' },
    ])
  } else if (tab === 'sla') {
    updateStats([
      { value: '-', label: '策略总数' },
      { value: '-', label: '已启用' },
    ])
  } else if (tab === 'delegation') {
    updateStats([
      { value: '-', label: '规则总数' },
      { value: '-', label: '已启用' },
    ])
  } else if (tab === 'escalation') {
    updateStats([
      { value: '-', label: '层级总数' },
      { value: '-', label: '已启用' },
    ])
  }
  // Other tabs: sub-components report their own stats via useHeroConsumer
})

/** Report stats for inline tabs when data is loaded for the current active tab */
function reportInlineStats() {
  const tab = activeTab.value
  if (tab === 'tickets') {
    const items = tickets.value
    updateStats([
      { value: items.length, label: '工单总数' },
      { value: items.filter((t: any) => t.current_status === 'running').length, label: '处理中' },
      { value: items.filter((t: any) => t.current_status === 'draft').length, label: '草稿' },
      { value: items.filter((t: any) => t.current_status === 'finished').length, label: '已完成' },
    ])
  } else if (tab === 'workflows') {
    const items = workflows.value
    updateStats([
      { value: items.length, label: '模板总数' },
      { value: items.filter((w: any) => !w.is_draft).length, label: '已发布' },
      { value: items.filter((w: any) => w.is_draft).length, label: '草稿' },
    ])
  } else if (tab === 'sla') {
    const items = slaPolicies.value
    updateStats([
      { value: items.length, label: '策略总数' },
      { value: items.filter((s: any) => s.is_active).length, label: '已启用' },
    ])
  } else if (tab === 'escalation') {
    const items = escalationLevels.value
    updateStats([
      { value: items.length, label: '层级总数' },
      { value: items.filter((e: any) => e.is_active).length, label: '已启用' },
    ])
  }
}

onMounted(async () => {
  await loadPageConfig()
  // loadAllData removed — data loads on-demand via useTabLazyLoad

  // Project switch: increment trigger → composable resets visitedTabs → current tab remounts
  window.addEventListener('project-changed', onProjectChanged)

  const key = 'opsflow_tour_itsm'
  if (!localStorage.getItem(key)) {
    ElMessage.info({ message: '🎫 ITSM — 全新 pipeline 驱动工单引擎，支持 AI 创建审批流程', duration: 1500 })
    localStorage.setItem(key, 'true')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('project-changed', onProjectChanged)
})
</script>

<style lang="scss" scoped>
@use '/@/styles/global' as *;

.itsm-page {
  position: absolute; top: 0; left: 0; right: 0; bottom: 0;
  display: flex; flex-direction: column;
  background: #f5f6fa; overflow: hidden;
}

/* ===== Hero ===== */
.itsm-hero { @include g-hero-container; }
.itsm-hero-bg { @include g-hero-bg-dots; }
.itsm-hero-inner { @include g-hero-inner; flex-direction: row; }
.itsm-hero-left { flex: 1 1 auto; }
.itsm-hero-title { @include g-hero-title; }
.itsm-hero-subtitle { @include g-hero-subtitle; }
.itsm-hero-search {
  margin-left: auto; margin-right: 20px;
  display: flex; align-items: center;
  :deep(.sm-search-input),
  :deep(.sa-search-input) { width: 280px; }
  :deep(.el-input__wrapper) {
    background: rgba(255,255,255,0.1);
    border: 1px solid rgba(255,255,255,0.12);
    box-shadow: none; border-radius: 10px;
  }
  :deep(.el-input__inner) { color: #fff; font-size: 14px; }
  :deep(.el-input__inner::placeholder) { color: rgba(255,255,255,0.4); }
  :deep(.el-input__prefix-inner) { color: rgba(255,255,255,0.4); }
}
.itsm-hero-stats { flex: 0 0 auto; display: flex; align-items: center; gap: 6px; }
.itsm-stat-item { text-align: center; padding: 0 10px; }
.itsm-stat-value { @include g-hero-stat-value; }
.itsm-stat-label { @include g-hero-stat-label; text-transform: uppercase; letter-spacing: 0.5px; }
.itsm-stat-divider { @include g-hero-stat-divider; flex-shrink: 0; }

.itsm-hero-tabs { @include g-hero-tabs; }
.itsm-hero-tab { @include g-hero-tab;
  .el-icon { font-size: 16px; }
  &.locked { opacity: 0.6; }
  &.locked:hover { opacity: 0.9; background: rgba(255,193,7,0.1); border-bottom-color: #ffc107; }
  .tab-lock { font-size: 11px; margin-left: 3px; }
}

/* ===== Body ===== */
.itsm-body { flex: 1; overflow-y: auto; padding: 0 20px 24px; }
.itsm-section { padding-top: 16px; }

/* ===== Filter bar ===== */
.itsm-filter-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 0 12px; gap: 16px; position: sticky; top: 0; z-index: 10; background: #f5f6fa;
}
.itsm-filter-tabs { display: flex; gap: 2px; }
.itsm-tab {
  display: flex; align-items: center; gap: 6px; padding: 7px 16px;
  border-radius: 20px; font-size: 13px; font-weight: 500; color: #606266;
  cursor: pointer; transition: all 0.2s; user-select: none;
}
.itsm-tab:hover { background: rgba(64,158,255,0.06); color: #409EFF; }
.itsm-tab.active { background: #409EFF; color: #fff; box-shadow: 0 2px 8px rgba(64,158,255,0.3); }
.itsm-tab-dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.itsm-filter-actions { display: flex; gap: 8px; align-items: center; flex-shrink: 0; }

/* ===== Table Card ===== */
.itsm-table-card {
  background: #fff; border-radius: 14px; box-shadow: $g-shadow-card; overflow: hidden;
}
.itsm-table-card :deep(.el-table th.el-table__cell) { background: #fafafa; color: #606266; font-weight: 600; font-size: 12px; }
.itsm-table-card :deep(.el-table__body tr:hover td) { background: #f5f7fa; }
.itsm-table-header {
  display: flex; justify-content: space-between; align-items: center; padding: 16px 20px 0;
}
.itsm-table-title { font-size: 15px; font-weight: 600; color: $g-text-primary; }

/* ===== Status Badge ===== */
.itsm-status-badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 500; padding: 2px 10px; border-radius: 10px;
}
.itsm-status-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; }
.it-status-draft .itsm-status-dot { background: #c0c4cc; }
.it-status-draft { background: #f5f7fa; color: #909399; }
.it-status-running .itsm-status-dot { background: #409EFF; }
.it-status-running { background: #ecf5ff; color: #409EFF; }
.it-status-finished .itsm-status-dot,
.it-status-success .itsm-status-dot,
.it-status-resolved .itsm-status-dot { background: #67C23A; }
.it-status-finished { background: #f0f9eb; color: #67C23A; }
.it-status-success { background: #f0f9eb; color: #67C23A; }
.it-status-resolved { background: #f0f9eb; color: #67C23A; }
.it-status-terminated .itsm-status-dot,
.it-status-failed .itsm-status-dot,
.it-status-danger .itsm-status-dot,
.it-status-escalated .itsm-status-dot { background: #F56C6C; }
.it-status-terminated { background: #fef0f0; color: #F56C6C; }
.it-status-failed { background: #fef0f0; color: #F56C6C; }
.it-status-suspended .itsm-status-dot { background: #E6A23C; }
.it-status-suspended { background: #fdf6ec; color: #E6A23C; }
.it-status-new .itsm-status-dot,
.it-status-open .itsm-status-dot { background: #409EFF; }
.it-status-new { background: #ecf5ff; color: #409EFF; }
.it-status-open { background: #ecf5ff; color: #409EFF; }

.it-status-assigned .itsm-status-dot,
.it-status-pending_approval .itsm-status-dot { background: #E6A23C; }
.it-status-assigned { background: #fdf6ec; color: #E6A23C; }
.it-status-pending_approval { background: #fdf6ec; color: #E6A23C; }

.it-status-closed .itsm-status-dot { background: #c0c4cc; }
.it-status-closed { background: #f5f7fa; color: #909399; }

/* ===== SLA Badge ===== */
.sla-badge { display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 8px; }
.sla-normal { background: #f0f9eb; color: #67C23A; }
.sla-warning { background: #fdf6ec; color: #E6A23C; }
.sla-violated { background: #fef0f0; color: #F56C6C; }

/* ===== Priority Badge ===== */
.itsm-prio-badge {
  display: inline-block; font-size: 11px; font-weight: 600; padding: 2px 10px; border-radius: 10px;
}
.it-prio-p1 { background: #fef0f0; color: #F56C6C; }
.it-prio-p2 { background: #fdf6ec; color: #E6A23C; }
.it-prio-p3,
.it-prio-p4 { background: #f0f9eb; color: #67C23A; }
.it-prio-low { background: #f0f9eb; color: #67C23A; }
.it-prio-medium { background: #fdf6ec; color: #E6A23C; }
.it-prio-high { background: #fef0f0; color: #F56C6C; }
.it-prio-critical { background: #fbe9e7; color: #D32F2F; }

/* ===== Workflow Grid ===== */
.itsm-wf-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(315px, 1fr)); gap: 14px;
}
.itsm-wf-card {
  border-radius: $g-radius-card; overflow: hidden; @include g-hover-lift;
}
.itsm-wf-card-inner {
  background: #fff; border: 1px solid $g-border-default; border-radius: $g-radius-card;
  padding: 18px; height: 100%; display: flex; flex-direction: column;
}
.itsm-wf-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.itsm-wf-type-tag {
  display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
}
.wf-type-change { background: #fdf6ec; color: #E6A23C; }
.wf-type-incident { background: #fef0f0; color: #F56C6C; }
.itsm-wf-name { font-weight: 600; font-size: 15px; color: $g-text-primary; margin-bottom: 6px; }
.itsm-wf-desc { font-size: 12px; color: $g-text-secondary; line-height: 1.5; flex: 1; margin-bottom: 10px; }
.itsm-wf-meta { font-size: 11px; color: $g-text-muted; display: flex; justify-content: space-between; margin-bottom: 10px; }
.itsm-wf-actions { display: flex; gap: 0px; padding-top: 8px; border-top: 1px solid $g-border-light; flex-wrap: nowrap; font-size: 11px; }
.itsm-wf-actions .el-button { padding: 2px 6px; height: auto; font-size: 12px; }
.itsm-wf-empty { grid-column: 1 / -1; }

/* ===== Dialog ===== */
.itsm-dialog :deep(.el-dialog__header) { @include g-dialog-header; }
.itsm-dialog :deep(.el-dialog__body) { @include g-dialog-body; }
.itsm-dialog :deep(.el-dialog__footer) { @include g-dialog-footer; }

/* ===== AI Preview ===== */
.itsm-ai-preview {
  border: 1px solid $g-border-blue; border-radius: 8px; padding: 14px; background: $g-bg-light-blue;
}
.itsm-ai-preview-header { font-size: 13px; font-weight: 600; margin-bottom: 10px; color: $g-text-primary; }
.itsm-ai-flow { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.itsm-ai-node { display: inline-flex; align-items: center; gap: 2px; font-size: 12px; }
.itsm-ai-node-badge {
  font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px;
}
.node-approval { background: #fdf6ec; color: #E6A23C; }
.node-normal { background: #ecf5ff; color: #409EFF; }
.node-task { background: #f0f9eb; color: #67C23A; }

</style>
