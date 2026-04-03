import { createRouter, createWebHistory } from 'vue-router'
import { useAppStore } from '@/store'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/',
    name: 'DatabaseConnection',
    component: () => import('@/views/DatabaseConnection.vue'),
    meta: { title: '数据库连接', requiresAuth: false }
  },
  {
    path: '/dict',
    name: 'DictManagement',
    component: () => import('@/views/DictManagement.vue'),
    meta: { title: '词典管理', requiresAuth: true }
  },
  {
    path: '/align',
    name: 'EntityAlign',
    component: () => import('@/views/EntityAlign.vue'),
    meta: { title: '实体对齐', requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} - APT 威胁实体对齐工具` : 'APT 威胁实体对齐工具'
  
  // 检查是否需要数据库连接
  if (to.meta.requiresAuth) {
    try {
      const appStore = useAppStore()
      if (!appStore.isDatabaseConnected) {
        // 未连接数据库，重定向到连接页面
        ElMessage.warning('请先连接数据库')
        next('/')
      } else {
        next()
      }
    } catch (error) {
      // 如果 store 未初始化，直接允许访问（开发阶段）
      console.warn('Store 未初始化，跳过权限检查:', error)
      next()
    }
  } else {
    next()
  }
})

export default router

