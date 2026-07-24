<template>
  <div class="import-page">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>Excel 导入</span>
          </template>
          <div class="import-card">
            <el-upload
              drag
              accept=".xlsx,.xls"
              :auto-upload="false"
              :on-change="handleExcelChange"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">将 Excel 文件拖到此处，或点击上传</div>
              <template #tip>
                <div class="upload-tip">支持 .xlsx, .xls 格式</div>
              </template>
            </el-upload>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>JSON 导入</span>
          </template>
          <div class="import-card">
            <el-upload
              drag
              accept=".json"
              :auto-upload="false"
              :on-change="handleJsonChange"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">将 JSON 文件拖到此处，或点击上传</div>
              <template #tip>
                <div class="upload-tip">支持 .json 格式</div>
              </template>
            </el-upload>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card>
          <template #header>
            <span>PDF 导入</span>
          </template>
          <div class="import-card">
            <el-upload
              drag
              accept=".pdf"
              :auto-upload="false"
              :on-change="handlePdfChange"
            >
              <el-icon class="upload-icon"><UploadFilled /></el-icon>
              <div class="upload-text">将 PDF 文件拖到此处，或点击上传</div>
              <template #tip>
                <div class="upload-tip">支持 .pdf 格式</div>
              </template>
            </el-upload>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { taskApi } from '@/api'

async function handleExcelChange(uploadFile: any) {
  try {
    const res: any = await taskApi.importExcel(uploadFile.raw)
    ElMessage.success(res.message)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '导入失败')
  }
}

async function handleJsonChange(uploadFile: any) {
  try {
    const res: any = await taskApi.importJson(uploadFile.raw)
    ElMessage.success(res.message)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '导入失败')
  }
}

async function handlePdfChange(uploadFile: any) {
  try {
    const res: any = await taskApi.importPdf(uploadFile.raw)
    ElMessage.success(res.message)
  } catch (err: any) {
    ElMessage.error(err.response?.data?.message || '导入失败')
  }
}
</script>

<style scoped>
.import-card {
  text-align: center;
}

.upload-icon {
  font-size: 48px;
  color: #c0c4cc;
  margin-bottom: 12px;
}

.upload-text {
  color: #606266;
  font-size: 14px;
}

.upload-tip {
  color: #909399;
  font-size: 12px;
  margin-top: 8px;
}
</style>