<template>
  <div class="recommendation-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">Guide Recommendation</p>
        <h1 class="workspace-hero__title">{{ sectionHeading }}</h1>
        <p class="hero-text workspace-hero__text">{{ heroDescription }}</p>
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

    <section v-if="showResultsPortraitSnapshot" class="content-shell result-portrait-shell">
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
            <span v-if="!(recommendationData?.teacher_snapshot.keywords || []).length" class="muted">当前暂无研究标签，可先完善教师档案或论文关键词。</span>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>学科 / 院系</strong>
          <div class="tag-list">
            <el-tag v-for="tag in recommendationData?.teacher_snapshot.disciplines || []" :key="tag" type="success" effect="plain">{{ tag }}</el-tag>
            <span v-if="!(recommendationData?.teacher_snapshot.disciplines || []).length" class="muted">当前暂无学科信息。</span>
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
            <span v-if="!(recommendationData?.teacher_snapshot.portrait_top_dimensions || []).length" class="muted">当前暂无画像维度摘要。</span>
          </div>
        </div>
      </el-card>
    </section>

    <section v-if="showControlShell" class="content-shell control-shell">
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
            <el-tag type="success" effect="plain"></el-tag>
          </div>
        </template>

        <div class="control-grid">
          <el-select
            v-if="showAdminTargetControls"
            v-model="selectedTeacherId"
            clearable
            filterable
            placeholder="请选择需要查看的教师"
            @change="handleTeacherChanged"
          >
            <el-option
              v-for="teacher in teacherOptions"
              :key="teacher.id"
              :label="`${teacher.real_name || teacher.username}（${teacher.department || '未分配院系'}）`"
              :value="teacher.id"
            />
          </el-select>

          <el-select
            v-if="showAdminTargetControls"
            v-model="compareTeacherId"
            clearable
            filterable
            placeholder="请选择对比教师"
            @change="handleCompareTeacherChanged"
          >
            <el-option
              v-for="teacher in teacherOptions.filter(item => item.id !== selectedTeacherId)"
              :key="teacher.id"
              :label="`${teacher.real_name || teacher.username}（${teacher.department || '未分配院系'}）`"
              :value="teacher.id"
            />
          </el-select>

          <el-input
            v-model="searchKeyword"
            clearable
            placeholder="搜索项目名称 / 发布单位 / 关键词"
          />

          <el-select v-model="selectedFocusTag" clearable placeholder="筛选命中标签">
            <el-option v-for="tag in focusTagOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>

          <el-select v-model="selectedGuideLevel" clearable placeholder="筛选指南级别">
            <el-option v-for="item in guideLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-select v-model="selectedPriority" clearable placeholder="筛选推荐优先级">
            <el-option v-for="item in priorityOptions" :key="item" :label="item" :value="item" />
          </el-select>

          <el-select v-model="selectedLabel" clearable placeholder="筛选推荐标签">
            <el-option v-for="tag in labelOptions" :key="tag" :label="tag" :value="tag" />
          </el-select>

          <el-select v-model="selectedSort" placeholder="推荐排序方式">
            <el-option v-for="item in sortOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>

          <el-switch class="favorites-switch" v-model="favoritesOnly" active-text="仅看收藏项目" inactive-text="显示全部推荐" />
        </div>

        <div class="tag-list">
          <el-tag type="success" effect="plain">推荐 {{ recommendationItems.length }}</el-tag>
          <el-tag type="primary" effect="plain">收藏 {{ favoriteGuideIds.length }}</el-tag>
          <el-tag v-if="recommendationData?.comparison_teacher_snapshot" type="primary" effect="plain">
            已开启教师对比
          </el-tag>
        </div>
      </el-card>
    </section>

    <section v-if="showResultsOverview" class="content-shell result-overview-shell">
      <div class="admin-card-grid result-summary-grid">
        <div v-for="item in resultSummaryCards" :key="item.label" class="admin-card">
          <strong>{{ item.value }}</strong>
          <span>{{ item.label }}</span>
          <p>{{ item.helper }}</p>
        </div>
      </div>
    </section>

    <section v-if="showFeedbackSnapshotGrid" class="content-shell feedback-overview-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>收藏与反馈概览</span>
            <el-tag type="warning" effect="plain">闭环沉淀</el-tag>
          </div>
        </template>
        <div class="snapshot-block">
          <strong>收藏与响应</strong>
          <div class="tag-list">
            <el-tag type="warning" effect="plain">收藏 {{ recommendationData?.feedback_summary?.favorite_count ?? favoriteGuideIds.length }}</el-tag>
            <el-tag type="success" effect="plain">
              已反馈 {{ recommendationData?.feedback_summary?.responded_guide_count ?? 0 }} / {{ recommendationData?.feedback_summary?.current_recommendation_count ?? recommendationItems.length }}
            </el-tag>
            <el-tag type="primary" effect="plain">覆盖率 {{ recommendationData?.feedback_summary?.response_rate ?? 0 }}%</el-tag>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>反馈分布</strong>
          <div class="tag-list">
            <el-tag type="success" effect="plain">感兴趣 {{ recommendationData?.feedback_summary?.interested_count ?? 0 }}</el-tag>
            <el-tag type="warning" effect="plain">计划申报 {{ recommendationData?.feedback_summary?.plan_to_apply_count ?? 0 }}</el-tag>
            <el-tag type="info" effect="plain">已申报 {{ recommendationData?.feedback_summary?.applied_count ?? 0 }}</el-tag>
            <el-tag type="danger" effect="plain">暂不相关 {{ recommendationData?.feedback_summary?.not_relevant_count ?? 0 }}</el-tag>
          </div>
        </div>
        <div class="snapshot-block">
          <strong>最近反馈</strong>
          <div class="history-preview-list">
            <div
              v-for="item in (recommendationData?.feedback_summary?.recent_feedback_items || []).slice(0, 3)"
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
      </el-card>
    </section>

    <section v-if="showAdminShell" class="content-shell admin-shell">
      <el-card shadow="never" class="workspace-surface-card">
        <template #header>
          <div class="section-head workspace-section-head">
            <span>管理员响应分析</span>
            <el-tag type="primary" effect="plain">管理员视角</el-tag>
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
          <span class="tag-label">高频标签</span>
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
          <span class="tag-label">响应概况</span>
          <div class="tag-list">
            <el-tag type="success" effect="plain">反馈覆盖率 {{ recommendationData?.admin_analysis?.response_rate ?? 0 }}%</el-tag>
            <el-tag type="primary" effect="plain">正向反馈 {{ recommendationData?.admin_analysis?.positive_feedback_count ?? 0 }}</el-tag>
            <el-tag type="warning" effect="plain">负向反馈 {{ recommendationData?.admin_analysis?.negative_feedback_count ?? 0 }}</el-tag>
            <el-tag type="info" effect="plain">计划申报 {{ recommendationData?.admin_analysis?.plan_to_apply_count ?? 0 }}</el-tag>
            <el-tag type="success" effect="plain">已申报 {{ recommendationData?.admin_analysis?.applied_count ?? 0 }}</el-tag>
          </div>
        </div>
      </el-card>
    </section>

    <div v-if="showFeedbackSnapshotGrid && !loading && !feedbackRecommendationItems.length" class="content-shell empty-shell workspace-empty-state">
      <el-empty description="当前还没有收藏或反馈过的项目，可先在推荐结果中收藏或提交反馈。" />
    </div>

    <section v-else-if="showFeedbackSnapshotGrid" class="recommendation-list content-shell recommendation-list--compact">
      <el-card
        v-for="item in feedbackRecommendationItems"
        :key="`feedback-${item.id}`"
        class="recommendation-card workspace-surface-card"
        shadow="hover"
      >
        <div class="recommendation-head">
          <div>
            <div class="title-row">
              <h2>{{ item.title }}</h2>
              <div class="tag-list compact-row">
                <el-tag v-if="isFavorited(item.id)" type="warning" effect="plain">已收藏</el-tag>
                <el-tag v-if="item.latest_feedback_label" type="success" effect="plain">{{ item.latest_feedback_label }}</el-tag>
              </div>
            </div>
            <p class="subline">
              {{ item.issuing_agency }} · {{ item.guide_level_display }}
              <span v-if="item.application_deadline"> · 截止 {{ item.application_deadline }}</span>
            </p>
          </div>
          <div class="compact-row">
            <el-button link :disabled="!interactionEnabled" :type="isFavorited(item.id) ? 'warning' : 'info'" @click="toggleFavorite(item)">
              {{ isFavorited(item.id) ? '取消收藏' : '收藏' }}
            </el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'INTERESTED')">感兴趣</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'PLAN_TO_APPLY')">计划申报</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'APPLIED')">已申报</el-button>
            <el-button size="small" :disabled="!interactionEnabled" @click="openFeedbackDialog(item, 'NOT_RELEVANT')">暂不相关</el-button>
          </div>
        </div>
        <p class="summary">{{ item.recommendation_summary }}</p>
        <div class="tag-section">
          <span class="tag-label">最近反馈</span>
          <p class="muted">{{ item.latest_feedback_note || '当前暂无文字备注，可继续补充反馈说明。' }}</p>
          <p v-if="item.last_feedback_at" class="muted">最近反馈时间：{{ item.last_feedback_at }}</p>
        </div>
      </el-card>
    </section>

    <div v-if="showPreparationShell && !loading && !preparationRecommendationItems.length" class="content-shell empty-shell workspace-empty-state">
      <el-empty description="当前暂无可用于申报准备的推荐结果，可先刷新推荐或补充成果。" />
    </div>

    <section v-else-if="showPreparationShell" class="content-shell preparation-shell">
      <el-card
        v-for="item in preparationRecommendationItems"
        :key="`preparation-${item.id}`"
        class="recommendation-card workspace-surface-card"
        shadow="hover"
      >
        <div class="recommendation-head">
          <div>
            <div class="title-row">
              <h2>{{ item.title }}</h2>
              <div class="tag-list compact-row">
                <el-tag type="success" effect="plain">匹配度 {{ item.recommendation_score }}</el-tag>
                <el-tag type="primary" effect="plain">{{ item.priority_label }}</el-tag>
              </div>
            </div>
            <p class="subline">
              {{ item.issuing_agency }} · {{ item.guide_level_display }}
              <span v-if="item.application_deadline"> · 截止 {{ item.application_deadline }}</span>
              <span v-if="item.support_amount"> · 资助 {{ item.support_amount }}</span>
            </p>
          </div>
          <div class="compact-row">
            <el-button plain @click="openAchievementEntry">录入成果</el-button>
            <el-button link type="success" @click="openAssistantDemo(item.id)">智能解读</el-button>
            <el-button v-if="item.source_url" link type="primary" @click="openGuide(item.source_url)">查看来源</el-button>
          </div>
        </div>
        <p class="summary">{{ buildPreparationHint(item) }}</p>
        <div class="preparation-grid">
          <div class="meta-item">
            <strong>已有支撑</strong>
            <div class="history-preview-list">
              <div v-for="record in item.supporting_records.slice(0, 2)" :key="`${record.type}-${record.id}`" class="history-preview-item">
                <strong>{{ record.title }}</strong>
                <p>{{ record.detail }}</p>
                <p class="muted">{{ record.reason }}</p>
              </div>
              <p v-if="!item.supporting_records.length" class="muted">当前还没有可直接定位的支撑成果，建议先补录成果。</p>
            </div>
          </div>
          <div class="meta-item">
            <strong>申报要点</strong>
            <p class="muted">{{ item.eligibility_notes || '当前指南未单独给出详细申报要求，请先查看来源页。' }}</p>
            <div class="tag-list">
              <el-tag v-for="dimension in item.portrait_dimension_links.slice(0, 2)" :key="`prep-${item.id}-${dimension.key}`" type="success" effect="plain">
                {{ dimension.label }}
              </el-tag>
            </div>
          </div>
        </div>
      </el-card>
    </section>
    <div v-if="showRecommendationList && !loading && !recommendationItems.length" class="content-shell empty-shell workspace-empty-state">
      <el-empty :description="recommendationData?.empty_state || '当前筛选条件下暂无推荐结果，可调整筛选条件或重新刷新推荐。'" />
    </div>

    <section v-else-if="showRecommendationList" id="recommendation-evidence-section" class="recommendation-list content-shell">
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
                <el-tag type="success" effect="plain">推荐分 {{ item.recommendation_score }}</el-tag>
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

        <div class="recommendation-detail-toggle">
          <el-button link type="primary" @click="toggleRecommendationDetail(item.id)">
            {{ isRecommendationDetailExpanded(item.id) ? '收起项目详情' : '展开项目详情' }}
          </el-button>
        </div>

        <el-collapse-transition>
          <div v-show="isRecommendationDetailExpanded(item.id)" class="recommendation-details">
            <div class="tag-section">
              <span class="tag-label">推荐摘要</span>
              <p class="summary">{{ item.recommendation_summary }}</p>
            </div>

            <div class="tag-section">
              <span class="tag-label">命中标签</span>
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
              <span class="tag-label">指南目标关键词</span>
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
              <span class="tag-label">画像联动</span>
              <div class="dimension-grid">
                <div v-for="dimension in item.portrait_dimension_links" :key="`portrait-${dimension.key}`" class="dimension-card">
                  <div class="dimension-card-head">
                    <strong>{{ dimension.label }}</strong>
                    <span>{{ dimension.current_value }}</span>
                  </div>
                  <p>{{ dimension.detail }}</p>
                  <p>关联方式：{{ dimension.relation }}</p>
                  <div class="dimension-card-actions">
                    <el-button link type="primary" @click="openPortraitDimensionEvidence(dimension.key)">查看画像证据</el-button>
                    <el-button link type="warning" @click="openAssistantDemo(item.id)">问答说明</el-button>
                  </div>
                </div>
                <p v-if="!item.portrait_dimension_links.length" class="muted">当前暂无与画像维度直接联动的说明。</p>
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
                  <div v-if="!currentUser?.is_admin" class="dimension-card-actions">
                    <el-button
                      link
                      type="primary"
                      @click="openSupportingRecordEvidence(record.type, record.id)"
                    >
                      查看支撑成果
                    </el-button>
                  </div>
                </div>
                <p v-if="!item.supporting_records.length" class="muted">当前暂无可直接回看的支撑成果，建议先补录成果并完善画像联动说明。</p>
              </div>
            </div>

            <div class="tag-section">
              <span class="tag-label">匹配依据</span>
              <div class="tag-list">
                <el-tag v-for="tag in item.matched_keywords" :key="`kw-${tag}`" type="warning" effect="plain">{{ tag }}</el-tag>
                <el-tag v-for="tag in item.matched_disciplines" :key="`dis-${tag}`" type="success" effect="plain">{{ tag }}</el-tag>
                <span v-if="!item.matched_keywords.length && !item.matched_disciplines.length" class="muted">当前没有直接命中的关键词或学科标签，建议结合推荐解释继续判断。</span>
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
              <span class="tag-label">反馈动作</span>
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
              <span v-if="item.support_amount">资助金额：{{ item.support_amount }}</span>
              <span v-if="item.eligibility_notes">申报提示：{{ item.eligibility_notes }}</span>
            </div>
          </div>
        </el-collapse-transition>
      </el-card>
    </section>

    <el-drawer v-model="historyVisible" title="推荐历史回看" size="540px">
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
          <p v-if="item.requested_by_name" class="muted">发起人：{{ item.requested_by_name }}</p>
        </div>
        <p v-if="!recommendationHistory.length" class="muted">当前暂无推荐历史记录。</p>
      </div>
    </el-drawer>

    <el-dialog
      v-model="feedbackDialogVisible"
      width="520px"
      :title="feedbackDialogGuideTitle ? `提交反馈：${feedbackDialogGuideTitle}` : '提交推荐反馈'"
    >
      <div class="meta-list">
        <div class="meta-item">
          <strong>反馈类型</strong>
          <div class="tag-list">
            <el-tag type="success" effect="plain">{{ feedbackSignalLabel }}</el-tag>
            <span class="muted">反馈会进入当前账号的推荐响应记录，用于后续回看和策略优化。</span>
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
            placeholder="可补充填写你对该推荐项目的判断、准备计划或不相关原因。"
          />
        </div>
      </div>
      <template #footer>
        <div class="compact-row">
          <el-button @click="feedbackDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="feedbackSubmitting" @click="confirmFeedback">提交反馈</el-button>
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
import { openFloatingAssistant } from '../utils/assistantLauncher'
import type { TeacherAccountResponse } from '../types/users'
import { buildDistributionCards, buildRecommendationSortOptions, filterRecommendationItems, sortRecommendationItems } from './project-guides/recommendationHelpers.js'
import type { RecommendationFeedbackSignal, RecommendationHistoryItem, RecommendationItem, RecommendationResponse } from './project-guides/types'

type RecommendationSection = 'results' | 'feedback' | 'preparation'

const props = withDefaults(
  defineProps<{
    sectionMode?: RecommendationSection
  }>(),
  {
    sectionMode: 'results',
  },
)

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
const expandedRecommendationDetailIds = ref<number[]>([])
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
const sectionHeadingMap: Record<RecommendationSection, string> = {
  results: '推荐结果',
  feedback: '收藏与反馈',
  preparation: '申报准备',
}

const sectionDescriptionMap: Record<RecommendationSection, string> = {
  results: '聚焦当前最值得关注的项目，优先展示可申报、可解释的推荐结果。',
  feedback: '沉淀收藏、反馈和响应状态，帮助教师与管理员持续复盘推荐效果。',
  preparation: '围绕当前高匹配项目组织已有支撑与申报要点，帮助教师更快进入准备状态。',
}
const feedbackSignalLabelMap: Record<Exclude<RecommendationFeedbackSignal, ''>, string> = {
  INTERESTED: '感兴趣',
  NOT_RELEVANT: '暂不相关',
  PLAN_TO_APPLY: '计划申报',
  APPLIED: '已申报',
}

const isAdminSelfRecommendationMode = computed(() => Boolean(currentUser.value?.is_admin))
const targetTeacherId = computed(() => {
  if (isAdminSelfRecommendationMode.value) {
    return currentUser.value?.id || 0
  }
  return selectedTeacherId.value || Number(route.query.user_id) || currentUser.value?.id || 0
})

const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'portrait') {
    return '来自教师画像的推荐联动'
  }
  if (linkContext.value?.source === 'achievement') {
    return '来自成果记录的推荐联动'
  }
  if (linkContext.value?.source === 'assistant') {
    return '来自智能问答的推荐联动'
  }
  return '推荐结果联动入口'
})

const linkContextDescription = computed(
  () =>
    linkContext.value?.note ||
    '当前页面会保留来源上下文，方便继续回看推荐解释、支撑成果和问答说明。',
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
const activeSection = computed(() => props.sectionMode)
const showAdminTargetControls = computed(() => Boolean(currentUser.value?.is_admin) && !isAdminSelfRecommendationMode.value)
const teacherDisplayName = computed(
  () => recommendationData.value?.teacher_snapshot.teacher_name || currentUser.value?.real_name || currentUser.value?.username || '当前教师',
)
const sectionHeading = computed(() => sectionHeadingMap[activeSection.value])
const heroDescription = computed(() => `${teacherDisplayName.value}${sectionDescriptionMap[activeSection.value]}`)
const showControlShell = computed(() => true)
const showResultsPortraitSnapshot = computed(() => activeSection.value === 'results')
const showResultsOverview = computed(() => activeSection.value === 'results')
const showFeedbackSnapshotGrid = computed(() => activeSection.value === 'feedback')
const showPreparationShell = computed(() => activeSection.value === 'preparation')
const showAdminShell = computed(
  () => activeSection.value === 'feedback' && Boolean(currentUser.value?.is_admin) && adminAnalysisCards.value.length > 0,
)
const showRecommendationList = computed(() => activeSection.value === 'results')

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

const resultSummaryCards = computed(() => {
  const items = recommendationItems.value
  const highPriorityCount = items.filter(item => item.priority_label === '重点关注').length
  const expiringSoonCount = items.filter(item => {
    if (!item.application_deadline) return false
    const diff = Math.ceil((new Date(item.application_deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24))
    return diff >= 0 && diff <= 45
  }).length
  const respondedCount = items.filter(item => Boolean(item.latest_feedback_signal)).length
  return [
    { label: '推荐项目总数', value: `${items.length} 项`, helper: '当前筛选条件下可直接查看和继续跟进的推荐项目。' },
    { label: '重点关注', value: `${highPriorityCount} 项`, helper: '优先度最高、建议先查看并判断是否进入申报准备。' },
    { label: '近期截止', value: `${expiringSoonCount} 项`, helper: '预计在 45 天内截止，适合优先安排准备节奏。' },
    { label: '收藏 / 已反馈', value: `${favoriteGuideIds.value.length} / ${respondedCount}`, helper: '帮助沉淀个人偏好和当前响应状态。' },
  ]
})

const feedbackRecommendationItems = computed(() =>
  recommendationItems.value.filter(item => isFavorited(item.id) || Boolean(item.latest_feedback_signal)),
)

const preparationRecommendationItems = computed(() => recommendationItems.value.slice(0, 4))

const interactionEnabled = computed(() => Boolean(recommendationData.value?.data_meta.interaction_enabled))
const feedbackSignalLabel = computed(() =>
  feedbackDialogSignal.value ? feedbackSignalLabelMap[feedbackDialogSignal.value as Exclude<RecommendationFeedbackSignal, ''>] : '',
)

const buildPreparationHint = (item: RecommendationItem) => {
  if (item.supporting_records.length >= 2) {
    return '当前已有多条支撑成果，可先梳理已有优势，再对照指南准备申报材料。'
  }
  if (item.supporting_records.length === 1 || item.portrait_dimension_links.length) {
    return '当前已有部分支撑，可围绕推荐指南补齐成果、画像维度和申报要点。'
  }
  return '当前支撑仍偏少，建议先补录成果并结合问答说明确认申报方向。'
}

const loadTeacherOptions = async () => {
  if (!currentUser.value?.is_admin || isAdminSelfRecommendationMode.value) return

  const { data } = await axios.get<TeacherAccountResponse[]>('/api/users/teachers/')
  teacherOptions.value = data || []
}

const loadRecommendations = async () => {
  loading.value = true
  errorNotice.value = null
  try {
    const shouldUseAdminScope = Boolean(currentUser.value?.is_admin) && !isAdminSelfRecommendationMode.value
    const params: Record<string, number> | undefined =
      shouldUseAdminScope && (selectedTeacherId.value || route.query.user_id || compareTeacherId.value)
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
      fallbackMessage: '项目推荐加载失败，请稍后重试。',
      fallbackGuidance: '可以先检查当前教师、筛选条件和会话状态，再重新加载推荐结果。',
    })
    ElMessage.warning(errorNotice.value.message)
  } finally {
    loading.value = false
  }
}

const recommendationCardId = (guideId: number) => `recommendation-card-${guideId}`
const isRecommendationDetailExpanded = (guideId: number) => expandedRecommendationDetailIds.value.includes(guideId)
const expandRecommendationDetail = (guideId: number) => {
  if (!expandedRecommendationDetailIds.value.includes(guideId)) {
    expandedRecommendationDetailIds.value = [...expandedRecommendationDetailIds.value, guideId]
  }
}
const toggleRecommendationDetail = (guideId: number) => {
  expandedRecommendationDetailIds.value = isRecommendationDetailExpanded(guideId)
    ? expandedRecommendationDetailIds.value.filter(id => id !== guideId)
    : [...expandedRecommendationDetailIds.value, guideId]
}

const matchesRecommendationContext = (item: RecommendationItem) => {
  const guideIdFromQuery = Number(route.query.guide_id || 0)
  if (Number.isFinite(guideIdFromQuery) && guideIdFromQuery > 0 && item.id === guideIdFromQuery) {
    return true
  }
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
  if (matchedGuideId) {
    expandRecommendationDetail(matchedGuideId)
  }
  focusEvidenceSection(
    'recommendation-evidence-section',
    matchedGuideId ? recommendationCardId(matchedGuideId) : undefined,
  )
}

const loadRecommendationHistory = async () => {
  const shouldUseAdminScope = Boolean(currentUser.value?.is_admin) && !isAdminSelfRecommendationMode.value
  const params: Record<string, number> | undefined =
    shouldUseAdminScope && (selectedTeacherId.value || route.query.user_id)
      ? { user_id: Number(selectedTeacherId.value || route.query.user_id) }
      : undefined
  const { data } = await axios.get<{ history: RecommendationHistoryItem[] }>('/api/project-guides/recommendation-history/', { params })
  recommendationHistory.value = data.history || []
}

const openGuide = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const openAchievementEntry = () => {
  router.push('/profile-editor/achievement-entry')
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
    ElMessage.warning('当前场景暂不开放收藏操作。')
    return
  }

  try {
    const nextFavorited = !isFavorited(item.id)
    await axios.post(`/api/project-guides/${item.id}/favorite/`, { is_favorited: nextFavorited })
    favoriteGuideIds.value = nextFavorited
      ? [...new Set([...favoriteGuideIds.value, item.id])]
      : favoriteGuideIds.value.filter(id => id !== item.id)
    item.is_favorited = nextFavorited
    ElMessage.success(nextFavorited ? '已加入收藏。' : '已取消收藏。')
    await loadRecommendationHistory()
    if (recommendationData.value?.feedback_summary) {
      recommendationData.value.feedback_summary.favorite_count = favoriteGuideIds.value.length
    }
  } catch (error) {
    console.error(error)
    const notice = buildApiErrorNotice(error, {
      fallbackMessage: '收藏操作失败，请稍后重试。',
      fallbackGuidance: '可以先刷新推荐列表，再重新尝试收藏。',
    })
    ElMessage.warning(notice.message)
  }
}

const isFavorited = (guideId: number) => favoriteGuideIds.value.includes(guideId)

const openFeedbackDialog = (item: RecommendationItem, signal: RecommendationFeedbackSignal) => {
  if (!interactionEnabled.value) {
    ElMessage.warning('当前场景暂不开放反馈操作。')
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
    ElMessage.success('反馈已提交。')
    await loadRecommendations()
    await loadRecommendationHistory()
  } finally {
    feedbackSubmitting.value = false
  }
}

const openAssistantDemo = (guideId?: number) => {
  openFloatingAssistant({
    contextHint: 'recommendation',
    draft: guideId
      ? `请解释推荐项目（ID: ${guideId}）为何命中我当前画像和成果，并给出下一步建议。`
      : '请总结我当前推荐结果的优先级和可执行建议。',
  })
}

onMounted(async () => {
  currentUser.value = await ensureSessionUserContext()
  if (currentUser.value?.is_admin && !isAdminSelfRecommendationMode.value && route.query.user_id) {
    selectedTeacherId.value = Number(route.query.user_id)
  }
  if (currentUser.value?.is_admin && !isAdminSelfRecommendationMode.value && route.query.compare_user_id) {
    compareTeacherId.value = Number(route.query.compare_user_id)
  }
  await loadTeacherOptions()
  await loadRecommendations()
})

watch(
  () => route.query,
  async nextQuery => {
    if (currentUser.value?.is_admin) {
      if (isAdminSelfRecommendationMode.value) {
        selectedTeacherId.value = undefined
        compareTeacherId.value = undefined
      } else {
        selectedTeacherId.value = nextQuery.user_id ? Number(nextQuery.user_id) : undefined
        compareTeacherId.value = nextQuery.compare_user_id ? Number(nextQuery.compare_user_id) : undefined
      }
    }
    await loadRecommendations()
  },
)
</script>

<style scoped>
.recommendation-page {
  min-height: 100%;
  padding: 28px;
  background: var(--page-bg);
  color: var(--text-secondary);
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
  background: var(--hero-bg);
  color: var(--text-on-brand);
  box-shadow: var(--workspace-shadow-strong);
}

.snapshot-grid :deep(.el-card),
.recommendation-card {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
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
  color: var(--text-primary);
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
  color: var(--text-tertiary);
  line-height: 1.7;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.control-shell {
  margin-bottom: 20px;
}

.result-overview-shell {
  margin-bottom: 20px;
}

.result-portrait-shell {
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
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.control-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
}

.favorites-switch {
  white-space: nowrap;
}

.favorites-switch :deep(.el-switch__label),
.favorites-switch :deep(.el-switch__label span) {
  white-space: nowrap;
}

.snapshot-grid {
  display: grid;
  grid-template-columns: 0.9fr 1.1fr;
  gap: 20px;
}

.snapshot-grid--wide {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.empty-shell {
  padding: 32px 0 8px;
}

.admin-shell {
  margin-top: 20px;
}

.admin-shell :deep(.el-card) {
  border: 1px solid var(--border-color-soft);
  border-radius: 24px;
  background: var(--card-bg);
  box-shadow: var(--workspace-shadow);
}

.admin-card-grid,
.dimension-grid {
  display: grid;
  gap: 14px;
}

.hero-panel {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 28px;
}

.hero-actions {
  display: flex;
  flex-wrap: nowrap;
  justify-content: flex-end;
  align-items: flex-start;
  gap: 16px;
}

.hero-actions :deep(.el-button) {
  min-width: 136px;
}

.admin-card-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin-bottom: 16px;
}

.result-summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
  margin-bottom: 0;
}

.admin-card,
.dimension-card {
  padding: 16px 18px;
  border-radius: 18px;
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
  display: grid;
  gap: 8px;
}

.admin-card strong,
.dimension-card strong {
  color: var(--text-primary);
}

.admin-card p,
.dimension-card p {
  margin: 0;
  color: var(--text-tertiary);
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
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.meta-item strong {
  display: block;
  margin-bottom: 8px;
  color: var(--text-primary);
}

.recommendation-list {
  display: grid;
  gap: 18px;
  margin-top: 20px;
}

.recommendation-list--compact .recommendation-card :deep(.el-card__body) {
  gap: 10px;
}

.recommendation-card :deep(.el-card__body) {
  display: grid;
  gap: 14px;
}

.recommendation-detail-toggle {
  display: flex;
  justify-content: flex-end;
}

.recommendation-details {
  display: grid;
  gap: 12px;
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
  color: var(--text-primary);
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
  background: var(--panel-bg);
  border: 1px solid var(--border-color-soft);
}

.preparation-shell {
  margin-top: 20px;
  display: grid;
  gap: 18px;
}

.preparation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
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

  .result-summary-grid,
  .preparation-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .recommendation-page {
    padding: 16px;
  }
}
</style>
