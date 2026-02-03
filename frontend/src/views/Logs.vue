<template>
  <div class="logs-container">
    <div class="page-header">
      <h2>错误日志</h2>
      <div class="header-actions">
        <el-button type="primary" @click="fetchLogs" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="danger" @click="handleClearLogs" :disabled="logs.length === 0">
          <el-icon><Delete /></el-icon>
          清空日志
        </el-button>
      </div>
    </div>

    <el-card class="logs-card">
      <div class="log-stats">
        <el-tag type="danger">错误日志: {{ logs.length }} 条</el-tag>
        <span class="auto-refresh">
          <el-switch v-model="autoRefresh" active-text="自动刷新" />
        </span>
      </div>

      <el-table :data="logs" style="width: 100%" :default-sort="{ prop: 'timestamp', order: 'descending' }" max-height="600">
        <el-table-column prop="timestamp" label="时间" width="180" sortable>
          <template #default="{ row }">
            {{ formatTime(row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="level" label="级别" width="80">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.level)" size="small">{{ row.level }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="logger" label="来源" width="150" />
        <el-table-column prop="message" label="消息" />
      </el-table>

      <el-empty v-if="logs.length === 0 && !loading" description="暂无错误日志" />

      <div v-if="logs.length > 0" class="log-footer">
        <span>显示最近 {{ logs.length }} 条日志</span>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Delete } from '@element-plus/icons-vue'
import { getLogs, clearLogs } from '@/api'

const logs = ref([])
const loading = ref(false)
const autoRefresh = ref(false)
let intervalId = null

const fetchLogs = async () => {
  loading.value = true
  try {
    const response = await getLogs(200)
    logs.value = response.data
  } catch (error) {
    ElMessage.error('获取日志失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

const handleClearLogs = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有日志吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    await clearLogs()
    logs.value = []
    ElMessage.success('日志已清空')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('清空日志失败')
    }
  }
}

const formatTime = (timestamp) => {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN')
}

const getLevelType = (level) => {
  const types = {
    'ERROR': 'danger',
    'CRITICAL': 'danger',
    'WARNING': 'warning',
    'INFO': 'success',
  }
  return types[level] || 'info'
}

const startAutoRefresh = () => {
  intervalId = setInterval(fetchLogs, 5000)
}

const stopAutoRefresh = () => {
  if (intervalId) {
    clearInterval(intervalId)
    intervalId = null
  }
}

watch(autoRefresh, (val) => {
  if (val) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

onMounted(() => {
  fetchLogs()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style lang="scss" scoped>
.logs-container {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  h2 {
    margin: 0;
    font-size: 18px;
    font-weight: 500;
  }
}

.header-actions {
  display: flex;
  gap: 10px;
}

.logs-card {
  margin-bottom: 20px;
}

.log-stats {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.auto-refresh {
  display: flex;
  align-items: center;
  gap: 10px;
}

.log-footer {
  margin-top: 15px;
  text-align: right;
  color: #909399;
  font-size: 13px;
}
</style>
