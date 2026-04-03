// 新版本的 generateHighlightedText 方法
// 替换 EntityAlign.vue 中从第1230行到第1564行的内容

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
