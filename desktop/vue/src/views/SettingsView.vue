<template>
  <div class="settings-view">
    <div class="settings-section">
      <h3 class="section-title">
        <el-icon><Setting /></el-icon> AI 接入设置
      </h3>
      <p class="section-desc">
        本系统<b>只使用你在这里配置的 API Key</b>，不含任何内置或系统默认密钥。
        配置后即可用 AI 识别上传的计划：Word / PDF / 图片(截图) 中的日期、科目与时间段会被自动解析排期。
        密钥仅保存在本机数据库，不上传、不计费。
      </p>

      <el-tag v-if="keySettings?.has_key && keySettings.enabled" type="success" round size="default" class="status-tag">
        ✓ AI 已启用（{{ keySettings.model }}）
      </el-tag>
      <el-tag v-else-if="keySettings?.has_key" type="info" round size="default" class="status-tag">
        已填 Key 但未启用
      </el-tag>
      <el-tag v-else type="warning" round size="default" class="status-tag">
        ⚠ 未配置（AI 功能不可用）
      </el-tag>
    </div>

    <el-form label-width="100px" class="key-form">
      <el-form-item label="API Key">
        <el-input
          v-model="form.api_key"
          type="password"
          show-password
          :placeholder="keySettings?.api_key_masked ? `当前：${keySettings.api_key_masked}（留空则不修改）` : '粘贴你的 API Key'"
        />
        <div class="form-help">
          推荐
          <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener">DeepSeek</a>
          （便宜好用）/
          <a href="https://dashscope.console.aliyun.com/apiKey" target="_blank" rel="noopener">通义千问</a>
          /
          <a href="https://open.bigmodel.cn/usercenter/apikeys" target="_blank" rel="noopener">智谱</a>
        </div>
      </el-form-item>
      <el-form-item label="Base URL">
        <el-input v-model="form.api_base" placeholder="https://api.deepseek.com" />
        <div class="form-help">DeepSeek 填 <code>https://api.deepseek.com</code>，通义填 <code>https://dashscope.aliyuncs.com/compatible-mode/v1</code></div>
      </el-form-item>
      <el-form-item label="模型名">
        <el-input v-model="form.model" placeholder="deepseek-chat" />
        <div class="form-help">DeepSeek: <code>deepseek-chat</code> / 通义: <code>qwen-plus</code> / 智谱: <code>glm-4-flash</code></div>
      </el-form-item>
      <el-form-item label="启用 AI">
        <el-switch v-model="form.enabled" />
        <div class="form-help">关闭后将无法使用 AI 计划解析（系统没有备用 Key）</div>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="saveKey">保存设置</el-button>
      </el-form-item>
    </el-form>

    <el-divider />

    <div class="settings-section">
      <h3 class="section-title">
        <el-icon><InfoFilled /></el-icon> 关于
      </h3>
      <p class="section-desc">
        StudyMate v{{ version }} — 基于艾宾浩斯遗忘曲线的考研复习管理工具。<br />
        AI 功能依赖你自己的 API Key，所有请求直连模型服务商，不经第三方中转。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, InfoFilled } from '@element-plus/icons-vue'
import { getKeySettings, saveKeySettings, type KeySettings } from '@/api/ai'
import { useAiKey } from '@/composables/useAiKey'

const { refresh } = useAiKey()

const version = ref('1.4.0')
const saving = ref(false)
const keySettings = ref<KeySettings | null>(null)
const form = ref({
  api_key: '',
  api_base: 'https://api.deepseek.com',
  model: 'deepseek-chat',
  enabled: true,
})

async function loadSettings() {
  try {
    const res = await getKeySettings()
    keySettings.value = res.data
    form.value.api_base = res.data.api_base || 'https://api.deepseek.com'
    form.value.model = res.data.model || 'deepseek-chat'
    form.value.enabled = res.data.enabled
  } catch {
    /* ignore */
  }
}

async function saveKey() {
  saving.value = true
  try {
    const res = await saveKeySettings({
      api_key: form.value.api_key || undefined,
      api_base: form.value.api_base,
      model: form.value.model,
      enabled: form.value.enabled,
    })
    keySettings.value = res.data
    form.value.api_key = ''
    ElMessage.success('AI 设置已保存到本机')
    await refresh() // 更新全局 Key 状态
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.settings-view {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 20px;
}
.settings-section { margin-bottom: 20px; }
.section-title {
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 8px; font-size: 16px; font-weight: 600; color: var(--text-strong);
}
.section-desc {
  margin: 0; font-size: 13px; color: var(--text-muted); line-height: 1.7;
}
.status-tag { margin-top: 10px; }
.key-form { max-width: 560px; margin-top: 16px; }
.form-help {
  font-size: 12px; color: var(--text-muted); margin-top: 4px; line-height: 1.6;
}
.form-help a { color: var(--el-color-primary); text-decoration: none; }
.form-help a:hover { text-decoration: underline; }
.form-help code {
  background: var(--el-fill-color-light); padding: 1px 5px; border-radius: 4px; font-size: 11px;
}
.el-divider { margin: 32px 0; }
</style>
