<template>
  <div class="sources-page">
    <el-card shadow="hover">
      <template #header>
        <div class="page-header">
          <span>订阅源管理</span>
          <el-button type="primary" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            添加订阅源
          </el-button>
        </div>
      </template>
      
      <el-table :data="sources" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="url" label="仓库 URL" min-width="250" show-overflow-tooltip />
        <el-table-column prop="sub_path" label="子路径" min-width="150">
          <template #default="{ row }">
            {{ row.sub_path || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="100" align="center" />
        <el-table-column prop="skill_count" label="Skills" width="80" align="center" />
        <el-table-column prop="last_sync_at" label="最后同步" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_sync_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 添加/编辑对话框 -->
    <el-dialog 
      :title="editMode ? '编辑订阅源' : '添加订阅源'" 
      v-model="showAddDialog" 
      width="500px"
    >
      <el-form :model="form" label-width="80px" :rules="rules" ref="formRef">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="输入名称" />
        </el-form-item>
        <el-form-item label="URL" prop="url">
          <el-input v-model="form.url" placeholder="GitHub 仓库 URL" />
        </el-form-item>
        <el-form-item label="子路径">
          <el-input v-model="form.sub_path" placeholder="Skills 子目录（可选）" />
        </el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="form.priority" :min="0" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ editMode ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getSources, createSource, updateSource, deleteSource } from '@/api'

const loading = ref(false)
const submitting = ref(false)
const showAddDialog = ref(false)
const editMode = ref(false)
const formRef = ref(null)

const sources = ref([])
const form = ref({
  id: '',
  name: '',
  url: '',
  sub_path: '',
  priority: 0
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入 URL', trigger: 'blur' }]
}

const formatDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchSources = async () => {
  loading.value = true
  try {
    const response = await getSources()
    sources.value = response.data
  } catch (error) {
    ElMessage.error('获取订阅源失败')
  } finally {
    loading.value = false
  }
}

const handleEdit = (row) => {
  editMode.value = true
  form.value = { ...row }
  showAddDialog.value = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该订阅源吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteSource(row.id)
    ElMessage.success('删除成功')
    fetchSources()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    
    if (editMode.value) {
      await updateSource(form.value.id, form.value)
      ElMessage.success('保存成功')
    } else {
      await createSource(form.value)
      ElMessage.success('添加成功')
    }
    
    showAddDialog.value = false
    resetForm()
    fetchSources()
  } catch (error) {
    if (error !== false) {
      ElMessage.error('操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const resetForm = () => {
  editMode.value = false
  form.value = {
    id: '',
    name: '',
    url: '',
    sub_path: '',
    priority: 0
  }
}

onMounted(fetchSources)
</script>

<style lang="scss" scoped>
.sources-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
