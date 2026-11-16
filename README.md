# 拾光通讯录 · Address Book V1.1 — Feature Enhancement

软件工程 EE308FZ 极限编程作业：支持联系人收藏、多种联系方式及 Excel 导入/导出的轻量 Web 通讯录。

## 功能清单

- 联系人新增、查看、编辑、删除，姓名/号码/邮箱/备注关键词搜索。
- 星标收藏、取消收藏、仅看星标联系人，星标数量实时统计。
- 同一联系人可添加多条手机、电话、邮箱、微信、QQ、微博、地址及其他信息。
- `.xlsx` 模板下载、整批校验导入、同名跳过、格式化导出。
- SQLite 自动建表与持久化；响应式中文界面；虚构演示数据一键初始化。

V1.1 在 V1.0 基础上补齐了**每条联系方式的可选自定义标签**：新建、编辑和详情展示均可使用，重复保存不会丢失原标签。数据库会为缺少 `label` 列的旧表补列；旧行和旧 Excel 模板继续兼容。详见 [V1.1 变更记录](V1.1_CHANGELOG.md)。

## 快速运行

### Windows

在本目录打开终端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe seed_demo.py
.\.venv\Scripts\python.exe app.py
```

也可在依赖安装后双击 `run.bat`。浏览器访问 **http://127.0.0.1:5000**。`seed_demo.py` 是可选步骤，只在数据库为空时写入 6 位虚构联系人，已有数据时不会覆盖或追加。

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python seed_demo.py
python app.py
```

首次启动自动创建 `instance/addressbook.db`。停止服务使用 `Ctrl+C`。该数据库已列入 `.gitignore`，不要上传个人真实联系人数据。

## 使用说明

### 收藏与搜索

点击联系人卡片或详情右上角的星形按钮切换收藏；点击左侧“星标联系人”只看收藏。搜索可与收藏筛选组合，快捷键 `Ctrl+K` 聚焦搜索框。

### 多种联系方式

新建或编辑联系人时点击“添加一条”，选择类型并输入内容。同类型可重复添加，例如两个手机号码。V1.1 的每行还可填写最多 30 字的独立标签，例如“工作”“个人”“学校”；标签可留空。空联系方式行保存时自动忽略，每个联系人最多 30 条。编辑已有联系人时，原标签会回填到对应行。

### Excel 导出

点击“导出 Excel”，得到 `拾光通讯录.xlsx`。每个联系人一行，表头为：

```text
姓名 | 收藏 | 手机 | 电话 | 邮箱 | 微信 | QQ | 微博 | 地址 | 其他联系方式 | 备注
```

同类型多个值使用中文分号 `；` 分隔；收藏为“是/否”。表头冻结并启用筛选，可直接使用 Excel/WPS 查看。

V1.1 若有非空联系方式标签，导出文件额外包含“联系方式标签”工作表，以通讯录行号、联系方式类型、同类型序号和原值对应标签。主表仍保持 V1.0 的 11 列格式。重新导入该文件会恢复标签；如果在 Excel 中改动联系方式内容，需要同步修改标签工作表，否则系统会拒绝不匹配的标签行，避免错误关联。

### Excel 导入

1. 在“导入 Excel”对话框下载标准模板，或使用本项目 `sample_data/contacts_sample.xlsx`。
2. 不要修改表头；每行填写一位联系人，姓名必填。
3. 上传 `.xlsx` 文件，最大 5 MiB；不支持旧版 `.xls` 或 CSV。
4. 同名联系人（含文件内重复姓名）跳过，不覆盖已有数据。
5. 任意数据行有错误时整批不写入，界面会返回具体行号与原因；修正后重新上传。

V1.0 的单工作表模板仍可直接导入；其联系方式默认没有标签。

## 自动化测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

macOS/Linux 使用 `.venv/bin/python -m pytest -q`。

V1.0 基线实测 **17 passed**；V1.1 完整回归实测 **26 passed**。测试使用临时目录中的独立数据库，覆盖原有 CRUD、收藏、搜索和 Excel 功能，以及标签新增、修改、留空、多条独立保存、旧库迁移和 Excel 往返。详见 `docs/v1.1-test-record.md`。原 `docs/test-report.md` 是队友提供的 V1.0 测试记录，予以保留。

## 项目结构

```text
app.py                         本地启动入口
addressbook/
  __init__.py                  Flask 应用工厂
  db.py                        SQLite 连接与建表
  repository.py                持久化与事务
  validation.py                输入校验
  excel.py                     Excel 导入导出
  routes.py                    Web 与 JSON API
  templates/index.html         页面结构
  static/styles.css            响应式样式
  static/app.js                前端交互
seed_demo.py                   虚构演示数据
sample_data/                   示例工作簿
tests/                         pytest 自动化测试
docs/                          设计、规范、PSP、博客等
Dockerfile                     可选云部署镜像
```

## Docker 与可选云部署

```bash
docker build -t xp-address-book .
docker run --rm -p 5000:5000 -v xp_address_book_data:/app/instance xp-address-book
```

云平台可选择支持 Docker 的华为云、阿里云等容器服务。部署后必须配置持久卷、HTTPS 与公网访问控制，并使用生产级 WSGI 服务；Flask 内置服务器仅用于本地演示。只有实际可公开访问的 URL 才能申报加分，`localhost` 或 `127.0.0.1` 不属于云部署。

## 文档导航

- [要求追踪矩阵](docs/requirements-traceability.md)
- [架构与实现设计](docs/design.md)
- [代码规范与 Git 协作约定](docs/code-standards.md)
- [分工、贡献比例与问题解决](docs/collaboration.md)
- [两名成员 PSP 表](docs/psp.md)
- [测试报告](docs/test-report.md)
- [完整演示视频脚本](docs/demo-script.md)
- [V1.0 代码审查报告](docs/v1.0-code-review.md)
- [V1.1 测试记录](docs/v1.1-test-record.md)
- [V1.1 交付说明](V1.1_DELIVERY.md)
- [个人 CSDN 博客 Markdown 模板](docs/blog.md)

## 提交前必须补充

团队名称、两位成员真实姓名/学号、真实分工与贡献比例、各自 PSP 实际工时、GitHub 团队仓库与代码规范 URL、至少三次提交的截图与人数统计、PR、Release、程序截图、完整演示视频、每位成员的个人 CSDN 博客链接。可选云部署还需公网 URL。所有 `待填写`/`待插入` 标记必须在提交前处理。
