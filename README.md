# 高校教师科研画像与智能辅助系统

## 项目说明

本项目是一个围绕“高校教师科研画像”主链路构建的教研管理与智能辅助系统。  
当前系统采用：

- 前端：Vue 3 + Vite + Element Plus
- 后端：Django + Django REST Framework + SimpleJWT
- 数据库：MySQL
- 图谱：Neo4j 可选，异常时保留 MySQL 回退链路

当前系统已经具备以下核心能力：

- 工号登录、注册、忘记密码、密码修改与账户管理
- 教师个人中心
- 多类成果录入、编辑、删除、导入与统计
- 教师画像、趋势分析与解释说明
- 学术图谱与轻量图分析
- 规则增强型项目推荐
- 受控的智能问答辅助
- 学院级管理看板

## 当前定位

当前版本更适合表述为：

- 一个可演示、可继续开发、边界清晰的完整系统原型
- 一个围绕教师科研画像主链路逐步扩展的教研管理平台

当前不应表述为：

- 已完成的复杂 BI 平台
- 已完成的完整知识平台
- 已完成的复杂机器学习推荐平台
- 已完成的高级图挖掘平台

## 快速启动

### 前端

```bash
cd frontend
cmd /c npm install
cmd /c npm run dev
```

### 后端

```bash
cd backend
python -m pip install -r requirements.txt
python scripts\restore_demo_state.py
python manage.py runserver
```

推荐顺序说明：

1. 先运行 `python scripts\startup_preflight.py`
2. 若提示存在未执行迁移，则先执行 `python manage.py migrate`
3. 迁移完成后再次运行 `python scripts\startup_preflight.py`
4. 执行 `python scripts\restore_demo_state.py`，安全同步内置演示账号、成果和项目指南
5. 最后执行 `python manage.py runserver`

## 演示数据恢复与账号说明

### 标准恢复命令

```bash
cd backend
python scripts\restore_demo_state.py
```

该脚本会顺序执行：

1. `python scripts\startup_preflight.py`
2. `python manage.py migrate`
3. `python manage.py init_demo_teachers --print-accounts`

默认行为是安全同步：

- 保留数据库中已有账号密码
- 补齐缺失的内置演示账号、成果和项目指南
- 打印当前演示账号清单与密码保留说明

如果你明确需要把演示账号恢复成统一默认密码，再显式执行带参数的硬重置。

### 仅重建演示数据

```bash
cd backend
python manage.py init_demo_teachers --reset-demo-data --reset-passwords --print-accounts
```

适用场景：

- 需要把内置演示账号、演示成果和演示指南都恢复成标准演示状态
- 明确接受将内置演示账号密码重置为统一默认密码
- 答辩前希望恢复到“统一账号口径”的标准演示环境

### 当前内置演示账号

- 默认情况下：
  - 系统会保留数据库中已有的管理员和教师账号密码
  - 数据库中只保存密码哈希，无法直接回显明文密码
- 若通过 `--reset-passwords` 显式重置，则标准演示密码为：
  - 管理员账号：`admin / Admin123456`
  - 教师账号：
    - `100001 / teacher123456`
    - `100002 / teacher123456`
    - `100003 / teacher123456`
    - `100004 / teacher123456`

说明：

- 仅在新建演示教师账号或显式执行 `--reset-passwords` 时，教师账号会恢复为“临时密码待修改”状态
- 这些账号和数据仅用于演示、回归和继续开发，不应混入真实业务环境
- 演示项目指南会一并初始化，用于推荐、问答和管理员项目指南管理演示

## 最小验证命令

### 前端

```bash
cd frontend
cmd /c npm run verify:baseline
```

### 后端

```bash
cd backend
python scripts\startup_preflight.py
python scripts\restore_demo_state.py
python manage.py check
python manage.py test --keepdb --noinput users achievements graph_engine project_guides ai_assistant
python scripts\verify_development_16_24_regression.py
```

### 统一自动验证入口

```bash
python backend/scripts/run_validation_pipeline.py
```

该入口会按以下顺序串联现有真实命令：

1. `backend/scripts/startup_preflight.py`
2. `backend/manage.py check`
3. `backend/manage.py test --keepdb --noinput users achievements graph_engine project_guides ai_assistant`
4. `backend/scripts/verify_development_16_24_regression.py`
5. `frontend/npm run verify:baseline`

## 主链路回归脚本覆盖范围

统一主链路回归脚本：

```bash
cd backend
python scripts\verify_development_16_24_regression.py
```

### 前置条件

- 启动前检查通过
- 迁移已执行
- 已恢复标准演示数据
- 当前数据库允许使用内置演示账号进行回归验证

### 当前覆盖的关键主链路

1. 登录与基础鉴权
   - 验证目的：确认教师 / 管理员演示账号存在、密码哈希可用、未登录访问受保护接口仍被拒绝
   - 预期结果：教师与管理员账号均处于可用状态，未登录访问 `GET /api/users/me/` 返回 `401`
2. 教师资料查看与编辑
   - 验证目的：确认教师个人中心资料查看与编辑链路可用
   - 预期结果：`GET /api/users/me/` 返回 `permission_scope`，`PATCH /api/users/me/` 能回写关键资料字段
3. 成果新增 / 编辑 / 查询 / 统计
   - 验证目的：确认成果中心主链路仍可完成新增、编辑、查询和统计
   - 预期结果：论文创建 `201`、编辑 `200`、搜索可命中新建论文、统计摘要返回总量和代表作数量
4. 教师画像展示
   - 验证目的：确认画像首页和雷达接口仍返回核心分析数据
   - 预期结果：画像首页返回成果概览、近期成果和画像说明，雷达接口返回 6 个维度及维度洞察
5. 图谱展示与权限回退
   - 验证目的：确认图谱接口和教师跨账号访问限制仍正常
   - 预期结果：本人图谱返回 `meta / nodes / links / analysis`，教师访问其他教师图谱返回 `403`
6. 推荐查看与问答查看
   - 验证目的：确认推荐和问答两条教师主链路仍可稳定使用
   - 预期结果：推荐接口返回推荐结果和教师快照，问答接口返回答案和来源说明
7. 管理员关键操作
   - 验证目的：确认管理员查看与管理闭环仍正常
   - 预期结果：
     - 教师列表和教师详情可查看
     - 教师密码可重置
     - 指定教师画像、图谱、推荐、问答、学院看板都可查看
     - 推荐对比返回管理员分析和对比摘要

### 当前未完全自动化但已有标准化验证说明

- 登录失效后的前端回跳
  - 当前主要由 `npm run verify:baseline` 中的前端 helper 校验覆盖
  - 如需页面级确认，可人工验证：清空 `sessionStorage` 后访问受保护路由，应自动跳回登录页并保留回跳目标

## 本地验证顺序

推荐本地按以下顺序执行：

1. `cd frontend && npm ci`
2. `cd backend && python -m pip install -r requirements.txt`
3. `cd backend && python scripts\startup_preflight.py`
4. 若提示迁移未执行，则运行 `python manage.py migrate`
5. 再次执行 `python scripts\startup_preflight.py`
6. 执行 `python scripts\restore_demo_state.py`
7. 回到项目根目录后执行 `python backend/scripts/run_validation_pipeline.py`

如果只想做最小回归，可优先执行第 3 到第 7 步。

## CI 验证范围

仓库新增了最小 GitHub Actions 工作流：

- `.github/workflows/validation.yml`

当前 CI 范围保持克制，只覆盖最小闭环：

1. 安装前端依赖与后端依赖
2. 执行后端迁移
3. 执行统一自动验证入口

统一入口内部会自动覆盖：

- 后端启动前检查
- 后端 `manage.py check`
- 后端关键测试
- 统一主链路回归脚本
- 前端 `verify:baseline`

## 统一异常展示与回退说明

当前系统已补充最小统一异常治理，核心口径如下：

- 后端 API 优先返回统一错误结构：`detail + error + request_id`
- 前端优先从统一错误结构中读取：
  - 用户可见错误消息
  - 下一步建议
  - 请求编号
- 关键链路已补统一回退或降级提示：
  - 登录
  - 项目推荐
  - 智能问答
  - 学术图谱

当前标准错误结构示例：

```json
{
  "success": false,
  "detail": "当前账号没有权限执行此操作。",
  "request_id": "abc123def456",
  "error": {
    "code": "permission_denied",
    "message": "当前账号没有权限执行此操作。",
    "status": 403,
    "recoverable": true,
    "next_step": "请确认当前身份权限或切换账号后重试。",
    "request_id": "abc123def456"
  }
}
```

## 开发环境与正式环境差异

- 开发环境：
  - 默认 `DJANGO_DEBUG=1`
  - 后端控制台仍会保留完整异常堆栈，便于排查
  - API 响应不再直接向前端暴露 Django HTML 调试页，而是优先返回统一 JSON 错误结构
- 正式环境：
  - 应设置 `DJANGO_DEBUG=0`
  - 前后端都不应直接暴露调试页或堆栈信息
  - 用户只看到统一错误消息、下一步建议和请求编号

## 系统级错误排查顺序

建议排查顺序如下：

1. 先记录页面或接口返回的请求编号 `request_id`
2. 执行 `python backend/scripts/startup_preflight.py`
3. 确认迁移已执行：`cd backend && python manage.py migrate`
4. 执行统一验证入口：`python backend/scripts/run_validation_pipeline.py`
5. 根据请求编号查看后端控制台或服务日志
6. 如果是图谱或问答问题，再分别确认：
   - Neo4j 是否启用
   - MySQL 回退链路是否仍正常
   - 当前目标教师是否存在有效数据

## 推荐阅读顺序

### 交接与总览

- [系统文档索引与交付总览](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%96%87%E6%A1%A3%E7%B4%A2%E5%BC%95%E4%B8%8E%E4%BA%A4%E4%BB%98%E6%80%BB%E8%A7%88.md)
- [文档维护规则与交付资料机制-统一版](e:/Project/BiShe/docs/%E6%96%87%E6%A1%A3%E7%BB%B4%E6%8A%A4%E8%A7%84%E5%88%99%E4%B8%8E%E4%BA%A4%E4%BB%98%E8%B5%84%E6%96%99%E6%9C%BA%E5%88%B6-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [系统接口清单-统一版](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%8E%A5%E5%8F%A3%E6%B8%85%E5%8D%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [模块边界与系统最终形态说明-统一版](e:/Project/BiShe/docs/%E6%A8%A1%E5%9D%97%E8%BE%B9%E7%95%8C%E4%B8%8E%E7%B3%BB%E7%BB%9F%E6%9C%80%E7%BB%88%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [数据口径与风险记录-统一版](e:/Project/BiShe/docs/%E6%95%B0%E6%8D%AE%E5%8F%A3%E5%BE%84%E4%B8%8E%E9%A3%8E%E9%99%A9%E8%AE%B0%E5%BD%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [完整版本路线图与系统最终形态说明](e:/Project/BiShe/docs/%E5%AE%8C%E6%95%B4%E7%89%88%E6%9C%AC%E8%B7%AF%E7%BA%BF%E5%9B%BE%E4%B8%8E%E7%B3%BB%E7%BB%9F%E6%9C%80%E7%BB%88%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E.md)

### 演示与验收

- [最终答辩演示步骤-第三轮](e:/Project/BiShe/docs/%E6%9C%80%E7%BB%88%E7%AD%94%E8%BE%A9%E6%BC%94%E7%A4%BA%E6%AD%A5%E9%AA%A4-%E7%AC%AC%E4%B8%89%E8%BD%AE.md)
- [最终验收清单-第三轮](e:/Project/BiShe/docs/%E6%9C%80%E7%BB%88%E9%AA%8C%E6%94%B6%E6%B8%85%E5%8D%95-%E7%AC%AC%E4%B8%89%E8%BD%AE.md)
- [测试验证与工程化增强-过程文档](e:/Project/BiShe/docs/26-%E6%B5%8B%E8%AF%95%E9%AA%8C%E8%AF%81%E4%B8%8E%E5%B7%A5%E7%A8%8B%E5%8C%96%E5%A2%9E%E5%BC%BA-%E8%BF%87%E7%A8%8B%E6%96%87%E6%A1%A3.md)

### 多轮开发过程记录

- `docs/01` 到 `docs/37` 对应多轮增量开发过程文档

## 文档持续维护机制

当前仓库的文档分为四层：

- 根级入口：`README.md`
- 统一现状文档：用于描述当前可交付状态、接口、模块边界、数据口径、风险与路线
- 演示与验收文档：用于答辩、交接和验证
- 多轮过程文档：用于保留每一轮增量开发的阶段记录

建议查看当前状态时优先阅读以下文档，而不是只看单轮过程记录：

- [系统文档索引与交付总览](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%96%87%E6%A1%A3%E7%B4%A2%E5%BC%95%E4%B8%8E%E4%BA%A4%E4%BB%98%E6%80%BB%E8%A7%88.md)
- [文档维护规则与交付资料机制-统一版](e:/Project/BiShe/docs/%E6%96%87%E6%A1%A3%E7%BB%B4%E6%8A%A4%E8%A7%84%E5%88%99%E4%B8%8E%E4%BA%A4%E4%BB%98%E8%B5%84%E6%96%99%E6%9C%BA%E5%88%B6-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [系统接口清单-统一版](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%8E%A5%E5%8F%A3%E6%B8%85%E5%8D%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [模块边界与系统最终形态说明-统一版](e:/Project/BiShe/docs/%E6%A8%A1%E5%9D%97%E8%BE%B9%E7%95%8C%E4%B8%8E%E7%B3%BB%E7%BB%9F%E6%9C%80%E7%BB%88%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [数据口径与风险记录-统一版](e:/Project/BiShe/docs/%E6%95%B0%E6%8D%AE%E5%8F%A3%E5%BE%84%E4%B8%8E%E9%A3%8E%E9%99%A9%E8%AE%B0%E5%BD%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)

每轮功能变更完成后，至少同步检查以下文档是否需要更新：

- 接口有变化：更新“系统接口清单-统一版”
- 模块能力边界有变化：更新“模块边界与系统最终形态说明-统一版”
- 字段、统计或解释口径有变化：更新“数据口径与风险记录-统一版”
- 新增风险、环境要求或回退说明：更新“遗留问题记录”或风险文档
- 演示主链路、入口或口径有变化：更新“最终答辩演示步骤-第三轮”
- 每轮实现过程与验证结果：新增对应序号的过程文档

## 说明

- 当前登录态继续使用 `sessionStorage`
- 教师账号继续使用工号登录
- Neo4j 不是论文录入和教师画像展示的强依赖
- 当前工程文档已尽量对齐代码状态，但历史过程文档保留其阶段性语境
