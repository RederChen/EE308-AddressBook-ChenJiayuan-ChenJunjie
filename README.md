# EverContact

软件工程 EE308FZ 极限编程作业：支持联系人收藏、多种联系方式及 Excel 导入/导出的轻量 Web 通讯录。

## 功能清单

- 联系人新增、查看、编辑、删除，姓名/号码/邮箱/备注关键词搜索。
- 星标收藏、取消收藏、仅看星标联系人，星标数量实时统计。
- 同一联系人可添加多条手机、电话、邮箱、微信、QQ、微博、地址及其他信息。
- `.xlsx` 模板下载、整批校验导入、同名跳过、格式化导出。
- SQLite 自动建表与持久化；响应式中文界面；虚构演示数据一键初始化。

## 快速运行

### Windows

在本目录打开终端：

```bash
python -m venv .venv
.venv/Scripts/activate
python -m pip install -r requirements.txt
python seed_demo.py
python app.py
```

也可在依赖安装后双击 `run.bat`。浏览器访问 **http://127.0.0.1:5000**。`seed_demo.py` 只在数据库为空时写入 6 位虚构联系人，已有数据时不会覆盖或追加。

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

新建或编辑联系人时点击“添加一条”，选择类型并输入内容。同类型可重复添加，例如两个手机号码。空联系方式行保存时自动忽略，每个联系人最多 30 条。

### Excel 导出

点击“Export Excel”，得到 `EverContact.xlsx`。每个联系人一行，表头为：

```text
Name | Favorite | Mobile | Phone | Email | WeChat | QQ | Weibo | Address | Other Contact Methods | Notes
```

同类型多个值使用英文分号 `;` 分隔；收藏为“Yes/No”。表头冻结并启用筛选，可直接使用 Excel/WPS 查看。

### Excel 导入

1. 在“导入 Excel”对话框下载标准模板，或使用本项目 `sample_data/contacts_sample.xlsx`。
2. 不要修改表头；每行填写一位联系人，姓名必填。
3. 上传 `.xlsx` 文件，最大 5 MiB；不支持旧版 `.xls` 或 CSV。
4. 同名联系人（含文件内重复姓名）跳过，不覆盖已有数据。
5. 任意数据行有错误时整批不写入，界面会返回具体行号与原因；修正后重新上传。

## 自动化测试

```bash
python -m pytest
```

当前结果：**18 passed**。测试使用临时目录中的独立数据库，覆盖联系人 CRUD、收藏、搜索、多联系方式、级联删除、导入校验、同名处理、导出格式、往返一致性，以及应用运行源文件无中文字符的自动检查。详见 `docs/test-report.md`。

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

云平台可选择支持 Docker 的华为云、阿里云等容器服务。部署后必须配置持久卷、HTTPS 与公网访问控制，并使用生产级 WSGI 服务；Flask 内置服务器仅用于本地演示。
