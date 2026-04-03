<template>
  <div class="entity-align">
    <!-- 顶部工具栏 -->
    <div class="top-toolbar">
      <div class="toolbar-left">
        <h2 class="page-title">实体关联分析系统</h2>
        <span class="page-subtitle">>> 系统就绪 :: 等待指令</span>
      </div>
      <div class="toolbar-actions">
        <el-button @click="handleImportFile">
          <el-icon><Upload /></el-icon>
          [ 导入数据 ]
        </el-button>
        <el-button @click="handleInitAlgorithm" :loading="initLoading">
          <el-icon><Setting /></el-icon>
          [ 初始化算法 ]
        </el-button>
        <el-button @click="handleOpenThresholdDialog">
          <el-icon><Tools /></el-icon>
          [ 参数配置 ]
        </el-button>
        <el-button type="primary" @click="handleBatchAlign" :disabled="selectedFiles.length === 0" :loading="batchAlignLoading">
          <el-icon><Search /></el-icon>
          [ 批量对齐 ({{ selectedFiles.length }}) ]
        </el-button>
        <el-button type="danger" @click="handleExportPdf" :disabled="!highlightedText || filteredAlignResult.length === 0" :loading="exportLoading">
          <el-icon><Document /></el-icon>
          [ 导出报告 ]
        </el-button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="main-content">
      <!-- 左侧文件列表 -->
      <div class="left-panel">
        <div class="panel-header">
          <span>// 文件列表</span>
          <div class="panel-actions">
            <el-button type="text" size="small" @click="handleSelectAll">[全选]</el-button>
            <el-button type="text" size="small" @click="handleClearSelection">[清空]</el-button>
          </div>
        </div>
        
        <div class="file-list-container">
          <transition-group name="list" tag="div">
            <!-- 文本输入项 -->
            <div key="text-input" class="file-item" :class="{ active: currentFileType === 'text' }" @click="handleSelectTextInput">
              <el-icon class="file-icon"><Document /></el-icon>
              <div class="file-info">
                <span class="file-name">文本输入流 (Input Stream)</span>
                <span class="file-meta">{{ alignForm.text.length }} 字符</span>
              </div>
              <el-tag size="small" effect="dark">RW</el-tag>
            </div>

            <!-- 上传的文件列表 -->
            <div
              v-for="(file, index) in uploadedFiles"
              :key="file.name"
              class="file-item"
              :class="{ active: currentFile && currentFile.name === file.name }"
              @click="handleSelectFile(file)"
            >
              <el-icon class="file-icon"><Document /></el-icon>
              <div class="file-info">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-meta">{{ formatFileSize(file.size) }}</span>
              </div>
              <div class="file-actions" @click.stop>
                <el-checkbox
                  :model-value="selectedFiles.includes(file.name)"
                  @change="(checked) => handleFileSelectionChange(file.name, checked)"
                  size="small"
                />
                <el-button type="text" size="small" @click.stop="handleRemoveFile(index)">
                  <el-icon><Close /></el-icon>
                </el-button>
              </div>
            </div>
          </transition-group>

          <!-- 空状态 -->
          <div v-if="uploadedFiles.length === 0 && !alignForm.text" class="empty-state">
            <span class="empty-text">>>> 暂无挂载文件</span>
          </div>
        </div>
      </div>

      <!-- 右侧内容展示区 -->
      <div class="right-panel">
        <div class="content-header">
          <div class="content-title">
            <h3>{{ currentFile ? currentFile.name : '文本输入流' }}</h3>
          </div>
          <div class="content-actions">
            <div class="entity-type-toggles">
            <div
              v-for="category in entityCategories"
              :key="category.value"
              class="toggle-button"
              :class="{ active: alignForm.entity_categories.includes(category.value) }"
              @click="handleToggleCategory(category.value)"
            >
              <span class="toggle-icon">{{ alignForm.entity_categories.includes(category.value) ? '🟢' : '🔴' }}</span>
              <span class="toggle-label">{{ category.label }}</span>
              <span class="toggle-status">{{ alignForm.entity_categories.includes(category.value) ? 'ON' : 'OFF' }}</span>
            </div>
          </div>
          
            <el-button
              v-if="currentFileType === 'text' && filteredAlignResult.length > 0"
              @click="switchToEditMode"
              size="small"
            >
              <el-icon><Edit /></el-icon>
              [ 编辑 ]
            </el-button>
            <el-button type="primary" @click="handleAlignCurrent" :loading="alignLoading" size="small">
              <el-icon><Search /></el-icon>
              [ 执行对齐 ]
            </el-button>
          </div>
        </div>

        <div class="content-body">
           <!-- 文本输入模式 -->
           <div v-if="currentFileType === 'text'" class="text-input-mode">
              <div class="text-input-container">
                <transition name="fade" mode="out-in">
                  <div v-if="filteredAlignResult.length > 0 && highlightedText" class="highlighted-text-display" key="result">
                    <div class="highlight-body" v-html="highlightedText" @click="handleHighlightClick" @mouseup="handleTextSelection"></div>
                  </div>
                  <el-input
                    v-else
                    key="input"
                    v-model="alignForm.text"
                    type="textarea"
                    resize="none"
                    placeholder=">> 请输入分析文本..."
                  />
                </transition>
              </div>
           </div>

           <!-- 文件预览模式 -->
           <div v-else-if="currentFile" class="file-preview-mode">
             <div class="file-content-container">
               <transition name="fade" mode="out-in">
                 <div v-if="alignResult.length > 0 && highlightedText" class="highlighted-text-display" key="result">
                   <div class="highlight-body" v-html="highlightedText" @click="handleHighlightClick" @mouseup="handleTextSelection"></div>
                 </div>
                 <div v-else class="highlighted-text-display" v-html="currentFileContent" key="content"></div>
               </transition>
             </div>
           </div>

           <div v-else class="empty-preview">
             <span>等待选择文件...</span>
           </div>
        </div>

<!-- 统计面板 -->
        <div v-if="filteredAlignResult.length > 0" class="result-statistics">
          <div class="stat-item">
             <span class="stat-label">实体数量</span>
             <span class="stat-value info">{{ filteredAlignResult.length }}</span>
          </div>
          <div class="stat-item">
             <span class="stat-label">平均置信度</span>
             <span class="stat-value success">{{ getAverageConfidence() }}%</span>
          </div>
           <div class="stat-item">
             <span class="stat-label">处理耗时</span>
             <span class="stat-value warning">{{ processTime.toFixed(3) }}s</span>
          </div>
        </div>

        <!-- 结果详情表格 (恢复功能) -->
        <!-- 结果详情表格 (已移除，功能整合至高亮点击交互) -->
      </div>
    </div>

    <!-- 隐藏的文件上传组件 -->
    <input
      ref="fileInputRef"
      type="file"
      multiple
      accept=".json,.txt,.pdf,.doc,.docx"
      style="display: none"
      @change="handleFileInputChange"
    />

    <!-- 阈值设置对话框 -->
    <el-dialog
      v-model="thresholdDialogVisible"
      title="系统配置 // 阈值参数"
      width="600px"
      :close-on-click-modal="false"
      class="hacker-dialog"
    >
      <el-form :model="thresholdForm" label-width="150px">
        <el-form-item label="模糊匹配阈值">
          <el-slider v-model="thresholdForm.levenshtein_thresh" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="语义匹配阈值">
          <el-slider v-model="thresholdForm.semantic_thresh" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>
        <el-form-item label="置信度截断">
          <el-slider v-model="thresholdForm.confidence_thresh" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>
        <el-form-item>
          <el-button @click="handleResetThreshold">重置</el-button>
          <el-button type="info" @click="handleApplyThresholdToForm">应用配置</el-button>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="thresholdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSetThreshold" :loading="thresholdLoading">确认</el-button>
      </template>
    </el-dialog>

    <!-- 实体添加对话框 -->
    <el-dialog
      v-model="correctDialogVisible"
      title="实体添加"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="newEntityForm" :rules="newEntityRules" ref="newEntityFormRef" label-width="120px">
        <el-form-item label="实体类型" prop="entity_type">
          <el-select v-model="newEntityForm.entity_type">
            <el-option label="APT组织" value="apt" />
            <el-option label="攻击工具" value="tool" />
            <el-option label="漏洞" value="vuln" />
          </el-select>
        </el-form-item>
        <el-form-item label="英文核心名" prop="en_core">
          <el-input v-model="newEntityForm.en_core" placeholder="请输入英文核心名称" />
        </el-form-item>
        <el-form-item label="中文核心名" prop="zh_core">
          <el-input v-model="newEntityForm.zh_core" placeholder="请输入中文核心名称" />
        </el-form-item>
        <el-form-item label="英文别名">
          <el-input 
            v-model="newEntityForm.en_variants" 
            placeholder="多个别名用逗号分隔"
          />
        </el-form-item>
        <el-form-item label="中文别名">
          <el-input 
            v-model="newEntityForm.zh_variants" 
            placeholder="多个别名用逗号分隔"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="newEntityForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请添加描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="correctDialogVisible = false">取消</el-button>
        <el-button
          type="success"
          @click="handleConfirmAddNewEntity"
          :loading="addEntityLoading"
        >
          确认添加
        </el-button>
      </template>
    </el-dialog>

    <!-- 批量新增实体对话框 -->
    <el-dialog
      v-model="batchAddDialogVisible"
      title="批量实体创建"
      width="800px"
      :close-on-click-modal="false"
    >
      <el-table :data="batchAddEntityList" border stripe max-height="400">
        <el-table-column prop="matched_text" label="匹配文本" width="200" />
        <el-table-column prop="entity_type" label="类型" width="120">
           <template #default="{ row, $index }">
              <el-select v-model="batchAddEntityList[$index].entity_type" size="small">
                 <el-option label="APT" value="apt" />
                 <el-option label="Tool" value="tool" />
                 <el-option label="Vuln" value="vuln" />
              </el-select>
           </template>
        </el-table-column>
        <el-table-column prop="en_core" label="英文核心名" min-width="180">
            <template #default="{ row, $index }">
               <el-input v-model="batchAddEntityList[$index].en_core" size="small" />
            </template>
        </el-table-column>
        <el-table-column prop="zh_core" label="中文核心名" min-width="180">
            <template #default="{ row, $index }">
               <el-input v-model="batchAddEntityList[$index].zh_core" size="small" />
            </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
           <template #default="{ row, $index }">
              <el-button type="danger" size="small" @click="handleRemoveBatchEntity($index)"><el-icon><Delete /></el-icon></el-button>
           </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="batchAddDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConfirmBatchAdd" :loading="batchAddLoading">
          确认批量 ({{ batchAddEntityList.length }})
        </el-button>
      </template>
    </el-dialog>
    <!-- 文本选择右键菜单 -->
    <div
      v-if="selectionMenuVisible"
      class="selection-context-menu"
      :style="{ top: selectionMenuPosition.top + 'px', left: selectionMenuPosition.left + 'px' }"
      @mousedown.stop
    >
      <div class="menu-item" @click="handleAddEntityFromSelection">
        <el-icon><Plus /></el-icon> 新增实体
      </div>
      <div class="menu-item" @click="handleAddAliasFromSelection">
        <el-icon><Connection /></el-icon> 添加别名
      </div>
    </div>
    <!-- 实体详情卡片 (Hacker Style) -->
    <el-dialog
      v-model="detailDialogVisible"
      :show-close="false"
      width="400px"
      class="hacker-detail-dialog"
      :modal="true"
      append-to-body
    >
      <div class="hacker-card">
        <div class="card-header">
          <span class="header-decoration left"></span>
          <span class="header-title">>> ENTITY_DETECTED</span>
          <span class="header-decoration right"></span>
        </div>
        
        <div class="card-body" v-if="currentDetailEntity">
           <div class="info-row highlight-row">
             <label>MATCHED:</label>
             <div class="value glitch-text">{{ currentDetailEntity.matched_text }}</div>
           </div>
           
           <div class="info-grid">
             <div class="info-item">
               <label>ID:</label>
               <div class="value code-font">{{ currentDetailEntity.entity_id }}</div>
             </div>
             <div class="info-item">
               <label>TYPE:</label>
               <div class="value">
                 <span :class="['type-tag', currentDetailEntity.entity_type]">
                   {{ currentDetailEntity.entity_type.toUpperCase() }}
                 </span>
               </div>
             </div>
           </div>

           <div class="info-row">
             <label>CORE_NAME (EN):</label>
             <div class="value">{{ currentDetailEntity.en_core }}</div>
           </div>
           <div class="info-row">
             <label>CORE_NAME (ZH):</label>
             <div class="value">{{ currentDetailEntity.zh_core }}</div>
           </div>

           <div class="info-row">
             <label>CONFIDENCE:</label>
             <div class="value confidence-wrapper">
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: (currentDetailEntity.confidence * 100) + '%' }"></div>
                </div>
                <span class="confidence-text">{{ (currentDetailEntity.confidence * 100).toFixed(1) }}%</span>
             </div>
           </div>
           
           <div class="info-row description-row">
             <label>DESCRIPTION:</label>
             <div class="value scrollable">{{ currentDetailEntity.description || 'NO_DATA' }}</div>
           </div>
        </div>
        
        <div class="card-footer">
          <button class="hacker-btn danger" @click="handleDeleteMatchFromDetail">
            <span class="btn-text">DELETE_MATCH</span>
            <span class="btn-glitch"></span>
          </button>
          <button class="hacker-btn primary" @click="detailDialogVisible = false">
            <span class="btn-text">CLOSE</span>
          </button>
        </div>
        
        <!-- Corner Decorations -->
        <div class="corner top-left"></div>
        <div class="corner top-right"></div>
        <div class="corner bottom-left"></div>
        <div class="corner bottom-right"></div>
      </div>
    </el-dialog>

    <!-- 快捷添加别名对话框 -->
    <el-dialog
      v-model="addAliasDialogVisible"
      title="添加别名"
      width="600px"
    >
      <el-form :model="addAliasForm" label-width="100px">
        <el-form-item label="待添加别名">
          <el-input v-model="addAliasForm.aliasText" disabled />
        </el-form-item>
        <el-form-item label="目标实体">
           <el-select
            v-model="addAliasForm.targetEntityId"
            filterable
            remote
            :remote-method="fetchEntities"
            :loading="searchLoading"
            placeholder="请输入名称搜索实体"
            style="width: 100%"
            @change="handleTargetEntityChange"
          >
            <el-option
              v-for="item in entityOptions"
              :key="item.entity_id"
              :label="`${item.en_core} / ${item.zh_core} (${item.entity_id})`"
              :value="item.entity_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="别名类型">
          <el-radio-group v-model="addAliasForm.aliasType">
            <el-radio label="en">英文变体</el-radio>
            <el-radio label="zh">中文变体</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addAliasDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddAlias" :loading="addAliasLoading">确认添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* 右键菜单 - Hacker Style */
.selection-context-menu {
  position: fixed;
  z-index: 9999;
  background: var(--bg-tertiary);
  border: 1px solid var(--primary-color);
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.5);
  padding: 4px 0;
  border-radius: 0;
  min-width: 130px;
  backdrop-filter: blur(4px);
}

.menu-item {
  padding: 8px 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-primary);
  transition: all 0.2s;
  font-family: var(--font-mono);
}

.menu-item:hover {
  background-color: rgba(51, 153, 255, 0.2);
  color: var(--primary-color);
  padding-left: 20px; /* 动效 */
}

.menu-item .el-icon {
  font-size: 14px;
}
</style>
<script setup>
import { ref, reactive, watch, nextTick, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search,
  Delete,
  Setting,
  Tools,
  Upload,
  UploadFilled,
  Plus,
  Edit,
  Refresh,
  Download,
  Document,
  Close,
  CircleCheck,
  CircleClose
} from '@element-plus/icons-vue'
import { initAlgorithm, singleTextAlign, setThreshold, uploadFileAlign, correctEntity } from '@/api/align'
import { queryEntity, addEntity, updateEntity, batchAddEntities } from '@/api/dict'

// 数据
const initLoading = ref(false)
const alignLoading = ref(false)
const batchAlignLoading = ref(false) // 批量对齐加载状态
const alignResult = ref([])
const processTime = ref(0)

// 计算属性：过滤掉失败的匹配结果
const filteredAlignResult = computed(() => {
  return alignResult.value.filter(result => result.match_type !== 'fail')
})
const thresholdDialogVisible = ref(false)
const thresholdLoading = ref(false)
const inputTab = ref('text')
const resultTab = ref('highlight')
const highlightedText = ref('')
const originalText = ref('')
const fileUploadLoading = ref(false)
const exportLoading = ref(false) // PDF导出加载状态
const uploadRef = ref(null)
const uploadFile = ref(null)
// uploadFileList 已被 uploadedFiles 替代
const uploadedFiles = ref([]) // 已上传的文件列表
const currentFile = ref(null) // 当前选中的文件
const currentFileType = ref('text') // 当前文件类型：'text' 或 'file'
const currentFileContent = ref('') // 当前文件内容
const fileInputRef = ref(null) // 文件输入引用
const selectedFiles = ref([]) // 选中的文件列表（用于批量对齐）
const correctDialogVisible = ref(false)
const correctLoading = ref(false)
const entityOptions = ref([])
const selectedEntities = ref([]) // 选中的实体
const correctTab = ref('existing') // 修正对话框标签页
const batchAddDialogVisible = ref(false) // 批量新增对话框
const batchAddLoading = ref(false) // 批量新增加载状态
const batchAddEntityList = ref([]) // 批量新增实体列表
const addEntityLoading = ref(false) // 新增实体加载状态
const newEntityFormRef = ref(null) // 新增实体表单引用

// 新增功能状态
const detailDialogVisible = ref(false)
const currentDetailEntity = ref(null)
const addAliasDialogVisible = ref(false)
const addAliasLoading = ref(false)
const searchLoading = ref(false)
const addAliasForm = reactive({
  aliasText: '',
  targetEntityId: '',
  aliasType: 'en' // en 或 zh
})

// 对齐表单
const alignForm = reactive({
  text: '',
  entity_categories: ['apt', 'tool', 'vuln'],
  confidence_threshold: 0.0 // 置信度过滤阈值
})

// 修正表单
const correctForm = reactive({
  original_text: '',
  current_entity_id: '',
  corrected_entity_id: '',
  add_to_variants: true,
  align_result_id: ''
})

// 阈值设置表单
const thresholdForm = reactive({
  levenshtein_thresh: 0.8,
  semantic_thresh: 0.75,
  confidence_thresh: 0.0 // 置信度过滤阈值
})

// 实体类别配置
const entityCategories = [
  { label: 'APT', value: 'apt' },
  { label: 'TOOL', value: 'tool' },
  { label: 'VULN', value: 'vuln' }
]

// 切换实体类别
const handleToggleCategory = (value) => {
  const index = alignForm.entity_categories.indexOf(value)
  if (index > -1) {
    // 已存在,移除
    alignForm.entity_categories.splice(index, 1)
  } else {
    // 不存在,添加
    alignForm.entity_categories.push(value)
  }
  console.log('切换后的实体类别:', alignForm.entity_categories)
}

// 新增实体表单
const newEntityForm = reactive({
  entity_type: 'apt',
  en_core: '',
  zh_core: '',
  en_variants: '',
  zh_variants: '',
  description: '',
  add_original_as_variant: true
})

// 新增实体表单验证规则
const newEntityRules = {
  entity_type: [{ required: true, message: '请选择实体类型', trigger: 'change' }],
  en_core: [{ required: true, message: '请输入英文核心名称', trigger: 'blur' }],
  zh_core: [{ required: true, message: '请输入中文核心名称', trigger: 'blur' }]
}

// 初始化算法
const handleInitAlgorithm = async () => {
  initLoading.value = true
  try {
    const response = await initAlgorithm({
      levenshtein_thresh: thresholdForm.levenshtein_thresh,
      semantic_thresh: thresholdForm.semantic_thresh
    })
    
    // 响应拦截器已经返回了 data 部分，所以直接检查 success
    if (response && response.success) {
      ElMessage.success('算法初始化成功')
    } else {
      ElMessage.error(response?.error_msg || '算法初始化失败')
    }
  } catch (error) {
    console.error('初始化算法失败:', error)
    ElMessage.error(error.message || '算法初始化失败')
  } finally {
    initLoading.value = false
  }
}

// 执行对齐
const handleAlign = async () => {
  if (!alignForm.text.trim()) {
    ElMessage.warning('请输入文本内容')
    return
  }

  if (alignForm.entity_categories.length === 0) {
    ElMessage.warning('请至少选择一个实体类别')
    return
  }

  alignLoading.value = true
  try {
      // 统一文本格式（与文件读取保持一致）
      let processedText = alignForm.text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      originalText.value = processedText

      const response = await singleTextAlign({
        text_chunk: {
        text: processedText
        },
      entity_categories: alignForm.entity_categories
      })

    // 响应拦截器已经返回了 data 部分
      if (response) {
        console.log('直接文本对齐API响应:', response)
        console.log('匹配结果数量:', response.align_result ? response.align_result.length : 0)
        console.log('匹配结果详情:', response.align_result)

        alignResult.value = response.align_result || []
        processTime.value = response.process_time || 0

      // 应用置信度过滤
      applyConfidenceFilter()
      
      // 生成高亮文本
        generateHighlightedText()

        if (alignResult.value.length === 0) {
          ElMessage.info('未找到匹配的实体')
        } else {
          ElMessage.success(`成功对齐 ${alignResult.value.length} 个实体`)
      }
    } else {
      ElMessage.error('对齐失败')
      alignResult.value = []
      processTime.value = 0
      highlightedText.value = ''
    }
  } catch (error) {
    console.error('对齐失败:', error)
    ElMessage.error(error.message || '对齐失败')
    alignResult.value = []
    processTime.value = 0
  } finally {
    alignLoading.value = false
  }
}

// 清空
const handleClear = () => {
  alignForm.text = ''
  alignResult.value = []
  processTime.value = 0
  highlightedText.value = ''
  originalText.value = ''
}

// 实体类别选择变化处理
const handleEntityCategoryChange = (value) => {
  console.log('实体类别选择变化:', value)
  console.log('变化后的类型:', typeof value)
  console.log('是否为数组:', Array.isArray(value))
  // 确保值是数组格式
  if (!Array.isArray(value)) {
    console.warn('实体类别不是数组格式，强制转换为数组')
    alignForm.entity_categories = value ? [value] : []
  } else {
    alignForm.entity_categories = value
  }
  console.log('更新后的 alignForm.entity_categories:', alignForm.entity_categories)
}

// 文件上传处理（支持批量）
const handleFileChange = (file, fileList) => {
  // 如果是批量上传模式
  if (inputTab.value === 'file') {
    // 更新文件列表
    // 已不再使用 uploadFileList
  } else {
    // 单文件模式（兼容旧代码）
    uploadFile.value = file.raw
  }
}

const handleFileRemove = (file, fileList) => {
  if (inputTab.value === 'file') {
    // 批量模式：更新文件列表
    // 已不再使用 uploadFileList
  } else {
    // 单文件模式
    uploadFile.value = null
  }
  if (uploadRef.value && fileList.length === 0) {
    uploadRef.value.clearFiles()
  }
}

// 应用置信度过滤
const applyConfidenceFilter = () => {
  if (alignForm.confidence_threshold > 0) {
    alignResult.value = alignResult.value.filter(result =>
      result.confidence >= alignForm.confidence_threshold
    )
  }
}

// 导入文件
const handleImportFile = () => {
  if (fileInputRef.value) {
    fileInputRef.value.click()
  }
}

// 文件输入变化处理
const handleFileInputChange = async (event) => {
  const files = Array.from(event.target.files)
  if (files.length === 0) return

  for (const file of files) {
    // 检查文件类型
    const lowerName = file.name.toLowerCase()
    const supportedExts = ['.json', '.txt', '.pdf', '.doc', '.docx']
    const isSupported = supportedExts.some(ext => lowerName.endsWith(ext))
    if (!isSupported) {
      ElMessage.warning(`文件 ${file.name} 格式不支持，仅支持 JSON/TXT/PDF/DOC/DOCX 格式`)
      continue
    }

    // 检查文件大小（限制 10MB）
    const maxSize = 10 * 1024 * 1024
    if (file.size > maxSize) {
      ElMessage.warning(`文件 ${file.name} 太大，请选择小于 10MB 的文件`)
      continue
    }

    // 检查是否已存在
    const exists = uploadedFiles.value.some(f => f.name === file.name && f.size === file.size)
    if (exists) {
      ElMessage.warning(`文件 ${file.name} 已存在`)
      continue
    }

    // 添加到上传文件列表
    uploadedFiles.value.push(file)
  }

  // 清空文件输入
  if (fileInputRef.value) {
    fileInputRef.value.value = ''
  }

  ElMessage.success(`成功导入 ${files.length} 个文件`)
}

// 选择文本输入
const handleSelectTextInput = () => {
  currentFileType.value = 'text'
  currentFile.value = null
  currentFileContent.value = ''
}

// 选择文件
const handleSelectFile = async (file) => {
  currentFileType.value = 'file'
  currentFile.value = file

  const lowerName = file.name.toLowerCase()
  const isTextLike = lowerName.endsWith('.json') || lowerName.endsWith('.txt')

  // 仅对文本类文件做前端预览，二进制文档给出提示
  if (!isTextLike) {
    currentFileContent.value = `[${file.name}] 为二进制文档，前端不直接预览内容。\n请点击“执行对齐”，由后端解析后处理。`
    return
  }

  try {
    const text = await readFileAsText(file)
    currentFileContent.value = text
  } catch (error) {
    console.error('读取文件失败:', error)
    currentFileContent.value = `读取文件失败: ${error.message}`
  }
}

// 读取文件为文本
const readFileAsText = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      let text = e.target.result
      // 统一换行符为 \n
      text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n')
      // 移除可能的BOM
      if (text.charCodeAt(0) === 0xFEFF) {
        text = text.slice(1)
      }
      resolve(text)
    }
    reader.onerror = (e) => reject(new Error('文件读取失败'))
    reader.readAsText(file, 'UTF-8')
  })
}

// 处理文件选择变化
const handleFileSelectionChange = (fileName, checked) => {
  if (checked) {
    if (!selectedFiles.value.includes(fileName)) {
      selectedFiles.value.push(fileName)
  }
    } else {
    const index = selectedFiles.value.indexOf(fileName)
    if (index > -1) {
      selectedFiles.value.splice(index, 1)
    }
  }
}

// 全选文件
const handleSelectAll = () => {
  selectedFiles.value = uploadedFiles.value.map(f => f.name)
  ElMessage.success('已全选所有文件')
}

// 清空选择
const handleClearSelection = () => {
  selectedFiles.value = []
  ElMessage.success('已清空选择')
}

// 对当前文件进行对齐
const handleAlignCurrent = async () => {
  if (currentFileType.value === 'text') {
    // 文本对齐
    await handleAlign()
  } else if (currentFile.value) {
    // 文件对齐
    await handleSingleFileAlign(currentFile.value)
  } else {
    ElMessage.warning('请选择要对齐的内容')
  }
}


// 切换到编辑模式
const switchToEditMode = () => {
  // 确保文本内容与原始输入一致
  alignForm.text = originalText.value
    alignResult.value = []
    highlightedText.value = ''
  processTime.value = 0
  ElMessage.info('已切换到编辑模式，可以重新输入文本')
}

// 对单个文件进行对齐
const handleSingleFileAlign = async (file) => {
  if (!file) {
    ElMessage.warning('请选择文件')
    return
  }

  if (alignForm.entity_categories.length === 0) {
    ElMessage.warning('请至少选择一个实体类别')
    return
  }

  // 调试：打印实际传递的实体类别
  console.log('前端传递的实体类别:', alignForm.entity_categories)
  console.log('实体类别类型:', typeof alignForm.entity_categories)
  console.log('是否为数组:', Array.isArray(alignForm.entity_categories))

  alignLoading.value = true
  try {
    let response
    // 所有文件都使用统一的上传对齐API
    response = await uploadFileAlign(file, alignForm.entity_categories)

    if (response) {
      console.log('文件对齐API响应:', response)
      console.log('匹配结果数量:', response.align_result ? response.align_result.length : 0)
      console.log('匹配结果详情:', response.align_result)

      alignResult.value = response.align_result || []
      processTime.value = response.process_time || 0

      // 统一使用后端返回的解析后完整文本（所有格式）
      originalText.value = response.original_text || currentFileContent.value

      // 应用置信度过滤
      applyConfidenceFilter()

      // 生成高亮文本
      generateHighlightedText()

      if (alignResult.value.length === 0) {
        ElMessage.info('未找到匹配的实体')
      } else {
        ElMessage.success(`成功对齐 ${alignResult.value.length} 个实体`)
      }
    } else {
      ElMessage.error('对齐失败')
    }
  } catch (error) {
    console.error('文件对齐失败:', error)
    ElMessage.error(error.message || '文件对齐失败')
  } finally {
    alignLoading.value = false
  }
}

// 批量对齐
const handleBatchAlign = async () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请先选择要对齐的文件')
    return
  }

  if (alignForm.entity_categories.length === 0) {
    ElMessage.warning('请至少选择一个实体类别')
    return
  }

  batchAlignLoading.value = true
  const allResults = []
  let totalProcessTime = 0
  let successCount = 0
  let failCount = 0

  try {
    for (let i = 0; i < selectedFiles.value.length; i++) {
      const fileName = selectedFiles.value[i]
      const file = uploadedFiles.value.find(f => f.name === fileName)

      if (!file) continue

      try {
        ElMessage.info(`正在对齐文件 ${i + 1}/${selectedFiles.value.length}: ${file.name}`)

        // 所有文件都使用统一的上传对齐API
        const response = await uploadFileAlign(file, alignForm.entity_categories)

        if (response) {
          console.log(`批量对齐文件 ${file.name} API响应:`, response)
          console.log(`匹配结果数量:`, response.align_result ? response.align_result.length : 0)
}

        if (response && response.align_result) {
          // 合并结果，添加文件来源标识
          const fileResults = response.align_result.map(result => ({
            ...result,
            source_file: file.name
          }))
          allResults.push(...fileResults)
          totalProcessTime += response.process_time || 0
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        console.error(`对齐文件 ${file.name} 失败:`, error)
        failCount++
        ElMessage.warning(`文件 ${file.name} 对齐失败: ${error.message || '未知错误'}`)
      }
}

    // 去重（按实体ID和匹配文本）
    const uniqueResults = []
    const seen = new Set()
    allResults.forEach(result => {
      const key = `${result.entity_id}_${result.matched_text}_${result.source_file}`
      if (!seen.has(key)) {
        seen.add(key)
        uniqueResults.push(result)
}
    })

    // 应用置信度过滤（与单个对齐保持一致）
    alignResult.value = uniqueResults
    applyConfidenceFilter()
    processTime.value = totalProcessTime

    // 生成高亮文本（显示统计信息）
    originalText.value = `批量对齐结果 - 处理 ${selectedFiles.value.length} 个文件`


    // 显示处理结果
    if (alignResult.value.length === 0) {
      ElMessage.info('未找到匹配的实体')
    } else {
      ElMessage.success(
        `批量对齐完成：成功 ${successCount} 个文件，失败 ${failCount} 个文件，共对齐 ${alignResult.value.length} 个实体`
      )
    }
  } catch (error) {
    console.error('批量对齐失败:', error)
    ElMessage.error(error.message || '批量对齐失败')
  } finally {
    batchAlignLoading.value = false
  }
}

const handleFileUpload = async () => {
  if (!uploadFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  fileUploadLoading.value = true
  try {
    // 所有文件都使用统一的上传对齐API
    const response = await uploadFileAlign(uploadFile.value, alignForm.entity_categories)
    
    if (response) {
      console.log('文件上传对齐API响应:', response)
      console.log('匹配结果数量:', response.align_result ? response.align_result.length : 0)
      console.log('匹配结果详情:', response.align_result)

      alignResult.value = response.align_result || []
      processTime.value = response.process_time || 0

      // 应用置信度过滤
      applyConfidenceFilter()
      
      // 应用置信度过滤
      applyConfidenceFilter()
      
      // 统一使用后端返回的解析后完整文本（所有格式）
      originalText.value = response.original_text || originalText.value
      generateHighlightedText()
      
      if (alignResult.value.length === 0) {
        ElMessage.info('未找到匹配的实体')
      } else {
        ElMessage.success(`成功对齐 ${alignResult.value.length} 个实体`)
        resultTab.value = 'highlight'
      }
    } else {
      ElMessage.error('文件对齐失败')
    }
  } catch (error) {
    console.error('文件上传失败:', error)
    ElMessage.error(error.message || '文件上传失败')
  } finally {
    fileUploadLoading.value = false
  }
}

// 1. 批量文件上传处理
const handleBatchFileUpload = async () => {
  if (uploadedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个文件')
    return
  }
  
  if (alignForm.entity_categories.length === 0) {
    ElMessage.warning('请至少选择一个实体类别')
    return
  }
  
  fileUploadLoading.value = true
  const allResults = []
  let totalProcessTime = 0
  let successCount = 0
  let failCount = 0
  
  try {
    // 逐个处理文件
    for (let i = 0; i < uploadedFiles.value.length; i++) {
      const file = uploadedFiles.value[i]
      try {
        ElMessage.info(`正在处理文件 ${i + 1}/${uploadedFiles.value.length}: ${file.name}`)

        // 所有文件都使用统一的上传对齐API
        const response = await uploadFileAlign(file, alignForm.entity_categories)
        
        if (response && response.align_result) {
          // 合并结果，添加文件来源标识
          const fileResults = response.align_result.map(result => ({
            ...result,
            source_file: file.name
          }))
          allResults.push(...fileResults)
          totalProcessTime += response.process_time || 0
          successCount++
        } else {
          failCount++
        }
      } catch (error) {
        console.error(`处理文件 ${file.name} 失败:`, error)
        failCount++
        ElMessage.warning(`文件 ${file.name} 处理失败: ${error.message || '未知错误'}`)
      }
}

    // 去重（按实体ID和匹配文本）
    const uniqueResults = []
    const seen = new Set()
    allResults.forEach(result => {
      const key = `${result.entity_id}_${result.matched_text}`
      if (!seen.has(key)) {
        seen.add(key)
        uniqueResults.push(result)
      }
    })
    
    // 应用置信度过滤
    alignResult.value = uniqueResults.filter(result => 
      result.confidence >= alignForm.confidence_threshold
    )
    processTime.value = totalProcessTime
    
    // 生成高亮文本（使用第一个文件的内容作为示例）
    if (uploadedFiles.value.length > 0) {
      originalText.value = `批量处理 ${uploadedFiles.value.length} 个文件，共找到 ${uniqueResults.length} 个实体`
    }
    generateHighlightedText()
    
    // 显示处理结果
    if (alignResult.value.length === 0) {
      ElMessage.info('未找到匹配的实体')
    } else {
      ElMessage.success(
        `批量处理完成：成功 ${successCount} 个文件，失败 ${failCount} 个文件，共对齐 ${alignResult.value.length} 个实体`
      )
      resultTab.value = 'highlight'
    }
  } catch (error) {
    console.error('批量文件上传失败:', error)
    ElMessage.error(error.message || '批量文件上传失败')
  } finally {
    fileUploadLoading.value = false
  }
  }

// 2. 清空所有文件
const handleClearAllFiles = () => {
  // 已不再使用 uploadFileList
  uploadFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  ElMessage.success('已清空所有文件')
  }

// 3. 移除单个文件
const handleRemoveFile = (index) => {
  if (index >= 0 && index < uploadedFiles.value.length) {
    const fileName = uploadedFiles.value[index].name
    uploadedFiles.value.splice(index, 1)
    ElMessage.success(`已移除文件: ${fileName}`)
  }
}

// 4. 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes || bytes === 0) return '0 B'
  
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// 5. 获取匹配类型数量
const getMatchTypeCount = (matchType) => {
  return filteredAlignResult.value.filter(result => result.match_type === matchType).length
}

// 获取实体类型数量
const getEntityTypeCount = (entityType) => {
  return filteredAlignResult.value.filter(result => result.entity_type === entityType).length
}

// 获取平均置信度
const getAverageConfidence = () => {
  if (filteredAlignResult.value.length === 0) return 0
  const sum = filteredAlignResult.value.reduce((acc, result) => acc + (result.confidence || 0), 0)
  return Math.round((sum / filteredAlignResult.value.length) * 100)
}


// 生成高亮文本
const generateHighlightedText = () => {
  const text = originalText.value || alignForm.text || ''
  
  if (!text || filteredAlignResult.value.length === 0) {
    highlightedText.value = text
    return
  }
  
  console.log('generateHighlightedText: 处理', filteredAlignResult.value.length, '个匹配结果')
  
  // 使用位置信息构建高亮
  const highlights = []
  const notFound = []
  
  for (const result of filteredAlignResult.value) {
    
    // 检查是否有位置信息
    if (result.start_pos !== undefined && result.start_pos >= 0 && result.end_pos >= 0) {
      // 使用后端返回的精确位置
      highlights.push({
        start: result.start_pos,
        end: result.end_pos,
        text: text.substring(result.start_pos, result.end_pos),
        entityId: result.entity_id,
        entityType: result.entity_type,
        matchType: result.match_type,
        confidence: result.confidence,
        length: result.end_pos - result.start_pos
      })
    } else {
      // 兼容旧数据：没有位置信息，尝试查找
      const matchedText = result.matched_text
      const lowerText = text.toLowerCase()
      const lowerMatch = matchedText.toLowerCase()
      const start = lowerText.indexOf(lowerMatch)
      
      if (start !== -1) {
        const end = start + matchedText.length
        highlights.push({
          start,
          end,
          text: text.substring(start, end),
          entityId: result.entity_id,
          entityType: result.entity_type,
          matchType: result.match_type,
          confidence: result.confidence,
          length: end - start
        })
      } else {
        notFound.push({
          matchedText,
          entityId: result.entity_id
        })
      }
    }
  }
  
  if (notFound.length > 0) {
    console.warn('以下匹配结果在原文中未找到:', notFound)
  }
  
  // 按优先级排序：长度降序 > 置信度降序 > 位置升序
  highlights.sort((a, b) => {
    if (a.length !== b.length) return b.length - a.length
    if (a.confidence !== b.confidence) return b.confidence - a.confidence
    return a.start - b.start
  })
  
  // 贪心选择（避免重叠）
  const selected = []
  const occupied = new Array(text.length).fill(false)
  
  for (const h of highlights) {
    // 检查是否与已选择的位置重叠
    let hasOverlap = false
    for (let i = h.start; i < h.end; i++) {
      if (occupied[i]) {
        hasOverlap = true
        break
      }
    }
    
    if (!hasOverlap) {
      // 标记占用
      for (let i = h.start; i < h.end; i++) {
        occupied[i] = true
      }
      selected.push(h)
    }
  }
  
  // 按位置排序用于HTML生成
  selected.sort((a, b) => a.start - b.start)
  
  // 生成HTML
  let html = ''
  let lastEnd = 0
  
  for (const highlight of selected) {
    // 添加普通文本
    html += escapeHtml(text.substring(lastEnd, highlight.start))
    
    // 添加高亮HTML
    const entityTypeShort = highlight.entityType === 'apt' ? 'apt' : (highlight.entityType === 'tool' ? 'tool' : 'vuln')
    const highlightClass = `${entityTypeShort}-${highlight.matchType}`
    const tooltip = `${highlight.entityId} (${getEntityTypeName(highlight.entityType)} - ${getMatchTypeName(highlight.matchType)}, ${(highlight.confidence * 100).toFixed(1)}%)`
    const escapedTooltip = tooltip.replace(/"/g, '&quot;').replace(/'/g, '&#39;')
    html += `<span class="entity-highlight ${highlightClass}" title="${escapedTooltip}" data-entity-id="${highlight.entityId}" data-entity-type="${highlight.entityType}" data-match-type="${highlight.matchType}">${escapeHtml(highlight.text)}</span>`
    
    lastEnd = highlight.end
  }
  
  // 添加剩余文本
  html += escapeHtml(text.substring(lastEnd))
  highlightedText.value = html
}

// HTML转义辅助函数
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}


// 转义正则表达式特殊字符
const escapeRegExp = (string) => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

// 获取匹配类型颜色
const getMatchTypeColor = (type) => {
  const map = {
    exact: 'rgba(103, 194, 58, 0.3)',
    fuzzy: 'rgba(230, 162, 60, 0.3)',
    semantic: 'rgba(144, 147, 153, 0.3)'
  }
  return map[type] || 'rgba(144, 147, 153, 0.3)'
}

// 修正实体
const handleCorrect = (row) => {
  correctForm.original_text = row.matched_text
  correctForm.current_entity_id = row.entity_id
  correctForm.corrected_entity_id = ''
  correctForm.align_result_id = row.entity_id + '_' + row.matched_text
  correctDialogVisible.value = true
}

// 搜索实体
const searchEntities = async (query) => {
  if (!query) {
    entityOptions.value = []
    return
  }
  
  try {
    // 搜索所有类型的实体
    const results = []
    for (const type of ['apt', 'tool', 'vuln']) {
      const response = await queryEntity({ keyword: query, entity_type: type })
      // 响应拦截器返回的是 data 部分，格式为 {entity_list: [], count: 0}
      if (response && response.entity_list) {
        results.push(...response.entity_list)
      }
    }
    entityOptions.value = results.slice(0, 20)  // 限制显示数量
  } catch (error) {
    console.error('搜索实体失败:', error)
    entityOptions.value = []
  }
}

// 确认修正
const handleConfirmCorrect = async () => {
  if (!correctForm.corrected_entity_id) {
    ElMessage.warning('请选择要修正的实体')
    return
  }
  
  correctLoading.value = true
  try {
    const response = await correctEntity({
      original_text: correctForm.original_text,
      corrected_entity_id: correctForm.corrected_entity_id,
      align_result_id: correctForm.align_result_id,
      add_to_variants: correctForm.add_to_variants
    })
    
    if (response && response.success) {
      ElMessage.success('修正成功，词典已自动更新')
      correctDialogVisible.value = false

      // 重新生成高亮文本
      generateHighlightedText()
    } else {
      ElMessage.error('修正失败')
    }
  } catch (error) {
    console.error('修正失败:', error)
    ElMessage.error(error.message || '修正失败')
  } finally {
    correctLoading.value = false
  }
}

// 删除匹配
const handleDeleteMatch = async () => {
  try {
    await ElMessageBox.confirm('确定要删除这个匹配吗？', '提示', {
      type: 'warning'
    })
    
    // 从结果中移除
    const index = alignResult.value.findIndex(r => 
      r.entity_id === correctForm.current_entity_id && 
      r.matched_text === correctForm.original_text
    )
    if (index > -1) {
      alignResult.value.splice(index, 1)
      generateHighlightedText()
      ElMessage.success('匹配已删除')
      correctDialogVisible.value = false
    }
  } catch {
    // 用户取消
  }
}

// 监听结果标签页变化，切换到图谱时初始化
watch(resultTab, (newTab) => {
  if (newTab === 'graph') {
    nextTick(() => {
      initGraph()
    })
  }
})

// 初始化关联图谱
const initGraph = () => {
  // 这里使用简单的可视化，实际可以使用 D3.js 或 vis.js
  const container = document.getElementById('graph-container')
  if (!container) return

  container.innerHTML = '<div class="graph-placeholder">关联图谱功能开发中，将显示实体之间的关系网络</div>'

  // TODO: 实现关联图谱可视化
  // 可以使用 D3.js, vis.js 或 ECharts 等库
}

// 6. 处理表格选择变化
const handleSelectionChange = (selection) => {
  selectedEntities.value = selection
}

// 7. 批量新增实体
const handleBatchAddEntities = () => {
  if (selectedEntities.value.length === 0) {
    ElMessage.warning('请先选择要新增的实体')
    return
  }

  // 从选中的结果中提取实体信息
  batchAddEntityList.value = selectedEntities.value.map(result => ({
    matched_text: result.matched_text,
    entity_type: result.entity_type,
    en_core: result.matched_text, // 默认使用匹配文本作为核心名称
    zh_core: result.matched_text,
    en_variants: '',
    zh_variants: '',
    description: `从对齐结果提取，匹配类型：${getMatchTypeName(result.match_type)}，置信度：${(result.confidence * 100).toFixed(1)}%`
  }))

  batchAddDialogVisible.value = true
}

// 8. 从结果新增实体
const handleAddEntityFromResult = (row) => {
  // 预填充新实体表单
  newEntityForm.entity_type = row.entity_type
  newEntityForm.en_core = row.matched_text
  newEntityForm.zh_core = row.matched_text
  newEntityForm.en_variants = ''
  newEntityForm.zh_variants = ''
  newEntityForm.description = `从对齐结果提取，匹配类型：${getMatchTypeName(row.match_type)}，置信度：${(row.confidence * 100).toFixed(1)}%`
  newEntityForm.add_original_as_variant = false

  // 切换到新增实体标签页
  correctTab.value = 'new'
  correctDialogVisible.value = true
}

// 9. 确认新增实体
const handleConfirmAddNewEntity = async () => {
  if (!newEntityFormRef.value) return

  await newEntityFormRef.value.validate(async (valid) => {
    if (!valid) return

    addEntityLoading.value = true
    try {
      // 处理变体（过滤空字符串，且排除与核心名相同的值）
      const enVariants = newEntityForm.en_variants
        ? newEntityForm.en_variants.split(',').map(v => v.trim()).filter(v => v && v !== newEntityForm.en_core)
        : []
      const zhVariants = newEntityForm.zh_variants
        ? newEntityForm.zh_variants.split(',').map(v => v.trim()).filter(v => v && v !== newEntityForm.zh_core)
        : []

      const entityData = {
        entity_type: newEntityForm.entity_type,
        entity_data: {
          en_core: newEntityForm.en_core,
          zh_core: newEntityForm.zh_core,
          en_variants: enVariants,
          zh_variants: zhVariants,
          description: newEntityForm.description || null
        }
      }

      const response = await addEntity(entityData)

      if (response && response.entity_id) {
        ElMessage.success(`实体 ${response.entity_id} 新增成功`)
        correctDialogVisible.value = false

        // 添加高亮匹配
        const matchText = selectedTextContent.value || newEntityForm.en_core
        const textToSearch = originalText.value || alignForm.text || ''
        
 
        
        if (matchText && textToSearch.includes(matchText)) {
          console.log('✅ 条件满足，调用 addHighlightMatch')
          addHighlightMatch(
            response.entity_id,
            newEntityForm.entity_type,
            matchText,
            newEntityForm.en_core,
            newEntityForm.zh_core,
            newEntityForm.description
          )
        } else {
          console.log('❌ 条件不满足，仅刷新高亮')
          // 即使不在当前文本中，也需要重新生成高亮（刷新显示）
          generateHighlightedText()
        }

        // 重置表单
        resetNewEntityForm()
      } else {
        ElMessage.error('新增实体失败')
      }
    } catch (error) {
      console.error('新增实体失败:', error)
      ElMessage.error(error.message || '新增实体失败')
    } finally {
      addEntityLoading.value = false
    }
  })
}

// 10. 处理新实体英文名称输入
const handleNewEntityEnCoreInput = (value) => {
  // 如果中文核心名称为空，则自动填充与英文相同的内容
  if (!newEntityForm.zh_core || newEntityForm.zh_core === newEntityForm.en_core) {
    newEntityForm.zh_core = value
  }
}

// 11. 刷新图谱
const handleRefreshGraph = () => {
  ElMessage.info('正在刷新关联图谱...')

  // 重新初始化图谱
  nextTick(() => {
    initGraph()
  })

  ElMessage.success('图谱已刷新')
}

// 12. 导出图谱
const handleExportGraph = () => {
  const container = document.getElementById('graph-container')
  if (!container) {
    ElMessage.warning('图谱容器不存在')
    return
  }

  try {
    // 这里可以实现导出功能，暂时显示提示
    ElMessage.info('导出功能开发中，实际可以使用 html2canvas 或类似库导出图片')

    // 示例代码（如果使用 html2canvas）：
    // import html2canvas from 'html2canvas'
    // html2canvas(container).then(canvas => {
    //   const link = document.createElement('a')
    //   link.download = 'entity-graph.png'
    //   link.href = canvas.toDataURL()
    //   link.click()
    // })
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  }
}

// 13. 重置阈值
const handleResetThreshold = () => {
  thresholdForm.levenshtein_thresh = 0.8
  thresholdForm.semantic_thresh = 0.75
  thresholdForm.confidence_thresh = 0.0

  ElMessage.success('已重置为默认值')
}

// 14. 应用阈值到表单
const handleApplyThresholdToForm = () => {
  alignForm.confidence_threshold = thresholdForm.confidence_thresh

  // 重新应用置信度过滤
  if (alignResult.value.length > 0) {
    applyConfidenceFilter()
    generateHighlightedText()
  }

  ElMessage.success('阈值已应用到当前表单')
}

// 15. 移除批量实体
// 更新批量实体字段
const updateBatchEntityField = (index, field, value) => {
  if (index >= 0 && index < batchAddEntityList.value.length) {
    batchAddEntityList.value[index][field] = value
    // 强制触发响应式更新
    batchAddEntityList.value = [...batchAddEntityList.value]
  }
}

// 导出PDF：使用 html2pdf.js，直接将高亮区域转换为PDF，支持中文和样式
const handleExportPdf = async () => {
  if (!highlightedText.value || alignResult.value.length === 0) {
    ElMessage.warning('没有可导出的高亮结果')
    return
  }

  exportLoading.value = true
  try {
    const { jsPDF } = await import('jspdf')
    const html2canvas = (await import('html2canvas')).default

    // 创建PDF专用的HTML内容，包含详细信息
    const pdfContent = createPDFContent()
    
    // 创建临时DOM元素
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = pdfContent
    
    // 关键样式配置
    tempDiv.style.width = '794px' // A4 宽度 (96DPI)
    tempDiv.style.padding = '20px'
    // 必须使用系统字体以确保显示正常
    tempDiv.style.fontFamily = '"PingFang SC", "Microsoft YaHei", "SimHei", Arial, sans-serif'
    tempDiv.style.lineHeight = '1.6'
    tempDiv.style.backgroundColor = '#ffffff'
    tempDiv.style.boxSizing = 'border-box'
    
    // 定位策略：绝对定位，确保不占位但可渲染
    tempDiv.style.position = 'absolute'
    tempDiv.style.left = '0'
    tempDiv.style.top = '0'
    tempDiv.style.zIndex = '-9999'
    
    document.body.appendChild(tempDiv)

    // 等待图片等资源加载
    await nextTick()
    // 等待较长时间确保渲染完成（特别是表格较长时）
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 获取完整高度
    const fullHeight = tempDiv.scrollHeight
    console.log('PDF 内容总高度:', fullHeight)

    // 创建 PDF
    const pdf = new jsPDF({
      orientation: 'p',
      unit: 'pt',
      format: 'a4',
      compress: true
    })

    const pageWidth = 595.28
    const pageHeight = 841.89
    const contentWidth = 555.28 // pageWidth - 20pt margin * 2

    // 生成 Canvas
    const canvas = await html2canvas(tempDiv, {
      scale: 2, // 提高清晰度
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#ffffff',
      height: fullHeight, // 强制完整高度
      windowHeight: fullHeight + 100, // 确保视口足够大
      scrollY: 0,
      scrollX: 0
    })

    const contentHeight = canvas.height * (contentWidth / canvas.width)
    let leftHeight = contentHeight
    let position = 20 // 顶部边距
    const imgWidth = contentWidth
    const imgHeight = (canvas.height * contentWidth) / canvas.width

    // 第一页
    pdf.addImage(canvas, 'JPEG', 20, 20, imgWidth, imgHeight)
    leftHeight -= pageHeight

    // 后续页
    while (leftHeight > 0) {
      position = leftHeight - imgHeight
      pdf.addPage()
      pdf.addImage(canvas, 'JPEG', 20, position + 20, imgWidth, imgHeight)
      leftHeight -= pageHeight
    }
    
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')
    const fileName = `entity_alignment_report_${timestamp}.pdf`
    
    pdf.save(fileName)
    document.body.removeChild(tempDiv)
    ElMessage.success(`PDF导出成功: ${fileName}`)

  } catch (error) {
    console.error('导出PDF失败:', error)
    ElMessage.error(`PDF导出失败: ${error.message}`)
  } finally {
    exportLoading.value = false
  }
}

// 处理高亮点击移除 (改为显示详情)
const handleHighlightClick = async (event) => {
  // 如果有文本选择，不触发点击事件
  const selection = window.getSelection()
  if (selection && selection.toString().length > 0) return

  const target = event.target.closest('.entity-highlight')
  if (!target) return

  const entityId = target.dataset.entityId
  if (!entityId) return

  // 获取完整信息
  const matchItem = alignResult.value.find(item => item.entity_id === entityId)
  if (matchItem) {
    currentDetailEntity.value = matchItem
    detailDialogVisible.value = true
  }
}

// 从详情页删除匹配
const handleDeleteMatchFromDetail = () => {
  if (!currentDetailEntity.value) return
  
  const entityId = currentDetailEntity.value.entity_id
  const index = alignResult.value.findIndex(item => item.entity_id === entityId)
  if (index > -1) {
    alignResult.value.splice(index, 1)
    generateHighlightedText() // 重新生成高亮文本
    ElMessage.success('实体匹配已移除')
    detailDialogVisible.value = false
  }
}

// 文本选择菜单状态
const selectionMenuVisible = ref(false)
const selectionMenuPosition = reactive({ top: 0, left: 0 })
const selectedTextContent = ref('')
const selectionTimer = ref(null) // 用于防抖

// 处理文本选择
const handleTextSelection = (event) => {
  // 延时处理，确保 selection 对象已更新
  setTimeout(() => {
    const selection = window.getSelection()
    const text = selection ? selection.toString().trim() : ''

    if (text && text.length > 0) {
      selectedTextContent.value = text
      
      // 计算菜单位置 (在鼠标位置附近)
      selectionMenuPosition.top = event.clientY + 15
      selectionMenuPosition.left = event.clientX + 10
      
      selectionMenuVisible.value = true
    } else {
      selectionMenuVisible.value = false
    }
  }, 10)
}

// 监听全局点击以关闭菜单
onMounted(() => {
  document.addEventListener('mousedown', (e) => {
    // 如果点击的是菜单本身，不关闭
    if (e.target.closest('.selection-context-menu')) return
    selectionMenuVisible.value = false
  })
})

// 从选择添加新实体 (逻辑修正：自动填充，然后走现有流程)
const handleAddEntityFromSelection = () => {
  newEntityForm.entity_type = 'apt'
  newEntityForm.en_core = selectedTextContent.value
  newEntityForm.zh_core = selectedTextContent.value
  newEntityForm.description = ''
  
  // 打开对话框并切换到 New Tab
  correctTab.value = 'new'
  correctDialogVisible.value = true
  selectionMenuVisible.value = false
}

// 从选择添加别名 (打开新对话框)
const handleAddAliasFromSelection = () => {
  addAliasForm.aliasText = selectedTextContent.value
  addAliasForm.targetEntityId = ''
  addAliasForm.aliasType = 'en'
  entityOptions.value = [] // 重置搜索结果
  
  addAliasDialogVisible.value = true
  selectionMenuVisible.value = false
}

// 搜索实体 (用于添加别名时的远程搜索)
const fetchEntities = async (query) => {
  if (!query) {
    entityOptions.value = []
    return
  }
  
  searchLoading.value = true
  try {
    // 搜索结果合并
    const results = []
    // 并行搜索三种类型（或者后端支持不传类型搜所有）
    // 这里简化为搜索所有类型
    for (const type of ['apt', 'tool', 'vuln']) {
      const response = await queryEntity({ keyword: query, entity_type: type })
      if (response && response.entity_list) {
        results.push(...response.entity_list)
      }
    }
    entityOptions.value = results.slice(0, 20)
  } catch (error) {
    console.error('搜索实体失败:', error)
  } finally {
    searchLoading.value = false
  }
}

// 目标实体改变处理
const handleTargetEntityChange = (val) => {
  // 可以在这里预加载实体详情，或者在提交时处理
}

// 添加高亮匹配记录（用于新增实体或别名后）
const addHighlightMatch = (entityId, entityType, matchedText, enCore, zhCore, description = '') => {
  // 检查是否已存在相同的exact/fuzzy/semantic匹配
  const exists = alignResult.value.some(item => 
    item.entity_id === entityId && 
    item.matched_text === matchedText && 
    item.match_type !== 'fail'
  )
  
  if (exists) {
    console.log('匹配已存在，跳过添加')
    return
  }
  
  // 移除所有包含或被包含于新匹配文本的 fail 类型匹配
  // 例如：新增 "The delivered LOLSnif malware" 应该移除 "LOLSnif"、"malware" 等所有子串的 fail
  const textLower = matchedText.toLowerCase()
  let removedCount = 0
  
  for (let i = alignResult.value.length - 1; i >= 0; i--) {
    const item = alignResult.value[i]
    if (item.match_type === 'fail') {
      const itemLower = item.matched_text.toLowerCase()
      // 检查是否有重叠：新文本包含fail文本，或fail文本包含新文本
      if (textLower.includes(itemLower) || itemLower.includes(textLower)) {
        console.log('移除重叠的 fail 匹配:', item.matched_text)
        alignResult.value.splice(i, 1)
        removedCount++
      }
    }
  }
  
  if (removedCount > 0) {
    console.log(`已移除 ${removedCount} 个重叠的 fail 匹配`)
  }
  
  // 添加新的匹配记录
  const newMatch = {
    entity_id: entityId,
    entity_type: entityType,
    matched_text: matchedText,
    match_type: 'exact', // 精确匹配
    confidence: 1.0, // 置信度100%
    en_core: enCore,
    zh_core: zhCore,
    description: description,
    // 添加时间戳用于排序
    _added_at: Date.now()
  }
  
  alignResult.value.push(newMatch)
  console.log('已添加高亮匹配:', newMatch)
  
  // 重新生成高亮文本
  generateHighlightedText()
}

// 从 entity_id 提取 entity_type
const extractEntityTypeFromId = (entityId) => {
  if (!entityId) return null
  const prefix = entityId.split('-')[0]
  const typeMap = {
    'APT': 'apt',
    'TOOL': 'tool',
    'VULN': 'vuln'
  }
  return typeMap[prefix] || null
}



// 确认添加别名
const confirmAddAlias = async () => {
  if (!addAliasForm.targetEntityId) {
    ElMessage.warning('请选择目标实体')
    return
  }

  addAliasLoading.value = true
  try {
    // 1. 获取目标实体当前详情
    let targetEntity = entityOptions.value.find(e => e.entity_id === addAliasForm.targetEntityId)
    
    if (!targetEntity) {
      throw new Error('无法获取目标实体信息')
    }
    
    // DEBUG: 打印实体数据结构
    console.log('目标实体数据:', targetEntity)
    console.log('实体类型字段:', targetEntity.entity_type)

    // 检查并补全 entity_type 字段
    if (!targetEntity.entity_type) {
      console.warn('实体缺少 entity_type 字段，从 entity_id 提取...')
      const extractedType = extractEntityTypeFromId(targetEntity.entity_id)
      if (extractedType) {
        targetEntity.entity_type = extractedType
        console.log('提取的类型:', extractedType)
      } else {
        throw new Error(`无法从 entity_id "${targetEntity.entity_id}" 提取类型`)
      }
    }

    // 2. 准备更新数据
    const currentEnVariants = Array.isArray(targetEntity.en_variants) ? [...targetEntity.en_variants] : []
    const currentZhVariants = Array.isArray(targetEntity.zh_variants) ? [...targetEntity.zh_variants] : []
    
    if (addAliasForm.aliasType === 'en') {
      if (!currentEnVariants.includes(addAliasForm.aliasText)) {
        currentEnVariants.push(addAliasForm.aliasText)
      } else {
        ElMessage.info('该别名已存在')
        addAliasDialogVisible.value = false
        return
      }
    } else {
      if (!currentZhVariants.includes(addAliasForm.aliasText)) {
        currentZhVariants.push(addAliasForm.aliasText)
      } else {
        ElMessage.info('该别名已存在')
        addAliasDialogVisible.value = false
        return
      }
    }
    
    const updateData = {
      entity_id: targetEntity.entity_id,
      entity_type: targetEntity.entity_type,
      update_data: {
        en_core: targetEntity.en_core || '',
        zh_core: targetEntity.zh_core || '',
        description: targetEntity.description || null,
        en_variants: currentEnVariants,
        zh_variants: currentZhVariants
      }
    }
    
    // DEBUG: 打印即将发送的数据
    console.log('即将发送的 updateData:', JSON.stringify(updateData, null, 2))
    
    // 3. 提交更新
    await updateEntity(updateData)
    
    ElMessage.success('别名添加成功')
    
    // 添加高亮匹配
    const matchText = addAliasForm.aliasText
    const textToSearch = originalText.value || alignForm.text || ''
    
    console.log('=== 别名高亮调试 ===')
    console.log('matchText:', matchText)
    console.log('textToSearch 长度:', textToSearch.length)
    console.log('包含匹配文本:', textToSearch.includes(matchText))
    
    if (matchText && textToSearch.includes(matchText)) {
      console.log('✅ 条件满足，调用 addHighlightMatch')
      addHighlightMatch(
        targetEntity.entity_id,
        targetEntity.entity_type,
        matchText,
        targetEntity.en_core,
        targetEntity.zh_core,
        targetEntity.description
      )
    } else {
      console.log('❌ 条件不满足，仅刷新高亮')
      // 即使不在当前文本中，也需要重新生成高亮（刷新显示）
      generateHighlightedText()
    }
    
    addAliasDialogVisible.value = false
    
  } catch (error) {
    console.error('添加别名失败 - 完整错误:', error)
    console.error('错误响应数据:', error.response?.data)
    
    // 提供更详细的错误信息
    const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || '添加别名失败'
    ElMessage.error(`失败: ${errorMsg}`)
  } finally {
    addAliasLoading.value = false
  }
}

// 创建PDF内容
const createPDFContent = () => {
  const summary = `本报告共对齐 ${filteredAlignResult.value.length} 个实体：APT组织 ${getEntityTypeCount('apt')} 个，攻击工具 ${getEntityTypeCount('tool')} 个，漏洞 ${getEntityTypeCount('vuln')} 个，平均置信度 ${getAverageConfidence()}%，处理耗时 ${processTime.value.toFixed(3)} 秒。`

  // CSS 样式注入 - 确保导出的 PDF 也有高亮颜色
  const highlightCSS = `
    <style>
      .entity-highlight {
        padding: 2px 6px;
        margin: 0 2px;
        font-weight: 600;
        border-width: 2px;
        border-style: solid;
        letter-spacing: 0.3px;
        border-radius: 0;
      }
      /* APT - 霓虹红 */
      .apt-exact, .apt-fuzzy, .apt-semantic {
        background-color: rgba(255, 0, 85, 0.1);
        color: #FF0055;
        border-color: #FF0055;
      }
      .apt-exact {
        border-style: solid;
        font-weight: bold;
      }
      .apt-fuzzy {
        border-style: dashed;
      }
      .apt-semantic {
        border-style: dotted;
        background-color: transparent;
      }
      /* Tool - 电光蓝 */
      .tool-exact, .tool-fuzzy, .tool-semantic {
        background-color: rgba(0, 243, 255, 0.1);
        color: #00F3FF;
        border-color: #00F3FF;
      }
      .tool-exact {
        border-style: solid;
        font-weight: bold;
      }
      .tool-fuzzy {
        border-style: dashed;
      }
      .tool-semantic {
        border-style: dotted;
        background-color: transparent;
      }
      /* Vuln - 赛博紫 */
      .vuln-exact, .vuln-fuzzy, .vuln-semantic {
        background-color: rgba(191, 0, 255, 0.1);
        color: #BF00FF;
        border-color: #BF00FF;
      }
      .vuln-exact {
        border-style: solid;
        font-weight: bold;
      }
      .vuln-fuzzy {
        border-style: dashed;
      }
      .vuln-semantic {
        border-style: dotted;
        background-color: transparent;
      }
    </style>
  `

  // 生成对齐结果表格
  let tableHTML = `
    <h3 style="margin: 20px 0 10px 0; color: #333; font-size: 18px;">对齐结果详情</h3>
    <table style="width: 100%; border-collapse: collapse; font-size: 10px; margin-bottom: 20px;">
      <thead>
        <tr style="background: #f5f7fa;">
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">序号</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">实体ID</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">类型</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">英文名称</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">中文名称</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">匹配类型</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">匹配文本</th>
          <th style="border: 1px solid #ddd; padding: 6px; text-align: center; font-weight: bold;">置信度</th>
        </tr>
      </thead>
      <tbody>`

  filteredAlignResult.value.forEach((result, index) => {
    tableHTML += `
        <tr ${index % 2 === 1 ? 'style="background: #fafafa;"' : ''}>
          <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">${index + 1}</td>
          <td style="border: 1px solid #ddd; padding: 4px; text-align: center; font-family: monospace;">${result.entity_id}</td>
          <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">${getEntityTypeName(result.entity_type)}</td>
          <td style="border: 1px solid #ddd; padding: 4px; word-break: break-all;">${result.en_core}</td>
          <td style="border: 1px solid #ddd; padding: 4px; word-break: break-all;">${result.zh_core}</td>
          <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">${getMatchTypeName(result.match_type)}</td>
          <td style="border: 1px solid #ddd; padding: 4px; word-break: break-all;">${result.matched_text}</td>
          <td style="border: 1px solid #ddd; padding: 4px; text-align: center;">${(result.confidence * 100).toFixed(1)}%</td>
        </tr>`
  })

  tableHTML += `
      </tbody>
    </table>`

  // 生成高亮颜色说明 (更新为霓虹色)
  const legendHTML = `
    <h3 style="margin: 20px 0 10px 0; color: #333; font-size: 16px;">高亮颜色说明</h3>
    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
      <!-- APT组织 -->
      <div style="border: 1px solid #ddd; padding: 10px;">
        <div style="font-weight: bold; margin-bottom: 8px; text-align: center; color: #FF0055;">APT组织 (霓虹红)</div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(255, 0, 85, 0.1); border: 2px solid #FF0055; margin-right: 6px;"></div>
          <span style="font-size: 11px;">精确匹配 (实线)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(255, 0, 85, 0.1); border: 2px dashed #FF0055; margin-right: 6px;"></div>
          <span style="font-size: 11px;">模糊匹配 (虚线)</span>
        </div>
        <div style="display: flex; align-items: center;">
          <div style="width: 12px; height: 12px; background: transparent; border: 2px dotted #FF0055; margin-right: 6px;"></div>
          <span style="font-size: 11px;">语义匹配 (点状)</span>
        </div>
      </div>

      <!-- 攻击工具 -->
      <div style="border: 1px solid #ddd; padding: 10px;">
        <div style="font-weight: bold; margin-bottom: 8px; text-align: center; color: #00F3FF;">攻击工具 (电光蓝)</div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(0, 243, 255, 0.1); border: 2px solid #00F3FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">精确匹配 (实线)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(0, 243, 255, 0.1); border: 2px dashed #00F3FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">模糊匹配 (虚线)</span>
        </div>
        <div style="display: flex; align-items: center;">
          <div style="width: 12px; height: 12px; background: transparent; border: 2px dotted #00F3FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">语义匹配 (点状)</span>
        </div>
      </div>

      <!-- 漏洞 -->
      <div style="border: 1px solid #ddd; padding: 10px;">
        <div style="font-weight: bold; margin-bottom: 8px; text-align: center; color: #BF00FF;">漏洞 (赛博紫)</div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(191, 0, 255, 0.1); border: 2px solid #BF00FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">精确匹配 (实线)</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
          <div style="width: 12px; height: 12px; background: rgba(191, 0, 255, 0.1); border: 2px dashed #BF00FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">模糊匹配 (虚线)</span>
        </div>
        <div style="display: flex; align-items: center;">
          <div style="width: 12px; height: 12px; background: transparent; border: 2px dotted #BF00FF; margin-right: 6px;"></div>
          <span style="font-size: 11px;">语义匹配 (点状)</span>
        </div>
      </div>
    </div>`

  // 生成高亮文本
  const highlightElement = document.querySelector('.highlighted-text-display .highlight-body') ||
                          document.querySelector('.highlighted-text-display')
  let highlightedText = highlightElement ? highlightElement.innerHTML : ''

  // 如果没有内容，尝试从Vue变量获取
  if (!highlightedText && highlightedText.value) {
    highlightedText = highlightedText.value
  }

  // 如果还是没有内容，使用原始文本并添加高亮样式
  if (!highlightedText) {
    console.warn('无法获取高亮文本内容，将显示原始文本')
    // 创建一个简单的带高亮标记的文本显示
    const original = originalText.value || '无文本内容'
    let processedText = original

    // 为匹配的实体添加简单的标记
    alignResult.value.forEach(result => {
      const entityTypeShort = result.entity_type === 'apt' ? 'APT' : (result.entity_type === 'tool' ? 'TOOL' : 'VULN')
      const matchTypeShort = result.match_type === 'exact' ? '精确' : (result.match_type === 'fuzzy' ? '模糊' : '语义')
      const marker = `[${entityTypeShort}-${matchTypeShort}]`
      // 这里可以添加更复杂的替换逻辑，但暂时用简单标记
      processedText = processedText.replace(new RegExp(result.matched_text, 'g'), `${marker}${result.matched_text}${marker}`)
    })

    highlightedText = `<div style="font-family: monospace; white-space: pre-wrap; line-height: 1.4; background: #f8f9fa; padding: 15px;">${processedText}</div>`
  }

  // 组合完整内容
  return `
    ${highlightCSS}
    <div style="padding: 20px; font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
      <h2 style="text-align: center; margin-bottom: 20px; color: #1976d2;">实体对齐报告</h2>

      <div style="background: rgba(102, 126, 234, 0.05); border: 1px solid rgba(102, 126, 234, 0.2); padding: 12px; margin-bottom: 20px; font-size: 13px;">
        ${summary}
      </div>

      ${tableHTML}

      ${legendHTML}

      <h3 style="margin: 20px 0 10px 0; color: #333; font-size: 16px;">原文及高亮结果</h3>
      <div style="border: 1px solid #e4e7ed; padding: 16px; background: white; font-size: 14px; line-height: 1.8; white-space: pre-wrap; word-wrap: break-word;">
        ${highlightedText}
      </div>
    </div>`
}

const handleRemoveBatchEntity = (index) => {
  if (index >= 0 && index < batchAddEntityList.value.length) {
    batchAddEntityList.value.splice(index, 1)
  }
}

// 重置新实体表单
const resetNewEntityForm = () => {
  newEntityForm.entity_type = 'apt'
  newEntityForm.en_core = ''
  newEntityForm.zh_core = ''
  newEntityForm.en_variants = ''
  newEntityForm.zh_variants = ''
  newEntityForm.description = ''
  newEntityForm.add_original_as_variant = true

  if (newEntityFormRef.value) {
    newEntityFormRef.value.resetFields()
  }
}

// 确认批量新增
const handleConfirmBatchAdd = async () => {
  if (batchAddEntityList.value.length === 0) {
    ElMessage.warning('没有可新增的实体')
    return
  }

  batchAddLoading.value = true
  try {
    // 转换数据格式
    const entities = batchAddEntityList.value.map(entity => ({
      entity_id: null, // 自动生成
      entity_type: `${entity.entity_type}_organization`, // 转换为用户格式
      cn_core: entity.zh_core,
      en_core: entity.en_core,
      zh_variants: entity.zh_variants ? entity.zh_variants.split(',').map(v => v.trim()).filter(v => v) : [],
      en_variants: entity.en_variants ? entity.en_variants.split(',').map(v => v.trim()).filter(v => v) : [],
      description: entity.description
    }))

    const response = await batchAddEntities({ entities })

    if (response) {
      const successCount = response.success_count || 0
      const failCount = response.fail_count || 0

      ElMessage.success(`批量新增完成：成功 ${successCount} 个，失败 ${failCount} 个`)

      if (failCount > 0) {
        // 显示失败详情
        const failedResults = response.results.filter(r => !r.success)
        console.warn('批量新增失败详情:', failedResults)
      }

      batchAddDialogVisible.value = false
      batchAddEntityList.value = []

      // 刷新对齐结果（如果有新实体可能会影响后续对齐）
      if (successCount > 0) {
        generateHighlightedText()
      }
    } else {
      ElMessage.error('批量新增失败')
    }
  } catch (error) {
    console.error('批量新增失败:', error)
    ElMessage.error(error.message || '批量新增失败')
  } finally {
    batchAddLoading.value = false
  }
}

// 获取实体类型标签
const getEntityTypeTag = (type) => {
  const map = {
    apt: 'danger',
    tool: 'warning',
    vuln: 'info'
  }
  return map[type] || ''
}

// 获取实体类型名称
const getEntityTypeName = (type) => {
  const map = {
    apt: 'APT组织',
    tool: '攻击工具',
    vuln: '漏洞'
  }
  return map[type] || type
}

// 获取匹配类型标签
const getMatchTypeTag = (type) => {
  const map = {
    exact: 'success',
    fuzzy: 'warning',
    semantic: 'info',
    fail: 'danger'
  }
  return map[type] || ''
}

// 获取匹配类型名称
const getMatchTypeName = (type) => {
  const map = {
    exact: '精确匹配',
    fuzzy: '模糊匹配',
    semantic: '语义匹配',
    fail: '匹配失败'
  }
  return map[type] || type
}

// 获取置信度颜色
const getConfidenceColor = (confidence) => {
  if (confidence >= 0.8) return '#67c23a'
  if (confidence >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

// 打开阈值设置对话框
const handleOpenThresholdDialog = () => {
  thresholdDialogVisible.value = true
}

// 设置阈值
const handleSetThreshold = async () => {
  thresholdLoading.value = true
  try {
    const response = await setThreshold({
      levenshtein_thresh: thresholdForm.levenshtein_thresh,
      semantic_thresh: thresholdForm.semantic_thresh,
      confidence_thresh: thresholdForm.confidence_thresh
    })
    
    // 响应拦截器已经返回了 data 部分，所以直接检查 success
    if (response && response.success) {
      ElMessage.success('阈值设置成功')
      thresholdDialogVisible.value = false

      // 同时更新前端表单的置信度阈值
      alignForm.confidence_threshold = thresholdForm.confidence_thresh
    } else {
      ElMessage.error('阈值设置失败')
    }
  } catch (error) {
    console.error('设置阈值失败:', error)
    ElMessage.error(error.message || '阈值设置失败')
  } finally {
    thresholdLoading.value = false
  }
}
</script>

<style scoped>
/* 容器布局 - 刚性结构 */
.entity-align {
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
  overflow: hidden;
}

/* 顶部工具栏 - 终端风格 */
.top-toolbar {
  height: 60px;
  flex-shrink: 0;
  background-color: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

.toolbar-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-family: var(--font-mono);
  font-size: 18px;
  font-weight: 700;
  color: var(--primary-color);
  margin: 0;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.page-subtitle {
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--text-tertiary);
  margin-top: 2px;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
}

/* 主内容区 - 网格布局 */
.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
}

.left-panel {
  width: 300px;
  flex-shrink: 0;
  background-color: var(--bg-panel);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-primary);
  overflow: hidden;
  position: relative;
}

/* 左侧面板组件 */
.panel-header {
  height: 40px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

.file-list-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.file-item {
  padding: 8px 16px;
  display: flex;
  align-items: center;
  cursor: pointer;
  border-bottom: 1px solid transparent;
  transition: background-color 0.2s;
}

.file-item:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.file-item.active {
  background-color: rgba(92, 124, 250, 0.1);
  border-left: 2px solid var(--primary-color);
}

.file-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-name {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  font-size: 11px;
  color: var(--text-tertiary);
}

/* 右侧内容区 */
.content-header {
  height: 50px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background-color: var(--bg-secondary);
}

.content-title h3 {
  font-family: var(--font-mono);
  font-size: 14px;
  color: var(--text-primary);
  margin: 0;
}

.content-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* 文本编辑器/显示区 */
.text-input-mode, .file-preview-mode {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.text-input-container, .file-content-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 复写 Element 输入框 */
:deep(.el-textarea__inner) {
  background-color: var(--bg-primary) !important;
  border: none !important;
  color: var(--text-primary) !important;
  font-family: var(--font-mono) !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  height: 100% !important;
  border-radius: 0 !important;
  padding: 20px !important;
}

/* 高亮显示区 */
.highlighted-text-display {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background-color: var(--bg-primary);
  font-family: var(--font-mono);
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

/* 实体高亮样式 - Hacker Style 2.0 Neon */
/* 必须使用 :deep() 因为这些内容是通过 v-html 插入的 */
:deep(.entity-highlight) {
  position: relative;
  border-radius: 0;
  padding: 2px 6px;
  margin: 0 2px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  border-width: 2px;
  border-style: solid;
  letter-spacing: 0.3px;
}

/* APT 组织 - 霓虹红 */
:deep(.apt-exact), :deep(.apt-fuzzy), :deep(.apt-semantic) {
  background-color: var(--apt-bg);
  color: var(--apt-color);
  border-color: var(--apt-color);
}

:deep(.apt-exact) {
  box-shadow: 0 0 8px rgba(255, 0, 85, 0.4), inset 0 0 4px rgba(255, 0, 85, 0.1);
  text-shadow: 0 0 4px rgba(255, 0, 85, 0.3);
}

:deep(.apt-fuzzy) {
  border-style: dashed;
  box-shadow: 0 0 4px rgba(255, 0, 85, 0.2);
}

:deep(.apt-semantic) {
  border-style: dotted;
  background-color: transparent;
  box-shadow: none;
  text-shadow: 0 0 2px rgba(255, 0, 85, 0.5);
}

/* 攻击工具 - 电光蓝 */
:deep(.tool-exact), :deep(.tool-fuzzy), :deep(.tool-semantic) {
  background-color: var(--tool-bg);
  color: var(--tool-color);
  border-color: var(--tool-color);
}

:deep(.tool-exact) {
  box-shadow: 0 0 8px rgba(0, 243, 255, 0.4), inset 0 0 4px rgba(0, 243, 255, 0.1);
  text-shadow: 0 0 4px rgba(0, 243, 255, 0.3);
}

:deep(.tool-fuzzy) {
  border-style: dashed;
  box-shadow: 0 0 4px rgba(0, 243, 255, 0.2);
}

:deep(.tool-semantic) {
  border-style: dotted;
  background-color: transparent;
  box-shadow: none;
  text-shadow: 0 0 2px rgba(0, 243, 255, 0.5);
}

/* 漏洞 - 赛博紫 */
:deep(.vuln-exact), :deep(.vuln-fuzzy), :deep(.vuln-semantic) {
  background-color: var(--vuln-bg);
  color: var(--vuln-color);
  border-color: var(--vuln-color);
}

:deep(.vuln-exact) {
  box-shadow: 0 0 8px rgba(191, 0, 255, 0.4), inset 0 0 4px rgba(191, 0, 255, 0.1);
  text-shadow: 0 0 4px rgba(191, 0, 255, 0.3);
}

:deep(.vuln-fuzzy) {
  border-style: dashed;
  box-shadow: 0 0 4px rgba(191, 0, 255, 0.2);
}

:deep(.vuln-semantic) {
  border-style: dotted;
  background-color: transparent;
  box-shadow: none;
  text-shadow: 0 0 2px rgba(191, 0, 255, 0.5);
}

/* Hover 效果增强 */
:deep(.entity-highlight:hover) {
  filter: brightness(1.3);
  transform: translateY(-1px);
  z-index: 10;
}

:deep(.apt-exact:hover) {
  box-shadow: 0 0 15px rgba(255, 0, 85, 0.6), inset 0 0 8px rgba(255, 0, 85, 0.2);
}

:deep(.tool-exact:hover) {
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.6), inset 0 0 8px rgba(0, 243, 255, 0.2);
}

:deep(.vuln-exact:hover) {
  box-shadow: 0 0 15px rgba(191, 0, 255, 0.6), inset 0 0 8px rgba(191, 0, 255, 0.2);
}

/* 对话框内滑块与输入框修复 */
:deep(.el-dialog .el-input__wrapper) {
  background-color: var(--bg-tertiary) !important;
  box-shadow: none !important;
  border: 1px solid var(--border-color) !important;
}

:deep(.el-slider__runway) {
  background-color: var(--bg-tertiary) !important;
  border: 1px solid var(--border-color) !important;
}

:deep(.el-slider__bar) {
  background-color: var(--primary-color) !important;
}

:deep(.el-slider__button) {
  border-color: var(--primary-color) !important;
  background-color: var(--bg-secondary) !important;
}

/* Toggle Button Group - Console Style */
.entity-type-toggles {
  display: flex;
  gap: 6px;
}

.content-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.toggle-button {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  background-color: var(--bg-tertiary);
  border: 1px solid var(--border-color);
  border-radius: 0;
  cursor: pointer;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  user-select: none;
  white-space: nowrap;
}

.toggle-button:hover {
  border-color: var(--primary-color);
  background-color: rgba(51, 153, 255, 0.05);
}

.toggle-button.active {
  border-color: var(--primary-color);
  background-color: rgba(51, 153, 255, 0.1);
  box-shadow: 0 0 8px rgba(51, 153, 255, 0.2);
}

.toggle-icon {
  font-size: 10px;
  line-height: 1;
}

.toggle-label {
  color: var(--text-primary);
  letter-spacing: 1px;
}

.toggle-status {
  color: var(--text-tertiary);
  font-size: 10px;
  opacity: 0.7;
  margin-left: 2px;
}

.toggle-button.active .toggle-status {
  color: var(--primary-color);
  opacity: 1;
  font-weight: 700;
}

/* 统计面板 */
.result-statistics {
  padding: 12px 20px;
  background-color: var(--bg-tertiary);
  border-bottom: 1px solid var(--border-color);
  display: flex;
  gap: 24px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 10px;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.stat-value {
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}
::-webkit-scrollbar-thumb {
  background: var(--border-hover);
  border-radius: 0;
}

/* Element UI 覆盖 */
:deep(.el-empty__description) {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
}

:deep(.el-tag) {
  background-color: rgba(255, 255, 255, 0.05);
  border-color: var(--border-color);
  color: var(--text-secondary);
}

:deep(.el-dialog) {
  background-color: var(--bg-secondary);
  border: 1px solid var(--primary-color);
  box-shadow: 0 0 20px rgba(51, 153, 255, 0.2);
}

:deep(.el-dialog__title) {
  color: var(--primary-color);
  font-family: var(--font-mono);
}

:deep(.el-drawer) {
  background-color: var(--bg-secondary) !important;
}

/* 结果表格样式 - Hacker Style */
.result-table-container {
  height: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
}

.result-table-header {
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.2);
  border-bottom: 1px solid var(--border-color);
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
}

:deep(.el-table) {
  background-color: transparent !important;
  color: var(--text-secondary) !important;
  --el-table-border-color: var(--border-color);
  --el-table-header-bg-color: rgba(255, 255, 255, 0.05);
  --el-table-row-hover-bg-color: rgba(92, 124, 250, 0.1);
  --el-table-tr-bg-color: transparent;
}

:deep(.el-table th) {
  background-color: var(--bg-tertiary) !important;
  color: var(--primary-color) !important;
  font-family: var(--font-mono) !important;
  font-weight: 600;
  border-bottom: 1px solid var(--border-color) !important;
}

:deep(.el-table tr), :deep(.el-table td) {
  background-color: transparent !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
  font-family: var(--font-mono);
}

:deep(.el-table__inner-wrapper::before) {
  background-color: var(--border-color) !important;
}

/* 表格内按钮 */
:deep(.el-table .el-button) {
  background-color: transparent;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}
:deep(.el-table .el-button:hover) {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background-color: rgba(92, 124, 250, 0.1);
}


/* 隐藏文件上传Input */
input[type="file"] {
  display: none;
}

/* 文本颜色工具类 */
.text-exact {
  color: var(--success-color);
  font-weight: bold;
}
.text-fuzzy {
  color: var(--warning-color);
  font-weight: bold;
}
.text-semantic {
  color: var(--text-secondary);
  font-style: italic;
}

</style>

<!-- Global Styles for Hacker Dialog -->
<style>
.hacker-detail-dialog .el-dialog {
  background: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

.hacker-detail-dialog .el-dialog__header {
  display: none !important;
}

.hacker-detail-dialog .el-dialog__body {
  padding: 0 !important;
  background: transparent !important;
}

/* Hacker Card Container */
.hacker-card {
  background: rgba(10, 15, 30, 0.85); /* Darker, slightly transparent */
  backdrop-filter: blur(16px);
  border: 1px solid var(--primary-color); /* Cyan border */
  box-shadow: 0 0 30px rgba(0, 243, 255, 0.15), inset 0 0 20px rgba(0, 243, 255, 0.05);
  padding: 24px;
  position: relative;
  color: #a0a6b5;
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  overflow: hidden;
}

/* Card Header */
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 1px solid rgba(0, 243, 255, 0.2);
  padding-bottom: 12px;
}

.header-title {
  color: var(--primary-color);
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  text-shadow: 0 0 8px rgba(0, 243, 255, 0.6);
}

.header-decoration {
  height: 2px;
  background: var(--primary-color);
  width: 20px;
  opacity: 0.5;
}

/* Info Rows */
.info-row {
  margin-bottom: 12px;
  display: flex;
  font-size: 13px;
  align-items: center; /* Align vertically */
}

.info-row label {
  width: 140px; /* Fixed match label width */
  color: #5c6b7f;
  font-weight: 600;
  letter-spacing: 0.5px;
  flex-shrink: 0;
}

.info-row .value {
  color: #d0d6e0;
  flex: 1;
}

.highlight-row {
  background: rgba(0, 243, 255, 0.05); /* Slight highlight bg */
  padding: 8px 12px;
  margin: 0 -12px 16px; /* Extend to edges */
  border-left: 2px solid var(--primary-color);
}

/* Glitch Text Effect */
.glitch-text {
  color: #fff;
  font-weight: 700;
  letter-spacing: 1px;
  font-size: 14px;
  text-shadow: 2px 0 rgba(255, 0, 85, 0.5), -2px 0 rgba(0, 243, 255, 0.5);
}

/* Info Grid for compact items */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}

.info-item label {
  display: block;
  font-size: 11px;
  color: #5c6b7f;
  margin-bottom: 4px;
}

.code-font {
  font-family: 'Consolas', monospace;
  color: var(--warning-color); /* Orange for IDs usually looks good */
  letter-spacing: 0.5px;
}

/* Type Tags */
.type-tag.apt { color: #ff0055; text-shadow: 0 0 5px rgba(255, 0, 85, 0.4); }
.type-tag.tool { color: #00f3ff; text-shadow: 0 0 5px rgba(0, 243, 255, 0.4); }
.type-tag.vuln { color: #bf00ff; text-shadow: 0 0 5px rgba(191, 0, 255, 0.4); }

/* Confidence Bar */
.confidence-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  position: relative;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--success-color); /* Green normally, maybe custom neon green */
  box-shadow: 0 0 8px var(--success-color);
}

.confidence-text {
  font-size: 12px;
  color: var(--success-color);
  font-weight: bold;
}

/* Description Scroll */
.description-row {
  margin-top: 16px;
  display: block; /* Stack label and value */
}
.description-row label {
  margin-bottom: 8px;
  display: block;
}
.scrollable {
  max-height: 80px;
  overflow-y: auto;
  font-size: 12px;
  line-height: 1.5;
  color: #8b9bb4;
  padding-right: 4px;
}

/* Scrollbar Style */
.scrollable::-webkit-scrollbar {
  width: 4px;
}
.scrollable::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 2px;
}

/* Footer Buttons */
.card-footer {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  padding-top: 16px;
}

.hacker-btn {
  background: transparent;
  border: 1px solid transparent;
  color: #fff;
  padding: 8px 16px;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.hacker-btn.primary {
  border-color: var(--primary-color);
  color: var(--primary-color);
  box-shadow: 0 0 10px rgba(0, 243, 255, 0.1);
}

.hacker-btn.primary:hover {
  background: rgba(0, 243, 255, 0.1);
  box-shadow: 0 0 15px rgba(0, 243, 255, 0.3);
  text-shadow: 0 0 5px var(--primary-color);
}

.hacker-btn.danger {
  border-color: #ff0055;
  color: #ff0055;
}

.hacker-btn.danger:hover {
  background: rgba(255, 0, 85, 0.1);
  box-shadow: 0 0 15px rgba(255, 0, 85, 0.3);
}

/* Decorations */
.corner {
  position: absolute;
  width: 8px;
  height: 8px;
  border: 2px solid var(--primary-color);
  transition: all 0.3s;
}

.top-left { top: 0; left: 0; border-right: none; border-bottom: none; }
.top-right { top: 0; right: 0; border-left: none; border-bottom: none; }
.bottom-left { bottom: 0; left: 0; border-right: none; border-top: none; }
.bottom-right { bottom: 0; right: 0; border-left: none; border-top: none; }

</style>

