<template>
  <div class="materials-page">
    <el-row :gutter="20">
      <el-col :xs="24" :lg="11">
        <el-card shadow="never" class="up-card">
          <template #header>上传复习资料</template>
          <el-form label-width="64px">
            <el-form-item label="标题">
              <el-input v-model="title" placeholder="如：2026 数据结构讲义" />
            </el-form-item>
            <el-form-item label="内容">
              <el-input v-model="content" type="textarea" :rows="8" placeholder="粘贴资料正文，或下方上传 .txt/.md/.pdf" />
            </el-form-item>
            <el-form-item label="文件">
              <el-upload :auto-upload="false" :show-file-list="true" :limit="1" @change="onFile">
                <el-button>选择 .txt/.md/.pdf</el-button>
              </el-upload>
            </el-form-item>
            <el-button type="primary" :loading="uploading" @click="upload">保存资料</el-button>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="13">
        <el-card shadow="never" class="match-card">
          <template #header>
            <div class="match-head">
              <span>关联检索（RAG 关键词 MVP）</span>
            </div>
          </template>
          <div class="match-bar">
            <el-input v-model="query" placeholder="输入任务/知识点，检索相关资料" @keyup.enter="match" />
            <el-button type="primary" :loading="matching" @click="match">检索</el-button>
          </div>
          <el-empty v-if="!matches.length && !matching" description="暂无检索结果" />
          <el-card v-for="m in matches" :key="m.id" shadow="hover" class="match-item">
            <div class="match-title">{{ m.title }} <el-tag size="small" type="success">相关度 {{ m.score }}</el-tag></div>
            <div class="match-snippet">{{ m.snippet }}</div>
          </el-card>
        </el-card>

        <el-card shadow="never" class="list-card" style="margin-top: 20px">
          <template #header>我的资料库（{{ list.length }}）</template>
          <el-table :data="list" stripe size="small">
            <el-table-column prop="title" label="标题" />
            <el-table-column prop="source" label="来源" width="80" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button text type="danger" size="small" @click="remove(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  uploadMaterial, listMaterials, deleteMaterial, matchMaterial,
  type MaterialItem, type MatchResult,
} from '@/api/material'

const title = ref('')
const content = ref('')
const file = ref<File | null>(null)
const uploading = ref(false)
const list = ref<MaterialItem[]>([])
const query = ref('')
const matching = ref(false)
const matches = ref<MatchResult[]>([])

function onFile(u: { raw?: File }) {
  file.value = u.raw || null
}

async function upload() {
  if (!title.value.trim()) { ElMessage.warning('请填写标题'); return }
  uploading.value = true
  try {
    const form = new FormData()
    form.append('title', title.value)
    if (content.value) form.append('content', content.value)
    if (file.value) form.append('file', file.value, file.value.name)
    await uploadMaterial(form)
    ElMessage.success('资料已保存')
    title.value = ''
    content.value = ''
    file.value = null
    await load()
  } finally {
    uploading.value = false
  }
}

async function match() {
  if (!query.value.trim()) return
  matching.value = true
  try {
    matches.value = await matchMaterial(query.value)
  } finally {
    matching.value = false
  }
}

async function remove(row: MaterialItem) {
  await deleteMaterial(row.id)
  await load()
}

async function load() {
  list.value = await listMaterials()
}

onMounted(load)
</script>

<style scoped>
.up-card, .match-card, .list-card { border-radius: 16px; }
.match-head { font-weight: 600; }
.match-bar { display: flex; gap: 10px; margin-bottom: 14px; }
.match-item { margin-bottom: 10px; border-radius: 12px; }
.match-title { font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
.match-snippet { color: var(--text-muted); font-size: 13px; margin-top: 6px; line-height: 1.6; }
</style>
