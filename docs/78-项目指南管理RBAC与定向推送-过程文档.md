# 78-项目指南管理RBAC与定向推送-过程文档

## 一、任务目标
在 `project_guides` 模块内落地“系统管理员/学院管理员”项目指南管理能力，覆盖：
- RBAC 权限与数据边界隔离
- 指南状态机（`DRAFT / ACTIVE / URGENT / ARCHIVED`）
- 定向推送（仅 `ACTIVE / URGENT` 可执行）
- 前端管理页契约与交互同步

## 二、后端实现说明

### 1) 模型与迁移
- 修改文件：
  - `backend/project_guides/models.py`
  - `backend/project_guides/migrations/0004_academy_projectguide_scope_alter_projectguide_status_and_more.py`
- 关键改动：
  - 新增 `Academy` 模型（最小学院实体，供 FK 使用）
  - `ProjectGuide.status` 改为：
    - `DRAFT`（草稿）
    - `ACTIVE`（申报中）
    - `URGENT`（临近截止）
    - `ARCHIVED`（已结束）
  - 新增 `scope`：`GLOBAL / ACADEMY`
  - 新增 `academy` 外键（数据库列名 `academy_id`）
  - 保留兼容映射：`OPEN -> ACTIVE`, `CLOSED -> ARCHIVED`

### 2) 序列化与接口
- 修改文件：
  - `backend/project_guides/serializers.py`
  - `backend/project_guides/views.py`
  - `backend/project_guides/services.py`
- 关键改动：
  - `ProjectGuideSerializer` 新增/对齐字段：
    - `scope`, `scope_display`
    - `academy_id`, `academy_name`
  - `ProjectGuideViewSet.get_queryset` 实现 RBAC 数据隔离：
    - 系统管理员：全量可见
    - 学院管理员：可见 `GLOBAL` + 本学院 `ACADEMY`
    - 教师：仅可见活跃状态（`ACTIVE/URGENT`）且遵循范围隔离
  - `perform_create` / `perform_update`：
    - 学院管理员强制写入 `scope=ACADEMY` 且自动绑定本学院 `academy_id`
  - 新增 `@action(detail=True, methods=['post']) targeted_push`
    - 仅 `ACTIVE/URGENT` 可执行
    - 按 `target_keywords` 匹配教师（模拟推送）
    - 返回匹配人数 `matched_count`
  - 生命周期摘要与推荐服务口径更新为新状态集，并保留兼容字段，避免旧链路回归失败

## 三、测试驱动开发（TDD）落地

### 1) 新增核心业务测试
- 修改文件：`backend/project_guides/tests.py`
- 新增测试类：`ProjectGuideAdminRbacPushTests`
- 对应 4 个场景：
  1. 系统管理员全局创建 + 状态流转 + 定向推送
  2. 学院管理员创建时强制降级为 `ACADEMY` 并自动绑定本学院
  3. 跨学院数据隔离（列表可见范围 + 删除越权拦截）
  4. `ARCHIVED` 指南调用推送被 400 拦截

### 2) 测试命令与结果摘要
- 全量回归：
  - 命令：`python manage.py test project_guides --keepdb`
  - 结果：`Ran 18 tests ... OK`（0 failures）
- 核心 4 场景单独验证：
  - 命令：`python manage.py test project_guides.tests.ProjectGuideAdminRbacPushTests --keepdb -v 2`
  - 结果：4/4 通过（每个场景均 `ok`）

## 四、前端契约与页面实现

### 1) TypeScript 契约对齐
- 修改文件：
  - `frontend/src/types/projectGuides.ts`
  - `frontend/src/views/project-guides/types.ts`
- 关键改动：
  - `GuideStatus` 对齐为 `DRAFT/ACTIVE/URGENT/ARCHIVED`
  - 新增 `GuideScope`（`GLOBAL/ACADEMY`）
  - `ProjectGuideRecord` 新增 `scope/scope_display/academy_id/academy_name`
  - 新增 `GuideTargetedPushResponse`
  - 生命周期摘要类型新增 `active_count/urgent_count/stale_active_count`

### 2) 管理页交互实现
- 修改文件：`frontend/src/views/ProjectGuideManagementView.vue`
- 关键改动：
  - 顶部筛选新增“发布范围”下拉
  - 状态色：
    - `DRAFT` 灰
    - `ACTIVE` 绿
    - `URGENT` 红
    - `ARCHIVED` 失效色
  - 操作列新增“定向推送”（仅 `ACTIVE/URGENT`）
  - 学院管理员前端表单隐藏范围选择并固定为“本学院”
  - 学院管理员对 `GLOBAL` 指南仅可查看，不展示管理操作

## 五、数据库迁移执行记录
- 是否执行迁移：**已执行**
- 命令：
  1. `python manage.py makemigrations project_guides`
  2. `python manage.py migrate`
- 结果：`project_guides.0004... OK`

## 六、静态检查与构建验证
- 后端检查：
  - `python manage.py check` -> `System check identified no issues`
- 前端静态类型检查：
  - `npm run type-check` -> 通过
- 前端构建（补充验证）：
  - `npm run build` -> 通过（仅保留既有 chunk size warning）
