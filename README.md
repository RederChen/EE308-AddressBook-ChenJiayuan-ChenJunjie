# 拾光通讯录 · Address Book V1.2

> 极限编程课程作业 · 通讯录程序第三版（V1.2）
> 技术栈：Python 3 + Flask 3.1 + SQLite + openpyxl + 原生 JavaScript（无前端构建步骤）

「拾光通讯录」是一个本地优先的个人通讯录应用：一位联系人可以拥有多条、不同类型的联系方式（手机 / 电话 / 邮箱 / 微信 / QQ / 微博 / 地址 / 其他），每条方式还可以带一个自定义标签（如「工作」「个人」「紧急」）；支持收藏、搜索、排序、分页、批量操作、回收站，以及符合作业要求的 Excel 导入导出。

---

## 1. 版本演进

| 版本 | 主要变化 | 自动化测试 |
| --- | --- | --- |
| V1.0 | 首个可运行版本：收藏、多联系方式、Excel 导入导出、英文界面 | 17 passed |
| V1.1 | 中文界面；联系方式「标签」及 Excel 标签工作表；旧数据库自动补列迁移 | 26 passed |
| **V1.2（本版）** | 回收站（软删除 + 撤销）、批量管理、排序与分页、按筛选导出、导入预检与覆盖模式、LIKE 通配符与 Excel 公式注入修复、统一 JSON 错误与安全响应头、毫秒级时间戳 | **60 passed** |

完整逐条改动见 [V1.2_CHANGELOG.md](V1.2_CHANGELOG.md)，改造思路与评估见 [V1.2_关键修改说明.md](V1.2_关键修改说明.md)。

---

## 2. 快速开始

需要 Python 3.10+（开发与验收环境为 Python 3.14）。

```bash
cd AddressBook_v1.2_ChenJunjie

# 1) 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 2) 安装依赖
pip install -r requirements.txt

# 3)（可选）写入演示数据
python seed_demo.py

# 4) 启动
python app.py
```

打开 <http://127.0.0.1:5000> 即可使用。Windows 也可以直接双击 `run.bat`（若不存在 `.venv` 则回退到系统 Python）。

自定义监听地址与端口（默认仅监听本机 127.0.0.1）：

```bash
# Windows PowerShell
$env:ADDRESS_BOOK_PORT="8080"; python app.py
# macOS / Linux
ADDRESS_BOOK_PORT=8080 python app.py
```

> 首次启动会自动在 `instance/addressbook.db` 创建数据库；如果检测到 V1.0 / V1.1 的旧数据库，会自动补齐新增字段，无需手工迁移。

---

## 3. 功能总览（对照作业要求）

### 3.1 基础功能

| 作业要求 | 本版实现 | 分值 |
| --- | --- | --- |
| 收藏 / 书签联系人 | 卡片与详情页星标按钮、侧边栏「星标」筛选、`PATCH /api/contacts/<id>/favorite` 切换、收藏状态随 Excel 导出导入 | 25 |
| 单个联系人多种联系方式 | 8 种类型（手机/电话/邮箱/微信/QQ/微博/地址/其他），每人最多 30 条，每条可加 ≤30 字标签；导出时同类型多值合并在同一列 | 10 |
| Excel 导入导出 | 导出：每联系人一行、每类信息一列（11 列中文表头），标签写入独立工作表；导入：标准模板 + 预检 + 重复策略（跳过/覆盖），整批原子（任一行出错则不写库） | 25 |
| 页面样式 | 原生 CSS 双栏布局、响应式（1120/820/570px 断点）、气泡提示、空状态、键盘可用性 | 10 |
| 云部署（可选） | 提供 `Dockerfile`，可自行部署到任意容器平台；本地版默认只监听 127.0.0.1 | +15 |

### 3.2 V1.2 新增 / 增强

- **回收站**：删除改为软删除（记录 `deleted_at`），删除后 8 秒内可点「撤销」；回收站支持恢复、彻底删除、清空。
- **批量管理**：进入批量模式后可全选/多选，批量收藏、取消收藏、移入回收站、恢复、彻底删除（单次 ≤500 条）。
- **排序与分页**：星标优先 / 姓名 A→Z / 最近更新 / 最近创建；列表每页 50 条，「加载更多」增量加载。
- **按当前筛选导出**：导出会带上当前搜索词、星标筛选、回收站视图与排序方式。
- **导入预检**：先解析并展示「新增 N 位 / 已存在 M 位 / 文件内重复 K 位」，确认后才写库。
- **重复策略**：导入时可选「跳过同名」或「覆盖同名」（覆盖会整体替换该联系人的联系方式与备注）。
- **体验细节**：一键复制联系方式、`tel:` / `mailto:` 可点击、创建时间展示、快捷键 `Ctrl+K`（搜索）/ `Ctrl+N`（新建）/ `Ctrl+B`（批量）。
- **安全性**：LIKE 通配符转义（`%`、`_` 按字面搜索）、Excel 公式注入防护、统一 JSON 错误结构、安全响应头、上传 5 MiB 限制。

---

## 4. 使用说明

### 4.1 联系人

- 「新建联系人」填写姓名（必填，≤80 字）、备注（≤500 字），可添加多条联系方式并可为每条填写标签。
- 点击列表卡片查看详情；详情页可编辑、删除、切换收藏。
- 删除 = 移入回收站，可通过 toast 上的「撤销」或侧边栏「回收站」恢复。

### 4.2 搜索与排序

- 搜索框匹配姓名、备注、联系方式内容与联系方式标签，输入后 250ms 自动查询。
- 搜索中的 `%`、`_` 等字符按字面匹配，不再作为 SQL 通配符。
- 排序下拉切换后立即生效；回收站视图固定按删除时间倒序。

### 4.3 Excel 导出

- 点击侧边栏「导出当前列表」下载 `拾光通讯录.xlsx`，包含当前筛选结果。
- 工作表「通讯录」共 11 列：`姓名 / 收藏 / 手机 / 电话 / 邮箱 / 微信 / QQ / 微博 / 地址 / 其他联系方式 / 备注`。
- 同一类型的多个值用中文分号 `；` 连接（导入时也支持英文 `;` 与换行）。
- 若存在联系方式标签，会额外生成工作表「联系方式标签」：
  `联系人行号 / 方式类型 / 同类型序号 / 联系方式内容 / 标签`。
- 以 `=`、`+`、`-`、`@` 等开头的文本会自动加 `'` 前缀，防止在 Excel 中被当作公式执行；再次导入时前缀会被还原。

### 4.4 Excel 导入

1. 在导入对话框点击「下载标准导入模板.xlsx」。
2. 填写数据（模板第 2 行是示例，可删除）并选择文件。
3. 选择重复策略：跳过同名（默认）或覆盖同名。
4. 点击「预览并导入」查看统计，再点击「确认导入」。

规则：仅支持 `.xlsx`、单次 ≤2000 行、表头必须与模板一致、收藏列只能填「是/否」；任一行不合格则整批取消，错误信息精确到 Excel 行号。

### 4.5 快捷操作

| 操作 | 方式 |
| --- | --- |
| 聚焦搜索 | `Ctrl+K` |
| 新建联系人 | `Ctrl+N` |
| 批量管理 | `Ctrl+B` 或顶部「批量管理」 |
| 选中卡片 | 点击 / `Enter` / `Space` |
| 复制联系方式 | 详情页方式右侧复制图标 |

---

## 5. 数据模型

```text
contacts
  id          INTEGER PRIMARY KEY
  name        TEXT NOT NULL
  favorite    INTEGER NOT NULL DEFAULT 0 CHECK (favorite IN (0, 1))
  notes       TEXT NOT NULL DEFAULT ''
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP   -- V1.2 起写入毫秒级 UTC
  updated_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
  deleted_at  TEXT                                      -- V1.2：NULL 表示未删除，非空表示在回收站

contact_methods
  id          INTEGER PRIMARY KEY
  contact_id  INTEGER NOT NULL REFERENCES contacts(id) ON DELETE CASCADE
  kind        TEXT NOT NULL      -- mobile/phone/email/wechat/qq/weibo/address/other
  label       TEXT NOT NULL DEFAULT ''   -- V1.1：如「工作」「个人」
  value       TEXT NOT NULL
  sort_order  INTEGER NOT NULL DEFAULT 0
```

索引：`idx_contacts_favorite`、`idx_contacts_name`、`idx_contacts_deleted`、`idx_methods_contact(contact_id, sort_order)`。

初始化顺序为「建表 → 按 `PRAGMA table_info` 补齐缺失列 → 建索引」，因此 V1.0 / V1.1 的旧库可以直接升级（补齐 `contact_methods.label` 与 `contacts.deleted_at`）。

---

## 6. API 一览

所有接口均返回 JSON；出错结构为 `{"error": "中文提示", "details": ["可选明细"]}`。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 单页应用页面 |
| GET | `/api/health` | 健康检查：状态、版本、统计 |
| GET | `/api/contacts` | 列表；支持 `query`、`favorite`、`trash`、`sort`、`limit`、`offset` |
| POST | `/api/contacts` | 新建联系人（201） |
| GET | `/api/contacts/<id>` | 联系人详情 |
| PUT | `/api/contacts/<id>` | 更新联系人（整体替换联系方式） |
| DELETE | `/api/contacts/<id>` | 移入回收站（204） |
| PATCH | `/api/contacts/<id>/favorite` | 收藏切换或显式设置 `{"favorite": true}` |
| POST | `/api/contacts/<id>/restore` | 从回收站恢复 |
| POST | `/api/contacts/bulk` | 批量操作：`{"action": "favorite|unfavorite|delete|restore|purge", "ids": [...]}` |
| GET | `/api/trash` | 回收站列表 |
| DELETE | `/api/trash/<id>` | 彻底删除（不可恢复） |
| DELETE | `/api/trash` | 清空回收站 |
| GET | `/api/contacts/export` | 导出 Excel（支持与列表相同的筛选参数） |
| GET | `/api/contacts/template` | 下载导入模板 |
| POST | `/api/contacts/import/preview` | 导入预检（不写库） |
| POST | `/api/contacts/import` | 导入；multipart 字段 `file` 与 `mode=skip|overwrite` |

`GET /api/contacts` 返回：`{"contacts": [...], "total": N, "has_more": bool, "limit": 50, "offset": 0, "sort": "favorite", "stats": {"total": N, "favorites": N, "methods": N, "trash": N}}`。

---

## 7. 自动化测试

```bash
cd AddressBook_v1.2_ChenJunjie
python -m pytest -q          # 60 passed
python -m pytest -q tests/test_excel.py -v
```

| 文件 | 用例数 | 覆盖内容 |
| --- | --- | --- |
| `tests/test_contacts.py` | 15 | CRUD、校验、收藏、搜索（含 LIKE 转义）、排序分页、回收站、批量操作 |
| `tests/test_excel.py` | 12 | 导出格式、标签工作表、模板、导入原子性、公式注入、行数上限、筛选导出 |
| `tests/test_import_modes.py` | 9 | 导入预检、跳过/覆盖模式、文件内重复、错误处理 |
| `tests/test_method_labels.py` | 9 | 标签增改、旧库迁移、标签工作表往返与不匹配拒绝 |
| `tests/test_api_errors.py` | 8 | 统一 JSON 错误、405/413、安全响应头、回收站接口 |
| `tests/test_frontend.py` | 7 | 前端契约：DOM 标识、SVG 图标、API 路径与后端路由一致 |

> 若在受限沙箱中遇到 pytest 临时目录权限问题，可设置 `TEMP`/`TMP` 指向可写目录后运行；普通开发机无需任何额外步骤。

---

## 8. 项目结构

```text
AddressBook_v1.2_ChenJunjie/
├── app.py                     # 入口：create_app() 并启动开发服务器
├── seed_demo.py               # 6 位虚构演示联系人
├── requirements.txt
├── pytest.ini
├── run.bat                    # Windows 一键启动
├── Dockerfile                 # 可选云部署
├── addressbook/
│   ├── __init__.py            # 应用工厂、统一错误处理、安全响应头
│   ├── db.py                  # 表结构、连接管理、旧库迁移
│   ├── repository.py          # 数据访问：列表/搜索/排序/分页/回收站/批量/导入
│   ├── validation.py          # 输入校验与业务常量
│   ├── excel.py               # 导入解析与导出生成（含公式注入防护）
│   ├── routes.py              # HTTP 接口（蓝图）
│   ├── templates/index.html   # 单页界面
│   └── static/
│       ├── app.js             # 前端逻辑（无框架）
│       └── styles.css         # 界面样式
├── tests/                     # 60 个自动化测试
├── docs/                      # 设计、需求追踪、测试报告、博客草稿等
├── sample_data/               # 示例导出文件与导入模板
├── evidence/                  # 测试与接口佐证
├── instance/                  # 运行时数据库（自动生成，已被 .gitignore 忽略）
├── README.md
├── V1.2_CHANGELOG.md
├── V1.2_DELIVERY.md
└── V1.2_关键修改说明.md
```

---

## 9. Docker 部署（可选 +15 分）

```bash
docker build -t address-book-v1.2 .
docker run --rm -p 8080:5000 address-book-v1.2
# 访问 http://127.0.0.1:8080
```

镜像内使用 `flask run --host=0.0.0.0 --port=5000`，因此容器外可访问。若部署到云服务器，请自行加反向代理与访问控制：本程序没有账号体系，不适合直接公开暴露到公网。

---

## 10. 文档导航

| 文档 | 内容 |
| --- | --- |
| [V1.2_关键修改说明.md](V1.2_关键修改说明.md) | 两版差异评估、V1.2 关键修改的原因/方案/影响/验证、运行与验收 |
| [V1.2_CHANGELOG.md](V1.2_CHANGELOG.md) | 逐条改动清单（修复 / 新增 / 变更） |
| [V1.2_DELIVERY.md](V1.2_DELIVERY.md) | 交付清单、验收步骤、已知限制 |
| [docs/design.md](docs/design.md) | 模块划分、数据模型、接口设计 |
| [docs/requirements-traceability.md](docs/requirements-traceability.md) | 作业要求 → 实现 → 测试 追踪矩阵 |
| [docs/test-report.md](docs/test-report.md) | 测试用例与执行记录 |
| [docs/code-standards.md](docs/code-standards.md) | 代码规范与命名约定 |
| [docs/blog.md](docs/blog.md) | CSDN 博客草稿 |
| [docs/psp.md](docs/psp.md) | 两人 PSP 表 |
| [docs/collaboration.md](docs/collaboration.md) | 分工、协作困难与解决 |
| [docs/demo-script.md](docs/demo-script.md) | 演示视频脚本 |
| [docs/v1.0-code-review.md](docs/v1.0-code-review.md) | 代码审查与缺陷修复记录 |
| [V1.1_CHANGELOG.md](V1.1_CHANGELOG.md) / [V1.1_DELIVERY.md](V1.1_DELIVERY.md) | 上一版历史文档（保留备查） |

---

## 11. 提交前需要团队补充

- [ ] 团队成员姓名 / 学号、分工与贡献比例（合计 100%）
- [ ] GitHub 仓库地址、提交历史截图、每人提交数（要求 commit ≥ 3）
- [ ] 程序运行截图与完整演示视频链接
- [ ] 两人各自的 CSDN 博客发布链接（可共用 `docs/blog.md` 草稿）
- [ ] PSP 表实际用时
- [ ] 若做云部署：部署地址、启动命令与访问截图
