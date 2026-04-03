# APT 威胁实体跨文本对齐工具

面向威胁情报类文本，对 **APT 组织**、**攻击工具**、**漏洞** 等实体进行识别，并与 MongoDB 中的实体词典做 **精确 / 模糊 / 语义** 三层对齐；支持多格式文档解析、文件上传与批量处理，前端提供高亮展示与报告导出。

## 功能概览

- **实体对齐**：单文本、文件上传（JSON / TXT / PDF / DOC / DOCX）、批量对齐；可调模糊与语义阈值。
- **词典管理**：APT / 工具 / 漏洞三类实体的增删改查与变体维护（依赖 MongoDB）。
- **文档处理**：独立文档解析与分词接口（`/api/document/*`），JSON 与 TXT 类走不同预处理管线。
- **前端**：Vue3 + Element Plus，实体对齐页、词典管理、数据库连接配置等。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+、FastAPI、Uvicorn |
| 前端 | Vue 3、Vite、Element Plus、Axios |
| 数据 | MongoDB（实体词典）；可选 Redis（实体向量缓存） |
| 算法 | Sentence-BERT（语义向量）、Levenshtein（模糊）、规则精确匹配 |
| 分词 | 中英混合分句分词、词性、n-gram 候选与置信度过滤（`TokenizerPipeline`） |

## 环境要求

- Python 3.11+
- Node.js 16+
- MongoDB（本地或远程，与 `.env` 中配置一致）
- （可选）Redis，用于语义阶段实体向量缓存

## 快速开始

### 1. 配置环境变量

复制 `env.example` 为项目根目录下的 `.env`，按需修改 MongoDB、Redis、模型路径与阈值：

```bash
cp env.example .env
```

`BERT_MODEL_PATH` 可指向本地 Sentence-Transformers 模型目录，或使用 Hugging Face 模型名（需联网下载）。

### 2. 安装后端依赖

建议在虚拟环境中安装（示例，按你实际 `requirements.txt` 或 pip 列表为准）：

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install fastapi uvicorn[standard] pydantic-settings pymongo python-Levenshtein numpy sentence-transformers redis PyPDF2 python-docx jieba nltk
```

若项目内提供 `requirements.txt`，优先执行：

```bash
pip install -r requirements.txt
```

### 3. 启动后端

在项目根目录执行：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

或直接：

```bash
python -m app.main
```

- API 文档：<http://localhost:8000/docs>  
- 健康检查：<http://localhost:8000/health>

### 4. 安装并启动前端

```bash
cd frontend
npm install
npm run dev
```

开发环境默认前端端口 **3000**，通过 Vite 代理将 `/api` 转发到 **8000**（见 `frontend/vite.config.js`）。

### 5. Windows 一键脚本

- `启动脚本.bat`：依次启动后端与前端（需已配置 Python / Node 与依赖）。
- `检查环境.bat`：检查 Python、Node、依赖与 MongoDB 等。

## 主要 API 前缀

| 前缀 | 说明 |
|------|------|
| `/api/align` | 算法初始化、单文本/批量对齐、文件上传对齐、实体修正等 |
| `/api/dict` | 实体词典 CRUD 与查询 |
| `/api/document` | 文档解析、分词、对齐流水线（`DocumentService`） |

## 目录结构（简要）

```
pythonProject1/
├── app/                 # 后端应用
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置（读取 .env）
│   ├── api/routes/      # 路由：align / dict / document
│   ├── core/            # 对齐、分词、解析、词典管理
│   ├── services/
│   └── utils/
├── frontend/            # Vue3 前端
├── data/                # 示例数据与测试用例
├── env.example          # 环境变量模板
├── 启动脚本.bat
└── README.md
```

## 注意事项

- 首次使用语义匹配前，前端或接口需调用 **初始化算法**（加载 Sentence-BERT），否则语义层可能跳过。
- 生产环境请收紧 CORS、配置 MongoDB 认证，并勿将 `.env` 提交到版本库。
- 大 PDF / 复杂 DOC 依赖 `PyPDF2`、`python-docx` 等库，缺失时解析会报错，请按提示安装。

## 许可证

毕业设计 / 个人学习用途，如需开源请自行补充许可证文件。
