<template>
  <div class="skills-page">
    <el-card shadow="hover">
      <template #header>
        <div class="page-header">
          <span>Skills 列表</span>
          <el-radio-group v-model="statusFilter" size="small">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="ready">就绪</el-radio-button>
            <el-radio-button label="blocked">阻塞</el-radio-button>
          </el-radio-group>
        </div>
      </template>
      
      <el-table :data="skills" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="source_id" label="来源 ID" width="100">
          <template #default="{ row }">
            {{ row.source_id?.slice(0, 8) || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ready' ? 'success' : 'danger'">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content_hash" label="Hash" width="100">
          <template #default="{ row }">
            {{ row.content_hash?.slice(0, 8) }}
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleView(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="fetchSkills"
        />
      </div>
    </el-card>

    <!-- 查看详情对话框 -->
    <el-dialog title="Skill 详情" v-model="showDetail" width="700px">
      <template v-if="currentSkill">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="名称">{{ currentSkill.name }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentSkill.status === 'ready' ? 'success' : 'danger'">
              {{ currentSkill.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="路径" :span="2">{{ currentSkill.path }}</el-descriptions-item>
          <el-descriptions-item label="Content Hash">{{ currentSkill.content_hash }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(currentSkill.updated_at) }}</el-descriptions-item>
        </el-descriptions>
        
        <template v-if="currentSkill.analysis">
          <el-divider>分析结果</el-divider>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="摘要">{{ currentSkill.analysis.summary || '-' }}</el-descriptions-item>
            <el-descriptions-item label="描述">{{ currentSkill.analysis.description || '-' }}</el-descriptions-item>
            <el-descriptions-item label="质量评分">
              <el-rate :value="currentSkill.analysis.quality_score" disabled show-score />
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              <el-tag v-for="tag in currentSkill.analysis.tags" :key="tag" size="small" style="margin-right: 8px">
                {{ tag }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="触发词">
              <el-tag v-for="trigger in currentSkill.analysis.triggers" :key="trigger" type="info" size="small" style="margin-right: 8px">
                {{ trigger }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSkills, getSkill } from '@/api'

const loading = ref(false)
const skills = ref([])
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const showDetail = ref(false)
const currentSkill = ref(null)

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchSkills = async () => {
  loading.value = true
  try {
    const params = { status: statusFilter.value || undefined }
    const response = await getSkills(params)
    skills.value = response.data
    total.value = response.data.length
  } catch (error) {
    ElMessage.error('获取 Skills 失败')
  } finally {
    loading.value = false
  }
}

const handleView = async (skill) => {
  try {
    const response = await getSkill(skill.id)
    currentSkill.value = response.data
    showDetail.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

watch(statusFilter, () => {
  currentPage.value = 1
  fetchSkills()
})

onMounted(fetchSkills)
</script>

<style lang="scss" scoped>
.skills-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .pagination-wrapper {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
