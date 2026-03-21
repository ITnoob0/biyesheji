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
python scripts\startup_preflight.py
python manage.py migrate
python scripts\startup_preflight.py
python manage.py init_demo_teachers
python manage.py runserver
```

推荐顺序说明：

1. 先运行 `python scripts\startup_preflight.py`
2. 若提示存在未执行迁移，则先执行 `python manage.py migrate`
3. 迁移完成后再次运行 `python scripts\startup_preflight.py`
4. 启动前再执行 `python manage.py init_demo_teachers`
5. 最后执行 `python manage.py runserver`

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
python manage.py check
python manage.py test --keepdb --noinput users achievements graph_engine project_guides ai_assistant
python scripts\verify_development_16_24_regression.py
```

## 推荐阅读顺序

### 交接与总览

- [系统文档索引与交付总览](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%96%87%E6%A1%A3%E7%B4%A2%E5%BC%95%E4%B8%8E%E4%BA%A4%E4%BB%98%E6%80%BB%E8%A7%88.md)
- [系统接口清单-统一版](e:/Project/BiShe/docs/%E7%B3%BB%E7%BB%9F%E6%8E%A5%E5%8F%A3%E6%B8%85%E5%8D%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [模块边界与系统最终形态说明-统一版](e:/Project/BiShe/docs/%E6%A8%A1%E5%9D%97%E8%BE%B9%E7%95%8C%E4%B8%8E%E7%B3%BB%E7%BB%9F%E6%9C%80%E7%BB%88%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [数据口径与风险记录-统一版](e:/Project/BiShe/docs/%E6%95%B0%E6%8D%AE%E5%8F%A3%E5%BE%84%E4%B8%8E%E9%A3%8E%E9%99%A9%E8%AE%B0%E5%BD%95-%E7%BB%9F%E4%B8%80%E7%89%88.md)
- [完整版本路线图与系统最终形态说明](e:/Project/BiShe/docs/%E5%AE%8C%E6%95%B4%E7%89%88%E6%9C%AC%E8%B7%AF%E7%BA%BF%E5%9B%BE%E4%B8%8E%E7%B3%BB%E7%BB%9F%E6%9C%80%E7%BB%88%E5%BD%A2%E6%80%81%E8%AF%B4%E6%98%8E.md)

### 演示与验收

- [最终答辩演示步骤-第三轮](e:/Project/BiShe/docs/%E6%9C%80%E7%BB%88%E7%AD%94%E8%BE%A9%E6%BC%94%E7%A4%BA%E6%AD%A5%E9%AA%A4-%E7%AC%AC%E4%B8%89%E8%BD%AE.md)
- [最终验收清单-第三轮](e:/Project/BiShe/docs/%E6%9C%80%E7%BB%88%E9%AA%8C%E6%94%B6%E6%B8%85%E5%8D%95-%E7%AC%AC%E4%B8%89%E8%BD%AE.md)
- [测试验证与工程化增强-过程文档](e:/Project/BiShe/docs/26-%E6%B5%8B%E8%AF%95%E9%AA%8C%E8%AF%81%E4%B8%8E%E5%B7%A5%E7%A8%8B%E5%8C%96%E5%A2%9E%E5%BC%BA-%E8%BF%87%E7%A8%8B%E6%96%87%E6%A1%A3.md)

### 多轮开发过程记录

- `docs/01` 到 `docs/26` 对应多轮增量开发过程文档

## 说明

- 当前登录态继续使用 `sessionStorage`
- 教师账号继续使用工号登录
- Neo4j 不是论文录入和教师画像展示的强依赖
- 当前工程文档已尽量对齐代码状态，但历史过程文档保留其阶段性语境
