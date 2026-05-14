/**
 * TreeCore — Headless 树型组件核心逻辑
 * 纯 JS 实现，不依赖任何框架
 */

class FlatNode {
  constructor({ key, id, parentId, level, children, label, disabled, selectable, checkable, isLeaf, data }) {
    this.key = key
    this.id = id
    this.parentId = parentId
    this.level = level
    this.children = children
    this.label = label
    this.disabled = disabled
    this.selectable = selectable
    this.checkable = checkable
    this.isLeaf = isLeaf
    this.data = data
  }
}

class TreeCore {
  /**
   * @param {Object} options
   * @param {Array} options.data - 嵌套结构的数据
   * @param {Function} [options.keyAccessor] - 自定义 key 生成函数
   * @param {Object} options.selection - 选择配置
   * @param {string} options.selection.mode - 'none' | 'single' | 'multi'
   * @param {string} options.selection.cascade - 'down' | 'up' | 'both' | 'none'
   */
  constructor(options = {}) {
    this.nodes = []         // FlatNode[]
    this.nodeMap = {}       // key -> FlatNode
    this.expandedKeys = {}  // key -> boolean
    this.selectedKeys = {}  // key -> boolean
    this.checkedKeys = {}   // key -> boolean (multi mode)
    this.indeterminateKeys = {} // key -> boolean (半选缓存)

    this.keyAccessor = options.keyAccessor || ((node, parentId) => {
      return parentId ? `${parentId}_${node.id}` : String(node.id)
    })

    this.selection = {
      mode: options.selection?.mode || 'none',
      cascade: options.selection?.cascade || 'none',
    }

    if (options.data) {
      this.setData(options.data)
    }
  }

  /**
   * 嵌套数据拍平
   */
  setData(data) {
    this.nodes = []
    this.nodeMap = {}

    const flatten = (items, parentId = null, level = 0) => {
      for (const item of items) {
        const key = this.keyAccessor(item, parentId)
        const children = item.children || []
        const isLeaf = children.length === 0

        const node = new FlatNode({
          key,
          id: item.id,
          parentId,
          level,
          children: [],
          label: item.label || '',
          disabled: item.disabled || false,
          selectable: item.selectable !== false,
          checkable: item.checkable !== false,
          isLeaf,
          data: item,
        })

        this.nodes.push(node)
        this.nodeMap[key] = node

        if (parentId && this.nodeMap[parentId]) {
          this.nodeMap[parentId].children.push(key)
          this.nodeMap[parentId].isLeaf = false
        }

        if (children.length > 0) {
          flatten(children, key, level + 1)
        }
      }
    }

    flatten(data)
    return this
  }

  /**
   * 获取可见节点（所有祖先节点都必须展开）
   */
  getVisibleNodes() {
    const result = []
    for (const node of this.nodes) {
      // 根节点始终可见
      if (node.parentId === null) {
        result.push(node)
        continue
      }
      // 沿着 parentId 链往上检查每一层是否都展开了
      let visible = true
      let currentKey = node.parentId
      while (currentKey !== null) {
        if (!this.expandedKeys[currentKey]) {
          visible = false
          break
        }
        const parent = this.nodeMap[currentKey]
        if (!parent) break
        currentKey = parent.parentId
      }
      if (visible) {
        result.push(node)
      }
    }
    return result
  }

  // ==================== 展开/折叠 ====================

  expand(key) {
    const node = this.nodeMap[key]
    if (!node || node.isLeaf) return this
    this.expandedKeys[key] = true
    return this
  }

  collapse(key) {
    const node = this.nodeMap[key]
    if (!node || node.isLeaf) return this
    delete this.expandedKeys[key]
    return this
  }

  toggleExpand(key) {
    if (this.expandedKeys[key]) {
      this.collapse(key)
    } else {
      this.expand(key)
    }
    return this
  }

  expandAll() {
    for (const node of this.nodes) {
      if (!node.isLeaf) {
        this.expandedKeys[node.key] = true
      }
    }
    return this
  }

  collapseAll() {
    this.expandedKeys = {}
    return this
  }

  isExpanded(key) {
    return !!this.expandedKeys[key]
  }

  // ==================== 选中（单选） ====================

  select(key) {
    if (this.selection.mode !== 'single') return this
    const node = this.nodeMap[key]
    if (!node || node.disabled || !node.selectable) return this

    this.selectedKeys = {}
    this.selectedKeys[key] = true
    return this
  }

  deselect(key) {
    delete this.selectedKeys[key]
    return this
  }

  // ==================== 勾选（多选） ====================

  check(key) {
    if (this.selection.mode !== 'multi') return this
    const node = this.nodeMap[key]
    if (!node || node.disabled || !node.selectable || !node.checkable) return this

    this.checkedKeys[key] = true

    // 向下联动
    if (this.selection.cascade === 'down' || this.selection.cascade === 'both') {
      this._checkDescendants(key)
    }

    // 向上更新祖先的 checked / indeterminate 状态
    if (this.selection.cascade === 'up' || this.selection.cascade === 'both') {
      this._updateAncestorsCheckState(key)
    } else {
      // 即使不联动，也需要更新半选缓存
      this._updateAncestorsCheckState(key)
    }

    return this
  }

  uncheck(key) {
    if (this.selection.mode !== 'multi') return this
    const node = this.nodeMap[key]
    if (!node || node.disabled || !node.selectable || !node.checkable) return this

    delete this.checkedKeys[key]

    // 向下联动
    if (this.selection.cascade === 'down' || this.selection.cascade === 'both') {
      this._uncheckDescendants(key)
    }

    // 向上更新祖先的 checked / indeterminate 状态
    this._updateAncestorsCheckState(key)

    return this
  }

  toggleCheck(key) {
    if (this.checkedKeys[key]) {
      this.uncheck(key)
    } else {
      this.check(key)
    }
    return this
  }

  // ==================== 状态查询 ====================

  getSelection() {
    // 单选
    const selectedKeys = Object.keys(this.selectedKeys)
    if (selectedKeys.length > 0) {
      return { keys: selectedKeys, nodes: selectedKeys.map(k => this.nodeMap[k]) }
    }
    // 多选
    const checkedKeys = Object.keys(this.checkedKeys)
    return { keys: checkedKeys, nodes: checkedKeys.map(k => this.nodeMap[k]) }
  }

  isSelected(key) {
    return !!this.selectedKeys[key]
  }

  isChecked(key) {
    return !!this.checkedKeys[key]
  }

  /**
   * 获取节点勾选状态：unchecked / checked / indeterminate（半选）
   */
  getCheckState(key) {
    if (this.checkedKeys[key]) return 'checked'
    if (this.indeterminateKeys[key]) return 'indeterminate'
    return 'unchecked'
  }

  getNode(key) {
    return this.nodeMap[key] || null
  }

  getAllNodes() {
    return [...this.nodes]
  }

  // ==================== 内部方法 ====================

  _checkDescendants(key) {
    const node = this.nodeMap[key]
    if (!node) return
    for (const childKey of node.children) {
      const child = this.nodeMap[childKey]
      if (child && !child.disabled && child.selectable && child.checkable) {
        this.checkedKeys[childKey] = true
        this._checkDescendants(childKey)
      }
    }
  }

  _uncheckDescendants(key) {
    const node = this.nodeMap[key]
    if (!node) return
    for (const childKey of node.children) {
      delete this.checkedKeys[childKey]
      delete this.indeterminateKeys[childKey]
      this._uncheckDescendants(childKey)
    }
  }

  /**
   * 从指定节点向上更新所有祖先的 checked / indeterminate 状态
   */
  _updateAncestorsCheckState(key) {
    const node = this.nodeMap[key]
    if (!node || !node.parentId) return
    const parent = this.nodeMap[node.parentId]
    if (!parent) return

    const allChecked = parent.children.every(ck => this.checkedKeys[ck])
    const someChecked = parent.children.some(ck =>
      this.checkedKeys[ck] || this.indeterminateKeys[ck]
    )

    if (allChecked && !parent.disabled && parent.selectable && parent.checkable) {
      this.checkedKeys[parent.key] = true
      delete this.indeterminateKeys[parent.key]
    } else if (someChecked) {
      delete this.checkedKeys[parent.key]
      this.indeterminateKeys[parent.key] = true
    } else {
      delete this.checkedKeys[parent.key]
      delete this.indeterminateKeys[parent.key]
    }

    this._updateAncestorsCheckState(parent.key)
  }
}

// 支持 Node.js 和浏览器
if (typeof window !== 'undefined') {
  window.TreeCore = TreeCore
}
