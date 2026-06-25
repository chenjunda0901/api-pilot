<template>
  <PageLayout
    :title="$t('scene.title')"
    compact
  >
    <template #hero-extra>
      <div class="scenes-hero-status" v-if="selectedScene">
        <span class="hero-status-label">{{ $t('scene.currentScene') }}</span>
        <span class="hero-status-value">{{ selectedScene?.name || $t('scene.notSelected') }}</span>
        <span class="hero-status-meta">{{ $t('scene.stepMetaInfo', { stepCount: steps.length, selectedCount: selectedStepKeys.size }) }}</span>
        <span v-if="isExecuting && execTotalSteps > 0" class="hero-status-progress">{{ $t('scene.execProgressLabel', { done: execDoneCount, total: execTotalSteps }) }}</span>
      </div>
    </template>

    <div class="scenes-workspace">
      <SceneTree
        ref="scene"
        :project-id="projectId"
        :selected-scene-id="selectedSceneId"
        :can-edit="canEdit"
        @select-scene="onTreeSceneSelected"
        @scene-created="onTreeSceneCreated"
        @scene-deleted="onTreeSceneDeleted"
      />

      <div class="steps-panel">
        <EmptyState
          v-if="sceneLoading && !selectedScene"
          illustration="scene"
          :title="$t('scene.loading')"
          :description="$t('scene.loadingDesc')"
        />

        <EmptyState
          v-else-if="sceneError"
          illustration="scene"
          :title="$t('scene.loadFailed')"
          :description="sceneError"
        >
          <template #action>
            <el-button type="primary" size="small" @click="selectedSceneId && loadSceneDetail(selectedSceneId)">
              {{ $t('scene.reload') }}
            </el-button>
          </template>
        </EmptyState>

        <template v-else-if="selectedScene">
          <div class="panel-head">
            <el-input v-model="editingName" size="small" style="width: 200px" :placeholder="$t('scene.sceneNamePlaceholder')" :aria-label="$t('scene.sceneNameAriaLabel')" :disabled="isExecuting" @blur="onSceneNameBlur">
              <template #prefix><FileText :size="14" /></template>
            </el-input>
            <div class="panel-actions">
              <el-button size="small" type="primary" @click="() => saveLock.run(saveScene)" :loading="saveLock.loading.value" :disabled="saveLock.disabled.value || isExecuting" aria-label="保存场景">{{ $t('scene.save') }}</el-button>
              <el-dropdown @command="handleExportScene" trigger="click">
                <el-button size="small">
                  {{ $t('scene.export') }} <ArrowDown :size="14" />
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="json">{{ $t('scene.exportAsJson') }}</el-dropdown-item>
                    <el-dropdown-item command="copy">{{ $t('scene.copyToClipboard') }}</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <div class="run-btn-group">
                <el-button size="small" type="success" @click.stop="runSceneWithCheck(selectedScene)" :disabled="isExecuting" aria-label="运行场景">
                  <Play :size="14" />{{ isExecuting ? $t('scene.executing') : $t('scene.runBtn') }}
                </el-button>
                <el-dropdown trigger="click" @command="onRunCommand">
                  <el-button size="small" type="success" class="run-dropdown-trigger" :aria-label="$t('scene.runOptions')">
                    <ChevronDown :size="12" />
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="failed-only">{{ $t('scene.runFailedOnly') }}</el-dropdown-item>
                      <el-dropdown-item command="stress">{{ $t('scene.stressMode') }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>
          </div>

          <!-- 场景描述与优先级 -->
          <div class="scene-meta-row">
            <div class="scene-desc-row">
              <label>{{ $t('common.description') }}</label>
              <el-input
                v-model="editingDescription"
                type="textarea"
                :rows="2"
                :aria-label="$t('scene.sceneDescription')"
                :placeholder="$t('scene.descPlaceholder2')"
                resize="none"
                class="scene-desc-input"
                :disabled="isExecuting"
              />
            </div>
            <div class="scene-priority-row">
              <label>{{ $t('scene.priority') }}</label>
              <el-select v-model="editingPriority" size="small" :disabled="isExecuting">
                <el-option :label="$t('scene.priorityP0')" value="P0" />
                <el-option :label="$t('scene.priorityP1')" value="P1" />
                <el-option :label="$t('scene.priorityP2')" value="P2" />
                <el-option :label="$t('scene.priorityP3')" value="P3" />
              </el-select>
            </div>
          </div>

          <div class="steps-area">
            <div class="steps-toolbar">
              <!-- 左侧：标签 + 主要操作 -->
              <div class="toolbar-left">
                <span class="steps-label">{{ $t('scene.stepsLabel') }}（{{ steps.length }}）</span>
                <span class="steps-hint" v-if="steps.length > 0"><kbd>Ctrl</kbd> {{ $t('scene.multiSelectHint') }} · <kbd>Shift</kbd> {{ $t('scene.rangeSelectHint') }}</span>
                <div class="steps-actions">
                  <el-button size="small" @click="openImport()">{{ $t('scene.importFromApi') }}</el-button>
                  <el-button size="small" @click="openAddWaitStep()">
                    <Clock :size="14" /> {{ $t('scene.addWait') }}
                  </el-button>
                </div>
              </div>

              <!-- 右侧：次要操作 + 批量操作 + 数据集切换 -->
              <div class="toolbar-right">
                <el-button size="small" :type="showDatasetPanel ? 'primary' : 'default'" @click="showDatasetPanel = !showDatasetPanel">
                  {{ $t('scene.dataset') }}
                </el-button>
                <el-button size="small" :type="showDataFlowView ? 'primary' : 'default'" @click="showDataFlowView = !showDataFlowView">
                  {{ showDataFlowView ? '✓' : '' }} {{ $t('scene.dataFlowView') }}
                </el-button>
                <div v-if="selectedStepKeys.size > 0" class="batch-toolbar">
                  <span class="batch-count">{{ $t('scene.selectedCountLabel', { count: selectedStepKeys.size }) }}</span>
                  <el-button size="small" type="danger" :loading="batchDeleting" @click="batchDelete">{{ $t('scene.batchDelete') }}</el-button>
                  <el-button size="small" @click="openCopyDialog">{{ $t('scene.move') }}</el-button>
                  <el-button size="small" text @click="clearSelection">{{ $t('scene.clearSelection') }}</el-button>
                </div>
              </div>
            </div>

            <!-- 执行进度条 -->
            <div v-if="isExecuting" class="execution-progress">
              <el-progress :percentage="execProgress" :status="execPercentStatus" />
              <span class="progress-text">{{ $t('scene.execProgressText', { completed: completedSteps, total: totalExecSteps, passed: passedSteps, failed: failedSteps }) }}</span>
            </div>

            <div class="steps-content">
              <div v-if="viewMode === 'steps'" class="steps-view">
                <div v-if="steps.length === 0" class="steps-empty">
                  <div class="steps-empty-icon"><List :size="32" /></div>
                  <p>{{ $t('scene.noSteps') }}</p>
                  <p class="steps-empty-hint">{{ $t('scene.noStepsHint') }}</p>
                </div>

                <SortableList
                  v-else
                  :items="steps"
                  item-key="_key"
                  handle=".drag-handle"
                  @update:items="onSortUpdate"
                  @end="handleDragEnd"
                  class="step-list"
                >
                  <div
                    v-for="(step, index) in steps"
                    :key="step._key"
                    :data-key="step._key"
                    class="step-row-wrapper"
                  >
                    <div
                      class="step-row"
                      :class="{ selected: selectedStepKeys.has(step._key), 'is-active': selectedStepKey === (step.id || step._key), disabled: !step.enabled }"
                      @click="onStepClick($event, step, index)"
                    >
                      <span class="step-status-dot" :class="getStepExecStatus(step)"></span>
                      <span class="drag-handle"><GripVertical :size="14" /></span>
                      <el-checkbox class="enable-cb" :model-value="step.enabled" @change="(val: boolean) => { step.enabled = val; markDirty(); }" @click.stop :title="$t('scene.enableDisableTip')" />
                      <span class="step-index" :class="{ disabled: !step.enabled }">{{ index + 1 }}</span>
                      <template v-if="step.wait_duration && !step.path">
                        <span class="step-method is-wait"><Clock :size="12" /> WAIT</span>
                      </template>
                      <template v-else>
                        <span class="step-method" :class="(step.method || 'GET').toLowerCase()">{{ step.method || 'GET' }}</span>
                      </template>
                      <span class="step-name" :class="{ 'depends-indicator': step.depends_on_step_id }" v-text="step.label || $t('scene.unnamedStep')"></span>
                      <div class="step-badges">
                        <template v-for="(badge, bi) in (stepBadgeMap[step._key] || [])" :key="bi">
                          <el-tag v-if="badge.tagType" :type="badge.tagType" size="small" class="badge-item">{{ badge.label }}</el-tag>
                          <span v-else-if="badge.isLoop" class="loop-badge badge-item" :title="$t('scene.loopTip')">
                            <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                              <path d="M17 1l4 4-4 4" />
                              <path d="M3 11V9a4 4 0 0 1 4-4h14" />
                              <path d="M7 23l-4-4 4-4" />
                              <path d="M21 13v2a4 4 0 0 1-4 4H3" />
                            </svg>
                            {{ step.loop_count }}x
                          </span>
                          <span v-else-if="badge.isCondition" class="condition-tag badge-item">{{ badge.label }}</span>
                          <span v-else-if="badge.isDepends" class="depends-tag badge-item" :title="$t('scene.dependsOnPrevStep')">⇪ {{ badge.label }}</span>
                        </template>
                        <span v-if="(stepBadgeMap[step._key] || []).length > 3" class="more-badge badge-item">+{{ (stepBadgeMap[step._key] || []).length - 3 }}</span>
                      </div>
                      <!-- 执行结果状态指示 -->
                      <span v-if="getStepExecResult(step)" class="step-exec-status" :class="getStepExecResult(step).status" @click.stop="toggleStepExpand(step._key)">
                        {{ getStepExecResult(step).status === 'success' ? '✓' : getStepExecResult(step).status === 'failed' ? '✗' : '○' }}
                      </span>
                      <el-dropdown trigger="click" @command="(cmd: string) => handleStepAction(cmd, step, index)" @click.stop>
                        <button class="icon-btn" :title="$t('scene.moreActions')" :aria-label="$t('scene.moreActions')"><MoreHorizontal :size="14" /></button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="insert_above">{{ $t('scene.insertAbove') }}</el-dropdown-item>
                            <el-dropdown-item command="insert_condition">{{ $t('scene.insertCondition') }}</el-dropdown-item>
                            <el-dropdown-item command="insert_wait">{{ $t('scene.insertWait') }}</el-dropdown-item>
                            <el-dropdown-item command="delete" divided>{{ $t('scene.deleteStep') }}</el-dropdown-item>
                          </el-dropdown-menu>
                        </template>
                      </el-dropdown>
                    </div>
                    <!-- 步骤执行详情展开区域 -->
                    <div v-if="expandedStepKey === step._key && getStepExecResult(step)" class="step-exec-detail">
                      <!-- 请求信息 -->
                      <div class="exec-detail-section">
                        <div class="exec-detail-title">{{ $t('scene.request') }}</div>
                        <div class="exec-detail-row"><span class="exec-label">{{ $t('scene.method') }}</span><span class="exec-value method-badge" :class="(getStepExecResult(step).method || 'GET').toLowerCase()">{{ getStepExecResult(step).method || 'GET' }}</span></div>
                        <div class="exec-detail-row"><span class="exec-label">URL</span><span class="exec-value mono">{{ getStepExecResult(step).request_url || '-' }}</span></div>
                        <div class="exec-detail-row" v-if="getStepExecResult(step).request_headers"><span class="exec-label">Headers</span><pre class="exec-value code-block">{{ formatExecData(getStepExecResult(step).request_headers) }}</pre></div>
                        <div class="exec-detail-row" v-if="getStepExecResult(step).request_body"><span class="exec-label">Body</span><pre class="exec-value code-block">{{ formatExecData(getStepExecResult(step).request_body) }}</pre></div>
                      </div>
                      <!-- 变量替换结果 -->
                      <div v-if="getStepExecResult(step).variable_substitutions && Object.keys(getStepExecResult(step).variable_substitutions || {}).length > 0" class="exec-detail-section">
                        <div class="exec-detail-title">{{ $t('scene.variableSubstitution') }}</div>
                        <div class="var-subst-list">
                          <div v-for="(resolved, varName) in (getStepExecResult(step).variable_substitutions || {})" :key="varName" class="var-subst-item">
                            <span class="var-subst-original" v-text="'{{' + varName + '}}'"></span>
                            <span class="var-subst-arrow">→</span>
                            <span class="var-subst-resolved">{{ resolved ?? '-' }}</span>
                          </div>
                        </div>
                      </div>
                      <!-- 响应信息 -->
                      <div class="exec-detail-section">
                        <div class="exec-detail-title">{{ $t('scene.response') }}</div>
                        <div class="exec-detail-row"><span class="exec-label">{{ $t('scene.statusCode') }}</span><span class="exec-value" :class="getStatusClass(getStepExecResult(step).response_status)">{{ getStepExecResult(step).response_status || '-' }}</span></div>
                        <div class="exec-detail-row"><span class="exec-label">{{ $t('scene.duration') }}</span><span class="exec-value">{{ getStepExecResult(step).duration_ms ? (getStepExecResult(step).duration_ms / 1000).toFixed(2) + 's' : '-' }}</span></div>
                        <div class="exec-detail-row" v-if="getStepExecResult(step).response_headers"><span class="exec-label">Headers</span><pre class="exec-value code-block">{{ formatExecData(getStepExecResult(step).response_headers) }}</pre></div>
                        <div class="exec-detail-row" v-if="getStepExecResult(step).response_body"><span class="exec-label">Body</span><pre class="exec-value code-block">{{ formatExecData(getStepExecResult(step).response_body) }}</pre></div>
                      </div>
                      <!-- 断言详情 -->
                      <div v-if="getStepExecResult(step).assertion_summary && getStepExecResult(step).assertion_summary.length > 0" class="exec-detail-section">
                        <div class="exec-detail-title">{{ $t('scene.assertionCount', { passed: getStepExecResult(step).assertion_summary.filter((a: AssertionSummary) => a.passed).length, total: getStepExecResult(step).assertion_summary.length }) }}</div>
                        <div class="assertion-list">
                          <div
                            v-for="(assertion, ai) in getStepExecResult(step).assertion_summary"
                            :key="ai"
                            class="assertion-item"
                            :class="{ 'assertion-passed': assertion.passed, 'assertion-failed': !assertion.passed }"
                          >
                            <div class="assertion-header">
                              <span class="assertion-icon">{{ assertion.passed ? '✓' : '✗' }}</span>
                              <span class="assertion-type">{{ assertion.type }}</span>
                              <span class="assertion-op">{{ assertion.op }}</span>
                              <span class="assertion-expected">{{ $t('assertion.expected') }} {{ assertion.expected }}</span>
                              <span v-if="!assertion.passed" class="assertion-actual">{{ $t('assertion.actual') }} {{ assertion.actual }}</span>
                            </div>
                            <!-- 失败断言的 diff 视图 -->
                            <div v-if="!assertion.passed && assertion.diff" class="assertion-diff">
                              <div class="diff-label">{{ $t('scene.diffCompare') }}</div>
                              <pre class="diff-content"><template v-for="(line, li) in assertion.diff.diff.split('\n')" :key="li"><span :class="getDiffLineClass(line)">{{ line }}</span>
</template></pre>
                            </div>
                          </div>
                        </div>
                      </div>
                      <!-- 脚本输出 -->
                      <div v-if="getStepExecResult(step).script_output || getStepExecResult(step).script_error" class="exec-detail-section">
                        <div class="exec-detail-title">{{ $t('scene.scriptOutput') }}</div>
                        <div v-if="getStepExecResult(step).script_output" class="script-output-panel">
                          <pre class="code-block script-stdout">{{ getStepExecResult(step).script_output }}</pre>
                        </div>
                        <div v-if="getStepExecResult(step).script_error" class="script-output-panel">
                          <pre class="code-block script-stderr">{{ getStepExecResult(step).script_error }}</pre>
                        </div>
                      </div>
                      <!-- 错误信息 -->
                      <div v-if="getStepExecResult(step).error_message" class="exec-detail-section">
                        <div class="exec-detail-title error">{{ $t('scene.errorMessage') }}</div>
                        <pre class="exec-value code-block error-text">{{ getStepExecResult(step).error_message }}</pre>
                      </div>
                    </div>
                  </div>
                </SortableList>
              </div>

              <!-- 数据集管理面板 -->
              <div v-if="showDatasetPanel" class="dataset-panel">
                <div class="dataset-panel-header">
                  <span class="dataset-panel-title">{{ $t('scene.datasetManagement') }}</span>
                  <div class="dataset-panel-actions">
                    <el-button size="small" @click="addDataset">{{ $t('scene.newDataset') }}</el-button>
                    <label class="upload-btn">
                      <input type="file" accept=".csv,.json" @change="onDatasetFileUpload" style="display: none" />
                      <el-button size="small">{{ $t('scene.uploadFile') }}</el-button>
                    </label>
                  </div>
                </div>
                <EmptyState
                  v-if="sceneDatasets.length === 0"
                  illustration="empty"
                  :title="$t('scene.noDatasets')"
                  :description="$t('scene.noDatasetsDesc')"
                />
                <div v-for="ds in sceneDatasets" :key="ds.id" class="dataset-card">
                  <div class="dataset-card-header">
                    <el-input v-model="ds.name" size="small" :aria-label="$t('scene.datasetName')" style="width: 160px" @change="updateDataset(ds)" />
                    <el-tag size="small" type="info">{{ ds.type }}</el-tag>
                    <span class="dataset-row-count">{{ $t('scene.rowCount', { count: ds.data?.length || 0 }) }}</span>
                    <el-button size="small" text type="danger" @click="deleteDataset(ds)">{{ $t('common.delete') }}</el-button>
                  </div>
                  <div class="dataset-table-wrap" v-if="ds.data && ds.data.length > 0">
                    <el-table :data="ds.data" size="small" border max-height="200" class="dataset-table">
                      <el-table-column v-for="col in getDatasetColumns(ds.data)" :key="col" :prop="col" :label="col" min-width="100">
                        <template #default="{ row }">
                          <el-input v-model="row[col]" size="small" :aria-label="col" @change="updateDataset(ds)" />
                        </template>
                      </el-table-column>
                      <el-table-column label="" width="40" fixed="right">
                        <template #default="{ $index }">
                          <el-button size="small" text type="danger" :aria-label="$t('scene.deleteDataRow')" @click="removeDatasetRow(ds, $index)">
                            <X :size="12" />
                          </el-button>
                        </template>
                      </el-table-column>
                    </el-table>
                    <el-button size="small" text @click="addDatasetRow(ds)">{{ $t('scene.addRow') }}</el-button>
                    <el-button size="small" text @click="addDatasetColumn(ds)">{{ $t('scene.addColumn') }}</el-button>
                  </div>
                </div>
              </div>

              <div v-if="showDataFlowView && dataFlowSteps.length > 0" class="data-flow-view">
                <div v-for="(step, index) in dataFlowSteps" :key="index" class="df-step">
                  <div class="df-step-header">
                    <span class="df-step-index">{{ index + 1 }}</span>
                    <span class="df-step-method" :class="(step.method || 'GET').toLowerCase()">{{ step.method || 'GET' }}</span>
                    <span class="df-step-label" v-text="step.label || $t('scene.unnamedStep')"></span>
                  </div>
                  <div v-if="(step.referencedVars || []).length > 0" class="df-var-refs">
                    <span class="df-arrow down">↓</span>
                    <span class="df-var-chip" v-for="v in (step.referencedVars || [])" :key="v" v-text="'{{' + v + '}}'"></span>
                  </div>
                  <div v-if="(step.extractedVars || []).length > 0" class="df-var-extract">
                    <span class="df-arrow up">↑</span>
                    <span class="df-var-chip extract" v-for="v in (step.extractedVars || [])" :key="v" v-text="'{{' + v + '}}'"></span>
                  </div>
                </div>
              </div>

              <div v-if="viewMode === 'variables'" class="variables-content">
                <VariablePreview mode="scene" :title="$t('scene.variablesAnalysis')" :scene-steps="steps" :all-vars="envStore.allVariablesForPreview" />
              </div>
            </div>
          </div>
        </template>

        <div v-else class="center-empty">
          <div class="center-empty-card">
            <div class="center-empty-visual">
              <div class="center-empty-icon-wrap">
                <FileText :size="28" />
              </div>
              <div class="center-empty-dots">
                <span class="dot dot-1"></span>
                <span class="dot dot-2"></span>
                <span class="dot dot-3"></span>
              </div>
            </div>
            <h3 class="center-empty-title">{{ $t('scene.selectScene') }}</h3>
            <p class="center-empty-desc">{{ $t('scene.selectSceneDesc') }}</p>
            <button class="center-empty-action" @click="handleCreateScene">
              <FolderPlus :size="14" />
              <span>{{ $t('scene.newSceneBtn') }}</span>
            </button>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="right-section" :class="{ 'config-disabled': !selectedScene }">
          <div class="section-header">
            <div class="section-title-group">
              <Settings2 :size="14" class="section-title-icon" />
              <span class="section-title">{{ $t('scene.runConfig') }}</span>
            </div>
          </div>
          <div class="cfg-empty-hint" v-if="!selectedScene">
            <span class="empty-hint-icon">↑</span>
            {{ $t('scene.selectSceneFirst') }}
          </div>
          <div class="cfg-form" v-if="selectedScene">
            <div class="cfg-row-grid">
              <div class="cfg-item">
                  <el-tooltip :content="$t('scene.envTooltip')" placement="top" :show-after="500">
                  <span class="cfg-label">{{ $t('scene.envLabel') }}</span>
                </el-tooltip>
                <el-select v-model="envId" size="small" :placeholder="$t('scene.envPlaceholder')" style="width: 100%">
                  <el-option v-for="e in envs" :key="e.id" :label="e.name" :value="e.id" />
                </el-select>
              </div>
              <div class="cfg-item">
                <span class="cfg-label">{{ $t('scene.loopCount') }}</span>
                <el-input-number v-model="loopCount" :min="1" :max="100" size="small" controls-position="right" style="width: 100%" />
              </div>
            </div>
            <div class="cfg-item">
              <el-tooltip :content="$t('scene.failureStrategyTooltip')" placement="top" :show-after="500">
                <span class="cfg-label">{{ $t('scene.failureStrategy') }}</span>
              </el-tooltip>
              <el-select v-model="onFailure" size="small" style="width: 100%">
                <el-option :label="$t('scene.stopImmediately')" value="stop" />
                <el-option :label="$t('scene.continueCurrent')" value="continue" />
                <el-option :label="$t('scene.markFailedSkip')" value="ignore" />
              </el-select>
            </div>
            <div class="cfg-item">
              <el-tooltip :content="$t('scene.varPersistTargetTooltip')" placement="top" :show-after="500">
                <span class="cfg-label">{{ $t('scene.varPersistTarget') }}</span>
              </el-tooltip>
              <el-select v-model="varPersistTarget" size="small" style="width: 100%">
                <el-option :label="$t('scene.varPersistEnvironment')" value="environment" />
                <el-option :label="$t('scene.varPersistGlobal')" value="global" />
                <el-option :label="$t('scene.varPersistNone')" value="none" />
              </el-select>
              <p class="config-hint">{{ $t('scene.varPersistHint') }}</p>
            </div>
            <div class="cfg-item cfg-item-check">
              <el-checkbox v-model="globalCookie">{{ $t('scene.cookieShare') }}</el-checkbox>
            </div>
            <el-divider style="margin: var(--space-3) 0 var(--space-2); border-color: var(--border-subtle)" />
            <div class="cfg-item">
              <span class="cfg-label">{{ $t('scene.dataDriven') }}</span>
              <el-select v-model="selectedDatasetId" size="small" :placeholder="$t('scene.noDataDriven')" clearable style="width: 100%">
                <el-option v-for="ds in sceneDatasets" :key="ds.id" :label="ds.name" :value="ds.id" />
              </el-select>
              <p class="config-hint">{{ $t('scene.dataDrivenHint') }}</p>
            </div>
            <div class="cfg-row-grid">
              <div class="cfg-item">
                <span class="cfg-label">{{ $t('scene.stepDelay') }}</span>
                <el-input-number v-model="stepDelay" :min="0" :max="60000" :step="100" size="small" controls-position="right" style="width: 100%" />
                <label class="cfg-sub-check">
                  <input type="checkbox" v-model="stepDelayRandom" />
                  <span>{{ $t('scene.randomRange') }}</span>
                </label>
              </div>
              <div class="cfg-item">
                <span class="cfg-label">{{ $t('scene.concurrency') }}</span>
                <el-input-number v-model="concurrency" :min="1" :max="10" size="small" controls-position="right" style="width: 100%" />
              </div>
            </div>
            <div v-if="stepDelayRandom" class="cfg-row-grid" style="margin-top: -4px">
              <div class="cfg-item">
                <span class="cfg-label">{{ $t('scene.minDelay') }}</span>
                <el-input-number v-model="stepDelayMin" :min="0" :max="stepDelayMax" :step="100" size="small" controls-position="right" style="width: 100%" />
              </div>
              <div class="cfg-item">
                <span class="cfg-label">{{ $t('scene.maxDelay') }}</span>
                <el-input-number v-model="stepDelayMax" :min="stepDelayMin" :max="60000" :step="100" size="small" controls-position="right" style="width: 100%" />
              </div>
            </div>
            <el-divider style="margin: var(--space-3) 0 var(--space-2); border-color: var(--border-subtle)" />
            <div class="cfg-item">
              <span class="cfg-label">{{ $t('scene.scheduledExec') }}</span>
              <el-switch v-model="scheduleEnabled" @change="onScheduleToggle" />
            </div>
            <div v-if="scheduleEnabled" style="margin-top: var(--space-2)">
              <div class="cfg-item" style="margin-bottom: var(--space-2)">
                <span class="cfg-label" style="font-size: var(--text-xs); color: var(--text-secondary)">{{ $t('scene.cronExpr') }}</span>
                <el-input v-model="scheduleCron" size="small" :placeholder="$t('scene.cronPlaceholder')" />
              </div>
              <div style="display: flex; gap: var(--space-1); flex-wrap: wrap; margin-bottom: var(--space-2)">
                <el-button size="small" text @click="setQuickCron('daily')">{{ $t('scene.daily9am') }}</el-button>
                <el-button size="small" text @click="setQuickCron('hourly')">{{ $t('scene.hourly') }}</el-button>
                <el-button size="small" text @click="setQuickCron('weekdays')">{{ $t('scene.weekdays9am') }}</el-button>
              </div>
              <el-button size="small" type="primary" :loading="scheduleLock.loading.value" :disabled="scheduleLock.disabled.value" @click="() => scheduleLock.run(saveSchedule)">
                {{ $t('scene.saveSchedule') }}
              </el-button>
            </div>
            <el-divider style="margin: var(--space-3) 0 var(--space-2); border-color: var(--border-subtle)" />
            <div class="config-section">
              <div class="section-header">
                <Bell :size="14" />
                <span>{{ $t('scene.webhookNotification') }}</span>
                <el-switch v-model="webhookEnabled" size="small" />
              </div>
              <div v-if="webhookEnabled" class="section-body">
                <label>{{ $t('scene.callbackUrl') }}</label>
                <el-input v-model="webhookUrl" placeholder="https://your-server.com/webhook/scenes" size="small" />
                <p class="config-hint">{{ $t('scene.webhookHint') }}</p>
                <label>{{ $t('scene.triggerCondition') }}</label>
                <el-checkbox-group v-model="webhookTriggers" size="small">
                  <el-checkbox label="always">{{ $t('scene.alwaysNotify') }}</el-checkbox>
                  <el-checkbox label="on_success">{{ $t('scene.notifyOnSuccess') }}</el-checkbox>
                  <el-checkbox label="on_failure">{{ $t('scene.notifyOnFailure') }}</el-checkbox>
                </el-checkbox-group>
              </div>
            </div>
          </div>
        </div>
        <div v-if="selectedScene && steps.length > 0 && !showStepDetail" class="step-hint-bar">
          {{ $t('scene.clickStepToDetail') }}
        </div>
        <StepDetailDialog
          v-model="showStepDetail"
          :step="selectedStep"
          :step-breadcrumb="stepBreadcrumb"
          :has-prev-step="hasPrevStep"
          :has-next-step="hasNextStep"
          :current-service-url="currentServiceUrl"
          :current-env-services="currentEnvServices"
          :step-url-segments="stepUrlSegments"
          :duplicate-variables="duplicateVariables"
          :step-detail-tabs="stepDetailTabs"
          :step-detail-tab="stepDetailTab"
          :previous-steps="previousStepsForDetail"
          @update:method="(m) => { selectedStep!.method = m; markDirty() }"
          @update:path="(v) => { selectedStep!.path = v; markDirty() }"
          @update:query-params="(v) => { selectedStep!.query_params = v; markDirty() }"
          @update:body="(v) => { selectedStep!.request_body = v; markDirty() }"
          @update:headers="(v) => { selectedStep!.headers = v; markDirty() }"
          @update:assertions="(v) => { selectedStep!.assertions = v; markDirty() }"
          @update:condition="(v) => { selectedStep!.condition_expression = v; markDirty() }"
          @update:loop="(v) => { selectedStep!.loop_count = v; markDirty() }"
          @update:loop-variable="(v) => { selectedStep!.loop_variable = v; markDirty() }"
          @update:wait="(v) => { selectedStep!.wait_duration = v; markDirty() }"
          @update:wait-mode="(v) => { selectedStep!.wait_mode = v; markDirty() }"
          @update:wait-min="(v) => { selectedStep!.wait_min = v; markDirty() }"
          @update:wait-max="(v) => { selectedStep!.wait_max = v; markDirty() }"
          @update:depends-on="(v) => { selectedStep!.depends_on_step_id = v; markDirty() }"
          @remove-extract="removeExtract"
          @add-extract="addExtract"
          @update:tab="(k) => stepDetailTab = k"
          @prev="goToPrevStep"
          @next="goToNextStep"
          @closed="onStepDetailClosed"
          @switch-env="switchEnvService"
        />
      </div>
    </div>

    <el-dialog v-model="showImportDialog" :title="$t('scene.importDialogTitle')" width="640px" class="import-tree-dialog">
      <div class="import-search-bar">
        <el-input v-model="rawImportSearch" :placeholder="$t('scene.searchApiCasePlaceholder')" size="small" clearable prefix-icon="Search" />
      </div>
      <div class="import-tree-body">
        <SkeletonTable v-if="importLoading" :rows="5" />
        <template v-else>
          <el-tree
          ref="importTreeRef"
          :data="importTreeData"
          :props="{ children: 'children', label: 'label' }"
          node-key="id"
          show-checkbox
          default-expand-all
          @check="onTreeCheck"
          class="import-tree"
        >
          <template #default="{ data }">
            <span class="import-tree-node">
              <template v-if="data.type === 'category'">
                <FolderOpen :size="14" class="tree-node-icon category-icon" />
                <span class="tree-node-label">{{ data.label }}</span>
                <span class="tree-node-count">{{ data.children?.filter((c: { type?: string }) => c.type === 'api').length || 0 }} {{ $t('scene.apiCount') }}</span>
              </template>
              <template v-else-if="data.type === 'api'">
                <span :class="['method-badge', data.method?.toLowerCase()]">{{ data.method }}</span>
                <span class="tree-node-label">{{ data.label }}</span>
                <span class="tree-node-path">{{ data.path }}</span>
              </template>
              <template v-else-if="data.type === 'case'">
                <el-tag :type="data.priority === 'P0' ? 'danger' : data.priority === 'P1' ? 'warning' : 'info'" size="small" class="case-priority-tag">{{ data.priority }}</el-tag>
                <span class="tree-node-label">{{ data.label }}</span>
              </template>
            </span>
          </template>
          </el-tree>
          <div v-if="importTreeData.length === 0" class="import-empty-tree">
            <span class="import-empty-text">{{ $t('scene.noImportData') }}</span>
          </div>
        </template>
      </div>
      <template #footer>
        <div class="import-footer-info">
          <span>{{ $t('scene.selectedItems', { count: importSelected.size }) }}</span>
        </div>
        <el-button size="small" @click="showImportDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" :disabled="importSelected.size === 0 || importLock.disabled.value" :loading="importLock.loading.value" @click="() => importLock.run(doImport)">{{ $t('scene.importBtn', { count: importSelected.size }) }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showCopyDialog" :title="$t('scene.copyDialogTitle')" width="400px" :close-on-click-modal="false">
      <div class="copy-dialog-content">
        <p class="copy-hint">{{ $t('scene.copyDesc', { count: selectedStepKeys.size }) }}</p>
        <el-select v-model="targetSceneId" :placeholder="$t('scene.selectTargetScene')" style="width: 100%">
          <el-option v-for="sceneItem in sceneList" :key="sceneItem.id" :label="sceneItem.name" :value="sceneItem.id" :disabled="sceneItem.id === selectedScene?.id" />
        </el-select>
      </div>
      <template #footer>
        <el-button @click="showCopyDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="batchCopy" :disabled="!targetSceneId" :loading="copyLoading">{{ $t('scene.copyBtn') }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showWaitStepDialog" :title="$t('scene.addWaitStep')" width="420px" :close-on-click-modal="false">
      <div class="wait-step-dialog-content">
        <div class="cfg-item" style="margin-bottom: var(--space-4)">
          <span class="cfg-label">{{ $t('scene.delayTimeMs') }}</span>
          <el-input-number v-model="newWaitDuration" :min="100" :max="60000" :step="100" :placeholder="1000" size="default" controls-position="right" style="width: 100%" />
          <p class="config-hint">{{ $t('scene.delayRangeHint') }}</p>
        </div>
        <div class="cfg-item">
          <span class="cfg-label">{{ $t('scene.descOptional') }}</span>
          <el-input v-model="newWaitLabel" size="default" :placeholder="$t('scene.waitStepPlaceholder')" maxlength="100" />
        </div>
      </div>
      <template #footer>
        <el-button size="small" @click="showWaitStepDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button size="small" type="primary" @click="addWaitStep">{{ $t('scene.addStepBtn') }}</el-button>
      </template>
    </el-dialog>

    <ExecutionProgress
      :visible="execVisible"
      :scene-name="execSceneName"
      :steps="execSteps"
      :total-steps="execTotalSteps"
      :done-count="execDoneCount"
      :pass-count="execPassCount"
      :fail-count="execFailCount"
      :skip-count="execSkipCount"
      :duration="execDuration"
      :report-status="execStatus"
      :current-step-index="execCurrentStepIndex"
      @close="() => { execVisible = false; stopPolling() }"
      @cancel="cancelExecution"
      @view-report="viewReport"
      @minimize="minimizeExecution"
      @rerun="rerunScene"
    />

    <!-- Data-driven execution results grouped by data row -->
    <div v-if="isDataDriven && datasetResults.length" class="dataset-results-grouped">
      <h4>{{ $t('scene.dataDrivenResults') }}</h4>
      <div v-for="(rowResult, rowIndex) in datasetResults" :key="rowIndex"
           class="dataset-row-result" :class="{ failed: !rowResult.allPassed }">
        <div class="dataset-row-header" @click="expandedRow = expandedRow === rowIndex ? null : rowIndex">
          <span class="row-index">{{ $t('scene.dataRowIndex', { index: rowIndex + 1 }) }}</span>
          <span class="row-status" :class="rowResult.allPassed ? 'passed' : 'failed'">
            {{ rowResult.allPassed ? $t('scene.dataRowPassed') : $t('scene.dataRowFailed') }}
          </span>
          <span class="row-time">{{ rowResult.totalTime }}ms</span>
        </div>
        <div v-if="expandedRow === rowIndex" class="dataset-row-steps">
          <div v-for="step in rowResult.steps" :key="step.id" class="mini-step-result">
            {{ step.name }}: <span :class="step.status">{{ step.status }}</span> {{ step.time }}ms
          </div>
        </div>
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated, watch, defineAsyncComponent } from "vue"
import { useRouter, useRoute } from "vue-router"
import { ElMessageBox } from "element-plus"
import { useI18n } from "vue-i18n"
import { msgSuccess, msgWarning, msgError } from "@/utils/message"
import { logger, isSilentAuthError } from "@/utils/logger"
import type { Environment, SceneStep, TestScene } from "@/types"
import type { ApiError } from "@/types/common"
import SortableList from "@/components/SortableList.vue"
import VariablePreview from "@/components/VariablePreview.vue"
import EmptyState from "@/components/EmptyState.vue"
import SkeletonTable from "@/components/SkeletonTable.vue"
import request from "@/api/request"
import { useEnvStore } from "@/stores/envStore"
import { useTabsStore } from "@/stores/tabsStore"
import { useRequireLogin } from "@/composables/useRequireLogin"
import { useProjectPermission } from "@/composables/useProjectPermission"
import { useSubmitLock } from "@/composables/useSubmitLock"
import { useEventBus } from "@/composables/useEventBus"
import { useSceneExecution, type AssertionSummary } from "@/composables/useSceneExecution"
import { useStepEditor } from "@/composables/useStepEditor"
import { useSceneImport } from "@/composables/useSceneImport"
import { useDebounce } from "@/composables/useDebounce"
import { useSceneSchedule } from "@/composables/useSceneSchedule"
import PageLayout from "@/components/common/PageLayout.vue"

import { exportSceneToJson, downloadSceneJson } from "@/utils/sceneExporter"
import SceneTree from "@/components/SceneTree.vue"
import ExecutionProgress from "@/components/ExecutionProgress.vue"
import {
  Settings2,
  Play,
  MoreHorizontal,
  FileText,
  FolderPlus,
  ChevronDown,
  GripVertical,
  List,
  FolderOpen,
  Clock,
  ArrowDown,
  Bell,
  X,
} from "lucide-vue-next"

interface SceneRecord extends Partial<TestScene> {
  id: number
  name: string
  description?: string
  thread_count?: number
  on_failure?: "continue" | "stop"
  var_persist_target?: "environment" | "global" | "none"
  env_id?: number | null
  global_cookie?: boolean | number
  step_delay?: number
  step_delay_random?: boolean | number
  step_delay_min?: number
  step_delay_max?: number
  concurrency?: number
}

interface SceneStepViewModel extends Partial<SceneStep> {
  id?: number
  _key: string
  method?: string
  label: string
  enabled: boolean
  path: string
  node_type: string
  query_params: Record<string, unknown>[]
  headers: Record<string, unknown>[]
  request_body: string
  assertions: Record<string, unknown>[]
  extract_vars: Record<string, unknown>[]
  condition_expression?: string
  loop_count?: number | null
  wait_duration?: number | null
  wait_mode?: string
  wait_min?: number | null
  wait_max?: number | null
  loop_variable?: string
  depends_on_step_id?: number | null
}

interface SceneListItem {
  id: number
  name: string
}

const scene = ref<Record<string, unknown> | null>(null)
const StepDetailDialog = defineAsyncComponent(() => import("@/components/StepDetailDialog.vue"))
const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const projectId = computed(() => Number(route.params.id))
const tabsStore = useTabsStore()
const sceneTabKey = computed(() => `scene-${projectId.value}`)
const eventBus = useEventBus()
const { requireLogin } = useRequireLogin()
const { canEdit, requireWrite } = useProjectPermission()
const envStore = useEnvStore()
const viewMode = ref<"steps" | "variables">("steps")
const selectedSceneId = ref<number | null>(null)
const selectedScene = ref<SceneRecord | null>(null)
const steps = ref<SceneStepViewModel[]>([])
const editingName = ref("")
const editingDescription = ref("")
const editingPriority = ref("P2")

const sceneLoading = ref(false)
const sceneError = ref("")
const envId = ref<number | null>(null)
const envs = ref<Environment[]>([])
let _syncingEnv = false

watch(envId, (newEnvId) => {
  if (_syncingEnv) return
  if (newEnvId && envStore.currentEnvId !== newEnvId) {
    _syncingEnv = true
    envStore.switchEnv(newEnvId)
    _syncingEnv = false
  }
})

watch(() => envStore.currentEnvId, (newGlobalEnvId) => {
  if (_syncingEnv) return
  if (newGlobalEnvId && envId.value !== newGlobalEnvId) {
    _syncingEnv = true
    envId.value = newGlobalEnvId
    isDirty.value = true
    _syncingEnv = false
  }
})
const loopCount = ref(1)
const threadCount = ref(1)
const onFailure = ref("stop")
const varPersistTarget = ref<"environment" | "global" | "none">("environment")
const globalCookie = ref(false)
const stepDelay = ref(0)
const stepDelayRandom = ref(false)
const stepDelayMin = ref(0)
const stepDelayMax = ref(0)
const concurrency = ref(1)
const targetSceneId = ref<number | null>(null)
const showCopyDialog = ref(false)
const copyLoading = ref(false)
const showWaitStepDialog = ref(false)
const newWaitDuration = ref(1000)
const newWaitLabel = ref("")
const sceneList = ref<SceneListItem[]>([])
const selectedStepKeys = ref(new Set<string>())
const batchDeleting = ref(false)
const isDirty = ref(false)
watch(isDirty, (dirty) => {
  if (dirty) {
    tabsStore.markDirty(sceneTabKey.value)
  } else {
    tabsStore.markClean(sceneTabKey.value)
  }
})
let _lastRunClickTime = 0
const _isRunning = ref(false)

const saveLock = useSubmitLock()
const scheduleLock = useSubmitLock()
const importLock = useSubmitLock()

const sceneNameChanged = computed(() => {
  return editingName.value !== (selectedScene.value?.name || '')
})

function onSceneNameBlur() {
  if (editingName.value && sceneNameChanged.value) {
    void saveScene()
  }
}

const webhookEnabled = ref(false)
const webhookUrl = ref("")
const webhookTriggers = ref<string[]>(["always"])

// ── 数据集相关 ──
interface SceneDatasetItem {
  id: number
  scene_id: number
  name: string
  data: Record<string, string>[]
  type: string
  created_at?: string
}
const showDatasetPanel = ref(false)
const sceneDatasets = ref<SceneDatasetItem[]>([])
const selectedDatasetId = ref<number | null>(null)
const expandedStepKey = ref<string | null>(null)

function parseJsonArray(value: unknown): Record<string, unknown>[] {
  if (Array.isArray(value)) return value as Record<string, unknown>[]
  if (typeof value === "string" && value.trim()) {
    try {
      const parsed = JSON.parse(value)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

function buildStepKey(step: Partial<SceneStep>, index: number) {
  return step.id ? `step_${step.id}_${index}` : `step_temp_${index}_${Date.now()}`
}

function normalizeStep(step: Partial<SceneStep>, index: number): SceneStepViewModel {
  return {
    ...step,
    _key: step._key || buildStepKey(step, index),
    method: (step as SceneStepViewModel).method || "GET",
    label: step.label || t('scene.stepLabel', { index: index + 1 }),
    enabled: Boolean(step.enabled ?? true),
    path: step.path || "",
    node_type: step.node_type || "request",
    query_params: parseJsonArray(step.query_params),
    headers: parseJsonArray(step.headers),
    request_body: typeof step.request_body === "string" ? step.request_body : "",
    assertions: parseJsonArray(step.assertions),
    extract_vars: parseJsonArray(step.extract_vars),
    condition_expression: step.condition_expression || "",
    loop_count: step.loop_count ?? null,
    wait_duration: step.wait_duration ?? null,
    wait_mode: (step as SceneStepViewModel).wait_mode || 'fixed',
    wait_min: (step as SceneStepViewModel).wait_min ?? null,
    wait_max: (step as SceneStepViewModel).wait_max ?? null,
    loop_variable: (step as SceneStepViewModel).loop_variable || '',
    depends_on_step_id: step.depends_on_step_id ?? null,
  }
}

function hydrateScene(sceneData: SceneRecord, stepList: Partial<SceneStep>[]) {
  selectedScene.value = sceneData
  editingName.value = sceneData.name || ""
  editingDescription.value = sceneData.description || ""
  editingPriority.value = (sceneData as Record<string, unknown>).priority as string || "P2"
  envId.value = sceneData.env_id ?? null
  loopCount.value = sceneData.loop_count || 1
  threadCount.value = sceneData.thread_count || 1
  onFailure.value = sceneData.on_failure || "stop"
  varPersistTarget.value = sceneData.var_persist_target || "environment"
  globalCookie.value = Boolean(sceneData.global_cookie)
  stepDelay.value = sceneData.step_delay || 0
  stepDelayRandom.value = Boolean(sceneData.step_delay_random)
  stepDelayMin.value = sceneData.step_delay_min || 0
  stepDelayMax.value = sceneData.step_delay_max || 0
  concurrency.value = sceneData.concurrency || sceneData.thread_count || 1
  steps.value = stepList.map((item, index) => normalizeStep(item, index))
}

async function loadSceneList() {
  try {
    const res = await request.get(`/projects/${projectId.value}/scenes`, { params: { page_size: 100 } })
    sceneList.value = (res.data?.items || []).map((item: SceneListItem) => ({ id: item.id, name: item.name }))
  } catch (e) {
    sceneList.value = []
    const err = e as ApiError
    if (err?.response?.status !== 401) {
      msgError(t('scene.loadSceneListFailed'))
    }
  }
}

async function loadEnvs() {
  try {
    const res = await request.get(`/projects/${projectId.value}/environments`, { params: { page_size: 100 } })
    envs.value = res.data?.items || res.data || []
    if (!envId.value && envs.value.length > 0) {
      envId.value = envs.value[0].id
    }
  } catch (error) {
    if (!isSilentAuthError(error)) {
      logger.error("[ScenesView] loadEnvs failed", error)
      msgError(t('scene.loadEnvFailed'))
    }
    envs.value = []
  }
}

async function loadSceneDetail(id: number) {
  sceneLoading.value = true
  sceneError.value = ""
  try {
    const res = await request.get(`/projects/${projectId.value}/scenes/${id}`)
    const data = res.data || {}
    const sceneData = (data.scene || data) as SceneRecord
    const stepList = (data.steps || []) as Partial<SceneStep>[]
    selectedSceneId.value = sceneData.id || id
    hydrateScene(sceneData, stepList)
    await loadSchedule(selectedSceneId.value)
    await loadDatasets(selectedSceneId.value)
  } catch (error: unknown) {
    const err = error as ApiError
    if (err?.response?.status !== 401) {
      logger.error("[ScenesView] loadSceneDetail failed", error)
      msgError(t('scene.loadSceneDetailFailed'))
      sceneError.value = err?.response?.data?.message || err?.message || t('scene.loadFailed')
    }
  } finally {
    sceneLoading.value = false
  }
}

async function saveScene() {
  if (!selectedScene.value) return
  if (!(await requireLogin(t('scene.saveScene')))) return
  try {
    const payload = {
      name: editingName.value.trim() || selectedScene.value.name,
      description: editingDescription.value.trim(),
      priority: editingPriority.value,
      loop_count: loopCount.value,
      thread_count: threadCount.value,
      on_failure: onFailure.value,
      var_persist_target: varPersistTarget.value,
      env_id: envId.value,
      schedule_enabled: scheduleEnabled.value ? 1 : 0,
      schedule_cron: scheduleCron.value || null,
      steps: steps.value.map((step, index) => ({
        id: step.id,
        node_id: step.node_id || step._key,
        node_type: step.node_type || "request",
        label: step.label,
        api_id: step.api_id ?? null,
        test_case_id: step.test_case_id ?? null,
        sort_order: index + 1,
        enabled: step.enabled ? 1 : 0,
        headers: JSON.stringify(step.headers || []),
        query_params: JSON.stringify(step.query_params || []),
        request_body: step.request_body || "",
        assertions: JSON.stringify(step.assertions || []),
        extract_vars: JSON.stringify(step.extract_vars || []),
        condition_expression: step.condition_expression || null,
        loop_count: step.loop_count ?? null,
        loop_variable: step.loop_variable || null,
        wait_duration: step.wait_duration ?? null,
        wait_mode: step.wait_mode || "fixed",
        wait_min: step.wait_min ?? null,
        wait_max: step.wait_max ?? null,
        depends_on_step_id: step.depends_on_step_id ?? null,
      })),
      edges: [],
    }

    await request.put(`/projects/${projectId.value}/scenes/${selectedScene.value.id}`, payload)
    msgSuccess(t('scene.sceneSaved'))
    isDirty.value = false
    await loadSceneDetail(selectedScene.value.id)
    await loadSceneList()
  } catch {
    msgError(t('scene.saveSceneFailed'))
  }
}

const {
  execVisible,
  execSceneName,
  execSteps,
  execDoneCount,
  execPassCount,
  execFailCount,
  execSkipCount,
  execTotalSteps,
  execDuration,
  execStatus,
  execCurrentStepIndex,
  runScene,
  runSceneStress,
  stopPolling,
  viewReport,
  rerunScene,
  cancelExecution,
  minimizeExecution,
} = useSceneExecution({
  projectId: projectId.value,
  requireLogin,
  selectedSceneId,
  saveScene,
  envId,
  eventBus,
  selectedStepKeys,
  datasetId: selectedDatasetId,
})

// 执行状态：检查是否有步骤正在运行（必须在 useSceneExecution 之后，依赖 execSteps）
const isExecuting = computed(() => {
  return execSteps.value.some((step: { status?: string }) => step.status === 'running')
})

// Data-driven execution result grouping
interface DatasetStepResult {
  id: string | number
  name: string
  status: string
  time: number
}

interface DatasetRowResult {
  allPassed: boolean
  totalTime: number
  steps: DatasetStepResult[]
}

const expandedRow = ref<number | null>(null)

const isDataDriven = computed(() => {
  // Check if execution results contain dataset_row_index (indicating data-driven execution)
  return execSteps.value.some((step: Record<string, unknown>) =>
    step.dataset_row_index !== undefined || step.dataset_row !== undefined
  )
})

const datasetResults = computed<DatasetRowResult[]>(() => {
  if (!isDataDriven.value) return []

  // Group steps by their dataset row index
  const rowMap = new Map<number, DatasetRowResult>()

  for (const step of execSteps.value) {
    const s = step as Record<string, unknown>
    const rowIndex = (s.dataset_row_index ?? s.dataset_row) as number | undefined
    if (rowIndex === undefined) continue

    if (!rowMap.has(rowIndex)) {
      rowMap.set(rowIndex, { allPassed: true, totalTime: 0, steps: [] })
    }

    const rowResult = rowMap.get(rowIndex)!
    const status = String((s.status as string) ?? 'pending').toLowerCase()
    const passed = status === 'success' || status === 'passed'
    if (!passed) rowResult.allPassed = false

    const time = typeof s.duration === 'number' ? s.duration : (typeof s.time === 'number' ? s.time : 0)
    rowResult.totalTime += time

    rowResult.steps.push({
      id: (s.id as string | number) || `${rowIndex}_${rowResult.steps.length}`,
      name: String((s.name as string) ?? (s.label as string) ?? t('scene.stepLabel', { index: rowResult.steps.length + 1 })),
      status,
      time,
    })
  }

  return Array.from(rowMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([, v]) => v)
})

// 执行前检查未保存修改
async function checkUnsavedBeforeRun() {
  const tempSteps = steps.value.filter(s => s._key?.startsWith('step_temp_'))
  if (tempSteps.length > 0 || isDirty.value) {
    try {
      await ElMessageBox.confirm(
        t('scene.unsavedBeforeRun'),
        t('scene.warning'),
        {
          confirmButtonText: t('scene.saveAndRun'),
          cancelButtonText: t('scene.runDirectly'),
          distinguishCancelAndClose: true,
          closeOnClickModal: false,
          type: 'warning',
        }
      )
      // 用户选择"保存并执行"
      await saveScene()
    } catch (action) {
      if (action === 'close') {
        return false // 用户点击关闭按钮(X) → 取消执行
      }
      // action === 'cancel' → 用户选择"直接执行"，不保存直接执行
    }
  }
  return true
}

// 执行前验证场景配置完整性
function validateSceneConfig(): { valid: boolean; message: string } {
  // 检查是否有启用的步骤
  const enabledSteps = steps.value.filter(s => s.enabled)
  if (enabledSteps.length === 0) {
    return { valid: false, message: t('scene.needEnabledStep') }
  }

  // 检查每个步骤是否有接口或用例
  for (let i = 0; i < enabledSteps.length; i++) {
    const step = enabledSteps[i]
    // 等待步骤不需要接口或用例
    if (step.wait_duration) continue

    // 有 api_id 或 test_case_id 即可
    if (step.api_id || step.test_case_id) continue

    // 没有关联接口/用例时，检查是否有 method 和 path（手动配置的步骤）
    if (step.method && step.path) continue

    return {
      valid: false,
      message: t('scene.stepMissingApi', { index: i + 1, label: step.label || t('scene.unnamedStep') })
    }
  }

  return { valid: true, message: '' }
}

// 包装运行函数，添加临时步骤检查 + 并发锁
async function runSceneWithCheck(scene: { id: number; name: string } | null) {
  if (!scene) {
    msgWarning(t('scene.selectSceneFirst'))
    return
  }
  if (_isRunning.value) {
    msgWarning(t('scene.sceneRunning'))
    return
  }
  const now = Date.now()
  if (now - _lastRunClickTime < 500) return
  _lastRunClickTime = now

  // 检查未保存修改
  if (!(await checkUnsavedBeforeRun())) return

  // 验证场景配置
  const validation = validateSceneConfig()
  if (!validation.valid) {
    msgError(validation.message)
    return
  }

  _isRunning.value = true
  try {
    await runScene(scene)
  } finally {
    _isRunning.value = false
  }
}

const {
  selectedStepKey,
  selectedStep,
  stepDetailTab,
  showStepDetail,
  stepBreadcrumb,
  hasPrevStep,
  hasNextStep,
  goToPrevStep,
  goToNextStep,
  onRunCommand,
  onStepDetailClosed,
  markDirty,
  stepAction,
  onSortUpdate,
  onDragEnd,
  currentServiceUrl,
  currentEnvServices,
  switchEnvService,
  stepUrlSegments,
  duplicateVariables,
  showDataFlowView,
  dataFlowSteps,
  stepDetailTabs,
  removeExtract,
  addExtract,
} = useStepEditor({
  steps,
  selectedScene,
  editingName,
  envId,
  envs,
  runScene: (...args: Parameters<typeof runScene>) => void runScene(...args),
  runSceneStress: (...args: Parameters<typeof runSceneStress>) => void runSceneStress(...args),
})

const _sceneImport = useSceneImport({
  projectId: projectId.value,
  steps,
  onImported: () => { isDirty.value = true },
})
const { showImportDialog, importLoading, importTreeData, importSelected, onTreeCheck, doImport } = _sceneImport

const rawImportSearch = ref('')
const importSearch = useDebounce(() => rawImportSearch.value, 300)
watch(importSearch, (val) => {
  _sceneImport.importSearch.value = val
})

const openImport = () => {
  rawImportSearch.value = ''
  _sceneImport.openImport()
}

const {
  scheduleEnabled,
  scheduleCron,
  setQuickCron,
  loadSchedule,
  onScheduleToggle: toggleSchedule,
  saveSchedule: persistSchedule,
} = useSceneSchedule()

const stepBadgeMap = computed(() => {
  const map: Record<string, Array<{ label: string; tagType?: "success" | "warning" | "danger" | "info"; isLoop?: boolean; isCondition?: boolean; isDepends?: boolean }>> = {}
  steps.value.forEach((step, index) => {
    const badges: Array<{ label: string; tagType?: "success" | "warning" | "danger" | "info"; isLoop?: boolean; isCondition?: boolean; isDepends?: boolean }> = []
    if (step.assertions?.length) badges.push({ label: t('scene.assertionBadge', { count: step.assertions.length }), tagType: "info" })
    if (step.extract_vars?.length) badges.push({ label: t('scene.variableBadge', { count: step.extract_vars.length }), tagType: "success" })
    if (step.condition_expression) badges.push({ label: t('scene.conditionBadge'), tagType: "warning", isCondition: true })
    if (step.wait_duration) badges.push({ label: `${step.wait_duration}ms`, tagType: "warning" })
    if (step.loop_count && step.loop_count > 1) badges.push({ label: t('scene.loopBadge', { count: step.loop_count }), isLoop: true })
    if (step.depends_on_step_id) {
      const depStep = steps.value.find((s) => s.id === step.depends_on_step_id)
      badges.push({ label: t('scene.dependsBadge', { label: depStep?.label || '?' }), isDepends: true })
    }
    if (!step.enabled) badges.push({ label: t('scene.disabledBadge'), tagType: "danger" })
    if (!badges.length && index === 0) badges.push({ label: t('scene.startBadge'), tagType: "success" })
    map[step._key] = badges.slice(0, 4)
  })
  return map
})

const previousStepsForDetail = computed(() => {
  if (!selectedStep.value) return []
  const currentIndex = steps.value.findIndex(
    (s: SceneStepViewModel) => (s.id && s.id === selectedStep.value!.id) || s._key === selectedStep.value!._key
  )
  if (currentIndex <= 0) return []
  return steps.value.slice(0, currentIndex).map((s: SceneStepViewModel) => ({
    id: s.id,
    _key: s._key,
    label: s.label || t('scene.stepLabel', { index: steps.value.indexOf(s) + 1 }),
  }))
})

function clearSelection() {
  selectedStepKeys.value = new Set()
}

function handleDragEnd() {
  onDragEnd()
  isDirty.value = true
  // 拖拽排序后自动保存，确保持久化到后端
  if (selectedScene.value) {
    void saveScene()
  }
}

function onStepClick(event: MouseEvent, step: SceneStepViewModel, index: number) {
  const key = step._key
  if (event.ctrlKey || event.metaKey) {
    const next = new Set(selectedStepKeys.value)
    if (next.has(key)) next.delete(key)
    else next.add(key)
    selectedStepKeys.value = next
  } else if (event.shiftKey) {
    // 如果没有上次选中项，Shift+点击时选中从首项到当前项
    const anchorKey = selectedStepKey.value || steps.value[0]?._key
    if (anchorKey) {
      const lastIndex = steps.value.findIndex((item) => item._key === anchorKey)
      const [start, end] = [lastIndex, index].sort((a, b) => a - b)
      selectedStepKeys.value = new Set(steps.value.slice(start, end + 1).map((item) => item._key))
    }
  } else {
    selectedStepKeys.value = new Set([key])
  }
  selectedStepKey.value = key
  selectedStep.value = step as Partial<SceneStep>
  showStepDetail.value = true
}

async function handleStepAction(cmd: string, step: SceneStepViewModel, index: number) {
  if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(
        t('scene.deleteStepConfirm'),
        t('scene.warning'),
        { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' }
      )
    } catch {
      return
    }
  }
  stepAction(cmd, step, index)
}

async function batchDelete() {
  if (!selectedScene.value || selectedStepKeys.value.size === 0) return
  try {
    await ElMessageBox.confirm(t('scene.batchDeleteConfirm', { count: selectedStepKeys.value.size }), t('scene.batchDeleteTitle'), { type: "warning" })
  } catch {
    return // 用户取消
  }
  batchDeleting.value = true
  try {
    const stepIds = steps.value.filter((step) => selectedStepKeys.value.has(step._key) && step.id).map((step) => step.id as number)
    if (stepIds.length > 0) {
      await request.delete(`/projects/${projectId.value}/scenes/${selectedScene.value.id}/steps/batch`, {
        data: { step_ids: stepIds },
      })
    }
    steps.value = steps.value.filter((step) => !selectedStepKeys.value.has(step._key))
    clearSelection()
    showStepDetail.value = false
    msgSuccess(t('scene.stepsDeletedOk'))
  } catch {
    msgError(t('scene.deleteStepFailed'))
  } finally {
    batchDeleting.value = false
  }
}

function handleExportScene(command: string) {
  if (!selectedScene.value) {
    msgWarning(t('scene.selectSceneWarning'))
    return
  }
  const sceneData = {
    name: selectedScene.value.name,
    steps: steps.value,
    config: {
      concurrency: concurrency.value,
      loop_count: loopCount.value,
      on_failure: onFailure.value,
      var_persist_target: varPersistTarget.value,
      env_id: envId.value,
      global_cookie: globalCookie.value,
      step_delay: stepDelay.value,
      step_delay_random: stepDelayRandom.value,
      step_delay_min: stepDelayMin.value,
      step_delay_max: stepDelayMax.value,
    },
  }
  if (command === "json") {
    downloadSceneJson(sceneData)
    msgSuccess(t('scene.exportJsonSuccess'))
  } else if (command === "copy") {
    const json = exportSceneToJson(sceneData)
    navigator.clipboard.writeText(json).then(() => {
      msgSuccess(t('scene.copyJsonSuccess'))
    }).catch(() => {
      msgError(t('scene.copyFailedManual'))
    })
  }
}

function openCopyDialog() {
  if (selectedStepKeys.value.size === 0) {
    msgWarning(t('scene.selectStepsFirst'))
    return
  }
  targetSceneId.value = null
  showCopyDialog.value = true
}

function openAddWaitStep() {
  if (!selectedScene.value) {
    msgWarning(t('scene.selectSceneWarning'))
    return
  }
  newWaitDuration.value = 1000
  newWaitLabel.value = ""
  showWaitStepDialog.value = true
}

function addWaitStep() {
  const duration = newWaitDuration.value || 1000
  const label = newWaitLabel.value.trim() || t('scene.waitLabel', { duration })
  steps.value.push(normalizeStep({
    _key: `step_wait_${Date.now()}`,
    node_type: "wait",
    label,
    method: "",
    path: "",
    enabled: true,
    wait_duration: duration,
    request_body: "",
    headers: [],
    query_params: [],
    assertions: [],
    extract_vars: [],
  }, steps.value.length))
  showWaitStepDialog.value = false
  isDirty.value = true
}

// ── 数据集方法 ──
async function loadDatasets(sceneId: number) {
  try {
    const res = await request.get(`/projects/${projectId.value}/scenes/${sceneId}/datasets`)
    sceneDatasets.value = res.data || []
  } catch {
    sceneDatasets.value = []
  }
}

async function addDataset() {
  if (!selectedScene.value) return
  try {
    const res = await request.post(`/projects/${projectId.value}/scenes/${selectedScene.value.id}/datasets`, {
      name: t('scene.datasetDefaultName', { index: sceneDatasets.value.length + 1 }),
      data: [{ col1: "" }],
      type: "json",
    })
    sceneDatasets.value.push(res.data)
  } catch {
    msgError(t('scene.createDatasetFailed'))
  }
}

async function updateDataset(ds: SceneDatasetItem) {
  if (!selectedScene.value) return
  try {
    await request.put(`/projects/${projectId.value}/scenes/${selectedScene.value.id}/datasets/${ds.id}`, {
      name: ds.name,
      data: ds.data,
      type: ds.type,
    })
  } catch {
    msgError(t('scene.updateDatasetFailed'))
  }
}

async function deleteDataset(ds: SceneDatasetItem) {
  if (!selectedScene.value) return
  try {
    await ElMessageBox.confirm(
      t('scene.deleteDatasetConfirm', { name: ds.name }),
      t('scene.warning'),
      { confirmButtonText: t('common.confirm'), cancelButtonText: t('common.cancel'), type: 'warning' }
    )
  } catch {
    return
  }
  try {
    await request.delete(`/projects/${projectId.value}/scenes/${selectedScene.value.id}/datasets/${ds.id}`)
    sceneDatasets.value = sceneDatasets.value.filter(d => d.id !== ds.id)
    if (selectedDatasetId.value === ds.id) selectedDatasetId.value = null
  } catch {
    msgError(t('scene.deleteDatasetFailed'))
  }
}

function getDatasetColumns(data: Record<string, string>[]): string[] {
  const colSet = new Set<string>()
  for (const row of data) {
    for (const key of Object.keys(row)) colSet.add(key)
  }
  return Array.from(colSet)
}

function addDatasetRow(ds: SceneDatasetItem) {
  const cols = getDatasetColumns(ds.data)
  const newRow: Record<string, string> = {}
  for (const col of cols) newRow[col] = ""
  ds.data.push(newRow)
  void updateDataset(ds)
}

function addDatasetColumn(ds: SceneDatasetItem) {
  const colName = `col${getDatasetColumns(ds.data).length + 1}`
  for (const row of ds.data) row[colName] = ""
  void updateDataset(ds)
}

function removeDatasetRow(ds: SceneDatasetItem, index: number) {
  ds.data.splice(index, 1)
  void updateDataset(ds)
}

function onDatasetFileUpload(event: Event) {
  if (!selectedScene.value) return
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const reader = new FileReader()
  reader.onload = async (e) => {
    const content = e.target?.result as string
    let data: Record<string, string>[] = []
    let type = "json"

    if (file.name.endsWith(".csv")) {
      type = "csv"
      const lines = content.split(/\r?\n/).filter(l => l.trim())
      if (lines.length < 2) { msgWarning(t('scene.csvMinRows')); return }
      const headers = parseCSVLine(lines[0])
      for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i])
        const row: Record<string, string> = {}
        headers.forEach((h, idx) => { row[h] = values[idx] || "" })
        data.push(row)
      }
    } else {
      try {
        const parsed = JSON.parse(content)
        if (Array.isArray(parsed)) {
          data = parsed.map((item: unknown) => {
            if (typeof item === "object" && item !== null) return item as Record<string, string>
            return { value: String(item) }
          })
        }
      } catch {
        msgError(t('scene.jsonParseFailed'))
        return
      }
    }

    try {
      const res = await request.post(`/projects/${projectId.value}/scenes/${selectedScene.value!.id}/datasets`, {
        name: file.name.replace(/\.\w+$/, ""),
        data,
        type,
      })
      sceneDatasets.value.push(res.data)
    } catch {
      msgError(t('scene.uploadDatasetFailed'))
    }
  }
  reader.readAsText(file)
  input.value = ""
}

// ── 步骤执行详情方法 ──

/** RFC 4180 兼容的 CSV 行解析：支持引号包裹的字段和转义引号 */
function parseCSVLine(line: string): string[] {
  const result: string[] = []
  let field = ''
  let inQuotes = false
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    if (inQuotes) {
      if (char === '"') {
        // 连续两个引号表示转义的引号
        if (line[i + 1] === '"') {
          field += '"'
          i++
        } else {
          inQuotes = false
        }
      } else {
        field += char
      }
    } else {
      if (char === '"') {
        inQuotes = true
      } else if (char === ',') {
        result.push(field.trim())
        field = ''
      } else {
        field += char
      }
    }
  }
  result.push(field.trim())
  return result
}

function getStepExecResult(step: SceneStepViewModel) {
  if (step.id) {
    const byId = execSteps.value.find((es: Record<string, unknown>) => {
      const esStepId = es.step_id
      if (esStepId === undefined || esStepId === null) return false
      return Number(esStepId) === Number(step.id)
    })
    if (byId) return byId as Record<string, unknown> | undefined
  }

  const stepIndex = steps.value.findIndex((s: SceneStepViewModel) => s._key === step._key)
  if (stepIndex >= 0 && stepIndex < execSteps.value.length) {
    const byIndex = execSteps.value[stepIndex]
    if (byIndex && byIndex.status && byIndex.status !== 'pending') {
      return byIndex as Record<string, unknown>
    }
  }

  return execSteps.value.find((es: Record<string, unknown>) => {
    const esName = (es.name as string) || ''
    const stepLabel = step.label || ''
    const stepPath = step.path || ''
    return esName === stepLabel || esName === stepPath || esName.endsWith(stepPath)
  }) as Record<string, unknown> | undefined
}

// 步骤执行状态标识
function getStepExecStatus(step: SceneStepViewModel): string {
  if (!isExecuting.value && execSteps.value.length === 0) return ''
  const result = getStepExecResult(step)
  if (!result) return 'pending'
  const status = String(typeof result.status === 'string' ? result.status : '')
  if (status === 'running') return 'running'
  if (status === 'success' || status === 'passed') return 'pass'
  if (status === 'failed' || status === 'error') return 'fail'
  return 'pending'
}

// 执行进度计算
const execProgress = computed(() => {
  if (execTotalSteps.value === 0) return 0
  return Math.round((execDoneCount.value / execTotalSteps.value) * 100)
})
const execPercentStatus = computed(() => {
  if (execStatus.value === 'success') return 'success'
  if (execStatus.value === 'failed') return 'exception'
  return undefined
})
const completedSteps = computed(() => execDoneCount.value)
const totalExecSteps = computed(() => execTotalSteps.value)
const passedSteps = computed(() => execPassCount.value)
const failedSteps = computed(() => execFailCount.value)

function toggleStepExpand(key: string) {
  expandedStepKey.value = expandedStepKey.value === key ? null : key
}

function formatExecData(data: unknown): string {
  if (!data) return ''
  if (typeof data === 'string') {
    try {
      const parsed = JSON.parse(data)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return data
    }
  }
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return '[object]'
  }
}

function getDiffLineClass(line: string): string {
  if (line.startsWith('+++') || line.startsWith('@@')) return 'diff-meta'
  if (line.startsWith('---')) return 'diff-meta'
  if (line.startsWith('+')) return 'diff-added'
  if (line.startsWith('-')) return 'diff-removed'
  return 'diff-context'
}

function getStatusClass(status: unknown): string {
  const code = Number(status) || 0
  if (code >= 200 && code < 300) return 'status-2xx'
  if (code >= 300 && code < 400) return 'status-3xx'
  if (code >= 400 && code < 500) return 'status-4xx'
  if (code >= 500) return 'status-5xx'
  return ''
}

async function batchCopy() {
  if (!selectedScene.value || !targetSceneId.value) return
  copyLoading.value = true
  try {
    const selectedSteps = steps.value.filter((step) => selectedStepKeys.value.has(step._key))
    const payload = {
      target_scene_id: targetSceneId.value,
      steps: selectedSteps.map((step, index) => ({
        id: step.id,
        node_id: step.node_id || step._key,
        node_type: step.node_type,
        label: step.label,
        api_id: step.api_id ?? null,
        test_case_id: step.test_case_id ?? null,
        sort_order: index + 1,
        enabled: step.enabled ? 1 : 0,
        headers: JSON.stringify(step.headers || []),
        query_params: JSON.stringify(step.query_params || []),
        request_body: step.request_body || "",
        assertions: JSON.stringify(step.assertions || []),
        extract_vars: JSON.stringify(step.extract_vars || []),
        condition_expression: step.condition_expression || null,
        loop_count: step.loop_count ?? null,
        loop_variable: step.loop_variable || null,
        wait_duration: step.wait_duration ?? null,
        wait_mode: step.wait_mode || "fixed",
        wait_min: step.wait_min ?? null,
        wait_max: step.wait_max ?? null,
        depends_on_step_id: step.depends_on_step_id ?? null,
      })),
    }
    await request.post(`/projects/${projectId.value}/scenes/${selectedScene.value.id}/steps/batch`, payload)
    showCopyDialog.value = false
    msgSuccess(t('scene.copySuccess'))
  } catch {
    msgError(t('scene.copyStepFailed'))
  } finally {
    copyLoading.value = false
  }
}

async function handleCreateScene() {
  if (!(await requireWrite('新建场景'))) return
  await scene.value?.createScene()
}

function onTreeSceneSelected(sceneItem: SceneListItem) {
  selectedSceneId.value = sceneItem.id
  void loadSceneDetail(sceneItem.id)
}

function onTreeSceneCreated(id: number) {
  selectedSceneId.value = id
  void loadSceneList()
  void loadSceneDetail(id)
}

function onTreeSceneDeleted(id: number) {
  if (selectedSceneId.value === id) {
    selectedSceneId.value = null
    selectedScene.value = null
    steps.value = []
    editingName.value = ""
    showStepDetail.value = false
  }
  void loadSceneList()
}

async function onScheduleToggle(value: boolean) {
  if (!selectedScene.value) return
  await toggleSchedule(value, selectedScene.value.id)
}

async function saveSchedule() {
  if (!selectedScene.value) return
  await persistSchedule(selectedScene.value.id, envId.value)
}

onMounted(() => {
  const qSceneId = route.query.sceneId
  if (qSceneId) selectedSceneId.value = Number(qSceneId)
  void loadEnvs()
  void loadSceneList()
  if (qSceneId) void loadSceneDetail(Number(qSceneId))
})

onActivated(async () => {
  if (isDirty.value) {
    try {
      await ElMessageBox.confirm(t('scene.unsavedChangesWarning'), t('scene.warning'), {
        confirmButtonText: t('scene.save'),
        cancelButtonText: t('scene.discard'),
        distinguishCancelAndClose: true,
        type: 'warning',
      })
      await saveScene()
    } catch (action) {
      if (action === 'close') return
      // action === 'cancel' → 放弃更改，继续刷新
    }
  }
  if (selectedSceneId.value) void loadSceneDetail(selectedSceneId.value)
  void loadEnvs()
  void loadSceneList()
})

watch(() => route.params.id, (newId, oldId) => {
  if (newId && oldId && newId !== oldId) {
    selectedSceneId.value = null
    steps.value = []
    void loadEnvs()
    void loadSceneList()
  }
})

watch(() => route.query.sceneId, (val) => {
  if (val) {
    selectedSceneId.value = Number(val)
    void loadSceneDetail(Number(val))
  }
})

watch(selectedSceneId, (id) => {
  // 仅在场景页面时更新 query，避免导航离开时劫持路由
  if (route.path.includes('/scenes')) {
    if (id) void router.replace({ query: { sceneId: id } })
    else void router.replace({ query: {} })
  }
})
</script>

<style src="./scenes-view.css"></style>
