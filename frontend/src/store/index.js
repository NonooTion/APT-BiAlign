import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    // 数据库连接信息
    databaseConnection: null
  }),
  getters: {
    // 是否已连接数据库
    isDatabaseConnected: (state) => {
      return state.databaseConnection !== null
    },
    // 获取数据库连接信息
    getDatabaseConnection: (state) => {
      return state.databaseConnection
    }
  },
  actions: {
    // 设置数据库连接信息
    setDatabaseConnection(connection) {
      this.databaseConnection = connection
      // 保存到 localStorage
      localStorage.setItem('databaseConnection', JSON.stringify(connection))
    },
    // 清除数据库连接信息
    clearDatabaseConnection() {
      this.databaseConnection = null
      localStorage.removeItem('databaseConnection')
    },
    // 从 localStorage 加载连接信息
    loadDatabaseConnection() {
      const saved = localStorage.getItem('databaseConnection')
      if (saved) {
        try {
          this.databaseConnection = JSON.parse(saved)
        } catch (e) {
          console.error('加载数据库连接信息失败:', e)
        }
      }
    }
  }
})

