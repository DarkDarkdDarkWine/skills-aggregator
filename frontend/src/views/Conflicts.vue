<template>
  <div class="conflicts-page">
    <el-card shadow="hover">
      <template #header>
        <div class="page-header">
          <span>冲突处理</span>
          <el-button :disabled="conflicts.length === 0" @click="handleRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <div v-if="conflicts.length === 0" class="empty-state">
        <el-icon class="empty-icon"><CircleCheck /></el-icon>
        <p>暂无冲突，所有 Skills 已就绪</p>
      </div>
      
      <el-collapse v-else v-model="activeNames">
        <el-collapse-item 
          v-for="conflict in conflicts" 
          :key="conflict.id" 
          :name="conflict.id"
          :title="`冲突 #${conflict.id.slice(0, 8)} - ${conflict.type}`"
        >
          <template #title>
            <div class="conflict-title">
              <el-tag :type="getTypeTag(conflict.type)">{{ conflict.type }}</el-tag>
              <span class="conflict-id">#{{ conflict.id.slice(0, 8) }}</span>
              <el-tag :type="conflict.status === 'pending' ? 'warning' : 'success'">
                {{ conflict.status }}
              </el-tag>
            </div>
          </template>
          
          <div class="conflict-content">
            <div class="conflict-info">
              <p><strong>冲突类型：</strong>{{ conflict.type }}</p>
              <p><strong>涉及 Skills：</strong>{{ conflict.skill_ids?.length || 0 }} 个</p>
            </div>
            
            <div v-if="conflict.ai_recommendation" class="ai-recommendation">
              <p class="recommendation-title">
                <el-icon><MagicStick /></el-icon>
                AI 推荐
              </p>
              <p v-if="conflict.ai_recommendation.recommendation">
                操作：{{ conflict.ai_recommendation.recommendation.action }}
              </p>
              <p v-if="conflict.ai_recommendation.recommendation?.reason">
                理由：{{ conflict.ai_recommendation.recommendation.reason }}
              </p>
            </div>
            
            <div class="conflict-actions">
              <el-button 
                v-if="conflict.ai_recommendation?.recommendation?.action === 'choose_one'"
                type="primary" 
                size="small"
                @click="handleAutoResolve(conflict)"
              >
                采用 AI 推荐
              </el-button>
              <el-button 
                type="primary" 
                size="small"
                @click="handleResolve(conflict)"
              >
                手动处理
              </el-button>
            </div>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 处理对话框 -->
    <el-dialog 
      title="处理冲突" 
      v-model="showResolveDialog" 
      width="600px"
    >
      <div v-if="currentConflict" class="resolve-dialog">
        <p><strong>冲突 ID：</strong>{{ currentConflict.id }}</p>
        <p><strong>类型：</strong>{{ currentConflict.type }}</p>
        
        <el-divider>处理方式</el-divider>
        
        <el-form label-width="100px">
          <el-form-item label="选择操作">
            <el-radio-group v-model="resolveForm.action">
              <el-radio label="choose_one">选择其一</el-radio>
              <el-radio label="merge">合并</el-radio>
              <el-radio label="keep_all">全部保留（重命名）</el-radio>
            </el-radio-group>
          </el-form-item>
          
          <el-form-item v-if="resolveForm.action === 'choose_one'" label="选择保留">
            <el-select v-model="resolveForm.chosen" placeholder="选择要保留的 Skill">
              <el-option 
                v-for="id in currentConflict.skill_ids" 
                :key="id" 
                :label="id.slice(0, 8)" 
                :value="id" 
              />
            </el-select>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="showResolveDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitResolve" :loading="resolving">
          确认处理
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, CircleCheck, MagicStick } from '@element-plus/icons-vue'
import { getConflicts, resolveConflict } from '@/api'

const loading = ref(false)
const resolving = ref(false)
const showResolveDialog = ref(false)
const activeNames = ref([])
const conflicts = ref([])
const currentConflict = ref(null)

const resolveForm = ref({
  action: 'choose_one',
  chosen: ''
})

const getTypeTag = (type) => {
  const types = {
    'name_conflict': 'danger',
    'similar_conflict': 'warning'
  }
  return types[type] || 'info'
}

const fetchConflicts = async () => {
  loading.value = true
  try {
    const response = await getConflicts()
    conflicts.value = response.data
    activeNames.value = response.data.map(c => c.id)
  } catch (error) {
    ElMessage.error('获取冲突失败')
  } finally {
    loading.value = false
  }
}

const handleRefresh = fetchConflicts

const handleResolve = (conflict) => {
  currentConflict.value = conflict
  resolveForm.value = { action: 'choose_one', chosen: '' }
  showResolveDialog.value = true
}

const handleAutoResolve = async (conflict) => {
  try {
    const recommendation = conflict.ai_recommendation?.recommendation
    if (!recommendation) {
      ElMessage.warning('无 AI 推荐信息')
      return
    }
    
    await resolveConflict(conflict.id, {
      action: recommendation.action,
      chosen_skill_id: recommendation.chosen
    })
    
    ElMessage.success('处理成功')
    fetchConflicts()
  } catch (error) {
    ElMessage.error('处理失败')
  }
}

const handleSubmitResolve = async () => {
  if (!currentConflict.value) return
  
  resolving.value = true
  try {
    await resolveConflict(currentConflict.value.id, resolveForm.value)
    ElMessage.success('处理成功')
    showResolveDialog.value = false
    fetchConflicts()
  } catch (error) {
    ElMessage.error('处理失败')
  } finally {
    resolving.value = false
  }
}

onMounted(fetchConflicts)
</script>

<style lang="scss" scoped>
.conflicts-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .conflict-title {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .conflict-id {
      font-family: monospace;
      color: #909399;
    }
  }
  
  .conflict-content {
    padding: 16px 0;
    
    .conflict-info {
      margin-bottom: 16px;
      p { margin: 4px 0; }
    }
    
    .ai-recommendation {
      background: #f4f4f5;
      padding: 12px;
      border-radius: 4px;
      margin-bottom: 16px;
      
      .recommendation-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-weight: 500;
        margin-bottom: 8px;
      }
      
      p { margin: 4px 0; }
    }
    
    .conflict-actions {
      display: flex;
      gap: 12px;
    }
  }
  
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    
    .empty-icon {
      font-size: 64px;
      color: #67C23A;
      margin-bottom: 16px;
    }
  }
}
</style>
