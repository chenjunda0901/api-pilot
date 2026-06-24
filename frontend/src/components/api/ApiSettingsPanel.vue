<template>
  <div class="advanced-tab">
    <!-- Markdown 描述 -->
    <div class="settings-group">
      <div class="settings-group-title">接口描述</div>
      <div class="md-editor-wrapper">
        <MdEditor
          :model-value="descriptionMd"
          language="zh-CN"
          :preview="true"
          :toolbars-exclude="['github', 'htmlPreview', 'catalog', 'save']"
          placeholder="使用 Markdown 编写接口描述文档..."
          :style="{ height: '360px' }"
          @update:model-value="$emit('update:descriptionMd', $event)"
        />
      </div>
    </div>

    <!-- 标签 -->
    <div class="settings-group">
      <div class="settings-group-title">标签</div>
      <div class="tag-editor-row">
        <el-select
          :model-value="tags"
          multiple
          filterable
          allow-create
          default-first-option
          :reserve-keyword="false"
          placeholder="输入标签名回车添加"
          style="width: 100%"
          @update:model-value="$emit('update:tags', $event)"
        >
          <el-option
            v-for="t in projectTags"
            :key="t.id"
            :label="t.name"
            :value="t.name"
          >
            <span class="tag-option-dot" :style="{ background: t.color }"></span>
            {{ t.name }}
          </el-option>
        </el-select>
      </div>
    </div>

    <!-- 请求设置 -->
    <div class="settings-group">
      <div class="settings-group-title">请求设置</div>
      <div class="setting-row" v-for="setting in requestSettings" :key="setting.key">
        <div class="setting-info">
          <span class="setting-label">{{ setting.label }}</span>
          <span class="setting-desc">{{ setting.desc }}</span>
        </div>
        <el-switch
          v-if="setting.type === 'switch'"
          :model-value="setting.value"
          @update:model-value="(v: boolean) => $emit('update:setting', setting.key, v)"
        />
        <el-input-number
          v-else-if="setting.type === 'number'"
          :model-value="setting.value"
          :min="setting.min ?? 1"
          :max="setting.max ?? 300"
          size="small"
          @update:model-value="(v: number) => $emit('update:setting', setting.key, v)"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { MdEditor } from 'md-editor-v3'
import 'md-editor-v3/lib/style.css'

export interface TagItem {
  id: number
  name: string
  color: string
}

export interface RequestSetting {
  key: string
  label: string
  desc: string
  type: 'switch' | 'number'
  value: boolean | number
  min?: number
  max?: number
}

const props = defineProps<{
  descriptionMd: string
  tags: string[]
  projectTags: TagItem[]
  settings: Record<string, unknown>
}>()

defineEmits<{
  'update:descriptionMd': [value: string]
  'update:tags': [value: string[]]
  'update:setting': [key: string, value: boolean | number]
}>()

const requestSettings = computed<RequestSetting[]>(() => [
  {
    key: 'follow_redirects',
    label: '跟随重定向',
    desc: '当响应状态码为 3xx 时自动跟随重定向',
    type: 'switch',
    value: (props.settings?.follow_redirects as boolean) ?? true,
  },
  {
    key: 'verify_ssl',
    label: 'SSL 证书验证',
    desc: '验证服务器 SSL 证书的有效性',
    type: 'switch',
    value: (props.settings?.verify_ssl as boolean) ?? true,
  },
  {
    key: 'timeout',
    label: '请求超时',
    desc: '等待服务器响应的最长时间（秒）',
    type: 'number',
    value: (props.settings?.timeout as number) ?? 30,
    min: 1,
    max: 300,
  },
])
</script>

<style scoped>
.advanced-tab {
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}
.settings-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}
.settings-group-title {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  color: var(--text-primary);
  padding-bottom: var(--space-1);
  border-bottom: 1px solid var(--border-subtle);
}
.tag-editor-row {
  display: flex;
  align-items: center;
}
.tag-option-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: var(--space-2);
}
.md-editor-wrapper {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) 0;
}
.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.setting-label {
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--text-primary);
}
.setting-desc {
  font-size: var(--text-xs);
  color: var(--text-muted);
}
</style>
