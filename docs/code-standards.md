# 代码规范与 Git 协作约定

## 1. 技术约定

- Python 3.11+；后端使用 Flask，数据库使用 SQLite，Excel 使用 OpenPyXL。
- 前端使用语义化 HTML、原生 CSS 与 JavaScript，不引入不必要的构建步骤。
- 文本统一 UTF-8；Python 缩进 4 个空格，JavaScript/CSS 缩进 2 个空格。
- Python 遵循 PEP 8；函数和变量使用 `snake_case`，类使用 `PascalCase`。
- JavaScript 使用 `camelCase`；CSS 类名使用短横线命名。
- API 路径使用复数名词；成功返回 JSON，失败返回 HTTP 4xx/5xx 和 `{ "error": "明确原因" }`。
- 数据库写入使用参数化 SQL，禁止字符串拼接 SQL；用户输出经 DOM `textContent` 或转义后渲染。
- 每次变更必须保持现有测试通过；新增核心功能须添加正常和异常测试。

## 2. 模块边界

- `addressbook/routes.py`：HTTP 参数、响应和错误码，不直接拼 SQL。
- `addressbook/repository.py`：联系人及联系方式持久化。
- `addressbook/excel.py`：工作簿导入导出、行解析和导入结果。
- `addressbook/validation.py`：输入规范化与业务校验。
- `addressbook/static/`、`templates/`：展示与交互。
- `tests/`：隔离数据库的可重复自动化测试。

## 3. 分支与提交

1. 从团队默认分支创建 `feature/<短横线功能名>`，禁止直接向主分支推送未完成代码。
2. 提交采用 Conventional Commits：`feat: 添加联系人收藏筛选`、`test: 覆盖 Excel 异常导入`。
3. 一个提交只表达一个完整意图，提交前运行 `python -m pytest`。
4. 两人分别使用自己的 GitHub 账号提交，不代提交、不虚构贡献。
5. 功能分支推送后创建 Pull Request，由另一名成员审查：功能、异常处理、测试、文档四项均通过方可合并。
6. 至少形成三次有意义的提交；建议拆分为项目骨架、核心联系人、Excel、界面、测试与文档等多个提交。
7. 合并后创建语义化版本标签，例如 `v1.0.0`，并在 GitHub Release 写明三项功能、运行方法和已知限制。

## 4. 代码审查清单

- [ ] 三项核心功能均可从界面操作。
- [ ] 输入为空、非法 Excel、重复数据有明确反馈。
- [ ] 多联系方式新增、修改、删除后无孤立记录。
- [ ] 导出后重新导入不丢失支持的字段。
- [ ] 无密码、真实个人数据、数据库文件被提交。
- [ ] README 命令可从干净环境复现。
- [ ] 两名成员均有真实代码贡献，测试全部通过。
