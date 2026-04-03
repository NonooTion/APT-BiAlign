# APT 威胁实体跨文本对齐工具 - 前端

## 项目简介

这是 APT 威胁实体跨文本对齐工具的前端项目，基于 Vue 3 + Element Plus 开发。

## 技术栈

- **Vue 3**: 渐进式 JavaScript 框架
- **Vue Router**: 官方路由管理器
- **Pinia**: 状态管理库
- **Element Plus**: Vue 3 UI 组件库
- **Axios**: HTTP 客户端
- **Vite**: 下一代前端构建工具

## 项目结构

```
frontend/
├── public/              # 静态资源
├── src/
│   ├── api/             # API 接口
│   │   └── dict.js      # 词典管理 API
│   ├── assets/          # 资源文件
│   ├── components/      # 公共组件
│   ├── router/          # 路由配置
│   │   └── index.js
│   ├── store/           # 状态管理
│   ├── utils/           # 工具函数
│   │   └── request.js   # Axios 封装
│   ├── views/           # 页面组件
│   │   ├── DictManagement.vue  # 词典管理页面
│   │   └── EntityAlign.vue     # 实体对齐页面
│   ├── App.vue          # 根组件
│   └── main.js          # 入口文件
├── index.html           # HTML 模板
├── package.json         # 依赖配置
├── vite.config.js       # Vite 配置
└── README.md            # 项目说明
```

## 安装与运行

### 1. 安装依赖

```bash
cd frontend
npm install
```

### 2. 开发运行

```bash
npm run dev
```

访问 http://localhost:3000

### 3. 构建生产版本

```bash
npm run build
```

### 4. 预览生产构建

```bash
npm run preview
```

## 功能模块

### 1. 词典管理

- 初始化 MongoDB 连接
- 实体查询（支持关键词搜索）
- 实体新增、编辑、删除
- 支持三种实体类型：APT组织、攻击工具、漏洞

### 2. 实体对齐

- 文本对齐（待实现）
- 支持中英文文本
- 显示对齐结果和置信度

## API 配置

前端通过 Vite 代理转发 API 请求到后端：

- 开发环境：`http://localhost:3000` → `http://localhost:8000`
- 生产环境：需要配置实际的后端地址

## 开发说明

1. 所有 API 请求统一通过 `src/utils/request.js` 封装
2. API 接口定义在 `src/api/` 目录下
3. 页面组件在 `src/views/` 目录下
4. 公共组件在 `src/components/` 目录下

## 注意事项

- 确保后端服务运行在 `http://localhost:8000`
- 如果后端地址不同，需要修改 `vite.config.js` 中的代理配置

