# 53-主题切换动画 View Transition 修复说明

## 本次修复范围

- 仅修复前端深色 / 浅色切换动画实现。
- 不改主题 token、业务逻辑、路由逻辑和权限逻辑。

## 旧方案问题

- 旧实现基于独立的全屏 overlay。
- overlay 使用 `clip-path` 从右上角扩张，但本质上是一个单独的遮罩层。
- 用户看到的是“遮罩扫过页面”，而不是“页面内容本身在变色”。
- 这也更容易和底层组件自身的颜色过渡叠加，形成额外闪动感。

## 本次实现

- 删除全屏 overlay 动画规则。
- 改为基于 `document.startViewTransition(() => applyTheme())` 提交主题切换。
- 通过 `::view-transition-old(root)` 与 `::view-transition-new(root)` 对页面根视图快照做 reveal。
- reveal 起点继续取右上角主题切换按钮中心点。
- `::view-transition-new(root)` 使用圆形 `clip-path` 从 origin 向外扩张。

## 当前效果特点

- 动画过程中用户始终能看到页面内容快照。
- 新主题是以页面内容快照的形式逐步显现，而不是被纯色 / 渐变遮罩盖住。
- 主题状态在 transition update 回调中一次提交，避免 reveal 结束后再单独切一次主题。

## 降级策略

- 浏览器不支持 View Transitions API 时，直接切换主题，不再使用不透明全屏遮罩。
- 用户启用 reduced motion 时，同样降级为无大面积 reveal 的轻量切换。

## 本次涉及文件

- `frontend/src/utils/workspaceTheme.ts`
- `frontend/src/assets/workspace-system.css`

