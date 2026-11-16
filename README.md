# 拾光通讯录 V1.3.0

EE308 极限编程通讯录项目最终迭代。V1.3 以已合并的 V1.2 为基础，保留联系人收藏、多种联系方式及其独立标签、Excel 导入导出，并完善导入预览与最终交付。

## 功能

- 新建、编辑、搜索联系人；一人可保存多条手机、电话、邮箱、微信、QQ、微博、地址或其他联系方式，每条可加独立标签。
- 收藏与星标筛选、四种排序、分页加载、批量管理、回收站与恢复。
- Excel `.xlsx` 导出当前视图、下载模板、按“跳过同名／覆盖同名”预览并导入；预览按所选策略计算新增、覆盖、跳过数量，换文件或策略后必须重新预览。
- SQLite 本地存储；旧版数据库启动时自动补齐联系方式标签和回收站字段。

## 本地运行

需要 Python 3.10+。在**含有 `app.py` 的项目根目录**运行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python seed_demo.py   # 可选：数据库为空时加入 6 位虚构演示联系人
python app.py
```

打开 <http://127.0.0.1:5000>。Windows 也可以在安装依赖后双击 `run.bat`。macOS/Linux 把激活命令换成 `source .venv/bin/activate`。默认数据库是 `instance/addressbook.db`，它已被 `.gitignore` 排除，**不要把真实联系人数据库上传到 GitHub**。

## 测试与验收

```powershell
python -m pytest -q
```

V1.3 本地核验结果：**66 passed**；`node --check addressbook/static/app.js` 通过；真实浏览器冒烟覆盖创建带标签联系人、收藏、两种导入预览、覆盖导入、筛选导出和窄屏布局。测试详情与人工复核步骤见 [docs/TESTING.md](docs/TESTING.md)。

## Excel 规则

主工作表每位联系人一行，共 11 列：姓名、收藏、手机、电话、邮箱、微信、QQ、微博、地址、其他联系方式、备注。同类多个值以 `；` 分隔。若有独立联系方式标签，导出文件增加“联系方式标签”工作表；再次导入可恢复标签。单文件不超过 5 MiB、单次不超过 2000 行；任一行不合格则整批不写库。

“跳过同名”不修改已有联系人；“覆盖同名”用文件内容替换已有联系人的收藏、备注及所有联系方式。导入预览只反映**预览当时**的数据库状态，若其他人同时修改数据，正式导入结果可能变化。

## Render 公网演示

本项目是 Flask 服务，应在 Render 创建 **Web Service**，选择 Python 运行环境。项目根目录为仓库根目录时：

- Build Command：`pip install -r requirements.txt`
- Start Command：`python seed_demo.py && gunicorn app:app --bind 0.0.0.0:$PORT --workers 1`
- Health Check Path：`/api/health`

`.python-version` 将 Render 运行环境限制在 Python 3.13 系列。免费 Web Service 的本地 SQLite 文件是**临时数据**，服务休眠、重启或重新部署后会丢失；启动命令会重新建立虚构演示数据。不要把它当作永久存储，也不要在无登录保护的公网演示中输入真实个人信息。若使用付费持久磁盘，可把环境变量 `ADDRESS_BOOK_DATABASE` 设为磁盘上的数据库绝对路径。具体上传、配置和检查步骤见压缩包外随附的 Render 教学文件。

## 项目资料

- [CHANGELOG.md](CHANGELOG.md)：四个版本的迭代记录。
- [docs/PROJECT.md](docs/PROJECT.md)：需求、结构、设计与代码规范。
- [docs/TESTING.md](docs/TESTING.md)：自动化与人工验收记录。
- [docs/TEAM_SUBMISSION.md](docs/TEAM_SUBMISSION.md)：需要团队本人填写的分工、PSP、博客与视频证据。

代码可运行不等于课程材料已全部提交。姓名、学号、真实工时、贡献比例、博客和演示视频须由团队据实补齐；未部署时不能声称已获得公网加分。
