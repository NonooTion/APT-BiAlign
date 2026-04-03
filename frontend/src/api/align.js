import request from '@/utils/request'

/**
 * 实体对齐 API
 */

// 初始化对齐算法
export function initAlgorithm(data) {
  return request({
    url: '/align/init',
    method: 'post',
    data
  })
}

// 单文本对齐
export function singleTextAlign(data) {
  return request({
    url: '/align/single-text',
    method: 'post',
    data
  })
}

// 设置匹配阈值
export function setThreshold(data) {
  return request({
    url: '/align/set-threshold',
    method: 'put',
    data
  })
}

// 批量文本对齐
export function batchTextAlign(data) {
  return request({
    url: '/align/batch-text',
    method: 'post',
    data
  })
}

// 上传文件对齐
export function uploadFileAlign(file, entityCategories) {
  console.log('uploadFileAlign 接收到的 entityCategories:', entityCategories)
  console.log('entityCategories 类型:', typeof entityCategories)
  console.log('是否为数组:', Array.isArray(entityCategories))
  
  const formData = new FormData()
  formData.append('file', file)
  const categoriesStr = Array.isArray(entityCategories) ? entityCategories.join(',') : entityCategories
  console.log('实际发送的 entity_categories 字符串:', categoriesStr)
  formData.append('entity_categories', categoriesStr)
  
  return request({
    url: '/align/upload-file',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}


// 修正实体
export function correctEntity(data) {
  return request({
    url: '/align/correct-entity',
    method: 'post',
    data
  })
}

