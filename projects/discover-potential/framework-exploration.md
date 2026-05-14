# 构建编程框架 — 探索计划

## 背景

在"发现自己的潜能"这个课题中，我倾向于先尝试**构建一个编程框架**。

选择理由：
- 比小说更容易界定完成度
- 结合了理解系统和构建系统
- 有 AI 辅助，门槛降低

## 项目定位

构建一个**跨框架的 Headless 树型组件**。

### 解决什么问题
同一个业务中使用 Vue 和 React 时，树型组件需要重复实现两次，每次需求变更都要改两处。

### 面向谁
在多前端框架项目中需要树型组件的开发者。

### 核心设计
- **Headless Core**：纯逻辑层（数据管理、展开折叠、搜索过滤、虚拟滚动），不涉及 UI 渲染
- **框架适配层**：分别为 Vue、React 等提供薄薄的视图绑定
- **API 设计目标**：简洁 + 灵活
- **性能目标**：大数据量下高性能

### 为什么选 Headless 而不是 Web Components
逻辑和视图彻底分离，每个框架都能用最原生的方式渲染，不受 Web Components 的样式隔离和交互定制限制。

## 架构设计

### 整体分层
```
@tree/headless-core   → 纯逻辑，不依赖任何框架
@tree/vue             → Vue 适配层
@tree/react           → React 适配层
```

### 设计原则
- 保持克制，Core 只做树的状态管理
- 数据格式转换不属于 Core，由外部或独立模块处理

### 数据模型
用户输入：嵌套结构（直觉友好）
内部运作：初始化时一次性拍平为 FlatNode

```typescript
interface FlatNode {
  key: string        // 内部唯一标识，默认自动生成，支持自定义
  id: string         // 用户业务 id，原样保留
  parentId: string | null
  level: number
  children: string[] // 存的是 key
  label: string
  disabled: boolean     // 灰显，可见但不可操作
  selectable: boolean   // 不参与选择逻辑，外观不变
  checkable: boolean    // 多选时是否显示 Checkbox
  isLeaf: boolean
  data: any             // 用户原始数据原样保留
}
```

### 选择/勾选配置

```typescript
interface SelectionConfig {
  mode: 'none' | 'single' | 'multi'
  cascade: 'down' | 'up' | 'both' | 'none'  // 仅 multi 时生效
  // cascade.down: 勾父自动勾所有子
  // cascade.up: 子全勾自动勾父
  // cascade.both: 双向联动
  // cascade.none: 父子各自独立
}

// 选中状态 API（单选/多选统一返回数组）
getSelection(): { keys: string[], nodes: FlatNode[] }

// key 生成策略：用户可自定义函数，不提供则使用默认策略
keyAccessor?: (node: any) => string  // 默认: parentId + id 拼接
```

扁平结构的优势：展开折叠、搜索、虚拟滚动都是数组切片，不需要递归。

## 进展记录

### 2026-05-13
- 确定方向：编程框架
- 确定项目：跨框架 Headless 树型组件
- 确定架构路线：Headless Core
- 确定内部数据模型：FlatNode（扁平结构）
- 确定 key 策略：支持自定义 key 函数，不提供则使用默认（parentId + id 拼接）
- 确定选中 API：统一返回数组（单选/多选），包含 keys 和 nodes
- 完成选择/勾选配置设计（mode + cascade + disabled/selectable/checkable）
- 实现半选状态（indeterminate），带缓存优化，O(1) 查询
- 拆分交互：箭头只管展开折叠，label/checkbox 只管选中勾选
- 修复 getVisibleNodes 多层嵌套可见性 bug（逐级检查祖先展开状态）
- 实现纯 HTML Demo（tree-demo/index.html）
- 实现虚拟滚动，1万节点只渲染约50个 DOM
- 添加大数据测试集（10层，1万节点）

### 待继续
- 搜索/过滤功能
- 节点增删改
- 键盘导航
- 虚拟滚动边界情况测试
- Vue / React 适配层

## 感悟

树型组件是我之前想做而不敢做的事情。借助 AI 我拥有了勇气。

现在我要做的不是一口气完成它，而是一点点细化自己的诉求，通过与 AI 协作来完成那些看似不可能完成的事情。

并在此过程中持续感受——哪些事情是自己真的愿意去做又能做好的。这才是"发现自己的潜能"这个课题的真正实践方式。

不是想出来的，是做出来的。
