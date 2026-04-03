<template>
  <el-container class="app-container">
    <el-header class="app-header">
      <div class="header-inner">
        <!-- Logo / Brand -->
        <div class="brand">
          <div class="brand-icon">
            <el-icon><Monitor /></el-icon>
          </div>
          <div class="brand-text">
            <h1 class="app-title">APT_TI_ALIGNER</h1>
            <span class="app-subtitle">>> ENTITY_CORRELATION_SYSTEM</span>
          </div>
        </div>

        <!-- System Status / Nav -->
        <nav class="nav-bar" v-if="showMenu">
          <router-link to="/dict" class="nav-item" :class="{ active: activeMenu === '/dict' }">
            <span class="nav-bracket">[</span>
            <span class="nav-text">DICT_MGMT</span>
            <span class="nav-bracket">]</span>
          </router-link>
          
          <router-link to="/align" class="nav-item" :class="{ active: activeMenu === '/align' }">
            <span class="nav-bracket">[</span>
            <span class="nav-text">ENTITY_ALIGN</span>
            <span class="nav-bracket">]</span>
          </router-link>
        </nav>

        <!-- Connectivity -->
        <div class="header-actions" v-if="showMenu">
          <div class="status-indicator online">
            <span class="status-dot"></span>
            <span class="status-text">SYSTEM_ONLINE</span>
          </div>
          <el-button 
            class="disconnect-btn"
            size="small"
            @click="handleDisconnect"
          >
            DISCONNECT
          </el-button>
        </div>
      </div>
      <div class="scan-line"></div>
    </el-header>

    <el-main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Monitor, Collection, Connection, Close } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAppStore } from '@/store'

const route = useRoute()
const router = useRouter()
const appStore = useAppStore()
const activeMenu = computed(() => route.path)

const showMenu = computed(() => {
  return route.path !== '/'
})

const handleDisconnect = () => {
  ElMessageBox.confirm(
    'Terminate database connection?',
    'WARNING',
    {
      confirmButtonText: 'CONFIRM',
      cancelButtonText: 'CANCEL',
      type: 'warning',
      customClass: 'hacker-message-box'
    }
  ).then(() => {
    appStore.clearDatabaseConnection()
    ElMessage.success('CONNECTION TERMINATED')
    router.push('/')
  }).catch(() => {})
}
</script>

<style scoped>
.app-container {
  height: 100vh;
  width: 100vw;
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.app-header {
  height: var(--header-height) !important;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  padding: 0;
  position: relative;
  flex-shrink: 0;
}

.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-icon {
  color: var(--primary-color);
  font-size: 24px;
  display: flex;
  align-items: center;
  text-shadow: 0 0 10px var(--primary-glow);
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.app-title {
  margin: 0;
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 1px;
}

.app-subtitle {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--primary-color);
  margin-top: 4px;
  opacity: 0.8;
}

.nav-bar {
  display: flex;
  gap: 24px;
}

.nav-item {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 6px 12px;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 4px;
}

.nav-bracket {
  opacity: 0;
  color: var(--primary-color);
  transition: opacity var(--transition-fast);
}

.nav-item:hover, .nav-item.active {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.03);
}

.nav-item:hover .nav-bracket, .nav-item.active .nav-bracket {
  opacity: 1;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--success-color);
}

.status-dot {
  width: 8px;
  height: 8px;
  background-color: var(--success-color);
  border-radius: 50%;
  box-shadow: 0 0 8px var(--success-color);
  animation: pulse 2s infinite;
}

.disconnect-btn {
  border: 1px solid var(--danger-border) !important;
  color: var(--danger-color) !important;
  font-family: var(--font-mono) !important;
  background: transparent !important;
}

.disconnect-btn:hover {
  background: var(--danger-bg) !important;
  box-shadow: 0 0 10px var(--danger-bg);
}

.scan-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, 
    transparent 0%, 
    var(--primary-color) 50%, 
    transparent 100%);
  opacity: 0.5;
  box-shadow: 0 0 4px var(--primary-color);
}

.app-main {
  flex: 1;
  padding: 0; /* Let children handle padding */
  overflow: hidden; /* Children should adapt */
  position: relative;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}
</style>

