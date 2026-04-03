<template>
  <div class="database-connection">
    <div class="connection-container">
      <div class="terminal-header">
        <span class="terminal-title">>> SYSTEM_ROOT :: DATABASE_LINK</span>
        <div class="terminal-controls">
          <span class="control-dot"></span>
          <span class="control-dot"></span>
          <span class="control-dot"></span>
        </div>
      </div>
      
      <el-card class="connection-card">
        <template #header>
          <div class="card-header">
            <h2 class="card-title">
              <el-icon><Connection /></el-icon>
              [ 数据库连接配置 ]
            </h2>
            <span class="status-indicator" :class="{ connected: connectionStatus.connected }">
              {{ connectionStatus.connected ? 'ONLINE' : 'OFFLINE' }}
            </span>
          </div>
        </template>

        <el-form
          ref="formRef"
          :model="connectionForm"
          :rules="formRules"
          label-width="140px"
          class="connection-form"
          status-icon
        >
          <el-alert
            v-if="connectionStatus.connected"
            title="CONNECTION_ESTABLISHED"
            type="success"
            :description="`LINK: ${connectionStatus.host}:${connectionStatus.port}/${connectionStatus.db_name}`"
            show-icon
            :closable="false"
            style="margin-bottom: 20px"
            effect="dark"
          />

          <el-form-item label="MongoDB HOST" prop="host">
            <el-input
              v-model="connectionForm.host"
              placeholder="Ex: localhost"
              clearable
            >
              <template #prepend>
                <el-icon><Monitor /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="MongoDB PORT" prop="port">
            <el-input-number
              v-model="connectionForm.port"
              :min="1"
              :max="65535"
              placeholder="Def: 27017"
              style="width: 100%"
            />
          </el-form-item>

          <el-form-item label="DB_NAME">
            <el-input
              value="apt_entity_db"
              disabled
            >
              <template #prepend>
                <el-icon><Folder /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <div class="form-divider">
            <span>// AUTHENTICATION (OPTIONAL)</span>
          </div>

          <el-form-item label="USERNAME" prop="username">
            <el-input
              v-model="connectionForm.username"
              placeholder="root_user"
              clearable
            >
              <template #prepend>
                <el-icon><User /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item label="PASSWORD" prop="password">
            <el-input
              v-model="connectionForm.password"
              type="password"
              placeholder="******"
              show-password
              clearable
            >
              <template #prepend>
                <el-icon><Lock /></el-icon>
              </template>
            </el-input>
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              @click="handleConnect"
              :loading="connecting"
              size="large"
              class="action-btn"
            >
              <el-icon><Connection /></el-icon>
              {{ connectionStatus.connected ? '[ 重连 ]' : '[ 建立连接 ]' }}
            </el-button>
            <el-button
              v-if="connectionStatus.connected"
              @click="handleDisconnect"
              size="large"
              type="danger"
              class="action-btn"
              plain
            >
              <el-icon><Close /></el-icon>
              [ 断开连接 ]
            </el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onErrorCaptured } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Connection,
  Monitor,
  Folder,
  User,
  Lock,
  Close
} from '@element-plus/icons-vue'
import { initMongoConn, checkConnection } from '@/api/dict'
import { useAppStore } from '@/store'

// 错误捕获
onErrorCaptured((err, instance, info) => {
  console.error('DatabaseConnection 组件错误:', err, info)
  return false
})

const router = useRouter()
const formRef = ref(null)
const connecting = ref(false)
const appStore = useAppStore()

// 连接表单
const connectionForm = reactive({
  host: 'localhost',
  port: 27017,
  db_name: 'apt_entity_db',
  username: '',
  password: ''
})

// 连接状态
const connectionStatus = reactive({
  connected: false,
  host: '',
  port: 27017,
  db_name: ''
})

// 表单验证规则
const formRules = {
  host: [
    { required: true, message: '请输入 MongoDB 主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入 MongoDB 端口', trigger: 'blur' },
    { type: 'number', min: 1, max: 65535, message: '端口号必须在 1-65535 之间', trigger: 'blur' }
  ]
}

// 连接数据库
const handleConnect = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    connecting.value = true
    try {
      const data = {
        host: connectionForm.host,
        port: connectionForm.port,
        db_name: connectionForm.db_name
      }

      // 如果有用户名和密码，添加到请求中
      if (connectionForm.username && connectionForm.password) {
        data.username = connectionForm.username
        data.password = connectionForm.password
      }

      const result = await initMongoConn(data)

      if (result.conn_success) {
        // 更新连接状态
        connectionStatus.connected = true
        connectionStatus.host = connectionForm.host
        connectionStatus.port = connectionForm.port
        connectionStatus.db_name = connectionForm.db_name

        // 保存到 store
        appStore.setDatabaseConnection({
          host: connectionForm.host,
          port: connectionForm.port,
          db_name: connectionForm.db_name,
          username: connectionForm.username,
          password: connectionForm.password
        })

        ElMessage.success('系统连接已建立')
        // 连接成功后直接跳转到词典管理
        setTimeout(() => {
          router.push('/dict')
        }, 500)
      } else {
        ElMessage.error(result.error_msg || '连接被拒绝')
      }
    } catch (error) {
      ElMessage.error('连接失败：' + (error.message || '未知错误'))
    } finally {
      connecting.value = false
    }
  })
}

// 断开连接
const handleDisconnect = () => {
  connectionStatus.connected = false
  appStore.clearDatabaseConnection()
  ElMessage.info('连接已断开')
}

// 检查连接状态
const checkConnectionStatus = async () => {
  try {
    const result = await checkConnection()
    if (result && result.connected) {
      connectionStatus.connected = true
      connectionStatus.host = result.host || ''
      connectionStatus.port = result.port || 27017
      connectionStatus.db_name = result.db_name || ''
    }
  } catch (error) {
    // 连接检查失败，忽略错误（可能是后端未启动）
    console.log('检查连接状态失败（可能后端未启动）:', error.message)
  }
}

// 加载保存的连接配置
const loadSavedConfig = () => {
  const saved = appStore.databaseConnection
  if (saved) {
    connectionForm.host = saved.host || 'localhost'
    connectionForm.port = saved.port || 27017
    connectionForm.db_name = 'apt_entity_db'  // 固定数据库名称
    connectionForm.username = saved.username || ''
    connectionForm.password = saved.password || ''
  }
}

onMounted(() => {
  try {
    loadSavedConfig()
    // 延迟检查连接状态，避免阻塞组件渲染
    setTimeout(() => {
      checkConnectionStatus()
    }, 100)
  } catch (error) {
    console.error('组件挂载错误:', error)
  }
})
</script>

<style scoped>
.database-connection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 80px);
  padding: 40px 20px;
  background-color: var(--bg-primary);
}

.connection-container {
  width: 100%;
  max-width: 680px;
  border: 1px solid var(--border-color);
  background-color: var(--bg-secondary);
  box-shadow: 0 0 20px rgba(0, 0, 0, 0.5);
}

.terminal-header {
  background-color: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.terminal-title {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  letter-spacing: 1px;
}

.terminal-controls {
  display: flex;
  gap: 6px;
}

.control-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--border-hover);
}

.connection-card {
  border: none;
  background-color: transparent;
  box-shadow: none;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 20px;
}

.card-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-mono);
  color: var(--primary-color);
  letter-spacing: 0.5px;
}

.status-indicator {
  font-family: var(--font-mono);
  font-size: 12px;
  padding: 2px 8px;
  background-color: rgba(255, 0, 0, 0.1);
  color: var(--danger-color);
  border: 1px solid var(--danger-border);
}

.status-indicator.connected {
  background-color: rgba(0, 255, 0, 0.1);
  color: var(--success-color);
  border-color: var(--success-border);
  box-shadow: 0 0 10px rgba(0, 255, 0, 0.2);
}

.connection-form {
  margin-top: 8px;
  padding: 0 16px;
}

.connection-form :deep(.el-form-item) {
  margin-bottom: 24px;
}

.connection-form :deep(.el-form-item__label) {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-size: 13px;
}

.form-divider {
  display: flex;
  align-items: center;
  margin: 30px 0 20px;
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 12px;
  border-bottom: 1px dashed var(--border-color);
  padding-bottom: 5px;
}

.action-btn {
  width: 200px;
  font-family: var(--font-mono);
  font-weight: bold;
}

/* 覆盖 Element Plus 组件样式 */
:deep(.el-input__wrapper) {
  background-color: var(--bg-tertiary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 0 !important;
}

:deep(.el-input__wrapper:hover), :deep(.el-input__wrapper.is-focus) {
  border-color: var(--primary-color) !important;
}

:deep(.el-input-group__prepend) {
  background-color: var(--bg-panel) !important;
  box-shadow: none !important; /* 移除可能存在的白色阴影/边框 */
  border: 1px solid var(--border-color) !important;
  border-right: none !important;
  color: var(--text-secondary);
  border-radius: 0 !important;
}

/* 确保按钮颜色正确 - 覆盖可能存在的 Element Plus 默认样式 */
:deep(.el-button--primary) {
  background-color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  color: #fff !important;
  border-radius: 0 !important; /* 保持硬朗风格 */
}

:deep(.el-button--primary:hover), :deep(.el-button--primary:focus) {
  background-color: #4b6cb7 !important; /* 稍微深一点的蓝色 */
  border-color: #4b6cb7 !important;
}

/* 数字输入框样式修复 */
:deep(.el-input-number) {
  width: 100%;
}

:deep(.el-input-number__decrease),
:deep(.el-input-number__increase) {
  background-color: var(--bg-panel) !important;
  border-color: var(--border-color) !important;
  color: var(--text-secondary) !important;
  border-radius: 0 !important;
}

:deep(.el-input-number__decrease:hover),
:deep(.el-input-number__increase:hover) {
  color: var(--primary-color) !important;
  border-color: var(--primary-color) !important;
  background-color: var(--bg-secondary) !important;
}

:deep(.el-input-number .el-input__wrapper) {
  padding-left: 10px !important;
  padding-right: 10px !important;
}
</style>

