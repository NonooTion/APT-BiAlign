<template>
  <div class="dict-management">
    <el-card class="page-card">
      <!-- 查询区域 - 固定顶部 -->
      <div class="query-form-wrapper">
      <el-form :inline="true" :model="queryForm" class="query-form">
        <el-form-item label="ENTITY_TYPE">
          <el-select v-model="queryForm.entity_type" placeholder="Select Type" style="width: 120px">
            <el-option label="APT组织" value="apt" />
            <el-option label="攻击工具" value="tool" />
            <el-option label="漏洞" value="vuln" />
          </el-select>
        </el-form-item>
        <el-form-item label="KEYWORD">
          <el-input
            v-model="queryForm.keyword"
            placeholder="Search payload..."
            clearable
            style="width: 200px"
            @keyup.enter="handleQuery"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">
            <el-icon><Search /></el-icon>
            [ 查询 ]
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            [ 重置 ]
          </el-button>
        </el-form-item>
          <el-form-item class="add-button-item">
            <el-button type="info" @click="handleBatchImport">
              <el-icon><Upload /></el-icon>
              [ 批量导入 ]
            </el-button>
            <el-button type="success" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              [ 新增实体 ]
            </el-button>
          </el-form-item>
      </el-form>
      </div>

      <!-- 表格区域 -->
      <div class="table-wrapper">
      <el-table
        v-loading="loading"
        :data="tableData"
        border
        stripe
          :height="tableHeight"
        style="width: 100%"
      >
        <el-table-column prop="entity_id" label="实体ID" width="120" />
        <el-table-column prop="en_core" label="英文核心名称" width="200" />
        <el-table-column prop="zh_core" label="中文核心名称" width="200" />
        <el-table-column prop="en_variants" label="英文变体" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="(variant, index) in row.en_variants"
              :key="index"
              size="small"
              style="margin-right: 5px"
            >
              {{ variant }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="zh_variants" label="中文变体" min-width="200">
          <template #default="{ row }">
            <el-tag
              v-for="(variant, index) in row.zh_variants"
              :key="index"
              size="small"
              type="success"
              style="margin-right: 5px"
            >
              {{ variant }}
            </el-tag>
          </template>
        </el-table-column>
          <el-table-column prop="description" label="描述" min-width="250" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.description">{{ row.description }}</span>
              <span v-else style="color: #909399;">-</span>
            </template>
          </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.create_time) }}
          </template>
        </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
              <div class="action-buttons">
            <el-button type="primary" size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
              </div>
          </template>
        </el-table-column>
      </el-table>
      </div>

      <!-- 分页 - 固定底部 -->
      <div class="pagination-wrapper">
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange"
        />
        </div>
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="120px"
      >
        <el-form-item label="实体类型" prop="entity_type">
          <el-select v-model="formData.entity_type" placeholder="请选择" :disabled="isEdit">
            <el-option label="APT组织" value="apt" />
            <el-option label="攻击工具" value="tool" />
            <el-option label="漏洞" value="vuln" />
          </el-select>
        </el-form-item>
        <el-form-item label="实体ID" prop="entity_id" v-if="isEdit">
          <el-input v-model="formData.entity_id" disabled />
        </el-form-item>
        <el-form-item label="英文核心名称" prop="entity_data.en_core">
          <el-input v-model="formData.entity_data.en_core" placeholder="请输入英文核心名称" />
        </el-form-item>
        <el-form-item label="中文核心名称" prop="entity_data.zh_core">
          <el-input v-model="formData.entity_data.zh_core" placeholder="请输入中文核心名称" />
        </el-form-item>
        <el-form-item label="英文变体">
          <el-input
            v-model="variantsText.en"
            type="textarea"
            :rows="3"
            placeholder="请输入英文变体，多个用逗号分隔"
          />
        </el-form-item>
        <el-form-item label="中文变体">
          <el-input
            v-model="variantsText.zh"
            type="textarea"
            :rows="3"
            placeholder="请输入中文变体，多个用逗号分隔"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="formData.entity_data.description"
            type="textarea"
            :rows="4"
            placeholder="请输入实体描述（可选）"
            maxlength="2000"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量导入对话框 -->
    <el-dialog
      v-model="batchDialogVisible"
      title="批量导入实体"
      width="800px"
      @close="handleBatchDialogClose"
    >
      <el-tabs v-model="importTab" type="border-card">
        <el-tab-pane label="JSON 粘贴" name="paste">
          <div class="import-tip">
            <el-alert
              title="JSON 格式说明"
              type="info"
              :closable="false"
              show-icon
            >
              <template #default>
                <div style="margin-top: 8px;">
                  <p>请粘贴 JSON 数组格式的实体数据，每个实体包含以下字段：</p>
                  <pre>[
  {
  "entity_type": "apt_organization",
  "cn_core": "中文名称",
  "en_core": "English Name",
  "description": "描述信息",
  "zh_variants": ["变体1"],
  "en_variants": ["variant1"]
  }
]</pre>
                  <p style="margin-top: 8px; color: #909399;">
                    entity_type 可选值：apt_organization / attack_tool / vulnerability<br>
                    <strong>注意：</strong>entity_id 字段已移除，由系统自动生成（APT-001、TOOL-001、VULN-001 格式）
                  </p>
                </div>
              </template>
            </el-alert>
          </div>
          <el-input
            v-model="batchJsonText"
            type="textarea"
            :rows="15"
            placeholder="请粘贴 JSON 数组，例如：[{...}, {...}]"
            style="margin-top: 16px;"
          />
        </el-tab-pane>
        <el-tab-pane label="文件上传" name="upload">
          <div class="import-tip">
            <el-alert
              title="文件格式说明"
              type="info"
              :closable="false"
              show-icon
            >
              <template #default>
                <p>请上传 JSON 文件，文件内容应为 JSON 数组格式</p>
                <p style="margin-top: 8px; color: #909399;">
                  支持 .json 文件，文件大小不超过 5MB
                </p>
              </template>
            </el-alert>
          </div>
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            accept=".json"
            drag
            style="margin-top: 16px;"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                只能上传 JSON 文件，且不超过 5MB
              </div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      
      <template #footer>
        <div class="batch-dialog-footer">
          <el-button @click="batchDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleBatchSubmit" :loading="batchLoading">
            开始导入
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 批量导入结果对话框 -->
    <el-dialog
      v-model="resultDialogVisible"
      title="导入结果"
      width="900px"
    >
      <div class="result-summary">
        <div class="statistics">
          <div class="stat-item">
            <div class="stat-label">总数</div>
            <div class="stat-value">{{ batchResult.total }}</div>
          </div>
          <div class="stat-item success">
            <div class="stat-label">成功</div>
            <div class="stat-value">
              {{ batchResult.success_count }}
              <el-icon style="color: #67c23a; margin-left: 4px;"><CircleCheck /></el-icon>
            </div>
          </div>
          <div class="stat-item fail">
            <div class="stat-label">失败</div>
            <div class="stat-value">
              {{ batchResult.fail_count }}
              <el-icon style="color: #f56c6c; margin-left: 4px;"><CircleClose /></el-icon>
            </div>
          </div>
        </div>
      </div>
      
      <el-table
        :data="batchResult.results"
        border
        stripe
        max-height="400"
        style="margin-top: 20px;"
      >
        <el-table-column prop="entity_id" label="实体ID" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.success ? 'success' : 'danger'">
              {{ row.success ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="error_msg" label="错误信息" min-width="300">
          <template #default="{ row }">
            <span v-if="row.error_msg" style="color: #f56c6c;">{{ row.error_msg }}</span>
            <span v-else style="color: #909399;">-</span>
          </template>
        </el-table-column>
      </el-table>
      
      <template #footer>
        <el-button type="primary" @click="resultDialogVisible = false">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, Edit, Delete, Upload, UploadFilled, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import { queryEntity, addEntity, updateEntity, deleteEntity, batchAddEntities } from '@/api/dict'
import { useRouter } from 'vue-router'
import { useAppStore } from '@/store'

const router = useRouter()
const appStore = useAppStore()

// 数据
const loading = ref(false)
const submitLoading = ref(false)
const allTableData = ref([]) // 存储所有数据
const tableData = ref([]) // 当前页显示的数据
const dialogVisible = ref(false)
const formRef = ref(null)

// 批量导入相关
const batchDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const batchLoading = ref(false)
const importTab = ref('paste')
const batchJsonText = ref('')
const uploadFile = ref(null)
const uploadRef = ref(null)
const batchResult = reactive({
  total: 0,
  success_count: 0,
  fail_count: 0,
  results: []
})

// 查询表单
const queryForm = reactive({
  entity_type: 'apt',
  keyword: ''
})

// 分页
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 表单数据
const formData = reactive({
  entity_type: 'apt',
  entity_id: '',
  entity_data: {
    en_core: '',
    zh_core: '',
    en_variants: [],
    zh_variants: [],
    description: ''
  }
})

// 变体文本（用于输入）
const variantsText = reactive({
  en: '',
  zh: ''
})

// 表单验证规则
const formRules = {
  entity_type: [{ required: true, message: '请选择实体类型', trigger: 'change' }],
  'entity_data.en_core': [{ required: true, message: '请输入英文核心名称', trigger: 'blur' }],
  'entity_data.zh_core': [{ required: true, message: '请输入中文核心名称', trigger: 'blur' }]
}

// 计算属性
const isEdit = computed(() => !!formData.entity_id)
const dialogTitle = computed(() => isEdit.value ? '编辑实体' : '新增实体')

// 表格高度计算（动态计算，减去搜索栏和分页的高度）
const tableHeight = ref(600) // 默认高度

// 计算表格高度
const calculateTableHeight = () => {
  // 获取容器高度
  const container = document.querySelector('.page-card')
  if (container) {
    const containerHeight = container.clientHeight
    // 搜索栏高度约 100px，分页高度约 80px，padding 约 40px
    const height = containerHeight - 220
    tableHeight.value = Math.max(400, height) // 最小高度 400px
  }
}

// 监听窗口大小变化
onMounted(() => {
  // 延迟计算，确保 DOM 已渲染
  setTimeout(() => {
    calculateTableHeight()
  }, 100)
  window.addEventListener('resize', calculateTableHeight)
})

onUnmounted(() => {
  window.removeEventListener('resize', calculateTableHeight)
  })

// 查询
const handleQuery = async () => {
  loading.value = true
  try {
    const params = {
      entity_type: queryForm.entity_type
    }
    
    if (queryForm.keyword) {
      params.keyword = queryForm.keyword
    }
    
    const result = await queryEntity(params)
    allTableData.value = result.entity_list || []
    pagination.total = allTableData.value.length
    
    // 应用分页
    applyPagination()
    
    // 重新计算表格高度
    setTimeout(() => {
      calculateTableHeight()
    }, 100)
  } catch (error) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

// 应用分页
const applyPagination = () => {
  const start = (pagination.page - 1) * pagination.size
  const end = start + pagination.size
  tableData.value = allTableData.value.slice(start, end)
}

// 分页改变
const handlePageChange = () => {
  applyPagination()
  // 滚动到表格顶部
  const tableEl = document.querySelector('.el-table')
  if (tableEl) {
    tableEl.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// 每页条数改变
const handleSizeChange = () => {
  pagination.page = 1 // 重置到第一页
  applyPagination()
}

// 重置
const handleReset = () => {
  queryForm.keyword = ''
  queryForm.entity_type = 'apt'
  pagination.page = 1
  pagination.size = 10
  handleQuery()
}

// 新增
const handleAdd = () => {
  resetForm()
  formData.entity_type = queryForm.entity_type
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  resetForm()
  formData.entity_type = queryForm.entity_type
  formData.entity_id = row.entity_id
  formData.entity_data.en_core = row.en_core
  formData.entity_data.zh_core = row.zh_core
  formData.entity_data.en_variants = [...(row.en_variants || [])]
  formData.entity_data.zh_variants = [...(row.zh_variants || [])]
  formData.entity_data.description = row.description || ''
  variantsText.en = (row.en_variants || []).join(', ')
  variantsText.zh = (row.zh_variants || []).join(', ')
  dialogVisible.value = true
}

// 删除
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除实体 "${row.en_core} / ${row.zh_core}" 吗？`,
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const data = {
      entity_id: row.entity_id,
      entity_type: queryForm.entity_type
    }
    
    await deleteEntity(data)
    ElMessage.success('删除成功')
    handleQuery()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitLoading.value = true
    
    try {
      // 处理变体
      formData.entity_data.en_variants = variantsText.en
        ? variantsText.en.split(',').map(v => v.trim()).filter(v => v)
        : []
      formData.entity_data.zh_variants = variantsText.zh
        ? variantsText.zh.split(',').map(v => v.trim()).filter(v => v)
        : []
      
      // 处理描述字段（如果为空字符串，转为 null）
      const description = formData.entity_data.description?.trim() || null
      
      if (isEdit.value) {
        // 更新
        const updateData = {
          entity_id: formData.entity_id,
          entity_type: formData.entity_type,
          update_data: {
            en_core: formData.entity_data.en_core,
            zh_core: formData.entity_data.zh_core,
            en_variants: formData.entity_data.en_variants,
            zh_variants: formData.entity_data.zh_variants,
            description: description
          }
        }
        await updateEntity(updateData)
        ElMessage.success('更新成功')
      } else {
        // 新增
        const addData = {
          entity_type: formData.entity_type,
          entity_data: {
            ...formData.entity_data,
            description: description
          }
        }
        await addEntity(addData)
        ElMessage.success('新增成功')
      }
      
      dialogVisible.value = false
      handleQuery()
    } catch (error) {
      ElMessage.error(isEdit.value ? '更新失败' : '新增失败')
    } finally {
      submitLoading.value = false
    }
  })
}

// 重置表单
const resetForm = () => {
  formData.entity_id = ''
  formData.entity_data.en_core = ''
  formData.entity_data.zh_core = ''
  formData.entity_data.en_variants = []
  formData.entity_data.zh_variants = []
  formData.entity_data.description = ''
  variantsText.en = ''
  variantsText.zh = ''
  formRef.value?.resetFields()
}

// 对话框关闭
const handleDialogClose = () => {
  resetForm()
}

// 格式化日期时间
const formatDateTime = (dateTime) => {
  if (!dateTime) return '-'
  const date = new Date(dateTime)
  return date.toLocaleString('zh-CN')
}

// 批量导入
const handleBatchImport = () => {
  batchDialogVisible.value = true
  importTab.value = 'paste'
  batchJsonText.value = ''
  uploadFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 文件变化处理
const handleFileChange = (file) => {
  uploadFile.value = file.raw
}

// 文件移除处理
const handleFileRemove = () => {
  uploadFile.value = null
}

// 批量导入提交
const handleBatchSubmit = async () => {
  let entities = []
  
  try {
    if (importTab.value === 'paste') {
      // JSON 粘贴模式
      if (!batchJsonText.value.trim()) {
        ElMessage.warning('请输入 JSON 数据')
        return
      }
      
      try {
        entities = JSON.parse(batchJsonText.value)
      } catch (error) {
        ElMessage.error('JSON 格式错误，请检查输入内容')
        return
      }
    } else {
      // 文件上传模式
      if (!uploadFile.value) {
        ElMessage.warning('请选择要上传的文件')
        return
      }
      
      // 读取文件内容
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const content = e.target.result
          entities = JSON.parse(content)
          await processBatchImport(entities)
        } catch (error) {
          ElMessage.error('文件解析失败：' + error.message)
          batchLoading.value = false
        }
      }
      reader.onerror = () => {
        ElMessage.error('文件读取失败')
        batchLoading.value = false
      }
      reader.readAsText(uploadFile.value)
      batchLoading.value = true
      return
    }
    
    // 处理批量导入
    await processBatchImport(entities)
  } catch (error) {
    ElMessage.error('处理失败：' + error.message)
    batchLoading.value = false
  }
}

// 处理批量导入
const processBatchImport = async (entities) => {
  if (!Array.isArray(entities)) {
    ElMessage.error('数据格式错误：必须是 JSON 数组')
    batchLoading.value = false
    return
  }
  
  if (entities.length === 0) {
    ElMessage.warning('没有可导入的数据')
    batchLoading.value = false
    return
  }

  // 处理实体数据：移除entity_id字段（由后端自动生成）
  const processedEntities = entities.map(entity => {
    const processedEntity = { ...entity }
    delete processedEntity.entity_id
    return processedEntity
  })
  
  batchLoading.value = true
  
  try {
    const result = await batchAddEntities({ entities: processedEntities })
    
    // 更新结果
    batchResult.total = result.total || 0
    batchResult.success_count = result.success_count || 0
    batchResult.fail_count = result.fail_count || 0
    batchResult.results = result.results || []
    
    // 显示结果对话框
    batchDialogVisible.value = false
    resultDialogVisible.value = true
    
    // 刷新列表
    if (batchResult.success_count > 0) {
      handleQuery()
    }
    
    ElMessage.success(`批量导入完成：成功 ${batchResult.success_count} 个，失败 ${batchResult.fail_count} 个`)
  } catch (error) {
    ElMessage.error('批量导入失败：' + (error.message || '未知错误'))
  } finally {
    batchLoading.value = false
  }
}

// 批量导入对话框关闭
const handleBatchDialogClose = () => {
  batchJsonText.value = ''
  uploadFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 初始化
handleQuery()
</script>

<style scoped>
.dict-management {
  height: 100%;
  width: 100%;
  background-color: var(--bg-primary);
  display: flex;
  flex-direction: column;
}

.page-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  border: none;
  border-radius: 0;
  box-shadow: none;
  background-color: transparent;
  overflow: hidden;
  position: relative;
}

/* 查询表单包装器 */
.query-form-wrapper {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: var(--bg-secondary);
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}

.query-form {
  background: transparent;
  padding: 0;
  border: none;
  box-shadow: none;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.query-form :deep(.el-form-item) {
  margin-bottom: 0;
  margin-right: 16px;
}

.query-form :deep(.el-form-item__label) {
  font-family: var(--font-mono);
  color: var(--text-secondary);
  font-size: 13px;
  padding-right: 8px;
}

.add-button-item {
  margin-left: auto;
  margin-right: 0 !important;
}

/* 表格包装器 */
.table-wrapper {
  flex: 1;
  padding: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--bg-primary);
}

/* 分页包装器 */
.pagination-wrapper {
  position: sticky;
  bottom: 0;
  z-index: 10;
  background-color: var(--bg-secondary);
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
}

/* 覆盖 Element Plus 组件样式 */
:deep(.el-input__wrapper),
:deep(.el-select .el-input__wrapper) {
  background-color: var(--bg-tertiary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color) !important;
  border-radius: 0 !important;
}

:deep(.el-input__wrapper:hover),
:deep(.el-select:hover .el-input__wrapper),
:deep(.el-input__wrapper.is-focus),
:deep(.el-select .el-input.is-focus .el-input__wrapper) {
  border-color: var(--primary-color) !important;
}

:deep(.el-button) {
  border-radius: 0;
  font-family: var(--font-mono);
  font-weight: bold;
}

/* 表格样式优化 */
.page-card :deep(.el-table) {
  background-color: transparent;
  --el-table-border-color: var(--border-color);
  --el-table-header-bg-color: var(--bg-tertiary);
  --el-table-row-hover-bg-color: rgba(92, 124, 250, 0.1);
  --el-table-tr-bg-color: transparent;
  color: var(--text-secondary);
}

.page-card :deep(.el-table th) {
  background-color: var(--bg-tertiary) !important;
  color: var(--primary-color) !important;
  font-family: var(--font-mono);
  border-bottom: 1px solid var(--border-color) !important;
  font-weight: 600;
}

.page-card :deep(.el-table td) {
  background-color: transparent !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
  font-family: var(--font-mono);
  color: var(--text-primary);
}

.page-card :deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background-color: rgba(255, 255, 255, 0.02);
}

/* tags */
.page-card :deep(.el-tag) {
  border-radius: 0;
  background-color: rgba(255, 255, 255, 0.1);
  border-color: rgba(255, 255, 255, 0.2);
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.page-card :deep(.el-tag--success) {
  background-color: var(--success-bg);
  border-color: var(--success-border);
  color: var(--success-color);
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 8px;
}

.page-card :deep(.el-button--small) {
  padding: 4px 8px;
  height: 24px;
  font-size: 12px;
}

/* 分页 */
.pagination :deep(.el-pagination) {
  --el-pagination-bg-color: transparent;
  --el-pagination-text-color: var(--text-secondary);
  --el-pagination-button-color: var(--text-secondary);
  --el-pagination-button-disabled-bg-color: transparent;
  --el-pagination-button-bg-color: transparent;
  --el-pagination-hover-color: var(--primary-color);
}

.pagination :deep(.el-pagination button:disabled) {
  background-color: transparent;
  color: var(--text-placeholder);
}

.pagination :deep(.el-pager li) {
  background-color: transparent;
  border: 1px solid var(--border-color);
  border-radius: 0;
  margin: 0 2px;
  color: var(--text-secondary);
}

.pagination :deep(.el-pager li.is-active) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
  color: #fff;
}

/* 对话框样式 */
:deep(.el-dialog) {
  background-color: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 0;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid var(--border-color);
  margin-right: 0;
  padding: 15px 20px;
}

:deep(.el-dialog__title) {
  color: var(--primary-color);
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: bold;
}

:deep(.el-dialog__body) {
  padding: 20px;
  color: var(--text-primary);
}

:deep(.el-dialog__footer) {
  border-top: 1px solid var(--border-color);
  padding: 15px 20px;
  background-color: rgba(0, 0, 0, 0.2);
}

:deep(.el-form-item__label) {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

:deep(.el-textarea__inner) {
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 0;
}

:deep(.el-textarea__inner:focus) {
  border-color: var(--primary-color);
}

/* 批量导入相关 */
.import-tip pre {
  background-color: var(--bg-tertiary) !important;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  border-radius: 0;
  padding: 12px;
  margin-top: 8px;
  font-size: 12px;
}

.import-tip :deep(.el-alert) {
  background-color: rgba(92, 124, 250, 0.1);
  border: 1px solid rgba(92, 124, 250, 0.2);
  color: var(--text-primary);
}

:deep(.el-upload-dragger) {
  background-color: var(--bg-tertiary);
  border: 1px dashed var(--border-color);
  border-radius: 0;
}

:deep(.el-upload-dragger:hover) {
  border-color: var(--primary-color);
  background-color: rgba(92, 124, 250, 0.05);
}

:deep(.el-upload__text) {
  color: var(--text-secondary);
}

:deep(.el-upload__text em) {
  color: var(--primary-color);
}

/* 统计区域 */
.statistics {
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 0;
}

.stat-label {
  color: var(--text-secondary);
  font-family: var(--font-mono);
}

.stat-value {
  color: var(--text-primary);
  font-family: var(--font-mono);
}

/* Tab样式修复 */
:deep(.el-tabs--border-card) {
  border: 1px solid var(--border-color);
  background: transparent;
}
:deep(.el-tabs--border-card>.el-tabs__header) {
  background-color: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
}
:deep(.el-tabs--border-card>.el-tabs__header .el-tabs__item.is-active) {
  background-color: var(--bg-secondary);
  border-right-color: var(--border-color);
  border-left-color: var(--border-color);
  color: var(--primary-color);
}
:deep(.el-tabs--border-card>.el-tabs__content) {
  background-color: var(--bg-secondary);
}
</style>
