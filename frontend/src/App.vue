<template>
  <el-config-provider :locale="locale">
    <el-container class="app-container">
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <h1>Skills Aggregator</h1>
        </div>
        <el-menu
          :default-active="activeRoute"
          router
          background-color="#304156"
          text-color="#bfcbd9"
          active-text-color="#409EFF"
        >
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/sources">
            <el-icon><Connection /></el-icon>
            <span>订阅源</span>
          </el-menu-item>
          <el-menu-item index="/conflicts">
            <el-icon><Warning /></el-icon>
            <span>冲突处理</span>
          </el-menu-item>
          <el-menu-item index="/skills">
            <el-icon><Grid /></el-icon>
            <span>Skills</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-container>
        <el-header class="header">
          <div class="header-title">{{ pageTitle }}</div>
          <div class="header-actions">
            <el-button type="primary" @click="handleSync" :loading="syncing">
              <el-icon><Refresh /></el-icon>
              同步
            </el-button>
          </div>
        </el-header>
        
        <el-main class="main-content">
          <router-view />
        </el-main>
      </el-container>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import { DataAnalysis, Connection, Warning, Grid, Refresh } from '@element-plus/icons-vue'
import { syncStatus } from '@/api'

const route = useRoute()
const locale = ref(zhCn)
const syncing = ref(false)

const activeRoute = computed(() => route.path)
const pageTitle = computed(() => {
  const titles = {
    '/': '仪表盘',
    '/sources': '订阅源管理',
    '/conflicts': '冲突处理',
    '/skills': 'Skills 列表'
  }
  return titles[route.path] || 'Skills Aggregator'
})

const handleSync = async () => {
  syncing.value = true
  try {
    await syncStatus()
    ElMessage.success('同步触发成功')
  } catch (error) {
    ElMessage.error('同步触发失败')
  } finally {
    syncing.value = false
  }
}
</script>

<style lang="scss" scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background-color: #304156;
  
  .logo {
    height: 60px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: #263445;
    
    h1 {
      color: #fff;
      font-size: 16px;
      margin: 0;
    }
  }
  
  .el-menu {
    border-right: none;
  }
}

.header {
  background-color: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-title {
    font-size: 18px;
    font-weight: 500;
  }
}

.main-content {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
