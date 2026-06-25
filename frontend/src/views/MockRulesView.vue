<template>
  <PageLayout
    :title="$t('mockRules.title')"
    compact
    :loading="loading && activeTab === 'rules'"
    :empty="filteredRules.length === 0 && !loading && activeTab === 'rules' && !error"
    :empty-title="$t('mockRules.noRules')"
    :empty-description="$t('mockRules.noRulesDesc')"
    :empty-icon="TestTube"
    :error="error"
    @retry="loadRules()"
  >
    <template #hero-meta>
      <div class="mock-hero-kicker">{{ $t('mockRules.kicker') }}</div>
    </template>

    <template #hero-extra>
      <div class="mock-hero-extra">
        <el-button type="primary" size="small" @click="openCreateDialog"><Plus :size="14" /> {{ $t('mockRules.newRule') }}</el-button>
        <div class="mock-hero-stats">
          <div class="mock-hero-stat"><span class="mock-stat-val">{{ total }}</span><span class="mock-stat-lbl">{{ $t('mockRules.totalRules') }}</span></div>
          <div class="mock-hero-stat"><span class="mock-stat-val">{{ filteredRules.filter((rule) => rule.enabled).length }}</span><span class="mock-stat-lbl">{{ $t('mockRules.enabledCount') }}</span></div>
          <div class="mock-hero-stat"><span class="mock-stat-val">{{ filteredRules.filter((rule) => !rule.enabled).length }}</span><span class="mock-stat-lbl">{{ $t('mockRules.disabledCount') }}</span></div>
        </div>
      </div>
    </template>

    <template #filter>
      <el-input
        v-model="rawSearch"
        :placeholder="$t('mockRules.searchPlaceholder')"
        :aria-label="$t('mockRules.searchPlaceholder')"
        clearable
        size="small"
        class="filter-input-search"
      >
        <template #prefix>
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="m21 21-4.3-4.3" />
          </svg>
        </template>
      </el-input>
      <el-select v-model="enabledFilter" :placeholder="$t('mockRules.statusFilterPlaceholder')" size="small" class="filter-input-status">
        <el-option :label="$t('mockRules.all')" value="all" />
        <el-option :label="$t('mockRules.enabled')" value="enabled" />
        <el-option :label="$t('mockRules.disabled')" value="disabled" />
      </el-select>
      <el-select
        v-model="methodFilter"
        :placeholder="$t('mockRules.methodFilterPlaceholder')"
        clearable
        size="small"
        class="filter-input-method"
      >
        <el-option label="GET" value="GET" />
        <el-option label="POST" value="POST" />
        <el-option label="PUT" value="PUT" />
        <el-option label="DELETE" value="DELETE" />
        <el-option label="PATCH" value="PATCH" />
        <el-option :label="$t('mockRules.any')" value="*" />
      </el-select>
    </template>

    <template #loading>
      <SkeletonTable :rows="5" />
    </template>

    <template #empty-action>
      <div class="empty-state-actions">
        <el-button type="primary" size="small" @click="openCreateDialog">{{ $t('mockRules.newRule') }}</el-button>
        <el-button size="small" @click="router.push(`/projects/${projectId}/apis`)">
          {{ $t('mockRules.goToApis') }}
        </el-button>
      </div>
    </template>

    <!-- Mock 服务地址信息卡片 -->
    <div v-if="activeTab === 'rules'" class="mock-service-banner">
      <div class="banner-left">
        <div class="banner-icon">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 17v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1"/>
            <polyline points="7 11 12 6 17 11"/>
            <line x1="12" y1="6" x2="12" y2="19"/>
          </svg>
        </div>
        <div class="banner-content">
          <div class="banner-title">{{ $t('mockRules.serviceAddress') }}</div>
          <div class="banner-url-row">
            <code class="banner-url">{{ getMockBaseUrl() }}/</code>
            <button class="banner-copy-btn" @click="copyMockBaseUrl" :title="$t('mockRules.copyUrl')">
              <Copy :size="14" />
              <span>{{ $t('mockRules.copyUrl') }}</span>
            </button>
          </div>
          <div class="banner-desc">{{ $t('mockRules.serviceDesc') }}</div>
        </div>
      </div>
      <button v-if="!hintDismissed" class="banner-close" :aria-label="$t('mockRules.closeHint')" @click="hintDismissed = true">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- Tab 切换 -->
    <div class="mock-tabs">
      <button class="mock-tab" :class="{ active: activeTab === 'rules' }" @click="activeTab = 'rules'">{{ $t('mockRules.rulesTab') }}</button>
      <button class="mock-tab" :class="{ active: activeTab === 'logs' }" @click="activeTab = 'logs'; loadCallLogs()">{{ $t('mockRules.callLogsTab') }}</button>
      <button class="mock-tab" :class="{ active: activeTab === 'stats' }" @click="activeTab = 'stats'; loadStats()">{{ $t('mockRules.statsTab') }}</button>
    </div>

    <!-- 规则列表 Tab -->
    <template v-if="activeTab === 'rules'">
      <!-- 规则列表 -->
      <div class="rule-list" ref="scrollContainer">
        <div :style="virtualEnabled ? totalHeightStyle : { display: 'contents' }">
          <div :style="virtualEnabled ? [offsetStyle, { display: 'flex', flexDirection: 'column', gap: 'var(--space-1-5)' }] : { display: 'contents' }">
            <div
              v-for="rule in (virtualEnabled ? virtualVisibleItems : filteredRules)"
              :key="rule.id"
              class="rule-card"
              :class="{ disabled: !rule.enabled }"
            >
              <div class="rule-card-left">
                <div class="rule-method-badge" :class="methodClass(rule.match_method)">
                  {{ rule.match_method === "*" ? "ANY" : rule.match_method }}
                </div>
                <div class="rule-path highlight-path">{{ rule.match_path }}</div>
              </div>
              <div class="rule-card-center">
                <div class="rule-name">{{ rule.name }}</div>
                <div class="rule-meta">
                  <span class="rule-status" :class="{ on: rule.enabled }">
                    <span class="status-dot"></span>
                    {{ rule.enabled ? $t('mockRules.enabled') : $t('mockRules.disable') }}
                  </span>
                  <span class="rule-sep">·</span>
                  <span>{{ $t('mockRules.statusCode') }} {{ rule.response_status }}</span>
                  <span v-if="rule.response_delay" class="rule-sep">·</span>
                  <span v-if="rule.response_delay">{{ $t('mockRules.delay') }} {{ rule.response_delay }}ms</span>
                  <span v-if="rule.priority" class="rule-sep">·</span>
                  <span v-if="rule.priority">{{ $t('mockRules.priority') }} {{ rule.priority }}</span>
                </div>
                <div class="rule-mock-url" v-if="getMockUrl(rule)">
                  <span class="mock-url-text">{{ getMockUrl(rule) }}</span>
                  <button class="icon-btn mock-url-copy" @click="copyMockUrl(rule)" :title="$t('mockRules.copyMockUrl')" :aria-label="$t('mockRules.copyMockUrl')">
                    <Copy :size="12" />
                  </button>
                </div>
              </div>
              <div v-if="canEdit" class="rule-card-right">
                <el-tooltip :content="$t('mockRules.editTooltip')" placement="top">
                  <button class="icon-btn" :aria-label="$t('mockRules.editTooltip')" @click="editRule(rule)"><Pencil :size="14" /></button>
                </el-tooltip>
                <el-tooltip :content="$t('mockRules.copyTooltip')" placement="top">
                  <button class="icon-btn" :aria-label="$t('mockRules.copyTooltip')" @click="duplicateRule(rule)"><Copy :size="14" /></button>
                </el-tooltip>
                <el-tooltip :content="rule.enabled ? $t('mockRules.disableTooltip') : $t('mockRules.enableTooltip')" placement="top">
                  <button class="icon-btn" :aria-label="rule.enabled ? $t('mockRules.disableTooltip') : $t('mockRules.enableTooltip')" @click="toggleRule(rule)">
                    <ToggleLeft :size="14" v-if="rule.enabled" />
                    <ToggleRight :size="14" v-else />
                  </button>
                </el-tooltip>
                <el-tooltip :content="$t('mockRules.deleteTooltip')" placement="top">
                  <button class="icon-btn icon-btn-danger" :aria-label="$t('mockRules.deleteTooltip')" @click="confirmDelete(rule)">
                    <Trash2 :size="14" />
                  </button>
                </el-tooltip>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 调用日志 Tab -->
    <template v-if="activeTab === 'logs'">
      <div class="call-logs-toolbar">
        <el-date-picker
          v-model="logDateRange"
          type="daterange"
          :range-separator="$t('mockRules.to')"
          :start-placeholder="$t('mockRules.startDate')"
          :end-placeholder="$t('mockRules.endDate')"
          size="small"
          value-format="YYYY-MM-DD"
          style="width: 280px"
          @change="loadCallLogs"
        />
        <el-button size="small" type="danger" @click="doClearCallLogs" :loading="clearingLogs">{{ $t('mockRules.clearLogs') }}</el-button>
      </div>
      <el-table :data="callLogs" border size="small" v-loading="logsLoading" max-height="500">
        <el-table-column prop="created_at" :label="$t('mockRules.timeCol')" width="180">
          <template #default="{ row }">
            {{ formatLogTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="request_method" :label="$t('mockRules.methodCol')" width="80" align="center">
          <template #default="{ row }">
            <span class="rule-method-badge" :class="methodClass(row.request_method)" style="font-size: var(--text-2xs)">
              {{ row.request_method }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="request_path" :label="$t('mockRules.pathCol')" min-width="200" />
        <el-table-column prop="matched_rule_name" :label="$t('mockRules.matchedRuleCol')" min-width="150">
          <template #default="{ row }">
            <span v-if="row.matched_rule_name">{{ row.matched_rule_name }}</span>
            <el-tag v-else type="danger" size="small">{{ $t('mockRules.unmatched') }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_status" :label="$t('mockRules.statusCodeCol')" width="80" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.response_status >= 400 ? 'var(--color-danger)' : 'var(--color-success)' }">
              {{ row.response_status }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" :label="$t('mockRules.durationCol')" width="80" align="center">
          <template #default="{ row }">
            {{ row.duration_ms }}ms
          </template>
        </el-table-column>
      </el-table>
      <div class="page-foot" v-if="logsTotal > 20">
        <el-pagination
          background
          layout="prev,pager,next"
          :total="logsTotal"
          :page-size="20"
          @current-change="(p: number) => { logsPage = p; loadCallLogs() }"
        />
      </div>
    </template>

    <!-- 统计 Tab -->
    <template v-if="activeTab === 'stats'">
      <MockStatistics :stats="mockStats" :call-trend="callTrend" :match-rate="matchRate" />
    </template>

    <template #footer>
      <el-pagination
        v-if="activeTab === 'rules' && total > 20"
        background
        layout="prev,pager,next"
        :total="total"
        :page-size="20"
        @current-change="loadRules"
      />
    </template>

    <!-- 新建/编辑弹窗 -->
    <el-drawer
      v-model="showDialog"
      :title="editingId ? $t('mockRules.editDialogTitle') : $t('mockRules.newDialogTitle')"
      direction="rtl"
      size="520px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form :model="form" label-width="100px" size="small" class="mock-form">
        <div class="mock-dialog-body">
          <el-form-item :label="$t('mockRules.ruleNameLabel')" required>
            <el-input
              v-model="form.name"
              :placeholder="$t('mockRules.ruleNamePlaceholder')"
              class="rule-name-input"
              :class="{ 'is-error': errors.name }"
            />
            <div v-if="errors.name" class="name-error">{{ errors.name }}</div>
          </el-form-item>

          <!-- WHEN 卡片 -->
          <div class="mock-section-card when-card">
            <div class="mock-section-header">
              <span class="mock-section-badge when">{{ $t('mockRules.whenBadge') }}</span>
              <span class="mock-section-title">{{ $t('mockRules.triggerCondition') }}</span>
            </div>
            <div class="mock-section-body">
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item :label="$t('mockRules.matchMethodLabel')">
                    <el-select v-model="form.match_method" style="width: 100%">
                      <el-option :label="$t('mockRules.any')" value="*" />
                      <el-option label="GET" value="GET" />
                      <el-option label="POST" value="POST" />
                      <el-option label="PUT" value="PUT" />
                      <el-option label="DELETE" value="DELETE" />
                      <el-option label="PATCH" value="PATCH" />
                    </el-select>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item :label="$t('mockRules.matchPathLabel')" required>
                    <el-input v-model="form.match_path" :placeholder="$t('mockRules.matchPathPlaceholder')" />
                  </el-form-item>
                </el-col>
                <el-col :span="4">
                  <el-form-item>
                    <template #label>
                      <el-tooltip :content="$t('mockRules.priorityTooltip')" placement="top">
                        <span class="label-with-hint">{{ $t('mockRules.priorityLabel') }}
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="12"
                            height="12"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            class="hint-icon-small"
                            aria-hidden="true"
                          >
                            <circle cx="12" cy="12" r="10" />
                            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                            <path d="M12 17h.01" /></svg></span>
                      </el-tooltip>
                    </template>
                    <el-input-number v-model="form.priority" :min="0" :max="100" style="width: 100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <!-- 可视化匹配条件 -->
              <div class="conditions-section">
                <div class="conditions-header">
                  <span class="conditions-title">{{ $t('mockRules.matchConditions') }}</span>
                  <el-button size="small" link type="primary" @click="addCondition">
                    <Plus :size="12" /> {{ $t('mockRules.addCondition') }}
                  </el-button>
                </div>
                <div v-if="form.conditions.length === 0" class="conditions-empty">
                  {{ $t('mockRules.noConditionsHint') }}
                </div>
                <div v-for="(cond, ci) in form.conditions" :key="ci" class="condition-row">
                  <el-select v-model="cond.type" size="small" style="width: 120px" :placeholder="$t('mockRules.conditionTypePlaceholder')">
                    <el-option :label="$t('mockRules.paramMatch')" value="param" />
                    <el-option :label="$t('mockRules.headerMatch')" value="header" />
                    <el-option :label="$t('mockRules.bodyMatch')" value="body" />
                  </el-select>
                  <el-input v-model="cond.field" size="small" style="width: 140px" :aria-label="$t('mockRules.matchField')" :placeholder="cond.type === 'header' ? $t('mockRules.headerFieldPlaceholder') : cond.type === 'body' ? $t('mockRules.bodyFieldPlaceholder') : $t('mockRules.paramFieldPlaceholder')" />
                  <el-select v-model="cond.operator" size="small" style="width: 100px" :placeholder="$t('mockRules.matchOperator')">
                    <el-option :label="$t('mockRules.operatorEquals')" value="equals" />
                    <el-option :label="$t('mockRules.operatorContains')" value="contains" />
                    <el-option :label="$t('mockRules.operatorRegex')" value="regex" />
                    <el-option :label="$t('mockRules.operatorNotEquals')" value="not_equals" />
                    <el-option :label="$t('mockRules.operatorExists')" value="exists" />
                  </el-select>
                  <el-input v-model="cond.value" size="small" style="flex:1" :aria-label="$t('mockRules.matchValue')" :placeholder="$t('mockRules.matchValuePlaceholder')" :disabled="cond.operator === 'exists'" />
                  <button class="icon-btn icon-btn-danger" :aria-label="$t('mockRules.deleteCondition')" @click="form.conditions.splice(ci, 1)">
                    <X :size="12" />
                  </button>
                </div>
              </div>

              <el-row :gutter="12">
                <el-col :span="8">
                  <el-form-item :label="$t('mockRules.statusCodeLabel')">
                    <el-input-number
                      v-model="form.response_status"
                      :min="100"
                      :max="599"
                      style="width: 100%"
                    />
                    <div class="preset-row">
                      <button
                        v-for="code in [200, 201, 400, 401, 404, 500]"
                        :key="code"
                        class="preset-btn"
                        :class="{ active: form.response_status === code }"
                        @click="form.response_status = code"
                      >
                        {{ code }}
                      </button>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item :label="$t('mockRules.delayLabel')">
                    <el-input-number
                      v-model="form.response_delay"
                      :min="0"
                      :max="30000"
                      :step="100"
                      style="width: 100%"
                    />
                    <div class="preset-row">
                      <button
                        v-for="d in delayPresets"
                        :key="d.label"
                        class="preset-btn"
                        :class="{ active: form.response_delay === d.value }"
                        @click="form.response_delay = d.value"
                      >
                        {{ d.label }}
                      </button>
                    </div>
                  </el-form-item>
                </el-col>
                <el-col :span="8">
                  <el-form-item :label="$t('mockRules.enableLabel')">
                    <el-switch v-model="form.enabled" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </div>

          <!-- THEN 卡片 -->
          <div class="mock-section-card then-card">
            <div class="mock-section-header">
              <span class="mock-section-badge then">{{ $t('mockRules.thenBadge') }}</span>
              <span class="mock-section-title">{{ $t('mockRules.expectedResponse') }}</span>
            </div>
            <div class="mock-section-body">
              <el-form-item :label="$t('mockRules.responseHeadersLabel')">
            <div class="kv-table">
              <div v-for="(h, i) in form.response_headers" :key="i" class="kv-row">
                <el-input v-model="h.key" :placeholder="$t('mockRules.nameLabel')" :aria-label="$t('mockRules.nameLabel')" size="small" />
                <el-input v-model="h.value" :placeholder="$t('mockRules.valueLabel')" :aria-label="$t('mockRules.valueLabel')" size="small" />
                <button class="icon-btn" :aria-label="$t('mockRules.deleteResponseHeader')" @click="form.response_headers.splice(i, 1)">
                  <X :size="12" />
                </button>
              </div>
              <button
                class="btn-add-row"
                @click="form.response_headers.push({ key: '', value: '' })"
              >
                {{ $t('mockRules.addHeader') }}
              </button>
            </div>
          </el-form-item>
          <el-form-item :label="$t('mockRules.responseBodyLabel')">
            <div class="body-type-tabs">
              <el-radio-group v-model="bodyType" size="small">
                <el-radio value="json">{{ $t('mockRules.jsonType') }}</el-radio>
                <el-radio value="text">{{ $t('mockRules.textType') }}</el-radio>
                <el-radio value="empty">{{ $t('mockRules.emptyType') }}</el-radio>
              </el-radio-group>
            </div>
            <template v-if="bodyType === 'json'">
              <div class="editor-toolbar">
                <button class="toolbar-btn" @click="formatJson" :title="$t('mockRules.formatBtn')">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 6h18" />
                    <path d="M3 12h18" />
                    <path d="M3 18h18" />
                  </svg>
                  {{ $t('mockRules.formatBtn') }}
                </button>
                <button class="toolbar-btn" @click="compressJson" :title="$t('mockRules.compressBtn')">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    aria-hidden="true"
                  >
                    <polyline points="4 14 10 14 10 20" />
                    <polyline points="20 10 14 10 14 4" />
                    <line x1="14" y1="10" x2="21" y2="3" />
                    <line x1="3" y1="21" x2="10" y2="14" />
                  </svg>
                  {{ $t('mockRules.compressBtn') }}
                </button>
                <el-dropdown trigger="click" @command="applyTemplate">
                  <button class="toolbar-btn" :title="$t('mockRules.insertTemplateBtn')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /><rect x="3" y="14" width="7" height="7" />
                    </svg>
                    {{ $t('mockRules.insertTemplateBtn') }}
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item v-for="tpl in jsonTemplates" :key="tpl.label" :command="tpl">{{ tpl.label }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown trigger="click" @command="insertMockFunction">
                  <button class="toolbar-btn" :title="$t('mockRules.insertMockFunction')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
                    </svg>
                    {{ $t('mockRules.mockFunction') }}
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item v-for="fn in mockFunctions" :key="fn.label" :command="fn.value">{{ fn.label }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown trigger="click" @command="insertFakerTemplate">
                  <button class="toolbar-btn" :title="$t('mockRules.insertFakerTemplate')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
                    </svg>
                    {{ $t('mockRules.fakerTemplate') }}
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item v-for="ft in fakerTemplates" :key="ft.label" :command="ft.value">{{ ft.label }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown trigger="click" @command="insertVariable">
                  <button class="toolbar-btn" :title="$t('mockRules.insertVariable')">
                    <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                      <path d="M4 7V4h16v3"/><path d="M9 20h6"/><path d="M12 4v16"/>
                    </svg>
                    {{ $t('mockRules.variable') }}
                  </button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="{{base_url}}">{{base_url}} - {{ $t('mockRules.varBaseUrl') }}</el-dropdown-item>
                      <el-dropdown-item command="{{project_id}}">{{project_id}} - {{ $t('mockRules.varProjectId') }}</el-dropdown-item>
                      <el-dropdown-item command="{{timestamp}}">{{timestamp}} - {{ $t('mockRules.varTimestamp') }}</el-dropdown-item>
                      <el-dropdown-item command="{{random_string}}">{{random_string}} - {{ $t('mockRules.varRandomString') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <button class="toolbar-btn" @click="showSchemaGenerateDialog" :title="$t('mockRules.generateFromSchema')">
                  <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
                  </svg>
                  {{ $t('mockRules.generateFromSchema') }}
                </button>
              </div>
              <div v-if="jsonError" class="json-error-bar">{{ jsonError }}</div>
              <el-input
                v-model="form.response_body"
                type="textarea"
                :rows="10"
                :placeholder="$t('mockRules.responseBodyPlaceholder')"
                :class="{ 'is-error': jsonError }"
              />
            </template>
            <el-input
              v-if="bodyType === 'text'"
              v-model="form.response_body"
              type="textarea"
              :rows="5"
              :placeholder="$t('mockRules.textContentPlaceholder')"
            />
          </el-form-item>
            </div>
          </div>
        </div>
      </el-form>
      <TestPanel
        :project-id="projectId"
        :rules="rules"
        :editing-rule="editingId ? form : undefined"
      />
      <template #footer>
        <el-button size="small" @click="showDialog = false">{{ $t('mockRules.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="saveLock.loading.value" :disabled="saveLock.disabled.value || !isValid.value" @click="saveRule">{{ $t('mockRules.save') }}</el-button>
      </template>
    </el-drawer>

    <!-- 从 Schema 生成 Mock 数据对话框 -->
    <el-dialog
      v-model="schemaGenDialogVisible"
      :title="$t('mockRules.generateFromSchema')"
      width="500px"
      destroy-on-close
    >
      <el-form label-width="100px" size="small">
        <el-form-item :label="$t('mockRules.selectSchema')">
          <el-select v-model="selectedSchemaId" :placeholder="$t('mockRules.selectSchemaPlaceholder')" style="width: 100%">
            <el-option
              v-for="s in schemas"
              :key="s.id"
              :label="s.name"
              :value="s.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!selectedSchemaId" :label="$t('mockRules.customSchema')">
          <el-input
            v-model="customSchemaJson"
            type="textarea"
            :rows="6"
            :placeholder="$t('mockRules.customSchemaPlaceholder')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button size="small" @click="schemaGenDialogVisible = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" :loading="schemaGenLoading" @click="doGenerateFromSchema">{{ $t('mockRules.generate') }}</el-button>
      </template>
    </el-dialog>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from "vue"
import { useRoute, useRouter } from "vue-router"
import { useI18n } from "vue-i18n"
import { msgSuccess, msgWarning, msgError } from "@/utils/message"
import { ElMessageBox } from "element-plus"
import request from "@/api/request"
import { listDataSchemas } from "@/api/schemas"
import { generateFromSchema, getMockCallLogs, clearMockCallLogs, getMockStatistics } from "@/api/mock"
import type { MockCallLog } from "@/api/mock"
import { useRequireLogin } from "@/composables/useRequireLogin"
import { useProjectPermission } from "@/composables/useProjectPermission"
import { useSubmitLock } from "@/composables/useSubmitLock"
import { useFormValidation } from "@/composables/useFormValidation"
import { useDebounce } from "@/composables/useDebounce"
import { useVirtualScroll } from "@/composables/useVirtualScroll"
import SkeletonTable from "@/components/SkeletonTable.vue"
import EmptyState from "@/components/EmptyState.vue"
import PageLayout from "@/components/common/PageLayout.vue"

import TestPanel from "@/components/TestPanel.vue"
import MockStatistics from "@/components/mock/MockStatistics.vue"
import { Plus, Pencil, ToggleLeft, ToggleRight, Trash2, X, TestTube, Copy } from "lucide-vue-next"
import type { MockRule } from "@/types"

const route = useRoute()
const router = useRouter()
const { t: $t } = useI18n()
const projectId = computed(() => Number(route.params.id))
const { requireLogin } = useRequireLogin()
const { canEdit, requireWrite } = useProjectPermission()

const loading = ref(false)
const error = ref<string | null>(null)
const saveLock = useSubmitLock()
const rules = ref<MockRule[]>([])
const total = ref(0)
const methodFilter = ref("")
const rawSearch = ref("")
const searchQuery = useDebounce(() => rawSearch.value, 300)
const enabledFilter = ref<"all" | "enabled" | "disabled">("all")
const hintDismissed = ref(false)

interface SchemaOption { id: number; name: string }
const schemas = ref<SchemaOption[]>([])

async function loadSchemas() {
  try {
    const res = await listDataSchemas(projectId.value, { page_size: 100 })
    schemas.value = res.data.items.map((s) => ({ id: s.id, name: s.name }))
  } catch {
    schemas.value = []
  }
}

const showDialog = ref(false)
const editingId = ref<number | null>(null)
const bodyType = ref<"json" | "text" | "empty">("json")

const defaultForm = () => ({
  name: "",
  enabled: true,
  priority: 0,
  match_method: "*",
  match_path: "/",
  response_status: 200,
  response_headers: [] as { key: string; value: string }[],
  response_body: "",
  response_delay: 0,
  conditions: [] as { type: string; field: string; operator: string; value: string }[],
})
const form = reactive(defaultForm())

const { errors, isValid } = useFormValidation(
  () => form,
  { name: { required: $t('mockRules.ruleNameRequired') } }
)

const delayPresets = [
  { label: "0ms", value: 0 },
  { label: "200ms", value: 200 },
  { label: "500ms", value: 500 },
  { label: "1s", value: 1000 },
  { label: "3s", value: 3000 },
]

const jsonError = computed(() => {
  if (bodyType.value !== "json" || !form.response_body.trim()) return ""
  try {
    JSON.parse(form.response_body)
    return ""
  } catch (e: unknown) {
    return $t('mockRules.jsonFormatError')
  }
})

function formatJson() {
  try {
    const obj = JSON.parse(form.response_body)
    form.response_body = JSON.stringify(obj, null, 2)
  } catch {
    /* invalid JSON, ignore formatting */
  }
}

function compressJson() {
  try {
    const obj = JSON.parse(form.response_body)
    form.response_body = JSON.stringify(obj)
  } catch {
    /* invalid JSON, ignore compression */
  }
}

const jsonTemplates = [
  { label: $t('mockRules.successResponseTpl'), value: JSON.stringify({ code: 200, data: {}, message: "成功" }, null, 2) },
  {
    label: $t('mockRules.paginatedListTpl'),
    value: JSON.stringify(
      { code: 200, data: { list: [], total: 0, page: 1 }, message: "成功" },
      null,
      2
    ),
  },
  { label: $t('mockRules.errorResponseTpl'), value: JSON.stringify({ code: 400, message: "参数错误" }, null, 2) },
  { label: $t('mockRules.emptyDataTpl'), value: JSON.stringify({ code: 200, data: null }, null, 2) },
]

function applyTemplate(tpl: { value: string }) {
  form.response_body = tpl.value
}

// Mock 函数列表
const mockFunctions = [
  { label: `$randomInt() - ${$t('mockRules.mockFuncRandomInt')}`, value: "$randomInt()" },
  { label: `$randomName() - ${$t('mockRules.mockFuncRandomName')}`, value: "$randomName()" },
  { label: `$randomEmail() - ${$t('mockRules.mockFuncRandomEmail')}`, value: "$randomEmail()" },
  { label: `$randomPhone() - ${$t('mockRules.mockFuncRandomPhone')}`, value: "$randomPhone()" },
  { label: `$randomAddress() - ${$t('mockRules.mockFuncRandomAddress')}`, value: "$randomAddress()" },
  { label: `$randomCompany() - ${$t('mockRules.mockFuncRandomCompany')}`, value: "$randomCompany()" },
  { label: `$randomDate() - ${$t('mockRules.mockFuncRandomDate')}`, value: "$randomDate()" },
  { label: `$randomUrl() - ${$t('mockRules.mockFuncRandomUrl')}`, value: "$randomUrl()" },
  { label: `$randomPrice() - ${$t('mockRules.mockFuncRandomPrice')}`, value: "$randomPrice()" },
  { label: `$randomId() - ${$t('mockRules.mockFuncRandomId')}`, value: "$randomId()" },
]

function insertMockFunction(fnValue: string) {
  form.response_body += fnValue
}

function insertVariable(varRef: string) {
  form.response_body += varRef
}

// Faker 模板列表
const fakerTemplates = [
  { label: `{{faker.name}} - ${$t('mockRules.fakerName')}`, value: "{{faker.name}}" },
  { label: `{{faker.firstName}} - ${$t('mockRules.fakerFirstName')}`, value: "{{faker.firstName}}" },
  { label: `{{faker.lastName}} - ${$t('mockRules.fakerLastName')}`, value: "{{faker.lastName}}" },
  { label: `{{faker.email}} - ${$t('mockRules.fakerEmail')}`, value: "{{faker.email}}" },
  { label: `{{faker.phone}} - ${$t('mockRules.fakerPhone')}`, value: "{{faker.phone}}" },
  { label: `{{faker.address}} - ${$t('mockRules.fakerAddress')}`, value: "{{faker.address}}" },
  { label: `{{faker.company}} - ${$t('mockRules.fakerCompany')}`, value: "{{faker.company}}" },
  { label: `{{faker.date}} - ${$t('mockRules.fakerDate')}`, value: "{{faker.date}}" },
  { label: `{{faker.number}} - ${$t('mockRules.fakerNumber')}`, value: "{{faker.number}}" },
  { label: `{{faker.uuid}} - ${$t('mockRules.fakerUuid')}`, value: "{{faker.uuid}}" },
  { label: `{{faker.url}} - ${$t('mockRules.fakerUrl')}`, value: "{{faker.url}}" },
  { label: `{{faker.username}} - ${$t('mockRules.fakerUsername')}`, value: "{{faker.username}}" },
  { label: `{{faker.city}} - ${$t('mockRules.fakerCity')}`, value: "{{faker.city}}" },
  { label: `{{faker.country}} - ${$t('mockRules.fakerCountry')}`, value: "{{faker.country}}" },
  { label: `{{faker.zipCode}} - ${$t('mockRules.fakerZipCode')}`, value: "{{faker.zipCode}}" },
  { label: `{{faker.sentence}} - ${$t('mockRules.fakerSentence')}`, value: "{{faker.sentence}}" },
  { label: `{{faker.paragraph}} - ${$t('mockRules.fakerParagraph')}`, value: "{{faker.paragraph}}" },
  { label: `{{faker.word}} - ${$t('mockRules.fakerWord')}`, value: "{{faker.word}}" },
  { label: `{{faker.boolean}} - ${$t('mockRules.fakerBoolean')}`, value: "{{faker.boolean}}" },
  { label: `{{faker.float}} - ${$t('mockRules.fakerFloat')}`, value: "{{faker.float}}" },
  { label: `{{faker.hex}} - ${$t('mockRules.fakerHex')}`, value: "{{faker.hex}}" },
  { label: `{{faker.color}} - ${$t('mockRules.fakerColor')}`, value: "{{faker.color}}" },
]

function insertFakerTemplate(template: string) {
  form.response_body += template
}

// Schema 生成 Mock 数据
const schemaGenDialogVisible = ref(false)
const selectedSchemaId = ref<number | ''>('')
const customSchemaJson = ref('')
const schemaGenLoading = ref(false)

function showSchemaGenerateDialog() {
  selectedSchemaId.value = ''
  customSchemaJson.value = ''
  schemaGenDialogVisible.value = true
}

async function doGenerateFromSchema() {
  schemaGenLoading.value = true
  try {
    let schemaObj: Record<string, unknown>
    if (selectedSchemaId.value) {
      // 从项目 Schema 获取
      const res = await request.get(`/projects/${projectId.value}/data-schemas/${selectedSchemaId.value}`)
      const schemaStr = res.data.schema_json || res.data.schema
      if (typeof schemaStr === 'string') {
        schemaObj = JSON.parse(schemaStr)
      } else {
        schemaObj = schemaStr as Record<string, unknown>
      }
    } else {
      if (!customSchemaJson.value.trim()) {
        msgWarning($t('mockRules.inputSchema'))
        return
      }
      schemaObj = JSON.parse(customSchemaJson.value)
    }
    const res = await generateFromSchema(projectId.value, schemaObj)
    form.response_body = JSON.stringify(res.data, null, 2)
    bodyType.value = 'json'
    schemaGenDialogVisible.value = false
    msgSuccess($t('mockRules.mockDataGenerated'))
  } catch (e: unknown) {
    msgError($t('mockRules.generateFailedMsg'))
  } finally {
    schemaGenLoading.value = false
  }
}

// 添加匹配条件
function addCondition() {
  form.conditions.push({ type: "param", field: "", operator: "equals", value: "" })
}

// Mock URL 生成
function getMockBaseUrl(): string {
  const envTarget = import.meta.env.VITE_API_TARGET as string | undefined
  const baseURL = request.defaults.baseURL || '/api/v1'
  let apiBase: string
  if (envTarget) {
    apiBase = envTarget.replace(/\/+$/, '')
  } else if (/^https?:\/\//.test(baseURL)) {
    apiBase = baseURL.replace(/\/api\/v1\/?$/, '')
  } else {
    apiBase = window.location.origin
  }
  return `${apiBase}/mock/${projectId.value}`
}

function getMockUrl(rule: MockRule): string {
  if (!rule.match_path || rule.match_path === "*") return ""
  const base = getMockBaseUrl()
  const path = rule.match_path.startsWith("/") ? rule.match_path.slice(1) : rule.match_path
  return `${base}/${path}`
}

function copyMockUrl(rule: MockRule) {
  const url = getMockUrl(rule)
  if (url) {
    navigator.clipboard.writeText(url).then(() => {
      msgSuccess($t('mockRules.mockUrlCopied'))
    }).catch(() => {
      msgWarning($t('mockRules.copyFailedManual'))
    })
  }
}

function copyMockBaseUrl() {
  const baseUrl = getMockBaseUrl() + '/'
  navigator.clipboard.writeText(baseUrl).then(() => {
    msgSuccess($t('mockRules.baseUrlCopied'))
  }).catch(() => {
    msgWarning($t('mockRules.copyFailedManual'))
  })
}

const filteredRules = computed(() => {
  let list = rules.value
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(
      (r) => r.name.toLowerCase().includes(q) || r.match_path.toLowerCase().includes(q)
    )
  }
  if (enabledFilter.value === "enabled") list = list.filter((r) => r.enabled)
  if (enabledFilter.value === "disabled") list = list.filter((r) => !r.enabled)
  if (methodFilter.value) list = list.filter((r) => r.match_method === methodFilter.value)
  return list
})

const {
  visibleItems: virtualVisibleItems,
  totalHeightStyle,
  offsetStyle,
  scrollContainer,
  enabled: virtualEnabled,
} = useVirtualScroll(filteredRules, { itemHeight: 80, threshold: 50 })

function _highlightPath(path: string): string {
  const escaped = escapeHtml(path)
  return escaped.replace(/(:\w+)/g, '<span class="param-highlight">$1</span>')
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

function methodClass(m: string) {
  const map: Record<string, string> = {
    GET: "get",
    POST: "post",
    PUT: "put",
    DELETE: "delete",
    PATCH: "patch",
  }
  return map[m] || "any"
}

async function loadRules(page = 1) {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, string | number> = { page, page_size: 20 }
    if (methodFilter.value) params.method = methodFilter.value
    const res = await request.get(`/projects/${projectId.value}/mock-rules`, { params })
    rules.value = res.data.items || []
    total.value = res.data.total || 0
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err?.response?.status !== 401) {
      error.value = $t('mockRules.loadErrorMsg')
    }
  } finally {
    loading.value = false
  }
}

async function openCreateDialog() {
  if (!(await requireWrite('新建Mock规则'))) return
  if (!(await requireLogin($t('mockRules.newRuleAction')))) return
  editingId.value = null
  bodyType.value = "json"
  Object.assign(form, defaultForm())
  showDialog.value = true
}

async function editRule(rule: MockRule) {
  if (!(await requireLogin($t('mockRules.editRuleAction')))) return
  editingId.value = rule.id
  const headers = Object.entries(rule.response_headers || {}).map(([key, value]) => ({
    key,
    value: String(value),
  }))
  // 解析已有条件
  const existingConditions = rule.conditions || []
  const parsedConditions = existingConditions.map((c: { field?: string; operator?: string; value?: string }) => {
    const field = c.field || ""
    let type = "param"
    if (field.startsWith("header.")) type = "header"
    else if (field.startsWith("body.")) type = "body"
    return {
      type,
      field: field.includes(".") ? field.split(".").slice(1).join(".") : field,
      operator: c.operator || "equals",
      value: c.value || "",
    }
  })
  form.name = rule.name
  form.enabled = rule.enabled
  form.priority = rule.priority
  form.match_method = rule.match_method
  form.match_path = rule.match_path
  form.response_status = rule.response_status
  form.response_headers = headers
  form.response_body = rule.response_body || ""
  form.response_delay = rule.response_delay || 0
  form.conditions = parsedConditions
  bodyType.value = !rule.response_body
    ? "empty"
    : rule.response_body.trim().startsWith("{") || rule.response_body.trim().startsWith("[")
      ? "json"
      : "text"
  showDialog.value = true
}

const saveRule = () => saveLock.run(async () => {
  if (!form.match_path.trim()) {
    msgWarning($t('mockRules.inputMatchPath'))
    return
  }
  if (bodyType.value === "json" && jsonError.value) {
    msgWarning($t('mockRules.fixJsonFormat'))
    return
  }
  try {
    const payload: Record<string, unknown> = {
      name: form.name,
      enabled: form.enabled,
      priority: form.priority,
      match_method: form.match_method,
      match_path: form.match_path,
      response_status: form.response_status,
      response_headers:
        form.response_headers.length > 0
          ? Object.fromEntries(
              form.response_headers.filter((h) => h.key).map((h) => [h.key, h.value])
            )
          : {},
      response_body: bodyType.value === "empty" ? "" : form.response_body,
      response_delay: form.response_delay,
      conditions: form.conditions.map((c) => ({
        field: c.type === "header" ? `header.${c.field}` : c.type === "body" ? `body.${c.field}` : `query.${c.field}`,
        operator: c.operator,
        value: c.value,
      })),
    }
    if (editingId.value) {
      await request.put(`/projects/${projectId.value}/mock-rules/${editingId.value}`, payload)
      msgSuccess($t('mockRules.ruleUpdated'))
    } else {
      await request.post(`/projects/${projectId.value}/mock-rules`, payload)
      msgSuccess($t('mockRules.ruleCreated'))
    }
    await loadRules()
    showDialog.value = false
  } catch (e: unknown) {
    msgError($t('mockRules.saveFailedMsg'))
  }
})

async function toggleRule(rule: MockRule) {
  if (!(await requireLogin($t('mockRules.modifyRule')))) return
  try {
    await request.put(`/projects/${projectId.value}/mock-rules/${rule.id}`, { enabled: !rule.enabled })
    msgSuccess(rule.enabled ? $t('mockRules.disabled') : $t('mockRules.enabled'))
    await loadRules()
  } catch (e: unknown) {
    msgError($t('mockRules.toggleFailedMsg'))
  }
}

async function duplicateRule(rule: MockRule) {
  if (!(await requireLogin($t('mockRules.copyRule')))) return
  editingId.value = null
  const headers = Object.entries(rule.response_headers || {}).map(([key, value]) => ({
    key,
    value: String(value),
  }))
  Object.assign(form, defaultForm())
  form.name = rule.name + $t('mockRules.copySuffix')
  form.enabled = false
  form.priority = rule.priority
  form.match_method = rule.match_method
  form.match_path = rule.match_path
  form.response_status = rule.response_status
  form.response_headers = headers
  form.response_body = rule.response_body || ""
  form.response_delay = rule.response_delay || 0
  bodyType.value = !rule.response_body
    ? "empty"
    : rule.response_body.trim().startsWith("{") || rule.response_body.trim().startsWith("[")
      ? "json"
      : "text"
  showDialog.value = true
}

async function confirmDelete(rule: MockRule) {
  try {
    await ElMessageBox.confirm(
      $t('mockRules.deleteConfirmMsg', { name: rule.name }),
      $t('mockRules.deleteDialogTitle'),
      { confirmButtonText: $t('mockRules.deleteBtn'), cancelButtonText: $t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  if (!(await requireLogin($t('mockRules.deleteRuleAction')))) return
  try {
    await request.delete(`/projects/${projectId.value}/mock-rules/${rule.id}`)
    msgSuccess($t('mockRules.ruleDeleted'))
    await loadRules()
  } catch (e: unknown) {
    msgError($t('mockRules.deleteFailedMsg'))
  }
}

// Tab 切换
const activeTab = ref<'rules' | 'logs' | 'stats'>('rules')

// 调用日志
const callLogs = ref<MockCallLog[]>([])
const logsTotal = ref(0)
const logsPage = ref(1)
const logsLoading = ref(false)
const clearingLogs = ref(false)
const logDateRange = ref<[string, string] | null>(null)

async function loadCallLogs() {
  logsLoading.value = true
  try {
    const params: Record<string, unknown> = { page: logsPage.value, page_size: 20 }
    if (logDateRange.value) {
      params.start_date = logDateRange.value[0]
      params.end_date = logDateRange.value[1]
    }
    const res = await getMockCallLogs(projectId.value, params)
    callLogs.value = res.data.items || []
    logsTotal.value = res.data.total || 0
  } catch {
    callLogs.value = []
  } finally {
    logsLoading.value = false
  }
}

async function doClearCallLogs() {
  clearingLogs.value = true
  try {
    await clearMockCallLogs(projectId.value)
    msgSuccess($t('mockRules.logsCleared'))
    await loadCallLogs()
  } catch (e: unknown) {
    msgError($t('mockRules.clearLogsFailed'))
  } finally {
    clearingLogs.value = false
  }
}

function formatLogTime(dt: string): string {
  if (!dt) return ''
  return dt.replace('T', ' ').substring(0, 19)
}

// 统计数据
const mockStats = ref({ total_rules: 0, enabled_rules: 0, total_hits: 0, top_rules: [] as MockRule[] })
const callTrend = ref<Array<{ date: string; count: number }>>([])
const matchRate = ref({ total_calls: 0, matched_calls: 0, unmatched_calls: 0, match_rate: 0 })

async function loadStats() {
  try {
    const [statsRes, trendRes, rateRes] = await Promise.all([
      getMockStatistics(projectId.value),
      request.get(`/projects/${projectId.value}/mock-rules/statistics/call-trend`),
      request.get(`/projects/${projectId.value}/mock-rules/statistics/match-rate`),
    ])
    mockStats.value = statsRes.data || mockStats.value
    callTrend.value = trendRes.data?.data || []
    matchRate.value = rateRes.data?.data || matchRate.value
  } catch {
    // 静默失败
  }
}

onMounted(() => {
  void loadRules()
  void loadSchemas()
})

watch(() => route.params.id, () => {
  void loadRules()
  void loadSchemas()
})

import "./MockRulesView.css"
</script>



<style scoped>
</style>
