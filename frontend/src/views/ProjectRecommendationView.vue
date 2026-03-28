<template>
  <div class="recommendation-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">Guide Recommendation</p>
        <h1 class="workspace-hero__title">项目指南推荐</h1>
        <p class="hero-text workspace-hero__text">
          面向
          <strong>{{ recommendationData?.teacher_snapshot.teacher_name || currentUser?.real_name || currentUser?.username || '当前教师' }}</strong>
          的轻量推荐结果，强调可解释规则，不依赖 RAG 或复杂模型。
        </p>
      </div>
      <div class="hero-actions workspace-page-actions">
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button plain @click="historyVisible = true">查看历史</el-button>
        <el-button plain @click="openAssistantDemo">问答说明</el-button>
        <el-button type="primary" :loading="loading" @click="loadRecommendations">刷新推荐</el-button>
      </div>
    </section>

    <section v-if="linkContext" class="content-shell link-context-shell">
      <el-alert
        :title="linkContextTitle"
        type="info"
        :description="linkContextDescription"
        :closable="false"
        show-icon
      />
    </section>

    <section class="content-shell control-shell">
      <el-alert
        v-if="errorNotice"
        class="page-error-alert"
        :title="errorNotice.message"
        type="warning"
        :description="[errorNotice.guidance, errorNotice.requestHint].filter(Boolean).join(' ')"
        :closable="false"
        show-icon
      />

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>推荐筛选与排序</span>
            <el-tag type="success" effect="plain">第三轮展示增强</el-tag>
          </div>
        </template>

        <div class="control-grid">
          <el-select
            v-if="currentUser?.is_admin"
            v-model="selectedTeacherId"
            clearable
            filterable
            placeholder="管理员可切换教师视角"
            @change="handleTeacherChanged"
          >
            <el-option
              v-for="teacher in teacherOptions"
              :key="teacher.id"
              :label="`${teacher.real_name || teacher.username}（${teacher.department || '未填写院系'}）`"
              :value="teacher.id"
            />
          </el-select>

          <el-select
            v-if="currentUser?.is_admin"
            v-model="compareTeacherId"
            clearable
            filterable
            placeholder="管理员可选择第二位教师对比"
            @change="handleCompareTeacherChanged"
          >
            <el-option
              v-for="teacher in teacherOptions.filter(item => item.id !== selectedTeacherId)"
              :key="teacher.id"
              :label="`${teacher.real_name || teacher.username}（${teacher.department || '未填写院系'}）`"
              :value="teacher.id"
            />
          </el-select>

          <el-input
            v-model="searchKeyword"
            clearable
            placeholder="按指南标题 / 发布单位 / 摘要搜索"
          />

          <el-select v-model="selectedFocusTag" clearable placeholder="按推荐类型筛选">
            <el-option v-for="tag in focusTagOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>

          <el-select v-model="selectedGuideLevel" clearable placeholder="按指南级别筛选">
            <el-option v-for="item in guideLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-select v-model="selectedPriority" clearable placeholder="按关注等级筛选">
            <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
          </el-select>

          <el-select v-model="selectedLabel" clearable placeholder="按推荐标签筛选">
            <el-option v-for="tag in labelOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>

          <el-select v-model="selectedSort" placeholder="排序方式">
            <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-switch v-model="favoritesOnly" active-text="仅看已收藏" inactive-text="全部结果" />
        </div>

        <div class="tag-list">
          <el-tag type="info" effect="plain">{{ recommendationData?.data_meta.current_strategy || '规则增强型推荐' }}</el-tag>
          <el-tag type="warning" effect="plain">{{ recommendationData?.data_meta.sorting_note || '默认按推荐分数排序' }}</el-tag>
          <el-tag type="success" effect="plain">结果数 {{ recommendationItems.length }}</el-tag>
          <el-tag type="primary" effect="plain">收藏 {{ favoriteGuideIds.length }}</el-tag>
          <el-tag v-if="recommendationData?.comparison_teacher_snapshot" type="primary" effect="plain">
            已开启教师对比
          </el-tag>
        </div>
      </el-card>
    </section>

    <section class="snapshot-grid content-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>教师画像摘要</span>
            <el-tag type="primary" effect="plain">推荐输入</el-tag>
          </div>
        </template>
        <div class="snapshot-block">
          <strong>研究标签</strong>
          <div class="tag-list">
            <el-tag v-for="tag in recommendationData?.teacher_snapshot.keywords || []" :key="tag" effect="plain">{{ tag }}</el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.keywords || []).length" class="muted">暂无研究标签，可先完善教师档案或论文关键词。</span>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>学科/院系</strong>
          <div class="tag-list">
            <el-tag v-for="tag in recommendationData?.teacher_snapshot.disciplines || []" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.disciplines || []).length" class="muted">暂无学科信息。</span>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>近三年成果活跃度</strong>
          <p class="muted">
            {{ recommendationData?.teacher_snapshot.recent_activity_count ?? 0 }} 项
            <span v-if="recommendationData?.teacher_snapshot.activity_level"> · {{ recommendationData?.teacher_snapshot.activity_level }}</span>
          </p>
        </div>
        <div class="snapshot-block">
          <strong>画像优势维度</strong>
          <div class="tag-list">
            <el-tag
              v-for="item in recommendationData?.teacher_snapshot.portrait_top_dimensions || []"
              :key="`portrait-${item.key}`"
              type="warning"
              effect="plain"
            >
              {{ item.name }} {{ item.value }}
            </el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.portrait_top_dimensions || []).length" class="muted">暂无画像维度摘要。</span>
          </div>
        </div>
      </el-card>

      <el-card v-if="recommendationData?.comparison_teacher_snapshot" shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>对比教师摘要</span>
            <el-tag type="success" effect="plain">管理员对比</el-tag>
          </div>
        </template>
        <div class="snapshot-block">
          <strong>{{ recommendationData?.comparison_teacher_snapshot?.teacher_name }}</strong>
          <div class="tag-list">
            <el-tag
              v-for="tag in recommendationData?.comparison_teacher_snapshot?.keywords || []"
              :key="`compare-kw-${tag}`"
              type="warning"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>学科/院系</strong>
          <div class="tag-list">
            <el-tag
              v-for="tag in recommendationData?.comparison_teacher_snapshot?.disciplines || []"
              :key="`compare-dis-${tag}`"
              type="success"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>近三年成果活跃度</strong>
          <p class="muted">
            {{ recommendationData?.comparison_teacher_snapshot?.recent_activity_count ?? 0 }} 项
            <span v-if="recommendationData?.comparison_teacher_snapshot?.activity_level">
              · {{ recommendationData?.comparison_teacher_snapshot?.activity_level }}
            </span>
          </p>
        </div>
        <div class="snapshot-block">
          <strong>对比摘要</strong>
          <p class="muted">
            当前教师更优 {{ recommendationData?.comparison_summary?.primary_better_count ?? 0 }} 条
            · 对比教师更优 {{ recommendationData?.comparison_summary?.compare_better_count ?? 0 }} 条
            · 持平 {{ recommendationData?.comparison_summary?.tie_count ?? 0 }} 条
          </p>
          <p class="muted" v-if="recommendationData?.comparison_summary?.biggest_gap_title">
            差异最大：{{ recommendationData?.comparison_summary?.biggest_gap_title }}
          </p>
        </div>
      </el-card>

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>推荐说明</span>
            <el-tag type="warning" effect="plain">可解释规则</el-tag>
          </div>
        </template>
        <div class="meta-list">
          <div class="meta-item">
            <strong>规则来源</strong>
            <p>{{ recommendationData?.data_meta.source_note || '基于研究方向、关键词、学科与活跃度的轻量推荐。' }}</p>
          </div>
          <div class="meta-item">
            <strong>当前阶段说明</strong>
            <p>{{ recommendationData?.data_meta.acceptance_scope || '本能力属于当前阶段扩展方向。' }}</p>
          </div>
          <div class="meta-item">
            <strong>后续扩展接口预留</strong>
            <p>{{ recommendationData?.data_meta.future_extension_hint || '后续可在本接口基础上扩展智能推荐能力。' }}</p>
          </div>
          <div class="meta-item">
            <strong>当前路线说明</strong>
            <p>{{ recommendationData?.data_meta.current_strategy || '当前仍以规则增强路线为主，未进入复杂模型推荐。' }}</p>
          </div>
          <div class="meta-item">
            <strong>反馈与历史边界</strong>
            <p>{{ recommendationData?.data_meta.feedback_scope_note || '当前反馈仅采集轻量显式信号。' }}</p>
            <p>{{ recommendationData?.data_meta.history_scope_note || '当前历史记录的是规则增强结果快照。' }}</p>
            <p>{{ recommendationData?.data_meta.feedback_ranking_boundary || '当前仅预留反馈影响排序边界。' }}</p>
          </div>
        </div>
      </el-card>
    </section>

    <section class="content-shell snapshot-grid">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>画像联动说明</span>
            <el-tag type="warning" effect="plain">推荐与画像关系</el-tag>
          </div>
        </template>
        <div class="snapshot-block">
          <strong>当前画像总分</strong>
          <p class="muted">{{ recommendationData?.portrait_link_summary?.teacher_total_score ?? 0 }} 分</p>
        </div>
        <div class="snapshot-block">
          <strong>优先参考维度</strong>
          <div class="tag-list">
            <el-tag
              v-for="item in recommendationData?.portrait_link_summary?.top_dimensions || []"
              :key="`link-${item.key}`"
              type="success"
              effect="plain"
            >
              {{ item.name }} · {{ item.value }}
            </el-tag>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>联动说明</strong>
          <p class="muted">{{ recommendationData?.portrait_link_summary?.link_note || recommendationData?.data_meta.portrait_link_note }}</p>
        </div>
      </el-card>

      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>推荐历史预览</span>
            <el-tag type="info" effect="plain">持续积累</el-tag>
          </div>
        </template>
        <div class="meta-list">
          <div class="meta-item">
            <strong>历史批次</strong>
            <p>{{ recommendationData?.history_batch_token || '当前尚未生成批次' }}</p>
          </div>
          <div class="meta-item">
            <strong>反馈统计</strong>
            <div class="tag-list">
              <el-tag
                v-for="(count, label) in recommendationData?.feedback_summary?.distribution || {}"
                :key="`feedback-${label}`"
                type="primary"
                effect="plain"
              >
                {{ label }} · {{ count }}
              </el-tag>
              <span v-if="!Object.keys(recommendationData?.feedback_summary?.distribution || {}).length" class="muted">当前尚未积累反馈信号。</span>
            </div>
          </div>
          <div class="meta-item">
            <strong>闭环概览</strong>
            <div class="tag-list">
              <el-tag type="success" effect="plain">
                已反馈 {{ recommendationData?.feedback_summary?.responded_guide_count ?? 0 }} / {{ recommendationData?.feedback_summary?.current_recommendation_count ?? recommendationItems.length }}
              </el-tag>
              <el-tag type="primary" effect="plain">覆盖率 {{ recommendationData?.feedback_summary?.response_rate ?? 0 }}%</el-tag>
              <el-tag type="warning" effect="plain">收藏 {{ recommendationData?.feedback_summary?.favorite_count ?? favoriteGuideIds.length }}</el-tag>
              <el-tag type="success" effect="plain">计划申报 {{ recommendationData?.feedback_summary?.plan_to_apply_count ?? 0 }}</el-tag>
              <el-tag type="info" effect="plain">已申报 {{ recommendationData?.feedback_summary?.applied_count ?? 0 }}</el-tag>
            </div>
          </div>
          <div class="meta-item">
            <strong>最近历史</strong>
            <div class="history-preview-list">
              <div v-for="item in recommendationHistory.slice(0, 4)" :key="item.id" class="history-preview-item">
                <strong>{{ item.guide_title_snapshot }}</strong>
                <p>{{ item.priority_label }} · {{ item.recommendation_score }} 分</p>
                <p>{{ item.feedback_label || '未反馈' }} · {{ item.generated_at }}</p>
              </div>
              <p v-if="!recommendationHistory.length" class="muted">当前尚无推荐历史记录。</p>
            </div>
          </div>
          <div class="meta-item">
            <strong>最近反馈</strong>
            <div class="history-preview-list">
              <div
                v-for="item in recommendationData?.feedback_summary?.recent_feedback_items || []"
                :key="`${item.guide_id}-${item.last_feedback_at}`"
                class="history-preview-item"
              >
                <strong>{{ item.guide_title }}</strong>
                <p>{{ item.feedback_label }} · {{ item.last_feedback_at }}</p>
                <p v-if="item.feedback_note" class="muted">{{ item.feedback_note }}</p>
              </div>
              <p v-if="!(recommendationData?.feedback_summary?.recent_feedback_items || []).length" class="muted">当前还没有可回看的反馈记录。</p>
            </div>
          </div>
          <div class="meta-item">
            <strong>策略边界</strong>
            <p>{{ recommendationData?.feedback_summary?.strategy_note || recommendationData?.data_meta.feedback_scope_note }}</p>
          </div>
        </div>
      </el-card>
    </section>

    <section v-if="currentUser?.is_admin && adminAnalysisCards.length" class="content-shell admin-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>管理员推荐分析</span>
            <el-tag type="primary" effect="plain">管理视角增强</el-tag>
          </div>
        </template>
        <div class="admin-card-grid">
          <div v-for="item in adminAnalysisCards" :key="item.label" class="admin-card">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
            <p>{{ item.helper }}</p>
          </div>
        </div>
        <div class="tag-section">
          <span class="tag-label">高频推荐标签</span>
          <div class="tag-list">
            <el-tag
              v-for="item in recommendationData?.admin_analysis?.top_labels || []"
              :key="item.label"
              type="success"
              effect="plain"
            >
              {{ item.label }} · {{ item.count }}
            </el-tag>
          </div>
        </div>
        <div class="tag-section">
          <span class="tag-label">响应情况</span>
          <div class="tag-list">
            <el-tag type="success" effect="plain">反馈覆盖 {{ recommendationData?.admin_analysis?.response_rate ?? 0 }}%</el-tag>
            <el-tag type="primary" effect="plain">正向反馈 {{ recommendationData?.admin_analysis?.positive_feedback_count ?? 0 }}</el-tag>
            <el-tag type="warning" effect="plain">暂不相关 {{ recommendationData?.admin_analysis?.negative_feedback_count ?? 0 }}</el-tag>
            <el-tag type="info" effect="plain">计划申报 {{ recommendationData?.admin_analysis?.plan_to_apply_count ?? 0 }}</el-tag>
            <el-tag type="success" effect="plain">已申报 {{ recommendationData?.admin_analysis?.applied_count ?? 0 }}</el-tag>
          </div>
        </div>
      </el-card>
    </section>

    <div v-if="!loading && !recommendationItems.length" class="content-shell empty-shell workspace-empty-state">
      <el-empty :description="recommendationData?.empty_state || '当前暂无匹配的项目指南推荐。'" />
    </div>

    <section v-else id="recommendation-evidence-section" class="recommendation-list content-shell">
      <el-card
        v-for="item in recommendationItems"
        :id="recommendationCardId(item.id)"
        :key="item.id"
        class="recommendation-card workspace-surface-card"
        :class="{ 'recommendation-card--active': isRecommendationCardActive(item) }"
        shadow="hover"
      >
        <div class="recommendation-head">
          <div>
            <div class="title-row">
              <h2>{{ item.title }}</h2>
              <div class="tag-list compact-row">
                <el-tag type="success" effect="plain">匹配度 {{ item.recommendation_score }}</el-tag>
                <el-tag type="primary" effect="plain">{{ item.priority_label }}</el-tag>
                <el-tag type="warning" effect="plain">{{ item.rule_profile_display }}</el-tag>
              </div>
            </div>
            <p class="subline">
              {{ item.issuing_agency }} · {{ item.guide_level_display }} · {{ item.status_display }}
              <span v-if="item.application_deadline"> · 截止 {{ item.application_deadline }}</span>
            </p>
          </div>
          <div class="compact-row">
            <el-button
              link
              :disabled="!interactionEnabled"
              :type="isFavorited(item.id) ? 'warning' : 'info'"
              @click="toggleFavorite(item)"
            >
              {{ isFavorited(item.id) ? '取消收藏' : '收藏' }}
            </el-button>
            <el-button link type="success" @click="openAssistantDemo(item.id)">智能解读</el-button>
            <el-button v-if="item.source_url" link type="primary" @click="openGuide(item.source_url)">查看来源</el-button>
          </div>
        </div>

        <p class="summary">{{ item.summary }}</p>

        <div class="tag-section">
          <span class="tag-label">推荐概括</span>
          <p class="summary">{{ item.recommendation_summary }}</p>
        </div>

        <div class="tag-section">
          <span class="tag-label">推荐类型</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.match_category_tags" :key="tag" type="primary" effect="plain">{{ tag }}</el-tag>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">推荐标签</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.recommendation_labels" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
            <el-tag v-for="tag in item.recommendation_tags" :key="`guide-${tag}`" effect="plain">{{ tag }}</el-tag>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">主题关键词</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.target_keywords" :key="tag" effect="plain">{{ tag }}</el-tag>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">推荐理由</span>
          <ul class="reason-list">
            <li v-for="reason in item.recommendation_reasons" :key="reason">{{ reason }}</li>
          </ul>
        </div>

        <div class="tag-section">
          <span class="tag-label">解释维度</span>
          <div class="dimension-grid">
            <div v-for="dimension in item.explanation_dimensions" :key="dimension.key" class="dimension-card">
              <div class="dimension-card-head">
                <strong>{{ dimension.label }}</strong>
                <span>+{{ dimension.score }}</span>
              </div>
              <el-progress :percentage="Math.min(Number(dimension.share_percent || 0), 100)" :stroke-width="8" :show-text="false" />
              <p>{{ dimension.detail }}</p>
              <p>贡献占比 {{ dimension.share_percent }}%</p>
            </div>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">画像联动</span>
          <div class="dimension-grid">
            <div v-for="dimension in item.portrait_dimension_links" :key="`portrait-${dimension.key}`" class="dimension-card">
              <div class="dimension-card-head">
                <strong>{{ dimension.label }}</strong>
                <span>{{ dimension.current_value }}</span>
              </div>
              <p>{{ dimension.detail }}</p>
              <p>联动关系：{{ dimension.relation }}</p>
              <div class="dimension-card-actions">
                <el-button link type="primary" @click="openPortraitDimensionEvidence(dimension.key)">查看画像维度</el-button>
                <el-button link type="warning" @click="openAssistantDemo(item.id)">问答说明</el-button>
              </div>
            </div>
            <p v-if="!item.portrait_dimension_links.length" class="muted">当前暂无显著画像联动说明。</p>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">支撑成果</span>
          <div class="dimension-grid">
            <div
              v-for="record in item.supporting_records"
              :key="`${record.type}-${record.id}`"
              class="dimension-card"
            >
              <div class="dimension-card-head">
                <strong>{{ record.title }}</strong>
                <span>{{ record.date_acquired }}</span>
              </div>
              <p>{{ record.detail }}</p>
              <p>{{ record.reason }}</p>
              <div class="dimension-card-actions">
                <el-button
                  v-if="!currentUser?.is_admin"
                  link
                  type="primary"
                  @click="openSupportingRecordEvidence(record.type, record.id)"
                >
                  查看支撑成果
                </el-button>
                <el-button link type="success" @click="openPortraitDimensionEvidence(mapAchievementTypeToPortraitDimension(record.type))">
                  查看画像维度
                </el-button>
              </div>
            </div>
            <p v-if="!item.supporting_records.length" class="muted">当前暂无可直接定位的支撑成果，将继续保留画像维度和指南规则解释。</p>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-label">匹配命中</span>
          <div class="tag-list">
            <el-tag v-for="tag in item.matched_keywords" :key="`kw-${tag}`" type="warning" effect="plain">{{ tag }}</el-tag>
            <el-tag v-for="tag in item.matched_disciplines" :key="`dis-${tag}`" type="success" effect="plain">{{ tag }}</el-tag>
            <span v-if="!item.matched_keywords.length && !item.matched_disciplines.length" class="muted">当前推荐更多基于成果活跃度与申报窗口判断。</span>
          </div>
        </div>

        <div v-if="recommendationData?.comparison_teacher_snapshot" class="tag-section">
          <span class="tag-label">教师对比</span>
          <div class="compare-panel">
            <el-tag type="primary" effect="plain">当前教师 {{ item.recommendation_score }} 分</el-tag>
            <el-tag type="success" effect="plain">{{ recommendationData?.comparison_teacher_snapshot?.teacher_name }} {{ item.compare_score }} 分</el-tag>
            <el-tag :type="item.compare_delta >= 0 ? 'warning' : 'danger'" effect="plain">
              差值 {{ item.compare_delta >= 0 ? '+' : '' }}{{ item.compare_delta }}
            </el-tag>
          </div>
          <p class="muted">{{ item.comparison_summary }}</p>
        </div>

        <div class="tag-section">
          <span class="tag-label">反馈采集</span>
          <div class="compact-row feedback-row">
            <el-tag v-if="item.latest_feedback_label" type="success" effect="plain">当前反馈：{{ item.latest_feedback_label }}</el-tag>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'INTERESTED')">感兴趣</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'PLAN_TO_APPLY')">计划申报</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'APPLIED')">已申报</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'NOT_RELEVANT')">暂不相关</el-button>
          </div>
          <p v-if="item.last_feedback_at" class="muted">最近反馈时间：{{ item.last_feedback_at }}</p>
          <p v-if="item.latest_feedback_note" class="muted">{{ item.latest_feedback_note }}</p>
        </div>

        <div class="footer-line">
          <span v-if="item.support_amount">资助强度：{{ item.support_amount }}</span>
          <span v-if="item.eligibility_notes">申报要求：{{ item.eligibility_notes }}</span>
        </div>
      </el-card>
    </section>

    <el-drawer v-model="historyVisible" title="推荐历史记录" size="540px">
      <div class="history-drawer">
        <div v-for="item in recommendationHistory" :key="item.id" class="history-drawer-item">
          <div class="dimension-card-head">
            <strong>{{ item.guide_title_snapshot }}</strong>
            <el-tag type="primary" effect="plain">{{ item.recommendation_score }} 分</el-tag>
          </div>
          <p class="muted">{{ item.priority_label }} · {{ item.generated_at }}</p>
          <div class="tag-list">
            <el-tag size="small" effect="plain">{{ item.rule_profile_snapshot }}</el-tag>
            <el-tag v-if="item.feedback_label" size="small" type="success" effect="plain">{{ item.feedback_label }}</el-tag>
            <el-tag v-if="item.is_favorited_snapshot" size="small" type="warning" effect="plain">已收藏</el-tag>
          </div>
          <p v-if="item.requested_by_name" class="muted">触发账号：{{ item.requested_by_name }}</p>
        </div>
        <p v-if="!recommendationHistory.length" class="muted">当前尚无推荐历史。</p>
      </div>
    </el-drawer>

    <el-dialog
      v-model="feedbackDialogVisible"
      width="520px"
      :title="feedbackDialogGuideTitle ? `记录反馈：${feedbackDialogGuideTitle}` : '记录推荐反馈'"
    >
      <div class="meta-list">
        <div class="meta-item">
          <strong>反馈信号</strong>
          <div class="tag-list">
            <el-tag type="success" effect="plain">{{ feedbackSignalLabel }}</el-tag>
            <span class="muted">当前只采集轻量显式反馈，用于规则复盘和后续策略优化，不直接重排推荐。</span>
          </div>
        </div>
        <div class="meta-item">
          <strong>反馈备注</strong>
          <el-input
            v-model="feedbackDialogNote"
            type="textarea"
            :rows="4"
            maxlength="300"
            show-word-limit
            placeholder="可选填写：为什么感兴趣、为什么暂不相关、预计何时申报等。"
          />
        </div>
      </div>
      <template #footer>
        <div class="compact-row">
          <el-button @click="feedbackDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="feedbackSubmitting" @click="confirmFeedback">保存反馈</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import {
  buildCrossModuleQuery,
  buildScopedTeacherQuery,
  focusEvidenceSection,
  mapAchievementTypeToPortraitDimension,
  parseCrossModuleLink,
  resolvePortraitRoute,
} from '../utils/crossModuleLinking'
import type { TeacherAccountResponse } from '../types/users'
import { buildDistributionCards, buildRecommendationSortOptions, filterRecommendationItems, sortRecommendationItems } from './project-guides/recommendationHelpers.js'
import type { RecommendationFeedbackSignal, RecommendationHistoryItem, RecommendationItem, RecommendationResponse } from './project-guides/types'

const route = useRoute()
const router = useRouter()
const currentUser = ref<SessionUser | null>(null)
const loading = ref(false)
const recommendationData = ref<RecommendationResponse | null>(null)
const teacherOptions = ref<TeacherAccountResponse[]>([])
const selectedTeacherId = ref<number | undefined>(undefined)
const compareTeacherId = ref<number | undefined>(undefined)
const searchKeyword = ref('')
const selectedFocusTag = ref('')
const selectedGuideLevel = ref('')
const selectedPriority = ref('')
const selectedLabel = ref('')
const favoritesOnly = ref(false)
const selectedSort = ref('score')
const favoriteGuideIds = ref<number[]>([])
const recommendationHistory = ref<RecommendationHistoryItem[]>([])
const historyVisible = ref(false)
const errorNotice = ref<{ message: string; guidance: string; requestHint: string } | null>(null)
const linkContext = computed(() => parseCrossModuleLink(route.query))
const feedbackDialogVisible = ref(false)
const feedbackSubmitting = ref(false)
const feedbackDialogGuideId = ref<number | null>(null)
const feedbackDialogGuideTitle = ref('')
const feedbackDialogSignal = ref<RecommendationFeedbackSignal>('INTERESTED')
const feedbackDialogNote = ref('')

const sortOptions = buildRecommendationSortOptions()
const feedbackSignalLabelMap: Record<Exclude<RecommendationFeedbackSignal, ''>, string> = {
  INTERESTED: '感兴趣',
  NOT_RELEVANT: '暂不相关',
  PLAN_TO_APPLY: '计划申报',
  APPLIED: '已申报',
}

const targetTeacherId = computed(() => selectedTeacherId.value || Number(route.query.user_id) || currentUser.value?.id || 0)

const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'portrait') {
    return '当前从画像模块进入，已定位到推荐证据区。'
  }
  if (linkContext.value?.source === 'achievement') {
    return '当前从成果模块进入，已定位到对应推荐证据区。'
  }
  if (linkContext.value?.source === 'assistant') {
    return '当前从问答来源卡片回跳，已定位到对应推荐证据区。'
  }
  return '当前已定位到推荐证据区。'
})

const linkContextDescription = computed(
  () =>
    linkContext.value?.note ||
    '当前推荐页只展示真实指南、真实画像维度联动和真实支撑成果；管理员仍不会获得教师成果录入权限。',
)

const focusTagOptions = computed(() => {
  const tags = new Set<string>()
  ;(recommendationData.value?.recommendations || []).forEach(item => {
    ;(item.match_category_tags || []).forEach(tag => tags.add(tag))
  })
  return [...tags]
})

const labelOptions = computed(() => {
  const labels = new Set<string>()
  ;(recommendationData.value?.recommendations || []).forEach(item => {
    ;(item.recommendation_labels || []).forEach(label => labels.add(label))
  })
  return [...labels]
})

const priorityOptions = ['重点关注', '建议关注', '可作备选']

const guideLevelOptions = [
  { label: '国家级', value: 'NATIONAL' },
  { label: '省部级', value: 'PROVINCIAL' },
  { label: '市厅级', value: 'MUNICIPAL' },
  { label: '企业合作', value: 'ENTERPRISE' },
]

const adminAnalysisCards = computed(() => buildDistributionCards(recommendationData.value?.admin_analysis || null))

const recommendationItems = computed<RecommendationItem[]>(() => {
  const filtered = filterRecommendationItems(
    recommendationData.value?.recommendations || [],
    searchKeyword.value,
    selectedFocusTag.value,
    {
      level: selectedGuideLevel.value,
      priority: selectedPriority.value,
      label: selectedLabel.value,
      favoritesOnly: favoritesOnly.value,
      favoriteIds: favoriteGuideIds.value,
    },
  )
  return sortRecommendationItems(filtered, selectedSort.value)
})

const interactionEnabled = computed(() => Boolean(recommendationData.value?.data_meta.interaction_enabled))
const feedbackSignalLabel = computed(() =>
  feedbackDialogSignal.value ? feedbackSignalLabelMap[feedbackDialogSignal.value as Exclude<RecommendationFeedbackSignal, ''>] : '',
)

const loadTeacherOptions = async () => {
  if (!currentUser.value?.is_admin) return

  const { data } = await axios.get<TeacherAccountResponse[]>('/api/users/teachers/')
  teacherOptions.value = data || []
}

const loadRecommendations = async () => {
  loading.value = true
  errorNotice.value = null
  try {
    const params: Record<string, number> | undefined =
      currentUser.value?.is_admin && (selectedTeacherId.value || route.query.user_id || compareTeacherId.value)
        ? {
            ...(selectedTeacherId.value || route.query.user_id ? { user_id: Number(selectedTeacherId.value || route.query.user_id) } : {}),
            ...(compareTeacherId.value ? { compare_user_id: Number(compareTeacherId.value) } : {}),
          }
        : undefined

    const { data } = await axios.get<RecommendationResponse>('/api/project-guides/recommendations/', { params })
    recommendationData.value = data
    favoriteGuideIds.value = data.favorites?.guide_ids || []
    recommendationHistory.value = data.history_preview || []
    await nextTick()
    focusRecommendationEvidence()
  } catch (error) {
    console.error(error)
    errorNotice.value = buildApiErrorNotice(error, {
      fallbackMessage: '项目指南推荐暂时不可用，请稍后重试。',
      fallbackGuidance: '你仍可返回画像主页、个人中心或成果中心继续操作，也可以稍后刷新推荐结果。',
    })
    ElMessage.warning(errorNotice.value.message)
  } finally {
    loading.value = false
  }
}

const recommendationCardId = (guideId: number) => `recommendation-card-${guideId}`

const matchesRecommendationContext = (item: RecommendationItem) => {
  if (linkContext.value?.guideId && item.id === linkContext.value.guideId) {
    return true
  }
  if (linkContext.value?.dimensionKey && item.portrait_dimension_links.some(dimension => dimension.key === linkContext.value?.dimensionKey)) {
    return true
  }
  if (
    linkContext.value?.recordType &&
    linkContext.value?.recordId &&
    item.supporting_records.some(record => record.type === linkContext.value?.recordType && record.id === linkContext.value?.recordId)
  ) {
    return true
  }
  return false
}

const isRecommendationCardActive = (item: RecommendationItem) => matchesRecommendationContext(item)

const focusRecommendationEvidence = () => {
  if (!linkContext.value?.section) {
    return
  }

  const matchedGuideId = recommendationItems.value.find(item => matchesRecommendationContext(item))?.id
  focusEvidenceSection(
    'recommendation-evidence-section',
    matchedGuideId ? recommendationCardId(matchedGuideId) : undefined,
  )
}

const loadRecommendationHistory = async () => {
  const params: Record<string, number> | undefined =
    currentUser.value?.is_admin && (selectedTeacherId.value || route.query.user_id)
      ? { user_id: Number(selectedTeacherId.value || route.query.user_id) }
      : undefined
  const { data } = await axios.get<{ history: RecommendationHistoryItem[] }>('/api/project-guides/recommendation-history/', { params })
  recommendationHistory.value = data.history || []
}

const openGuide = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const openPortraitDimensionEvidence = (dimensionKey: string) => {
  router.push(
    resolvePortraitRoute(
      currentUser.value,
      targetTeacherId.value,
      buildCrossModuleQuery({
        source: 'recommendation',
        page: 'portrait',
        section: 'portrait-dimensions',
        dimension_key: dimensionKey,
      }),
    ),
  )
}

const openSupportingRecordEvidence = (recordType: string, recordId: number) => {
  router.push({
    name: 'AchievementEntry',
    query: buildCrossModuleQuery({
      source: 'recommendation',
      page: 'achievement-entry',
      section: 'achievement-records',
      record_type: recordType,
      record_id: String(recordId),
      dimension_key: mapAchievementTypeToPortraitDimension(recordType),
    }),
  })
}

const handleTeacherChanged = async () => {
  await loadRecommendations()
}

const handleCompareTeacherChanged = async () => {
  await loadRecommendations()
}

const toggleFavorite = async (item: RecommendationItem) => {
  if (!interactionEnabled.value) {
    ElMessage.warning('当前仅支持教师本人收藏推荐结果。')
    return
  }

  const nextFavorited = !isFavorited(item.id)
  await axios.post(`/api/project-guides/${item.id}/favorite/`, { is_favorited: nextFavorited })
  favoriteGuideIds.value = nextFavorited
    ? [...new Set([...favoriteGuideIds.value, item.id])]
    : favoriteGuideIds.value.filter(id => id !== item.id)
  item.is_favorited = nextFavorited
  ElMessage.success(nextFavorited ? '已收藏该指南。' : '已取消收藏。')
  await loadRecommendationHistory()
  if (recommendationData.value?.feedback_summary) {
    recommendationData.value.feedback_summary.favorite_count = favoriteGuideIds.value.length
  }
}

const isFavorited = (guideId: number) => favoriteGuideIds.value.includes(guideId)

const openFeedbackDialog = (item: RecommendationItem, signal: RecommendationFeedbackSignal) => {
  if (!interactionEnabled.value) {
    ElMessage.warning('当前仅支持教师本人提交推荐反馈。')
    return
  }

  feedbackDialogGuideId.value = item.id
  feedbackDialogGuideTitle.value = item.title
  feedbackDialogSignal.value = signal
  feedbackDialogNote.value = item.latest_feedback_note || ''
  feedbackDialogVisible.value = true
}

const confirmFeedback = async () => {
  if (!feedbackDialogGuideId.value || !feedbackDialogSignal.value) {
    return
  }

  feedbackSubmitting.value = true
  try {
    const { data } = await axios.post(`/api/project-guides/${feedbackDialogGuideId.value}/feedback/`, {
      feedback_signal: feedbackDialogSignal.value,
      feedback_note: feedbackDialogNote.value,
    })

    const targetItem = recommendationData.value?.recommendations.find(item => item.id === feedbackDialogGuideId.value)
    if (targetItem) {
      targetItem.latest_feedback_signal = data.feedback_signal
      targetItem.latest_feedback_label = data.feedback_label
      targetItem.latest_feedback_note = data.feedback_note
      targetItem.last_feedback_at = data.last_feedback_at
    }

    feedbackDialogVisible.value = false
    ElMessage.success('推荐反馈已记录。')
    await loadRecommendations()
    await loadRecommendationHistory()
  } finally {
    feedbackSubmitting.value = false
  }
}

const openAssistantDemo = (guideId?: number) => {
  const query: Record<string, string> = {}

  if (targetTeacherId.value) {
    query.user_id = String(targetTeacherId.value)
  }
  if (guideId) {
    query.guide_id = String(guideId)
    query.question_type = 'guide_reason'
  }
  query.source = 'recommendation'
  query.page = 'assistant'
  query.section = 'assistant-answer'

  router.push({
    name: 'assistant-demo',
    query,
  })
}

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (currentUser.value?.is_admin && route.query.user_id) {
    selectedTeacherId.value = Number(route.query.user_id)
  }
  if (currentUser.value?.is_admin && route.query.compare_user_id) {
    compareTeacherId.value = Number(route.query.compare_user_id)
  }
  await loadTeacherOptions()
  await loadRecommendations()
})

watch(
  () => route.query,
  async nextQuery => {
    if (currentUser.value?.is_admin) {
      selectedTeacherId.value = nextQuery.user_id ? Number(nextQuery.user_id) : undefined
      compareTeacherId.value = nextQuery.compare_user_id ? Number(nextQuery.compare_user_id) : undefined
    }
    await loadRecommendations()
  },
)
</script>

<style scoped>
.recommendation-page {
  min-height: 100vh;
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.12), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.1), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
}

.hero-panel {
  max-width: 1180px;
  margin: 0 auto 22px;
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  padding: 28px 32px;
  border-radius: 26px;
  background: linear-gradient(135deg, #0f172a 0%, #1d4ed8 62%, #0f766e 100%);
  color: #fff;
  box-shadow: 0 26px 56px rgba(15, 23, 42, 0.14);
}

.snapshot-grid :deep(.el-card),
.recommendation-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.hero-actions,
.section-head,
.recommendation-head,
.title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

h1,
h2 {
  margin: 0;
}

h1 {
  color: #fff;
}

h2 {
  color: #16362c;
}

.hero-text {
  margin: 12px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.8;
}

.subline,
.summary,
.muted,
.meta-item p,
.footer-line,
.reason-list {
  color: #557068;
  line-height: 1.7;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.control-shell {
  margin-bottom: 20px;
}

.link-context-shell {
  margin-bottom: 20px;
}

.page-error-alert {
  margin-bottom: 16px;
  border-radius: 18px;
}

.control-shell :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.snapshot-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 20px;
}

.empty-shell {
  padding: 32px 0 8px;
}

.admin-shell {
  margin-top: 20px;
}

.admin-shell :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.admin-card-grid,
.dimension-grid {
  display: grid;
  gap: 14px;
}

.admin-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 16px;
}

.admin-card,
.dimension-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f7faf9;
  display: grid;
  gap: 8px;
}

.admin-card strong,
.dimension-card strong {
  color: #16362c;
}

.admin-card p,
.dimension-card p {
  margin: 0;
  color: #557068;
  line-height: 1.7;
}

.dimension-card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.dimension-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.snapshot-block + .snapshot-block {
  margin-top: 18px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.meta-list {
  display: grid;
  gap: 14px;
}

.meta-item {
  padding: 16px 18px;
  border-radius: 18px;
  background: #f7faf9;
}

.meta-item strong {
  display: block;
  margin-bottom: 8px;
  color: #16362c;
}

.recommendation-list {
  display: grid;
  gap: 18px;
  margin-top: 20px;
}

.recommendation-card :deep(.el-card__body) {
  display: grid;
  gap: 14px;
}

.recommendation-card--active {
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.2);
}

.subline,
.summary,
.footer-line,
.reason-list {
  margin: 0;
}

.tag-section {
  display: grid;
  gap: 8px;
}

.tag-label {
  font-weight: 600;
  color: #16362c;
}

.reason-list {
  padding-left: 18px;
}

.footer-line {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
}

.compare-panel {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.compact-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.history-preview-list,
.history-drawer {
  display: grid;
  gap: 12px;
}

.history-preview-item,
.history-drawer-item {
  padding: 14px 16px;
  border-radius: 16px;
  background: #f7faf9;
}

.feedback-row {
  align-items: center;
}

@media (max-width: 1080px) {
  .control-grid,
  .snapshot-grid,
  .admin-card-grid,
  .hero-panel,
  .hero-actions,
  .recommendation-head,
  .title-row {
    grid-template-columns: 1fr;
    display: grid;
  }
}

@media (max-width: 768px) {
  .recommendation-page {
    padding: 16px;
  }
}
</style>
