<template>
  <div class="upload-plan">
    <div class="intro">
      <h3>上传学习计划，AI 自动识别并排期</h3>
      <p class="hint">
        支持 <b>文本粘贴</b> 与 <b>文件上传</b>（.txt / .md / .pdf / .docx / .png / .jpg）。
        AI 会读懂文档，把「周一 / 7月最后一周」这类相对安排<b>推算成具体日期</b>，并按作息表<b>补上时间段</b>，生成可直接执行的每日计划。
        解析全部由 <b>你在「设置」页配置的 API Key</b> 驱动，请先完成配置。
      </p>
    </div>

    <!-- 上传区 -->
    <div v-if="step === 'upload'" class="upload-zone">
      <!-- AI 解析中提示：请勿切换页面（切换后无法看到解析结果） -->
      <div v-if="parsing" class="parse-tip" role="alert">
        <span class="pt-dot"></span>
        <span>{{ parseProgress }} <b>请勿切换页面</b>，解析完成后会自动显示结果</span>
      </div>
      <el-input
        v-model="textInput"
        type="textarea"
        :rows="6"
        placeholder="直接粘贴计划文本，例如：&#10;8月1日 08:30-11:30 数学 高数强化&#10;14:00-15:30 英语 阅读+单词"
        class="text-area"
      />
      <div class="upload-actions">
        <el-button type="primary" :loading="parsing" @click="parseText">解析文本</el-button>
        <span class="divider">或</span>
        <el-upload
          class="drop"
          drag
          :auto-upload="false"
          :show-file-list="false"
          :on-change="onFile"
          accept=".txt,.md,.pdf,.docx,.png,.jpg,.jpeg"
        >
          <el-icon class="up-icon"><UploadFilled /></el-icon>
          <div class="up-text">把计划文件拖到这里，或点击选择</div>
          <div class="up-sub">.txt / .md / .pdf / .docx / 图片</div>
        </el-upload>
      </div>
    </div>

    <!-- 解析中 -->
    <div v-if="parsing" class="parsing-overlay">
      <div class="parsing-card">
        <div class="parsing-spinner" />
        <div class="parsing-text">{{ parseProgress || 'AI 正在识别计划…' }}</div>
        <div class="parsing-hint">图片 / 文档解析可能需要 10-60 秒，请耐心等待</div>
      </div>
    </div>

    <!-- 校正 -->
    <div v-else-if="step === 'review'" class="review">
      <div class="review-head">
        <div>
          <span class="ok-tag">已识别 {{ plans.length }} 条计划</span>
          <span v-if="needsReviewCount" class="warn-tag">需复核 {{ needsReviewCount }} 条（标黄）</span>
        </div>
        <div>
          <el-button @click="step = 'upload'">重新上传</el-button>
          <el-button type="primary" :loading="saving" @click="confirm">确认保存到今日计划</el-button>
        </div>
      </div>

      <el-table :data="plans" border class="tbl">
        <el-table-column type="index" label="#" width="48" />
        <el-table-column label="日期" width="170">
          <template #default="{ row }">
            <el-date-picker v-model="row.date" type="date" value-format="YYYY-MM-DD" size="small" placeholder="日期" />
          </template>
        </el-table-column>
        <el-table-column label="科目" width="150">
          <template #default="{ row }">
            <el-input v-model="row.subject" :class="{ warn: row.needs_review }" size="small" placeholder="科目" />
          </template>
        </el-table-column>
        <el-table-column label="内容">
          <template #default="{ row }">
            <el-input v-model="row.content" :class="{ warn: row.needs_review }" size="small" placeholder="学习内容" />
          </template>
        </el-table-column>
        <el-table-column label="开始" width="120">
          <template #default="{ row }">
            <el-time-picker v-model="row.start_time" format="HH:mm" value-format="HH:mm" size="small" placeholder="开始" style="width:100%" />
          </template>
        </el-table-column>
        <el-table-column label="结束" width="120">
          <template #default="{ row }">
            <el-time-picker v-model="row.end_time" format="HH:mm" value-format="HH:mm" size="small" placeholder="结束" style="width:100%" />
          </template>
        </el-table-column>
        <el-table-column label="状态" width="84">
          <template #default="{ row }">
            <el-tag v-if="row.needs_review" type="warning" size="small">需复核</el-tag>
            <el-tag v-else type="success" size="small">OK</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="" width="60">
          <template #default="{ $index }">
            <el-button text type="danger" size="small" @click="plans.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-alert
      v-if="message"
      :title="message"
      :type="messageType"
      show-icon
      class="msg"
      @close="message = ''"
    />

    <el-divider />

    <div class="plan-manage">
      <div class="plan-head">
        <h3 class="section-title">
          <el-icon><Files /></el-icon> 已上传 / 已添加的计划
        </h3>
        <div class="plan-tools">
          <el-select v-model="sourceFilter" size="small" style="width: 130px" @change="onFilterChange">
            <el-option label="全部来源" value="all" />
            <el-option label="仅上传(解析)" value="uploaded" />
            <el-option label="仅手动添加" value="manual" />
          </el-select>
          <el-input
            v-model="keyword"
            size="small"
            clearable
            placeholder="搜索科目/内容"
            style="width: 160px"
            @input="onFilterChange"
          />
          <template v-if="!selectMode">
            <el-button size="small" type="danger" plain @click="enterSelectMode">
              <el-icon><Delete /></el-icon> 删除
            </el-button>
            <el-button size="small" text type="primary" @click="openCriteria">按条件删除</el-button>
          </template>
          <template v-else>
            <el-button size="small" type="danger" :disabled="!selectedIds.length" @click="batchDelete">
              批量删除 ({{ selectedIds.length }})
            </el-button>
            <el-button size="small" @click="cancelSelectMode">取消</el-button>
          </template>
        </div>
      </div>
      <p class="section-desc">查看、修改或批量删除你上传 / 添加的学习计划。删除后不可恢复。</p>

      <el-table
        ref="tableRef"
        v-loading="planLoading"
        :data="managedPlans"
        size="small"
        class="plan-table"
        row-key="id"
        @selection-change="onSelectionChange"
        @row-click="onRowClick"
      >
        <el-table-column v-if="selectMode" type="selection" width="40" />
        <el-table-column label="序号" width="64" align="center">
          <template #default="{ $index }">{{ globalIndex($index) }}</template>
        </el-table-column>
        <el-table-column label="日期" width="100" prop="date" />
        <el-table-column label="科目" width="80" prop="subject" />
        <el-table-column label="内容" min-width="160" show-overflow-tooltip prop="content" />
        <el-table-column label="时间" width="116">
          <template #default="{ row }">
            {{ row.start_time || '—' }}<template v-if="row.end_time"> - {{ row.end_time }}</template>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag
              size="small"
              :type="row.status === 'done' ? 'success' : row.status === 'cancelled' ? 'info' : 'warning'"
            >
              {{ row.status === 'done' ? '已完成' : row.status === 'cancelled' ? '已取消' : '待开始' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!planLoading && !managedPlans.length" class="empty">还没有计划，先上传文件或粘贴文本让 AI 帮你排期吧。</div>
      <div v-else class="table-foot">
        <span class="total-text">共 {{ total }} 条记录</span>
        <el-pagination
          v-if="total > pageSize"
          layout="prev, pager, next"
          :total="total"
          :page-size="pageSize"
          :current-page="page"
          small
          @current-change="onPageChange"
        />
      </div>
    </div>

    <el-dialog v-model="criteriaVisible" title="按条件删除计划" width="480px">
      <p class="criteria-hint">至少填写一个条件；未填的条件不参与筛选。删除后不可恢复。</p>
      <el-form label-width="80px">
        <el-form-item label="科目">
          <el-input v-model="criteriaForm.subject" placeholder="如：数学" />
        </el-form-item>
        <el-form-item label="日期范围">
          <div class="range-row">
            <el-date-picker v-model="criteriaForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width: 160px" />
            <span class="range-sep">至</span>
            <el-date-picker v-model="criteriaForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width: 160px" />
          </div>
        </el-form-item>
        <el-form-item label="时间段">
          <div class="range-row">
            <el-time-picker v-model="criteriaForm.start_time" format="HH:mm" value-format="HH:mm" placeholder="开始时间" style="width: 160px" />
            <span class="range-sep">至</span>
            <el-time-picker v-model="criteriaForm.end_time" format="HH:mm" value-format="HH:mm" placeholder="结束时间" style="width: 160px" />
          </div>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="criteriaForm.status" clearable placeholder="不限" style="width: 100%">
            <el-option label="待开始" value="pending" />
            <el-option label="已完成" value="done" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
        <el-form-item label="来源">
          <el-select v-model="criteriaForm.plan_source" clearable placeholder="不限" style="width: 100%">
            <el-option label="全部来源" value="" />
            <el-option label="仅上传(解析)" value="uploaded" />
            <el-option label="仅手动添加" value="manual" />
          </el-select>
        </el-form-item>
      </el-form>
      <div v-if="criteriaPreviewCount !== null" class="preview-count">
        将删除 <b>{{ criteriaPreviewCount }}</b> 条计划
      </div>
      <template #footer>
        <el-button @click="criteriaVisible = false">取消</el-button>
        <el-button :loading="criteriaPreviewLoading" @click="previewCriteriaDelete">预览数量</el-button>
        <el-button type="danger" :disabled="criteriaPreviewCount === null || criteriaPreviewCount === 0" :loading="criteriaDeleting" @click="confirmCriteriaDelete">
          确认删除
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editVisible" title="修改计划" width="420px">
      <el-form label-width="80px">
        <el-form-item label="日期">
          <el-date-picker v-model="editForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="科目">
          <el-input v-model="editForm.subject" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="editForm.content" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="开始">
          <el-time-picker v-model="editForm.start_time" format="HH:mm" value-format="HH:mm" placeholder="开始" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束">
          <el-time-picker v-model="editForm.end_time" format="HH:mm" value-format="HH:mm" placeholder="结束" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="待开始" value="pending" />
            <el-option label="已完成" value="done" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editLoading" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, onBeforeRouteLeave } from 'vue-router'
import { UploadFilled, Files, Delete } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { parsePlan, confirmPlans, type PlanItem } from '@/api/plan'
import {
  listTasks,
  updateTask,
  batchDeleteTasks,
  previewDeleteByCriteria,
  deleteTasksByCriteria,
  type TaskItem,
  type TaskFilters,
  type DeleteCriteria,
} from '@/api/task'
import type { TableInstance } from 'element-plus'
import { useAiKey } from '@/composables/useAiKey'

const router = useRouter()
const { ensureKey } = useAiKey()

const step = ref<'upload' | 'review'>('upload')
const textInput = ref('')
const plans = ref<PlanItem[]>([])
const planName = ref('')
const parsing = ref(false)
const parseProgress = ref('')
const saving = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

const needsReviewCount = computed(() => plans.value.filter((p) => p.needs_review).length)

function isImage(name: string) {
  return /\.(png|jpe?g)$/i.test(name)
}

async function doParse(form: FormData, isImageFile = false) {
  parsing.value = true
  parseProgress.value = isImageFile ? 'AI 正在识别图片中的计划…' : 'AI 正在识别计划内容…'
  try {
    const res = await parsePlan(form)
    if (res.code === 200 && Array.isArray(res.data?.plans)) {
      plans.value = res.data.plans
      planName.value = res.data.plan_name || ''
      if (!plans.value.length) {
        message.value = '未识别出计划，请检查内容或换一种格式'
        messageType.value = 'error'
      } else {
        step.value = 'review'
        message.value = ''
      }
    } else {
      message.value = res.message || '解析失败'
      messageType.value = 'error'
    }
  } catch (e: any) {
    const msg = e?.message || ''
    const isAiKeyError =
      /401|unauthorized|认证失败|API Key|api key|未配置.*[Kk]ey|invalid.*key/i.test(msg)
    if (isAiKeyError) {
      message.value = 'AI 解析失败：请到「设置」页填入你自己的 API Key（或更换已失效的 Key）后重试'
    } else if (msg.includes('超时') || msg.includes('timeout')) {
      message.value = 'AI 解析超时，文档/图片过大时可重试或精简内容'
    } else if (msg.includes('不支持') || msg.includes('类型')) {
      message.value = '不支持的文件类型，请用 txt/md/pdf/docx/png/jpg'
    } else {
      message.value = `解析失败：${msg || '未知错误'}`
    }
    messageType.value = 'error'
  } finally {
    parsing.value = false
  }
}

async function parseText() {
  const text = textInput.value.trim()
  if (!text) {
    message.value = '请先粘贴计划文本'
    messageType.value = 'error'
    return
  }
  const form = new FormData()
  form.append('text', text)
  await doParse(form)
}

async function onFile(uploadFile: any) {
  const file: File = uploadFile?.raw
  if (!file) return
  message.value = ''
  if (isImage(file.name)) {
    const ok = await ensureKey('识别计划截图')
    if (!ok) return
  }
  const form = new FormData()
  form.append('file', file, file.name)
  await doParse(form, isImage(file.name))
}

async function confirm() {
  const valid = plans.value.filter((p) => (p.subject || '').trim() && (p.content || '').trim())
  if (!valid.length) {
    message.value = '没有可保存的有效计划（科目与内容不能为空）'
    messageType.value = 'error'
    return
  }
  saving.value = true
  try {
    const res = await confirmPlans({ plan_name: planName.value || undefined, tasks: valid })
    if (res.code === 200) {
      const skipped = res.data.skipped?.length || 0
      message.value =
        `已保存 ${res.data.created} 条计划（v${res.data.version}）` +
        (skipped ? `，跳过 ${skipped} 条时间冲突` : '') +
        '，去「今日计划」查看并按点提醒计时'
      messageType.value = 'success'
      step.value = 'upload'
      plans.value = []
      planName.value = ''
      textInput.value = ''
      setTimeout(() => router.push('/tasks'), 800)
    } else {
      message.value = res.message || '保存失败'
      messageType.value = 'error'
    }
  } catch (e: any) {
    message.value = e?.message || '保存失败'
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

// ---- 已上传 / 已添加计划管理 ----
const managedPlans = ref<TaskItem[]>([])
const planLoading = ref(false)
const selectedIds = ref<number[]>([])
const keyword = ref('')
const sourceFilter = ref<'all' | 'uploaded' | 'manual'>('all')
const editVisible = ref(false)
const editLoading = ref(false)
const editForm = ref<Partial<TaskItem>>({})
const tableRef = ref<TableInstance>()

const criteriaVisible = ref(false)
const criteriaPreviewLoading = ref(false)
const criteriaDeleting = ref(false)
const criteriaPreviewCount = ref<number | null>(null)
const criteriaForm = ref<DeleteCriteria>({})

// 选择模式 / 分页 / 序号
const selectMode = ref(false)
const allPlans = ref<TaskItem[]>([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

function globalIndex($index: number) {
  return (page.value - 1) * pageSize.value + $index + 1
}
function enterSelectMode() {
  selectMode.value = true
}
function cancelSelectMode() {
  selectMode.value = false
  selectedIds.value = []
}
function onFilterChange() {
  page.value = 1
  loadPlans()
}
function applyPage() {
  const start = (page.value - 1) * pageSize.value
  managedPlans.value = allPlans.value.slice(start, start + pageSize.value)
}
function onPageChange(p: number) {
  page.value = p
  applyPage()
}

function openCriteria() {
  criteriaForm.value = {}
  criteriaPreviewCount.value = null
  criteriaVisible.value = true
}

async function previewCriteriaDelete() {
  criteriaPreviewLoading.value = true
  try {
    const res = await previewDeleteByCriteria(criteriaForm.value)
    criteriaPreviewCount.value = res.count
  } catch (e: any) {
    ElMessage.error(e?.message || '预览失败')
  } finally {
    criteriaPreviewLoading.value = false
  }
}

async function confirmCriteriaDelete() {
  if (criteriaPreviewCount.value === null || criteriaPreviewCount.value === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除符合条件的 ${criteriaPreviewCount.value} 条计划？此操作不可恢复。`,
      '按条件删除',
      { type: 'warning' },
    )
  } catch {
    return
  }
  criteriaDeleting.value = true
  try {
    await deleteTasksByCriteria(criteriaForm.value)
    ElMessage.success('已按条件删除')
    criteriaVisible.value = false
    await loadPlans()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  } finally {
    criteriaDeleting.value = false
  }
}

async function loadPlans() {
  planLoading.value = true
  try {
    const filters: TaskFilters = {}
    if (keyword.value.trim()) filters.keyword = keyword.value.trim()
    const res = await listTasks(filters)
    let list = (res.data || []).slice()
    if (sourceFilter.value === 'uploaded') {
      list = list.filter((t) => t.plan_source && t.plan_source !== 'manual')
    } else if (sourceFilter.value === 'manual') {
      list = list.filter((t) => t.plan_source === 'manual')
    }
    // 序号小号在前：按日期升序、同日期按开始时间升序
    list.sort(
      (a, b) =>
        (a.date || '').localeCompare(b.date || '') ||
        (a.start_time || '00:00').localeCompare(b.start_time || '00:00'),
    )
    allPlans.value = list
    total.value = list.length
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (page.value > maxPage) page.value = maxPage
    applyPage()
  } catch {
    /* ignore */
  } finally {
    planLoading.value = false
  }
}

function onSelectionChange(rows: TaskItem[]) {
  selectedIds.value = rows.map((r) => r.id)
}

async function batchDelete() {
  if (!selectedIds.value.length) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selectedIds.value.length} 条计划？此操作不可恢复。`,
      '批量删除',
      { type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await batchDeleteTasks(selectedIds.value)
    ElMessage.success('已删除选中的计划')
    selectedIds.value = []
    await loadPlans()
  } catch (e: any) {
    ElMessage.error(e?.message || '删除失败')
  }
}

function onRowClick(row: TaskItem, column: any) {
  if (selectMode.value) {
    if (column?.type === 'selection') return
    tableRef.value?.toggleRowSelection(row)
    return
  }
  openEdit(row)
}

function openEdit(t: TaskItem) {
  editForm.value = {
    id: t.id,
    date: t.date,
    subject: t.subject,
    content: t.content,
    start_time: t.start_time,
    end_time: t.end_time,
    status: t.status,
  }
  editVisible.value = true
}

async function saveEdit() {
  if (!editForm.value.id) return
  editLoading.value = true
  try {
    await updateTask(editForm.value.id, {
      date: editForm.value.date,
      subject: editForm.value.subject,
      content: editForm.value.content,
      start_time: editForm.value.start_time || null,
      end_time: editForm.value.end_time || null,
      status: editForm.value.status,
    })
    ElMessage.success('已保存修改')
    editVisible.value = false
    await loadPlans()
  } catch (e: any) {
    ElMessage.error(e?.message || '保存失败')
  } finally {
    editLoading.value = false
  }
}

onMounted(() => {
  loadPlans()
})

// AI 解析中切换页面：确认提醒（离开则无法看到本次解析结果）
onBeforeRouteLeave(() => {
  if (!parsing.value) return true
  return ElMessageBox.confirm(
    'AI 正在解析计划，切换页面将看不到本次解析结果。确定离开？',
    '解析进行中',
    { type: 'warning', confirmButtonText: '仍要离开', cancelButtonText: '留下等待' },
  )
    .then(() => true)
    .catch(() => false)
})
</script>

<style scoped>
.upload-plan { max-width: 1000px; margin: 0 auto; }
.intro h3 { margin: 0 0 8px; font-size: 18px; }
.hint { color: var(--el-text-color-secondary); font-size: 13px; margin: 0 0 20px; line-height: 1.7; }
.hint code { background: var(--el-fill-color-light); padding: 1px 6px; border-radius: 4px; }
.upload-zone { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; padding: 20px; }
.parse-tip {
  display: flex; align-items: center; gap: 10px;
  background: #FEF3C7; color: #92400E;
  border: 1px solid #FCD34D; border-radius: 10px;
  padding: 10px 14px; margin-bottom: 16px;
  font-size: 13px;
}
.pt-dot {
  width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
  background: #F59E0B;
  animation: pt-pulse 1.2s ease-in-out infinite;
}
@keyframes pt-pulse { 0%, 100% { opacity: 1; } 50% { opacity: .35; } }
.text-area { margin-bottom: 16px; }
.upload-actions { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
.divider { color: var(--text-muted); font-size: 13px; }
.drop { flex: 1; min-width: 280px; }
.up-icon { font-size: 40px; color: var(--el-color-primary); }
.up-text { font-size: 14px; margin-top: 6px; }
.up-sub { color: var(--el-text-color-secondary); font-size: 12px; margin-top: 4px; }

.review-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
.ok-tag { background: var(--el-color-success-light-9); color: var(--el-color-success); padding: 4px 10px; border-radius: 6px; font-size: 13px; }
.warn-tag { background: var(--el-color-warning-light-9); color: var(--el-color-warning); padding: 4px 10px; border-radius: 6px; font-size: 13px; margin-left: 8px; }
.tbl :deep(.warn .el-input__wrapper) { background: var(--el-color-warning-light-9); box-shadow: 0 0 0 1px var(--el-color-warning) inset; }
.msg { margin-top: 16px; }

.parsing-overlay { display: flex; align-items: center; justify-content: center; padding: 60px 20px; }
.parsing-card { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.parsing-spinner { width: 40px; height: 40px; border: 3px solid var(--el-color-primary-light-8); border-top-color: var(--el-color-primary); border-radius: 50%; animation: sm-spin 0.8s linear infinite; }
@keyframes sm-spin { to { transform: rotate(360deg); } }
.parsing-text { font-size: 15px; font-weight: 600; color: var(--text-strong); }
.parsing-hint { font-size: 12px; color: var(--text-muted); }

.plan-manage { margin-top: 28px; }
.section-title {
  display: flex; align-items: center; gap: 8px;
  margin: 0 0 8px; font-size: 16px; font-weight: 600; color: var(--text-strong);
}
.section-desc {
  margin: 0; font-size: 13px; color: var(--text-muted); line-height: 1.7;
}
.plan-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
.plan-tools { display: flex; gap: 8px; align-items: center; }
.plan-table { margin-top: 12px; }
.plan-table :deep(.el-table__row) { cursor: pointer; }
.empty { color: var(--text-muted); font-size: 13px; padding: 24px 0; text-align: center; }
.table-foot { display: flex; justify-content: space-between; align-items: center; margin-top: 12px; gap: 12px; flex-wrap: wrap; }
.total-text { font-size: 13px; color: var(--text-muted); }
.table-foot :deep(.el-pagination) { justify-content: flex-end; }
.criteria-hint { margin: 0 0 16px; font-size: 12px; color: var(--text-muted); }
.range-row { display: flex; align-items: center; gap: 8px; }
.range-sep { color: var(--text-muted); font-size: 13px; }
.preview-count { margin-top: 8px; padding: 10px 12px; background: var(--el-fill-color-light); border-radius: 6px; font-size: 13px; color: var(--text-strong); }
</style>
