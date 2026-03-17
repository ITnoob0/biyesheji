# 成果批量导入-BibTeX 一期过程文档

## 1. 任务背景

本轮任务目标是在不破坏现有论文手工录入主链路的前提下，为系统补齐一个可演示、可验收、低风险的“一期成果批量导入”能力。

需求约束如下：

- 优先支持 BibTeX
- PDF 元数据解析可评估，但不强行纳入一期
- 导入失败不能影响既有论文数据
- 导入后的论文必须继续进入关键词、合作作者、图谱、画像统计链路

## 2. 改造前链路梳理

### 2.1 现有论文写入复用点

后端核心复用链路如下：

- `backend/achievements/serializers.py`
  - `PaperSerializer`
  - 已包含标题、期刊、引用次数、合作者、DOI 重复校验
- `backend/achievements/views.py`
  - `PaperViewSet.perform_create`
  - 创建后会调用 `sync_graph`
  - `sync_graph` 内部同时触发关键词提取与图谱同步

这意味着如果批量导入不复用 `PaperSerializer + sync_graph`，就会和现有手工录入链路分叉，风险较高。

### 2.2 前端现状

- 论文成果录入页面位于 `frontend/src/views/AchievementEntryView.vue`
- 该页面已是统一成果中心
- 论文 tab 仍是当前最核心工作流

因此前端适合采用“在论文 tab 内增加导入弹窗”的形式，而不是新增一个独立复杂工作台。

## 3. 方案选择

最终采用的最小可用方案：

1. 上传 BibTeX 文件
2. 后端解析并返回预览结果
3. 前端展示预览、状态与错误原因
4. 用户确认后，仅导入“可导入”项
5. 导入时逐条复用现有 `PaperSerializer` 保存

未纳入本轮的内容：

- PDF 自动元数据解析
- 大规模异步任务系统
- 全自动智能纠错与字段补全

原因：

- BibTeX 更稳定，字段结构更清晰
- PDF 元数据解析质量与依赖不稳定，容易拉高一期风险
- 当前项目阶段应优先做可演示闭环，而非重型导入平台

## 4. 实现内容

### 4.1 后端拆分

新增文件：

- `backend/achievements/bibtex_import.py`
- `backend/achievements/import_serializers.py`

设计原因：

- 将 BibTeX 解析逻辑从 view 中拆出，避免 `views.py` 继续膨胀
- 将预览请求与确认导入请求分别做 serializer，便于控制接口形状

### 4.2 BibTeX 解析能力

`bibtex_import.py` 实现了：

- BibTeX 文件字节解码
  - 兼容 `utf-8-sig`
  - 兼容 `utf-8`
  - 兼容 `gbk`
- 条目切分
- 字段提取
- 标题、摘要、期刊/会议、DOI、作者、年份归一化
- 作者列表转为合作者
- 当前登录教师姓名/工号从作者列表中排除，避免把本人误写入合作者

### 4.3 接口设计

基于现有 `PaperViewSet`，新增两个 action：

- `POST /api/achievements/papers/import/bibtex-preview/`
- `POST /api/achievements/papers/import/bibtex-confirm/`

选择 action 的原因：

- 路由风格与现有 `papers` 模块保持一致
- 前端更容易理解和复用
- 不需要再引入一套额外资源命名体系

### 4.4 预览策略

预览阶段会返回：

- 标准化后的论文字段
- `preview_status`
  - `ready`
  - `duplicate`
  - `invalid`
- `issues`
- 汇总统计

重复 DOI 处理策略：

- 若 DOI 已存在于当前教师账号下，标记为 `duplicate`
- 若同一批 BibTeX 文件内部 DOI 重复，后出现的条目标记为 `duplicate`

### 4.5 确认导入策略

确认导入时：

- 仅对前端确认提交的条目逐条处理
- 每条都重新走 `PaperSerializer`
- 每条都在独立事务中写入
- 保存成功后继续调用现有 `sync_graph`

这样做的结果是：

- 现有论文写入逻辑保持一致
- 单条失败不会污染其他条目
- 导入失败不会影响系统中原有论文数据

### 4.6 前端实现

新增组件：

- `frontend/src/views/achievement-entry/PaperBibtexImportDialog.vue`

设计原因：

- 避免把文件选择、预览状态、确认导入、错误提示全部堆进 `AchievementEntryView.vue`
- 保持现有手工录入表单几乎不变

页面改动：

- 在论文录入卡片头部新增 “BibTeX 批量导入” 按钮
- 打开导入弹窗后可：
  - 选择 `.bib / .bibtex` 文件
  - 查看预览状态
  - 确认导入可导入条目

同时明确标注：

- PDF 解析暂未纳入当前阶段验收，仅作为后续预留

## 5. 修改文件清单

- `backend/achievements/bibtex_import.py`
- `backend/achievements/import_serializers.py`
- `backend/achievements/views.py`
- `backend/achievements/tests.py`
- `frontend/src/views/AchievementEntryView.vue`
- `frontend/src/views/achievement-entry/PaperBibtexImportDialog.vue`
- `frontend/src/views/achievement-entry/constants.ts`
- `frontend/src/views/achievement-entry/types.ts`

## 6. 验证结果

执行通过：

1. `cmd /c E:\Project\anaconda\envs\biyesheji\python.exe manage.py check`
2. `cmd /c E:\Project\anaconda\envs\biyesheji\python.exe manage.py test achievements --keepdb`
3. `cmd /c npm run type-check`

自动化测试新增覆盖：

- BibTeX 预览可识别：
  - 可导入条目
  - 重复 DOI 条目
  - 关键字段异常条目
- BibTeX 确认导入后：
  - 仍写入 `Paper`
  - 仍写入合作者
  - 仍触发图谱同步

## 7. 数据库与迁移说明

本轮未新增或修改 Django 模型。  
无需执行数据库迁移。

## 8. 当前能力边界

当前一期批量导入能力的边界如下：

- 已支持：
  - BibTeX 文件上传
  - 预览
  - 重复 DOI 提示
  - 错误字段提示
  - 确认导入
- 未支持：
  - PDF 元数据自动解析
  - 批量导入项目、知识产权等其他成果类型
  - 超大文件异步导入

## 9. 遗留问题与后续建议

- 若后续扩展 PDF 导入，建议先做“PDF 元数据预解析 + 人工确认”，不要直接自动入库
- 若后续扩展其他成果类型导入，建议延续“预览 -> 确认 -> 逐条复用现有 serializer”的模式
- 目前 BibTeX 字段标准化为最小方案，复杂 LaTeX 转义与作者别名识别仍有提升空间
