import request from '@/utils/request'

/**
 * 词典管理 API
 */

// 初始化 MongoDB 连接
export function initMongoConn(data) {
  return request({
    url: '/dict/init',
    method: 'post',
    data
  })
}

// 检查数据库连接状态
export function checkConnection() {
  return request({
    url: '/dict/check',
    method: 'get'
  })
}

// 查询实体
export function queryEntity(params) {
  return request({
    url: '/dict/query',
    method: 'get',
    params
  })
}

// 新增实体
export function addEntity(data) {
  return request({
    url: '/dict/add',
    method: 'post',
    data
  })
}

// 更新实体
export function updateEntity(data) {
  return request({
    url: '/dict/update',
    method: 'put',
    data
  })
}

// 删除实体
export function deleteEntity(data) {
  return request({
    url: '/dict/delete',
    method: 'delete',
    data
  })
}

// 批量添加实体
export function batchAddEntities(data) {
  return request({
    url: '/dict/batch-add',
    method: 'post',
    data
  })
}

