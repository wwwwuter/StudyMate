<template>
  <div class="tasks-view">
    <!-- 顶部：标题 + 今日完成度 -->
    <section class="page-head">
      <div>
        <h2 class="page-title">学习计划</h2>
        <p class="page-sub">管理每日复习任务，支持手动录入、批量创建与 Excel / JSON / PDF 导入。</p>
      </div>
      <div class="head-stat" v-if="stats">
        <div class="hs-block">
          <div class="hs-value">{{ stats.done }}/{{ stats.total }}</div>
          <div class="hs-label">当日完成</div>
        </div>
        <div class="hs-block">
          <div class="hs-value" :style="{ color: rateColor }">{{ stats.completion_rate }}%</div>
          <div class="hs-label">完成率</div>
        </div>
        <div class="hs-block">
          <div class="hs-value">{{ stats.subjects.length }}</div>
          <div class="hs-label">涉及科目</div>
        </div>
      </div>
    </section>

    <!-- 过滤栏 -->
    <el-card class="filter-card" shadow="never">
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :clearable="true"
          />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="filters.subject" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="s in SUBJECTS" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable style="width: 130px">
            <el-option v-for="s in STATUS_LIST" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.keyword" placeholder="任务内容" clearable style="width: 180px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :icon="Search" @click="page = 1; loadTasks()">查询</el-button>
          <el-button :icon="Refresh" @click="resetFilter">重置</el-button>
          <el-button text type="primary" :icon="Calendar" @click="quickToday">今日</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="tb-left">
        <el-button type="primary" :icon="Plus" @click="openCreate">新建任务</el-button>
        <el-button :icon="Document" @click="openBatch">批量创建</el-button>
        <el-dropdown @command="openImportType">
          <el-button :icon="Upload">
            导入计划<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="excel">从 Excel 导入 (.xlsx)</el-dropdown-item>
              <el-dropdown-item command="json">从 JSON 导入</el-dropdown-item>
              <el-dropdown-item command="pdf">从 PDF 导入</el-dropdown-item>
              <el-dropdown-item command="pdf-ai">从 PDF 智能导入（AI）</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
      <div class="tb-right">
        <span class="count-tip">共 {{ tasks.length }} 条</span>
      </div>
    </div>

    <!-- 任务表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tasks" v-loading="loading" empty-text="暂无任务，点击「新建任务」开始规划">
        <el-table-column prop="date" label="日期" width="120" />
        <el-table-column label="科目" width="110">
          <template #default="{ row }">
            <el-tag :style="subjectTagStyle(row.subject)" effect="plain" round>{{ row.subject || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content" label="任务内容" min-width="220" show-overflow-tooltip />
        <el-table-column label="时间" width="150">
          <template #default="{ row }">
            <span v-if="row.start_time || row.end_time">{{ row.start_time || '–' }} ~ {{ row.end_time || '–' }}</span>
            <span v-else class="muted">未排期</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="150">
          <template #default="{ row }">
            <el-select
              :model-value="row.status"
              size="small"
              :style="{ width: '108px' }"
              @change="(v: string) => saveStatus(row, v)"
            >
              <el-option v-for="s in STATUS_LIST" :key="s.value" :label="s.label" :value="s.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="90">
          <template #default="{ row }">
            <el-tag size="small" effect="light" type="info">{{ sourceLabel(row.plan_source) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" :icon="Edit" @click="openEdit(row)">编辑</el-button>
            <el-button link type="danger" :icon="Delete" @click="removeTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next, total"
          background
          hide-on-single-page
          @current-change="loadTasks"
        />
      </div>
    </el-card>

    <!-- 新建 / 编辑 对话框 -->
    <el-dialog v-model="formVisible" :title="editingId ? '编辑任务' : '新建任务'" width="520px">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="84px">
        <el-form-item label="日期" prop="date">
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="科目" prop="subject">
          <el-select v-model="form.subject" filterable allow-create default-first-option placeholder="选择或输入科目" style="width: 100%">
            <el-option v-for="s in SUBJECTS" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="任务内容" prop="content">
          <el-input v-model="form.content" type="textarea" :rows="3" placeholder="例如：高数·中值定理专题训练" />
        </el-form-item>
        <el-form-item label="开始时间">
          <el-time-picker v-model="form.start_time" format="HH:mm" value-format="HH:mm" placeholder="可选" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-time-picker v-model="form.end_time" format="HH:mm" value-format="HH:mm" placeholder="可选" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%">
            <el-option v-for="s in STATUS_LIST" :key="s.value" :label="s.label" :value="s.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="form.priority" style="width: 100%">
            <el-option :value="0" label="普通" />
            <el-option :value="1" label="高" />
            <el-option :value="2" label="紧急" />
          </el-select>
        </el-form-item>
        <el-form-item label="预估时长">
          <el-input-number v-model="form.estimated_minutes" :min="0" :max="600" :controls="false" placeholder="分钟" style="width: 100%" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="逗号分隔，如：强化,真题" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量创建 对话框 -->
    <el-dialog v-model="batchVisible" title="批量创建任务" width="620px">
      <p class="hint">每行一个 JSON 对象，或粘贴一个 JSON 数组。必填字段：<code>date</code>、<code>subject</code>、<code>content</code>。</p>
      <el-input
        v-model="batchText"
        type="textarea"
        :rows="10"
        placeholder='[{"date":"2026-08-01","subject":"数学","content":"高数强化"},{"date":"2026-08-02","subject":"英语","content":"阅读真题"}]'
      />
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitBatch">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入 对话框 -->
    <el-dialog v-model="importVisible" :title="`导入计划（${sourceLabel(importType)}）`" width="560px">
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        :on-change="onImportFile"
        :on-remove="() => (importFile = null)"
        accept=".xlsx,.xls,.json,.pdf"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击选择</em></div>
        <template #tip>
          <div class="el-upload__tip">
            {{ importType === 'excel' ? '支持 .xlsx（旧版 .xls 暂需转换）' : importType === 'json' ? '支持 JSON 数组或 { tasks: [...] }' : importType === 'pdf-ai' ? 'AI 自动识别任务（日期/科目/内容/时段），需后端配置 DeepSeek 或开启 PDF_AI_MOCK' : '从 PDF 中提取「日期 科目 内容 时间范围」行' }}
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" :disabled="!importFile" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- AI 导入预览 / 人工复核（U2） -->
    <el-dialog v-model="previewVisible" title="AI 识别结果预览（请复核后保存）" width="900px" top="5vh">
      <el-alert
        v-if="previewList.some((t) => t.needs_review)"
        type="warning"
        :closable="false"
        show-icon
        title="部分任务日期缺失或置信度较低，已标红，请在保存前补全日期。"
        style="margin-bottom: 12px"
      />
      <el-table :data="previewList" border size="small" max-height="460">
        <el-table-column label="日期" width="150">
          <template #default="{ row }">
            <el-date-picker
              v-model="row.date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="补全日期"
              :class="{ 'cell-warn': row.needs_review && !row.date }"
              style="width: 100%"
            />
          </template>
        </el-table-column>
        <el-table-column label="科目" width="110">
          <template #default="{ row }"><el-input v-model="row.subject" /></template>
        </el-table-column>
        <el-table-column label="任务内容" min-width="180">
          <template #default="{ row }"><el-input v-model="row.content" /></template>
        </el-table-column>
        <el-table-column label="开始" width="110">
          <template #default="{ row }">
            <el-time-picker v-model="row.start_time" format="HH:mm" value-format="HH:mm" placeholder="可选" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="结束" width="110">
          <template #default="{ row }">
            <el-time-picker v-model="row.end_time" format="HH:mm" value-format="HH:mm" placeholder="可选" style="width: 100%" />
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="120">
          <template #default="{ row }">
            <el-tooltip v-if="row.reason" :content="row.reason" placement="top">
              <el-tag :type="confColor(row.confidence)" size="small">
                {{ row.confidence != null ? Math.round(row.confidence * 100) + '%' : '—' }}
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="confColor(row.confidence)" size="small">
              {{ row.confidence != null ? Math.round(row.confidence * 100) + '%' : '—' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="previewVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="confirmSave">确认保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus, Upload, UploadFilled, Edit, Delete, Search, Refresh, Calendar, Document, ArrowDown,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import {
  listTasks, createTask, updateTask, deleteTask, batchCreate, importTasks, dailyStats,
  importPdfAiPreview, confirmPdfAi,
  type TaskItem, type DailyStats, type PreviewTask,
} from '@/api/task'

const userStore = useUserStore()

const SUBJECTS = ['数学', '英语', '政治', '408']
const STATUS_LIST = [
  { value: 'pending', label: '待完成' },
  { value: 'done', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
]
const RATE_COLOR = '#0F766E'
const rateColor = RATE_COLOR

function subjectTagStyle(subject?: string): Record<string, string> {
  const map: Record<string, string> = {
    数学: '#0F766E', 英语: '#0EA5E9', 政治: '#F59E0B', 408: '#8B5CF6',
  }
  const color = map[subject || ''] || '#64748B'
  return { background: `${color}1A`, color, borderColor: `${color}55` }
}
function sourceLabel(src?: string): string {
  return ({ manual: '手动', excel: 'Excel', json: 'JSON', pdf: 'PDF', 'pdf-ai': 'PDF·AI', auto: '自动' } as Record<string, string>)[src || ''] || src || '手动'
}

// ---- 状态 ----
const loading = ref(false)
const tasks = ref<TaskItem[]>([])
const total = ref(0)
const stats = ref<DailyStats | null>(null)
const dateRange = ref<[string, string] | null>(null)
const filters = ref<{ subject?: string; status?: string; keyword?: string }>({})
const page = ref(1)
const pageSize = ref(10)

// ---- 生命周期 ----
onMounted(async () => {
  await userStore.ensureToken()
  await loadTasks()
  await loadStats(todayStr())
})

async function loadStats(date: string) {
  try {
    stats.value = await dailyStats(date)
  } catch {
    stats.value = null
  }
}

async function loadTasks() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { ...filters.value }
    if (dateRange.value) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    params.page = page.value
    params.page_size = pageSize.value
    const res = await listTasks(params)
    tasks.value = res.data
    total.value = res.total
  } catch (e) {
    ElMessage.error((e as Error).message || '加载任务失败')
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  dateRange.value = null
  filters.value = {}
  page.value = 1
  loadTasks()
}
function quickToday() {
  const t = todayStr()
  dateRange.value = [t, t]
  filters.value = {}
  page.value = 1
  loadTasks()
}
function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

// ---- 新建 / 编辑 ----
const formVisible = ref(false)
const editingId = ref<number | null>(null)
const submitting = ref(false)
const formRef = ref<FormInstance>()
interface TaskForm {
  date: string
  subject: string
  content: string
  start_time: string | null
  end_time: string | null
  status: 'pending' | 'done' | 'cancelled'
  priority: number
  estimated_minutes: number | null
  tags: string | null
}
const form = ref<TaskForm>({
  date: '',
  subject: '',
  content: '',
  start_time: null,
  end_time: null,
  status: 'pending',
  priority: 0,
  estimated_minutes: null,
  tags: null,
})
const rules: FormRules = {
  date: [{ required: true, message: '请选择日期', trigger: 'change' }],
  subject: [{ required: true, message: '请选择或输入科目', trigger: 'change' }],
  content: [{ required: true, message: '请输入任务内容', trigger: 'blur' }],
}

function resetForm() {
  form.value = { date: '', subject: '', content: '', start_time: '', end_time: '', status: 'pending', priority: 0, estimated_minutes: null, tags: null }
  editingId.value = null
}
function openCreate() {
  resetForm()
  formVisible.value = true
}
function openEdit(row: TaskItem) {
  editingId.value = row.id
  form.value = {
    date: row.date,
    subject: row.subject,
    content: row.content,
    start_time: row.start_time || '',
    end_time: row.end_time || '',
    status: row.status,
    priority: row.priority ?? 0,
    estimated_minutes: row.estimated_minutes ?? null,
    tags: row.tags ?? null,
  }
  formVisible.value = true
}
async function submitForm() {
  if (!formRef.value) return
  await formRef.value.validate()
  if (form.value.start_time && form.value.end_time && form.value.start_time > form.value.end_time) {
    ElMessage.warning('结束时间不能早于开始时间')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateTask(editingId.value, { ...form.value })
      ElMessage.success('已更新')
    } else {
      await createTask({ ...form.value })
      ElMessage.success('已创建')
    }
    formVisible.value = false
    await loadTasks()
  } catch (e) {
    ElMessage.error((e as Error).message || '保存失败')
  } finally {
    submitting.value = false
  }
}

// ---- 状态切换 ----
async function saveStatus(row: TaskItem, val: string) {
  try {
    await updateTask(row.id, { status: val as TaskItem['status'] })
    row.status = val as TaskItem['status']
    ElMessage.success('状态已更新')
    await loadStats(row.date)
  } catch (e) {
    ElMessage.error((e as Error).message || '更新失败')
  }
}

// ---- 删除 ----
async function removeTask(row: TaskItem) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.content}」？`, '删除任务', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteTask(row.id)
    ElMessage.success('已删除')
    await loadTasks()
    await loadStats(row.date)
  } catch (e) {
    ElMessage.error((e as Error).message || '删除失败')
  }
}

// ---- 批量 ----
const batchVisible = ref(false)
const batchText = ref('')
function openBatch() {
  batchText.value = ''
  batchVisible.value = true
}
async function submitBatch() {
  let items: unknown
  try {
    items = JSON.parse(batchText.value)
  } catch {
    ElMessage.error('JSON 解析失败，请检查格式')
    return
  }
  const arr = Array.isArray(items) ? items : (items as { tasks?: unknown[] }).tasks
  if (!Array.isArray(arr) || arr.length === 0) {
    ElMessage.error('未找到任务数组')
    return
  }
  submitting.value = true
  try {
    const res = await batchCreate(arr as Partial<TaskItem>[])
    ElMessage.success(res.message || `成功创建 ${arr.length} 条`)
    batchVisible.value = false
    await loadTasks()
  } catch (e) {
    ElMessage.error((e as Error).message || '批量创建失败')
  } finally {
    submitting.value = false
  }
}

// ---- 导入 ----
const importVisible = ref(false)
const importType = ref<'excel' | 'json' | 'pdf' | 'pdf-ai'>('excel')
const importFile = ref<File | null>(null)
function openImportType(type: 'excel' | 'json' | 'pdf' | 'pdf-ai') {
  importType.value = type
  importFile.value = null
  importVisible.value = true
}
function onImportFile(file: { raw: File }) {
  importFile.value = file.raw
}
async function submitImport() {
  if (!importFile.value) return
  submitting.value = true
  const file = importFile.value
  try {
    if (importType.value === 'pdf-ai') {
      const res = await importPdfAiPreview(file, file.name)
      previewList.value = (res.data?.tasks || []).map((t) => ({ ...t }))
      if (!previewList.value.length) {
        ElMessage.info('未识别到任务')
      } else {
        importVisible.value = false
        previewVisible.value = true
      }
    } else {
      const res = await importTasks(importType.value, file, file.name)
      ElMessage.success(res.message || '导入成功')
      importVisible.value = false
      await loadTasks()
    }
  } catch (e) {
    ElMessage.error((e as Error).message || '导入失败')
  } finally {
    submitting.value = false
  }
}

// ---- AI 导入预览 / 人工复核（U2） ----
const previewVisible = ref(false)
const previewList = ref<PreviewTask[]>([])
async function confirmSave() {
  submitting.value = true
  try {
    const res = await confirmPdfAi(previewList.value)
    ElMessage.success(res.message || `已保存 ${res.data?.count ?? 0} 条（跳过 ${res.data?.skipped ?? 0}）`)
    previewVisible.value = false
    previewList.value = []
    await loadTasks()
  } catch (e) {
    ElMessage.error((e as Error).message || '保存失败')
  } finally {
    submitting.value = false
  }
}
function confColor(c?: number | null): string {
  if (c == null) return 'info'
  if (c >= 0.8) return 'success'
  if (c >= 0.6) return 'warning'
  return 'danger'
}
</script>

<style scoped>
.tasks-view { display: flex; flex-direction: column; gap: 16px; }

.page-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.page-title { margin: 0; font-size: 20px; font-weight: 700; color: var(--text-strong); }
.page-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); }
.head-stat { display: flex; gap: 12px; }
.hs-block {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 18px;
  text-align: center;
  min-width: 84px;
  box-shadow: var(--shadow-sm);
}
.hs-value { font-size: 20px; font-weight: 700; color: var(--brand-700); }
.hs-label { font-size: 12px; color: var(--text-muted); margin-top: 2px; }

.filter-card { border-radius: var(--radius); }
.filter-card :deep(.el-form-item) { margin-bottom: 0; }

.toolbar { display: flex; align-items: center; justify-content: space-between; }
.count-tip { font-size: 13px; color: var(--text-muted); }

.table-card { border-radius: var(--radius); }
.muted { color: var(--text-muted); }

.pager { display: flex; justify-content: flex-end; margin-top: 14px; }

.hint { font-size: 13px; color: var(--text-secondary); margin: 0 0 12px; }
.hint code { background: var(--bg-soft); padding: 1px 6px; border-radius: 4px; color: var(--brand-700); }
.cell-warn { box-shadow: 0 0 0 2px #F8717155; border-radius: 6px; }
</style>
