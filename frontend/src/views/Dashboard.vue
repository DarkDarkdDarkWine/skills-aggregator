<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :value="stats.ready_count" title="就绪">
            <template #prefix>
              <el-icon color="#67C23A"><CircleCheck /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :value="stats.blocked_count" title="阻塞">
            <template #prefix>
              <el-icon color="#F56C6C"><Warning /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :value="sources.length" title="订阅源">
            <template #prefix>
              <el-icon color="#409EFF"><Connection /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <el-statistic :value="conflicts.length" title="冲突">
            <template #prefix>
              <el-icon color="#E6A23C"><WarningFilled /></el-icon>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
    </el-row>

    <!-- 状态和操作 -->
    <el-row :gutter="20" class="content-row">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>同步状态</span>
              <el-tag :type="statusTagType">{{ syncState }}</el-tag>
            </div>
          </template>
          <div class="sync-status">
            <div v-if="syncState === 'IDLE'" class="status-item">
              <el-icon><CircleClose /></el-icon>
              <span>空闲</span>
            </div>
            <div v-else class="status-item">
              <el-icon><Loading /></el-icon>
              <span>{{ currentAction }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>快速操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="handleSync" :loading="syncing">
              <el-icon><Refresh /></el-icon>
              触发同步
            </el-button>
            <el-button @click="handleDownload">
              <el-icon><Download /></el-icon>
              下载 Skills
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 订阅源列表 -->
    <el-card shadow="hover" class="sources-card">
      <template #header>
        <div class="card-header">
          <span>订阅源</span>
          <el-button type="primary" size="small" @click="showAddSource = true">
            <el-icon><Plus /></el-icon>
            添加
          </el-button>
        </div>
      </template>
      
      <el-table :data="sources" stripe v-loading="loading">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="url" label="URL" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="100" align="center" />
        <el-table-column prop="skill_count" label="Skills" width="100" align="center" />
        <el-table-column prop="last_sync_at" label="最后同步" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_sync_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加订阅源对话框 -->
    <el-dialog v-model="showAddSource" title="添加订阅源" width="500px">
      <el-form :model="newSource" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="newSource.name" placeholder="输入名称" />
        </el-form-item>
        <el-form-item label="URL" required>
          <el-input v-model="newSource.url" placeholder="GitHub 仓库 URL" />
        </el-form-item>
        <el-form-item label="子路径">
          <el-input v-model="newSource.sub_path" placeholder="Skills 子目录（可选）" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="newSource.priority" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddSource = false">取消</el-button>
        <el-button type="primary" @click="handleAddSource" :loading="adding">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  CircleCheck, Warning, WarningFilled, 
  CircleClose, Loading, Refresh, 
  Download, Plus 
} from '@element-plus/icons-vue'
import { getSyncStatus, getSources, triggerSync, downloadSkills, createSource } from '@/api'

const loading = ref(false)
const syncing = ref(false)
const adding = ref(false)
const showAddSource = ref(false)

const syncState = ref('IDLE')
const currentAction = ref('')
const sources = ref([])
const conflicts = ref([])

const stats = computed(() => ({
  ready_count: 0,
  blocked_count: conflicts.value.length
}))

const statusTagType = computed(() => {
  const types = {
    'IDLE': 'info',
    'READY': 'success',
    'PARTIAL_READY': 'warning',
    'PULLING': 'primary',
    'ANALYZING': 'primary',
    'MERGING': 'primary'
  }
  return types[syncState.value] || 'info'
})

const newSource = ref({
  name: '',
  url: '',
  sub_path: '',
  priority: 0
})

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchData = async () => {
  loading.value = true
  try {
    const [statusRes, sourcesRes] = await Promise.all([
      getSyncStatus(),
      getSources()
    ])
    syncState.value = statusRes.data.state
    currentAction.value = statusRes.data.current_action || ''
    sources.value = sourcesRes.data
    conflicts.value = statusRes.data.conflicts || []
  } catch (error) {
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleSync = async () => {
  syncing.value = true
  try {
    await triggerSync()
    ElMessage.success('同步已触发')
    fetchData()
  } catch (error) {
    ElMessage.error('触发同步失败')
  } finally {
    syncing.value = false
  }
}

const handleDownload = async () => {
  try {
    const response = await downloadSkills('ready')
    ElMessage.success('下载成功')
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const handleAddSource = async () => {
  if (!newSource.value.name || !newSource.value.url) {
    ElMessage.warning('请填写名称和 URL')
    return
  }
  
  adding.value = true
  try {
    await createSource(newSource.value)
    ElMessage.success('添加成功')
    showAddSource.value = false
    newSource.value = { name: '', url: '', sub_path: '', priority: 0 }
    fetchData()
  } catch (error) {
    ElMessage.error('添加失败')
  } finally {
    adding.value = false
  }
}

onMounted(fetchData)
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-row {
    margin-bottom: 20px;
  }
  
  .content-row {
    margin-bottom: 20px;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .sync-status {
    .status-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 16px;
    }
  }
  
  .quick-actions {
    display: flex;
    gap: 12px;
  }
  
  .sources-card {
    margin-bottom: 20px;
  }
}
</style>
