<template>
  <div class="achievement-entry-page workspace-page">
    <section class="hero-panel workspace-hero workspace-hero--brand">
      <div>
        <p class="eyebrow workspace-hero__eyebrow">Research Achievement Workspace</p>
        <h1 class="workspace-hero__title">教师成果录入中心</h1>
        <p class="hero-text workspace-hero__text">
          当前录入账号：
          <strong>{{ teacherLabel }}</strong>
          <span v-if="sessionUser?.department"> · {{ sessionUser.department }}</span>
          <span v-if="sessionUser?.title"> · {{ sessionUser.title }}</span>
        </p>
      </div>
      <div class="hero-actions workspace-page-actions">
        <el-button plain @click="goToProfileCenter">个人中心</el-button>
        <el-button plain @click="goToRecommendation">推荐入口</el-button>
        <el-button plain @click="goToAssistant">问答入口</el-button>
        <el-button plain @click="router.push('/dashboard')">返回画像主页</el-button>
        <el-button type="primary" @click="refreshAllRecords" :loading="pageLoading">刷新数据</el-button>
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

    <section class="overview-grid content-shell">
      <el-card
        id="achievement-records-section"
        shadow="never"
        class="overview-card workspace-surface-card"
        :class="{ 'evidence-section-highlight': linkContext?.section === 'achievement-records' }"
      >
        <template #header>
          <div class="card-header workspace-section-head">
            <span>成果管理概览</span>
            <el-tag type="info">统一入口</el-tag>
          </div>
        </template>
        <div class="metric-grid">
          <div v-for="item in achievementOverviewCards" :key="item.label" class="metric-item">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
            <p>{{ item.helper }}</p>
          </div>
        </div>
      </el-card>

      <el-card shadow="never" class="overview-card workspace-surface-card">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>成果联动入口</span>
            <el-tag type="success">画像 / 推荐 / 问答</el-tag>
          </div>
        </template>
        <div class="hub-links">
          <el-button type="primary" plain @click="goToPortraitAndGraph">画像与图谱主页</el-button>
          <el-button type="success" plain @click="goToRecommendation">项目推荐入口</el-button>
          <el-button type="warning" plain @click="goToAssistant">成果问答入口</el-button>
          <el-button plain @click="goToProfileCenter">返回个人中心</el-button>
        </div>
        <p class="panel-note">当前不新增独立图谱路由，继续复用画像主页中的图谱展示与回退链路。</p>
      </el-card>

      <el-card shadow="never" class="overview-card workspace-surface-card">
        <template #header>
          <div class="card-header workspace-section-head">
            <span>最近成果</span>
            <el-tag>{{ recentAchievements.length }} 条</el-tag>
          </div>
        </template>
        <div v-if="recentAchievements.length" class="recent-list">
          <div
            v-for="item in recentAchievements"
            :id="recentAchievementEvidenceId(item.type, item.id)"
            :key="`${item.type}-${item.id}`"
            class="recent-item"
            :class="{ 'recent-item--active': isActiveRecentAchievement(item.type, item.id) }"
          >
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.type_label }} · {{ item.detail }}</p>
            </div>
            <div class="recent-meta">
              <span>{{ item.date_acquired }}</span>
              <el-tag size="small" type="info" effect="plain">{{ item.highlight }}</el-tag>
              <div class="recent-actions">
                <el-button link type="primary" @click="goToPortraitDimensionFromAchievement(item.type, item.id)">画像维度</el-button>
                <el-button link type="success" @click="goToRecommendationFromAchievement(item.type, item.id)">推荐解释</el-button>
                <el-button link type="warning" @click="goToAssistantFromAchievement(item.type, item.id)">问答说明</el-button>
              </div>
            </div>
          </div>
        </div>
          <div v-else class="workspace-empty-state">
            <el-empty description="暂无最近成果，可先在下方补充论文、项目或其他成果记录。" />
          </div>
      </el-card>
    </section>

    <el-tabs v-model="activeTab" class="entry-tabs content-shell">
      <el-tab-pane label="论文成果" name="papers">
        <div class="entry-grid">
          <el-card shadow="never" class="workspace-surface-card">
            <template #header>
              <div class="card-header workspace-section-head">
                <span>{{ isEditing('papers') ? editingLabelMap.papers.edit : editingLabelMap.papers.create }}</span>
                <el-button type="primary" plain @click="bibtexDialogVisible = true">BibTeX 批量导入</el-button>
              </div>
            </template>
            <el-form ref="paperFormRef" :model="paperForm" :rules="paperRules" label-position="top">
              <el-form-item label="论文题目" prop="title">
                <el-input v-model="paperForm.title" placeholder="请输入论文题目" />
              </el-form-item>
              <el-form-item label="摘要" prop="abstract">
                <el-input v-model="paperForm.abstract" type="textarea" :rows="4" placeholder="请输入论文摘要" />
              </el-form-item>
              <el-alert v-if="paperDuplicateWarnings.length" type="warning" show-icon :closable="false" class="form-alert">
                <template #title>重复录入提醒</template>
                <template #default>
                  <p v-for="warning in paperDuplicateWarnings" :key="warning">{{ warning }}</p>
                </template>
              </el-alert>
              <el-alert v-if="paperMetadataHints.length" type="info" show-icon :closable="false" class="form-alert">
                <template #title>元数据补充建议</template>
                <template #default>
                  <p v-for="hint in paperMetadataHints" :key="hint">{{ hint }}</p>
                </template>
              </el-alert>
              <div class="double-grid">
                <el-form-item label="获得时间" prop="date_acquired">
                  <el-date-picker v-model="paperForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="论文类型" prop="paper_type">
                  <el-select v-model="paperForm.paper_type" style="width: 100%">
                    <el-option v-for="option in paperTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="期刊/会议名称" prop="journal_name">
                  <el-input v-model="paperForm.journal_name" placeholder="请输入期刊或会议名称" />
                </el-form-item>
                <el-form-item label="级别">
                  <el-input v-model="paperForm.journal_level" placeholder="如 SCI、EI、CCF-B" />
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="引用次数">
                  <el-input-number v-model="paperForm.citation_count" :min="0" style="width: 100%" />
                </el-form-item>
                <el-form-item label="DOI">
                  <el-input v-model="paperForm.doi" placeholder="如 10.1000/xyz123" />
                </el-form-item>
              </div>
              <div class="triple-grid">
                <el-form-item label="卷号">
                  <el-input v-model="paperForm.published_volume" placeholder="如 18" />
                </el-form-item>
                <el-form-item label="期号">
                  <el-input v-model="paperForm.published_issue" placeholder="如 3" />
                </el-form-item>
                <el-form-item label="页码范围">
                  <el-input v-model="paperForm.pages" placeholder="如 22-30" />
                </el-form-item>
              </div>
              <el-form-item label="来源链接">
                <el-input v-model="paperForm.source_url" placeholder="请输入论文来源链接" />
              </el-form-item>
              <el-form-item>
                <el-switch v-model="paperForm.is_first_author" active-text="第一作者/通讯作者" inactive-text="非第一作者" />
              </el-form-item>
              <el-form-item>
                <el-switch v-model="paperForm.is_representative" active-text="标记为代表作" inactive-text="普通论文" />
              </el-form-item>
              <el-form-item label="合作者">
                <el-input
                  v-model="paperForm.coauthorInput"
                  placeholder="多个合作者请用中文逗号、英文逗号或换行分隔"
                  type="textarea"
                  :rows="3"
                />
              </el-form-item>
              <div class="actions">
                <el-button v-if="isEditing('papers')" @click="resetPaperForm">取消编辑</el-button>
                <el-button v-else @click="resetPaperForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap.papers" @click="submitPaper">
                  {{ isEditing('papers') ? editingLabelMap.papers.submitEdit : editingLabelMap.papers.submitCreate }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never" class="workspace-surface-card">
            <template #header>
              <div class="card-header card-header-wrap workspace-section-head">
                <span>我的论文记录</span>
                <div class="header-tools workspace-toolbar">
                  <el-input
                    v-model="queryMap.papers.search"
                    clearable
                    placeholder="按题目 / 期刊 / DOI 搜索"
                    class="filter-input"
                    @keyup.enter="fetchRecords('papers'); fetchPaperInsights()"
                    @clear="fetchRecords('papers'); fetchPaperInsights()"
                  />
                  <el-select v-model="queryMap.papers.paper_type" class="filter-select" @change="fetchRecords('papers'); fetchPaperInsights()">
                    <el-option label="全部类型" value="ALL" />
                    <el-option v-for="option in paperTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                  <el-select v-model="queryMap.papers.year" class="filter-select" @change="fetchRecords('papers'); fetchPaperInsights()">
                    <el-option v-for="option in paperYearOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                  <el-select v-model="queryMap.papers.is_representative" class="filter-select" @change="fetchRecords('papers'); fetchPaperInsights()">
                    <el-option
                      v-for="option in paperRepresentativeOptions"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    />
                  </el-select>
                  <el-select v-model="queryMap.papers.sort_by" class="filter-select filter-select-wide" @change="fetchRecords('papers')">
                    <el-option v-for="option in paperSortOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                  <el-button plain @click="clearFilters('papers')">清空筛选</el-button>
                  <el-tag type="info">{{ papers.length }} 篇</el-tag>
                </div>
              </div>
            </template>
            <div class="paper-summary-strip">
              <el-tag type="success">代表作 {{ paperSummary?.representative_count || 0 }} 篇</el-tag>
              <el-tag type="info">近三年 {{ paperSummary?.recent_count || 0 }} 篇</el-tag>
              <el-tag type="warning">缺 DOI {{ paperSummary?.missing_doi_count || 0 }} 篇</el-tag>
              <el-tag type="danger">待补元数据 {{ paperSummary?.incomplete_metadata_count || 0 }} 篇</el-tag>
            </div>
            <div class="distribution-strip">
              <div class="distribution-group">
                <span class="distribution-label">按年份</span>
                <div class="tag-list">
                  <el-tag
                    v-for="item in (paperSummary?.yearly_distribution || []).slice(0, 6)"
                    :key="item.year"
                    size="small"
                    effect="plain"
                  >
                    {{ item.year }} 年 {{ item.count }} 篇
                  </el-tag>
                </div>
              </div>
              <div class="distribution-group">
                <span class="distribution-label">按类型</span>
                <div class="tag-list">
                  <el-tag
                    v-for="item in paperSummary?.type_distribution || []"
                    :key="item.paper_type"
                    size="small"
                    type="success"
                    effect="plain"
                  >
                    {{ item.label }} {{ item.count }} 篇
                  </el-tag>
                </div>
              </div>
            </div>
            <el-table :data="papers" v-loading="loadingMap.papers" empty-text="暂无论文成果">
              <el-table-column label="题目" min-width="240">
                <template #default="{ row }">
                  <div class="paper-title-cell">
                    <strong>{{ row.title }}</strong>
                    <div class="tag-list">
                      <el-tag v-if="row.is_representative" size="small" type="success" effect="plain">代表作</el-tag>
                      <el-tag size="small" effect="plain">{{ row.citation_count }} 引用</el-tag>
                      <el-tag v-if="row.doi" size="small" type="info" effect="plain">DOI</el-tag>
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="paper_type_display" label="类型" width="110" />
              <el-table-column prop="journal_name" label="期刊/会议" min-width="170" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="元数据状态" min-width="180">
                <template #default="{ row }">
                  <span v-if="row.metadata_alerts.length" class="warning-text">{{ row.metadata_alerts[0] }}</span>
                  <span v-else class="success-text">信息完整度良好</span>
                </template>
              </el-table-column>
              <el-table-column label="关键词" min-width="180">
                <template #default="{ row }">
                  <div class="tag-list">
                    <el-tag v-for="keyword in row.keywords" :key="keyword" size="small" effect="plain">{{ keyword }}</el-tag>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="联动入口" width="210">
                <template #default="{ row }">
                  <div class="table-action-group workspace-table-actions">
                    <el-button link type="primary" @click="goToPortraitDimensionFromAchievement('paper', row.id)">画像/图谱</el-button>
                    <el-button link type="success" @click="goToRecommendationFromAchievement('paper', row.id)">推荐</el-button>
                    <el-button link type="warning" @click="goToAssistantFromAchievement('paper', row.id)">问答</el-button>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="startEditRecord('papers', row)">编辑</el-button>
                  <el-button link type="danger" @click="removeRecord('papers', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
        <PaperGovernancePanel
          :papers="papers"
          :query-state="queryMap.papers"
          @refresh="handleGovernanceRefresh"
          @edit-paper="handleGovernanceEditPaper"
        />
      </el-tab-pane>

      <el-tab-pane label="科研项目" name="projects">
        <div class="entry-grid">
          <el-card shadow="never" class="workspace-surface-card">
            <template #header>{{ isEditing('projects') ? editingLabelMap.projects.edit : editingLabelMap.projects.create }}</template>
            <el-form ref="projectFormRef" :model="projectForm" :rules="projectRules" label-position="top">
              <el-form-item label="项目名称" prop="title">
                <el-input v-model="projectForm.title" placeholder="请输入项目名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="立项时间" prop="date_acquired">
                  <el-date-picker v-model="projectForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="项目级别" prop="level">
                  <el-select v-model="projectForm.level" style="width: 100%">
                    <el-option v-for="option in projectLevelOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <div class="double-grid">
                <el-form-item label="承担角色" prop="role">
                  <el-select v-model="projectForm.role" style="width: 100%">
                    <el-option v-for="option in projectRoleOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
                <el-form-item label="经费（万元）" prop="funding_amount">
                  <el-input-number v-model="projectForm.funding_amount" :min="0" :precision="2" style="width: 100%" />
                </el-form-item>
              </div>
              <el-form-item label="项目状态" prop="status">
                <el-input v-model="projectForm.status" placeholder="如 ONGOING、COMPLETED" />
              </el-form-item>
              <div class="actions">
                <el-button v-if="isEditing('projects')" @click="resetProjectForm">取消编辑</el-button>
                <el-button v-else @click="resetProjectForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap.projects" @click="submitProject">
                  {{ isEditing('projects') ? editingLabelMap.projects.submitEdit : editingLabelMap.projects.submitCreate }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never" class="workspace-surface-card">
            <template #header>
              <div class="card-header card-header-wrap workspace-section-head">
                <span>我的项目记录</span>
                <div class="header-tools workspace-toolbar">
                  <el-input
                    v-model="queryMap.projects.search"
                    clearable
                    placeholder="按项目名称 / 状态搜索"
                    class="filter-input"
                    @keyup.enter="fetchRecords('projects')"
                    @clear="fetchRecords('projects')"
                  />
                  <el-button plain @click="clearFilters('projects')">清空筛选</el-button>
                  <el-tag type="success">{{ projects.length }} 项</el-tag>
                </div>
              </div>
            </template>
            <el-table :data="projects" v-loading="loadingMap.projects" empty-text="暂无科研项目">
              <el-table-column prop="title" label="项目名称" min-width="220" />
              <el-table-column prop="level_display" label="级别" width="120" />
              <el-table-column prop="role_display" label="角色" width="120" />
              <el-table-column prop="funding_amount" label="经费(万元)" width="120" />
              <el-table-column prop="status" label="状态" width="120" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="startEditRecord('projects', row)">编辑</el-button>
                  <el-button link type="danger" @click="removeRecord('projects', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="知识产权" name="intellectual-properties">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>{{ isEditing('intellectual-properties') ? editingLabelMap['intellectual-properties'].edit : editingLabelMap['intellectual-properties'].create }}</template>
            <el-form ref="ipFormRef" :model="ipForm" :rules="ipRules" label-position="top">
              <el-form-item label="成果名称" prop="title">
                <el-input v-model="ipForm.title" placeholder="请输入知识产权名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="授权/登记时间" prop="date_acquired">
                  <el-date-picker v-model="ipForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="类型" prop="ip_type">
                  <el-select v-model="ipForm.ip_type" style="width: 100%">
                    <el-option v-for="option in ipTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="登记号/专利号" prop="registration_number">
                <el-input v-model="ipForm.registration_number" placeholder="请输入登记号或专利号" />
              </el-form-item>
              <el-form-item>
                <el-switch v-model="ipForm.is_transformed" active-text="已成果转化" inactive-text="未成果转化" />
              </el-form-item>
              <div class="actions">
                <el-button v-if="isEditing('intellectual-properties')" @click="resetIpForm">取消编辑</el-button>
                <el-button v-else @click="resetIpForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['intellectual-properties']" @click="submitIp">
                  {{
                    isEditing('intellectual-properties')
                      ? editingLabelMap['intellectual-properties'].submitEdit
                      : editingLabelMap['intellectual-properties'].submitCreate
                  }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header card-header-wrap">
                <span>我的知识产权</span>
                <div class="header-tools">
                  <el-input
                    v-model="queryMap['intellectual-properties'].search"
                    clearable
                    placeholder="按名称 / 登记号搜索"
                    class="filter-input"
                    @keyup.enter="fetchRecords('intellectual-properties')"
                    @clear="fetchRecords('intellectual-properties')"
                  />
                  <el-button plain @click="clearFilters('intellectual-properties')">清空筛选</el-button>
                  <el-tag type="warning">{{ intellectualProperties.length }} 项</el-tag>
                </div>
              </div>
            </template>
            <el-table :data="intellectualProperties" v-loading="loadingMap['intellectual-properties']" empty-text="暂无知识产权成果">
              <el-table-column prop="title" label="名称" min-width="220" />
              <el-table-column prop="ip_type_display" label="类型" width="140" />
              <el-table-column prop="registration_number" label="登记号" min-width="180" />
              <el-table-column label="转化" width="90">
                <template #default="{ row }">
                  <el-tag :type="row.is_transformed ? 'success' : 'info'">{{ row.is_transformed ? '已转化' : '未转化' }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="startEditRecord('intellectual-properties', row)">编辑</el-button>
                  <el-button link type="danger" @click="removeRecord('intellectual-properties', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="教学成果" name="teaching-achievements">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>{{ isEditing('teaching-achievements') ? editingLabelMap['teaching-achievements'].edit : editingLabelMap['teaching-achievements'].create }}</template>
            <el-form ref="teachingFormRef" :model="teachingForm" :rules="teachingRules" label-position="top">
              <el-form-item label="成果名称" prop="title">
                <el-input v-model="teachingForm.title" placeholder="请输入教学成果名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="获得时间" prop="date_acquired">
                  <el-date-picker v-model="teachingForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="成果类型" prop="achievement_type">
                  <el-select v-model="teachingForm.achievement_type" style="width: 100%">
                    <el-option v-for="option in teachingTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="级别" prop="level">
                <el-input v-model="teachingForm.level" placeholder="如 国家级、省级、校级" />
              </el-form-item>
              <div class="actions">
                <el-button v-if="isEditing('teaching-achievements')" @click="resetTeachingForm">取消编辑</el-button>
                <el-button v-else @click="resetTeachingForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['teaching-achievements']" @click="submitTeaching">
                  {{
                    isEditing('teaching-achievements')
                      ? editingLabelMap['teaching-achievements'].submitEdit
                      : editingLabelMap['teaching-achievements'].submitCreate
                  }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header card-header-wrap">
                <span>我的教学成果</span>
                <div class="header-tools">
                  <el-input
                    v-model="queryMap['teaching-achievements'].search"
                    clearable
                    placeholder="按名称 / 级别搜索"
                    class="filter-input"
                    @keyup.enter="fetchRecords('teaching-achievements')"
                    @clear="fetchRecords('teaching-achievements')"
                  />
                  <el-button plain @click="clearFilters('teaching-achievements')">清空筛选</el-button>
                  <el-tag>{{ teachingAchievements.length }} 项</el-tag>
                </div>
              </div>
            </template>
            <el-table :data="teachingAchievements" v-loading="loadingMap['teaching-achievements']" empty-text="暂无教学成果">
              <el-table-column prop="title" label="名称" min-width="220" />
              <el-table-column prop="achievement_type_display" label="类型" width="140" />
              <el-table-column prop="level" label="级别" width="120" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="startEditRecord('teaching-achievements', row)">编辑</el-button>
                  <el-button link type="danger" @click="removeRecord('teaching-achievements', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <el-tab-pane label="学术服务" name="academic-services">
        <div class="entry-grid">
          <el-card shadow="never">
            <template #header>{{ isEditing('academic-services') ? editingLabelMap['academic-services'].edit : editingLabelMap['academic-services'].create }}</template>
            <el-form ref="serviceFormRef" :model="serviceForm" :rules="serviceRules" label-position="top">
              <el-form-item label="服务名称" prop="title">
                <el-input v-model="serviceForm.title" placeholder="请输入服务事项或报告名称" />
              </el-form-item>
              <div class="double-grid">
                <el-form-item label="服务时间" prop="date_acquired">
                  <el-date-picker v-model="serviceForm.date_acquired" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
                </el-form-item>
                <el-form-item label="服务类型" prop="service_type">
                  <el-select v-model="serviceForm.service_type" style="width: 100%">
                    <el-option v-for="option in serviceTypeOptions" :key="option.value" :label="option.label" :value="option.value" />
                  </el-select>
                </el-form-item>
              </div>
              <el-form-item label="服务机构" prop="organization">
                <el-input v-model="serviceForm.organization" placeholder="请输入期刊、会议或机构名称" />
              </el-form-item>
              <div class="actions">
                <el-button v-if="isEditing('academic-services')" @click="resetServiceForm">取消编辑</el-button>
                <el-button v-else @click="resetServiceForm">重置</el-button>
                <el-button type="primary" :loading="submittingMap['academic-services']" @click="submitService">
                  {{
                    isEditing('academic-services')
                      ? editingLabelMap['academic-services'].submitEdit
                      : editingLabelMap['academic-services'].submitCreate
                  }}
                </el-button>
              </div>
            </el-form>
          </el-card>

          <el-card shadow="never">
            <template #header>
              <div class="card-header card-header-wrap">
                <span>我的学术服务</span>
                <div class="header-tools">
                  <el-input
                    v-model="queryMap['academic-services'].search"
                    clearable
                    placeholder="按事项 / 服务机构搜索"
                    class="filter-input"
                    @keyup.enter="fetchRecords('academic-services')"
                    @clear="fetchRecords('academic-services')"
                  />
                  <el-button plain @click="clearFilters('academic-services')">清空筛选</el-button>
                  <el-tag type="danger">{{ academicServices.length }} 项</el-tag>
                </div>
              </div>
            </template>
            <el-table :data="academicServices" v-loading="loadingMap['academic-services']" empty-text="暂无学术服务">
              <el-table-column prop="title" label="事项" min-width="220" />
              <el-table-column prop="service_type_display" label="类型" width="140" />
              <el-table-column prop="organization" label="服务机构" min-width="180" />
              <el-table-column prop="date_acquired" label="时间" width="120" />
              <el-table-column label="操作" width="140" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" @click="startEditRecord('academic-services', row)">编辑</el-button>
                  <el-button link type="danger" @click="removeRecord('academic-services', row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>
    </el-tabs>

    <PaperBibtexImportDialog v-model="bibtexDialogVisible" @imported="handleBibtexImported" />
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import PaperBibtexImportDialog from './achievement-entry/PaperBibtexImportDialog.vue'
import PaperGovernancePanel from './achievement-entry/PaperGovernancePanel.vue'
import { createAchievement, deleteAchievement, fetchAchievementList, fetchPaperSummary, updateAchievement } from './achievement-entry/api'
import { removeAchievementRecord, upsertAchievementRecord } from './achievement-entry/recordState.js'
import { ensureSessionUserContext, type SessionUser } from '../utils/sessionAuth'
import {
  buildCrossModuleQuery,
  focusEvidenceSection,
  mapAchievementTypeToEntryTab,
  mapAchievementTypeToPortraitDimension,
  parseCrossModuleLink,
} from '../utils/crossModuleLinking'
import type { DashboardStatsResponse, RecentAchievementRecord } from './dashboard/portrait'
import {
  achievementEndpointMap,
  createAchievementQueryState,
  createAchievementStatusMap,
  ipTypeOptions,
  paperTypeOptions,
  paperRepresentativeOptions,
  paperSortOptions,
  parseCoauthorInput,
  projectLevelOptions,
  projectRoleOptions,
  serviceTypeOptions,
  teachingTypeOptions,
} from './achievement-entry/constants'
import { buildPaperDuplicateWarnings, buildPaperMetadataHints, buildPaperYearOptions } from './achievement-entry/paperLifecycle.js'
import type {
  AchievementMutationPayloadMap,
  AchievementQueryState,
  IpFormState,
  IpRecord,
  BibtexImportResponse,
  PaperSummaryResponse,
  PaperFormState,
  PaperRecord,
  ProjectFormState,
  ProjectRecord,
  ServiceFormState,
  ServiceRecord,
  TabName,
  TeachingFormState,
  TeachingRecord,
} from './achievement-entry/types'

const route = useRoute()
const router = useRouter()
const linkContext = computed(() => parseCrossModuleLink(route.query))
const activeTab = ref<TabName>('papers')
const pageLoading = ref(false)
const sessionUser = ref<SessionUser | null>(null)
const bibtexDialogVisible = ref(false)
const dashboardStats = ref<DashboardStatsResponse | null>(null)
const paperSummary = ref<PaperSummaryResponse | null>(null)

const paperFormRef = ref<FormInstance>()
const projectFormRef = ref<FormInstance>()
const ipFormRef = ref<FormInstance>()
const teachingFormRef = ref<FormInstance>()
const serviceFormRef = ref<FormInstance>()

const papers = ref<PaperRecord[]>([])
const projects = ref<ProjectRecord[]>([])
const intellectualProperties = ref<IpRecord[]>([])
const teachingAchievements = ref<TeachingRecord[]>([])
const academicServices = ref<ServiceRecord[]>([])

const loadingMap = reactive<Record<TabName, boolean>>(createAchievementStatusMap())
const submittingMap = reactive<Record<TabName, boolean>>(createAchievementStatusMap())
const editingMap = reactive<Record<TabName, number | null>>({
  papers: null,
  projects: null,
  'intellectual-properties': null,
  'teaching-achievements': null,
  'academic-services': null,
})
const queryMap = reactive<AchievementQueryState>(createAchievementQueryState())

const paperForm = reactive<PaperFormState>({
  title: '',
  abstract: '',
  date_acquired: '',
  paper_type: 'JOURNAL',
  journal_name: '',
  journal_level: '',
  published_volume: '',
  published_issue: '',
  pages: '',
  source_url: '',
  citation_count: 0,
  is_first_author: true,
  is_representative: false,
  doi: '',
  coauthorInput: '',
})

const projectForm = reactive<ProjectFormState>({
  title: '',
  date_acquired: '',
  level: 'NATIONAL',
  role: 'PI',
  funding_amount: 0,
  status: 'ONGOING',
})

const ipForm = reactive<IpFormState>({
  title: '',
  date_acquired: '',
  ip_type: 'PATENT_INVENTION',
  registration_number: '',
  is_transformed: false,
})

const teachingForm = reactive<TeachingFormState>({
  title: '',
  date_acquired: '',
  achievement_type: 'COMPETITION',
  level: '',
})

const serviceForm = reactive<ServiceFormState>({
  title: '',
  date_acquired: '',
  service_type: 'EDITOR',
  organization: '',
})

const teacherLabel = computed(() => {
  if (!sessionUser.value) {
    return '未识别教师'
  }

  return sessionUser.value.real_name || sessionUser.value.username
})

const recentAchievements = computed<RecentAchievementRecord[]>(() => dashboardStats.value?.recent_achievements || [])
const linkContextTitle = computed(() => {
  if (linkContext.value?.source === 'recommendation') {
    return '当前从推荐模块回跳，已定位到成果证据区。'
  }
  if (linkContext.value?.source === 'assistant') {
    return '当前从问答来源卡片回跳，已定位到成果证据区。'
  }
  if (linkContext.value?.source === 'portrait') {
    return '当前从画像模块回跳，已定位到成果证据区。'
  }
  return '当前已定位到成果证据区。'
})
const linkContextDescription = computed(
  () => linkContext.value?.note || '当前成果联动只回跳到本人可编辑、可核验的真实成果记录，不会虚构支撑证据。',
)

const paperYearOptions = computed(() => buildPaperYearOptions(paperSummary.value))

const paperDuplicateWarnings = computed(() =>
  buildPaperDuplicateWarnings(paperForm, papers.value, editingMap.papers),
)

const paperMetadataHints = computed(() => buildPaperMetadataHints(paperForm))

const achievementOverviewCards = computed(() => [
  {
    label: '成果总量',
    value: dashboardStats.value?.achievement_overview?.total_achievements || 0,
    helper: '覆盖论文、项目、知识产权、教学成果与学术服务',
  },
  {
    label: '论文代表作',
    value: paperSummary.value?.representative_count || 0,
    helper: '已标记为代表作的论文数量',
  },
  {
    label: '近三年论文',
    value: paperSummary.value?.recent_count || 0,
    helper: '用于观察近年持续产出情况',
  },
  {
    label: '待补元数据',
    value: paperSummary.value?.incomplete_metadata_count || 0,
    helper: '缺少链接、页码或期刊级别的论文记录',
  },
])

const recentAchievementEvidenceId = (type: string, id: number) => `recent-achievement-${type}-${id}`

const isActiveRecentAchievement = (type: string, id: number) =>
  linkContext.value?.recordType === type && linkContext.value?.recordId === id

const requiredRule = (message: string) => [{ required: true, message, trigger: 'blur' }]

const isEditing = (tab: TabName): boolean => editingMap[tab] !== null

const editingLabelMap: Record<TabName, { create: string; edit: string; submitCreate: string; submitEdit: string }> = {
  papers: {
    create: '论文录入',
    edit: '论文编辑',
    submitCreate: '提交论文',
    submitEdit: '保存论文',
  },
  projects: {
    create: '项目录入',
    edit: '项目编辑',
    submitCreate: '提交项目',
    submitEdit: '保存项目',
  },
  'intellectual-properties': {
    create: '知识产权录入',
    edit: '知识产权编辑',
    submitCreate: '提交知识产权',
    submitEdit: '保存知识产权',
  },
  'teaching-achievements': {
    create: '教学成果录入',
    edit: '教学成果编辑',
    submitCreate: '提交教学成果',
    submitEdit: '保存教学成果',
  },
  'academic-services': {
    create: '学术服务录入',
    edit: '学术服务编辑',
    submitCreate: '提交学术服务',
    submitEdit: '保存学术服务',
  },
}

const paperRules: FormRules = {
  title: requiredRule('请输入论文题目'),
  abstract: requiredRule('请输入论文摘要'),
  date_acquired: requiredRule('请选择获得时间'),
  paper_type: requiredRule('请选择论文类型'),
  journal_name: requiredRule('请输入期刊或会议名称'),
}

const projectRules: FormRules = {
  title: requiredRule('请输入项目名称'),
  date_acquired: requiredRule('请选择立项时间'),
  level: requiredRule('请选择项目级别'),
  role: requiredRule('请选择承担角色'),
  funding_amount: requiredRule('请输入项目经费'),
  status: requiredRule('请输入项目状态'),
}

const ipRules: FormRules = {
  title: requiredRule('请输入成果名称'),
  date_acquired: requiredRule('请选择授权时间'),
  ip_type: requiredRule('请选择知识产权类型'),
  registration_number: requiredRule('请输入登记号'),
}

const teachingRules: FormRules = {
  title: requiredRule('请输入成果名称'),
  date_acquired: requiredRule('请选择获得时间'),
  achievement_type: requiredRule('请选择成果类型'),
  level: requiredRule('请输入成果级别'),
}

const serviceRules: FormRules = {
  title: requiredRule('请输入服务名称'),
  date_acquired: requiredRule('请选择服务时间'),
  service_type: requiredRule('请选择服务类型'),
  organization: requiredRule('请输入服务机构'),
}

const fetchRecords = async (tab: TabName): Promise<void> => {
  loadingMap[tab] = true
  try {
    const items = await fetchAchievementList(tab, queryMap[tab])

    if (tab === 'papers') papers.value = items as PaperRecord[]
    if (tab === 'projects') projects.value = items as ProjectRecord[]
    if (tab === 'intellectual-properties') intellectualProperties.value = items as IpRecord[]
    if (tab === 'teaching-achievements') teachingAchievements.value = items as TeachingRecord[]
    if (tab === 'academic-services') academicServices.value = items as ServiceRecord[]
  } finally {
    loadingMap[tab] = false
  }
}

const fetchDashboardStats = async (): Promise<void> => {
  const response = await axios.get<DashboardStatsResponse>('/api/achievements/dashboard-stats/')
  dashboardStats.value = response.data
}

const fetchPaperInsights = async (): Promise<void> => {
  paperSummary.value = await fetchPaperSummary(queryMap.papers)
}

const refreshAllRecords = async (): Promise<void> => {
  pageLoading.value = true
  try {
    sessionUser.value = await ensureSessionUserContext()
    await Promise.all((Object.keys(achievementEndpointMap) as TabName[]).map(fetchRecords))
    await Promise.all([fetchDashboardStats(), fetchPaperInsights()])
    await nextTick()
    focusAchievementEvidence()
  } finally {
    pageLoading.value = false
  }
}

const focusAchievementEvidence = (): void => {
  if (linkContext.value?.recordType) {
    activeTab.value = mapAchievementTypeToEntryTab(linkContext.value.recordType) as TabName
  }

  if (linkContext.value?.section !== 'achievement-records') {
    return
  }

  focusEvidenceSection(
    'achievement-records-section',
    linkContext.value?.recordType && linkContext.value?.recordId
      ? recentAchievementEvidenceId(linkContext.value.recordType, linkContext.value.recordId)
      : undefined,
  )
}

const resetPaperForm = (): void => {
  paperFormRef.value?.resetFields()
  paperForm.paper_type = 'JOURNAL'
  paperForm.published_volume = ''
  paperForm.published_issue = ''
  paperForm.pages = ''
  paperForm.source_url = ''
  paperForm.citation_count = 0
  paperForm.is_first_author = true
  paperForm.is_representative = false
  paperForm.coauthorInput = ''
  editingMap.papers = null
}

const resetProjectForm = (): void => {
  projectFormRef.value?.resetFields()
  projectForm.level = 'NATIONAL'
  projectForm.role = 'PI'
  projectForm.funding_amount = 0
  projectForm.status = 'ONGOING'
  editingMap.projects = null
}

const resetIpForm = (): void => {
  ipFormRef.value?.resetFields()
  ipForm.ip_type = 'PATENT_INVENTION'
  ipForm.is_transformed = false
  editingMap['intellectual-properties'] = null
}

const resetTeachingForm = (): void => {
  teachingFormRef.value?.resetFields()
  teachingForm.achievement_type = 'COMPETITION'
  editingMap['teaching-achievements'] = null
}

const resetServiceForm = (): void => {
  serviceFormRef.value?.resetFields()
  serviceForm.service_type = 'EDITOR'
  editingMap['academic-services'] = null
}

const clearFilters = async (tab: TabName): Promise<void> => {
  if (tab === 'papers') {
    queryMap.papers.paper_type = 'ALL'
    queryMap.papers.year = 'ALL'
    queryMap.papers.is_representative = 'ALL'
    queryMap.papers.sort_by = 'date_desc'
  }
  queryMap[tab].search = ''
  await fetchRecords(tab)
  if (tab === 'papers') {
    await fetchPaperInsights()
  }
}

const populatePaperForm = (record: PaperRecord): void => {
  paperForm.title = record.title
  paperForm.abstract = record.abstract
  paperForm.date_acquired = record.date_acquired
  paperForm.paper_type = record.paper_type
  paperForm.journal_name = record.journal_name
  paperForm.journal_level = record.journal_level
  paperForm.published_volume = record.published_volume
  paperForm.published_issue = record.published_issue
  paperForm.pages = record.pages
  paperForm.source_url = record.source_url
  paperForm.citation_count = record.citation_count
  paperForm.is_first_author = record.is_first_author
  paperForm.is_representative = record.is_representative
  paperForm.doi = record.doi
  paperForm.coauthorInput = record.coauthor_details.map(item => item.name).join('，')
}

const populateProjectForm = (record: ProjectRecord): void => {
  projectForm.title = record.title
  projectForm.date_acquired = record.date_acquired
  projectForm.level = record.level
  projectForm.role = record.role
  projectForm.funding_amount = Number(record.funding_amount)
  projectForm.status = record.status
}

const populateIpForm = (record: IpRecord): void => {
  ipForm.title = record.title
  ipForm.date_acquired = record.date_acquired
  ipForm.ip_type = record.ip_type
  ipForm.registration_number = record.registration_number
  ipForm.is_transformed = record.is_transformed
}

const populateTeachingForm = (record: TeachingRecord): void => {
  teachingForm.title = record.title
  teachingForm.date_acquired = record.date_acquired
  teachingForm.achievement_type = record.achievement_type
  teachingForm.level = record.level
}

const populateServiceForm = (record: ServiceRecord): void => {
  serviceForm.title = record.title
  serviceForm.date_acquired = record.date_acquired
  serviceForm.service_type = record.service_type
  serviceForm.organization = record.organization
}

const startEditRecord = (tab: TabName, record: PaperRecord | ProjectRecord | IpRecord | TeachingRecord | ServiceRecord): void => {
  editingMap[tab] = record.id
  activeTab.value = tab

  if (tab === 'papers') populatePaperForm(record as PaperRecord)
  if (tab === 'projects') populateProjectForm(record as ProjectRecord)
  if (tab === 'intellectual-properties') populateIpForm(record as IpRecord)
  if (tab === 'teaching-achievements') populateTeachingForm(record as TeachingRecord)
  if (tab === 'academic-services') populateServiceForm(record as ServiceRecord)
}

const submitAchievement = async <T extends TabName>(
  tab: T,
  payload: AchievementMutationPayloadMap[T],
  onReset: () => void,
): Promise<void> => {
  submittingMap[tab] = true

  try {
    const savedRecord = editingMap[tab]
      ? await updateAchievement(tab, editingMap[tab] as number, payload)
      : await createAchievement(tab, payload)

    if (editingMap[tab]) {
      ElMessage.success(`${editingLabelMap[tab].edit}已保存`)
    } else {
      ElMessage.success(`${editingLabelMap[tab].create}已提交`)
    }

    if (tab === 'papers') papers.value = upsertAchievementRecord(papers.value, savedRecord as PaperRecord)
    if (tab === 'projects') projects.value = upsertAchievementRecord(projects.value, savedRecord as ProjectRecord)
    if (tab === 'intellectual-properties') intellectualProperties.value = upsertAchievementRecord(intellectualProperties.value, savedRecord as IpRecord)
    if (tab === 'teaching-achievements') teachingAchievements.value = upsertAchievementRecord(teachingAchievements.value, savedRecord as TeachingRecord)
    if (tab === 'academic-services') academicServices.value = upsertAchievementRecord(academicServices.value, savedRecord as ServiceRecord)

    await fetchDashboardStats()
    if (tab === 'papers') {
      await fetchPaperInsights()
    }

    onReset()
  } finally {
    submittingMap[tab] = false
  }
}

const submitPaper = async (): Promise<void> => {
  const valid = await paperFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (paperDuplicateWarnings.value.length) {
    try {
      await ElMessageBox.confirm(paperDuplicateWarnings.value.join('\n'), '重复录入提示', {
        type: 'warning',
        confirmButtonText: '继续提交',
        cancelButtonText: '返回检查',
      })
    } catch {
      return
    }
  }

  await submitAchievement(
    'papers',
    {
      title: paperForm.title,
      abstract: paperForm.abstract,
      date_acquired: paperForm.date_acquired,
      paper_type: paperForm.paper_type,
      journal_name: paperForm.journal_name,
      journal_level: paperForm.journal_level,
      published_volume: paperForm.published_volume,
      published_issue: paperForm.published_issue,
      pages: paperForm.pages,
      source_url: paperForm.source_url,
      citation_count: paperForm.citation_count,
      is_first_author: paperForm.is_first_author,
      is_representative: paperForm.is_representative,
      doi: paperForm.doi,
      coauthors: parseCoauthorInput(paperForm.coauthorInput),
    },
    resetPaperForm,
  )
}

const submitProject = async (): Promise<void> => {
  const valid = await projectFormRef.value?.validate().catch(() => false)
  if (!valid) return

  await submitAchievement('projects', { ...projectForm }, resetProjectForm)
}

const submitIp = async (): Promise<void> => {
  const valid = await ipFormRef.value?.validate().catch(() => false)
  if (!valid) return

  await submitAchievement('intellectual-properties', { ...ipForm }, resetIpForm)
}

const submitTeaching = async (): Promise<void> => {
  const valid = await teachingFormRef.value?.validate().catch(() => false)
  if (!valid) return

  await submitAchievement('teaching-achievements', { ...teachingForm }, resetTeachingForm)
}

const submitService = async (): Promise<void> => {
  const valid = await serviceFormRef.value?.validate().catch(() => false)
  if (!valid) return

  await submitAchievement('academic-services', { ...serviceForm }, resetServiceForm)
}

const removeRecord = async (tab: TabName, id: number): Promise<void> => {
  await ElMessageBox.confirm('删除后将同步影响画像统计与图谱展示，确认继续吗？', '删除确认', {
    type: 'warning',
  })

  await deleteAchievement(tab, id)
  ElMessage.success('记录已删除')
  if (editingMap[tab] === id) {
    if (tab === 'papers') resetPaperForm()
    if (tab === 'projects') resetProjectForm()
    if (tab === 'intellectual-properties') resetIpForm()
    if (tab === 'teaching-achievements') resetTeachingForm()
    if (tab === 'academic-services') resetServiceForm()
  }
  if (tab === 'papers') papers.value = removeAchievementRecord(papers.value, id)
  if (tab === 'projects') projects.value = removeAchievementRecord(projects.value, id)
  if (tab === 'intellectual-properties') intellectualProperties.value = removeAchievementRecord(intellectualProperties.value, id)
  if (tab === 'teaching-achievements') teachingAchievements.value = removeAchievementRecord(teachingAchievements.value, id)
  if (tab === 'academic-services') academicServices.value = removeAchievementRecord(academicServices.value, id)
  await fetchDashboardStats()
  if (tab === 'papers') {
    await fetchPaperInsights()
  }
}

const handleBibtexImported = async (payload: BibtexImportResponse): Promise<void> => {
  await Promise.all([fetchRecords('papers'), fetchDashboardStats(), fetchPaperInsights()])
  if (payload.imported_records.length === 1) {
    const target = papers.value.find(item => item.id === payload.imported_records[0]?.id)
    if (target) {
      startEditRecord('papers', target)
      ElMessage.info('已为你打开导入论文的修订表单，可继续补充元数据。')
    }
  }
}

const handleGovernanceRefresh = async (): Promise<void> => {
  await Promise.all([fetchRecords('papers'), fetchDashboardStats(), fetchPaperInsights()])
}

const handleGovernanceEditPaper = (paperId: number): void => {
  const target = papers.value.find(item => item.id === paperId)
  if (target) {
    startEditRecord('papers', target)
  }
}

const goToPortraitAndGraph = (): void => {
  void router.push('/dashboard')
}

const goToRecommendation = (): void => {
  void router.push('/project-recommendations')
}

const goToAssistant = (): void => {
  void router.push('/assistant-demo')
}

const goToPortraitDimensionFromAchievement = (type: string, id: number): void => {
  void router.push({
    name: 'dashboard',
    query: buildCrossModuleQuery({
      source: 'achievement',
      page: 'portrait',
      section: 'portrait-dimensions',
      dimension_key: mapAchievementTypeToPortraitDimension(type),
      record_type: type,
      record_id: String(id),
    }),
  })
}

const goToRecommendationFromAchievement = (type: string, id: number): void => {
  void router.push({
    name: 'project-recommendations',
    query: buildCrossModuleQuery({
      source: 'achievement',
      page: 'recommendations',
      section: 'recommendation-evidence',
      dimension_key: mapAchievementTypeToPortraitDimension(type),
      record_type: type,
      record_id: String(id),
    }),
  })
}

const goToAssistantFromAchievement = (type: string, id: number): void => {
  void router.push({
    name: 'assistant-demo',
    query: buildCrossModuleQuery({
      source: 'achievement',
      page: 'assistant',
      section: 'assistant-answer',
      question_type: 'achievement_summary',
      record_type: type,
      record_id: String(id),
    }),
  })
}

const goToProfileCenter = (): void => {
  void router.push('/profile-editor')
}

onMounted(() => {
  void refreshAllRecords()
})

watch(linkContext, () => {
  focusAchievementEvidence()
})
</script>

<style scoped>
.achievement-entry-page {
  padding: 28px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.12), transparent 26%),
    radial-gradient(circle at bottom right, rgba(37, 99, 235, 0.1), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #eef6ff 100%);
  min-height: 100vh;
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

.entry-tabs :deep(.el-card) {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
  margin-bottom: 20px;
}

.link-context-shell {
  margin-bottom: 20px;
}

.overview-card {
  border: none;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.08);
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.metric-item {
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
  display: grid;
  gap: 6px;
}

.metric-item strong {
  font-size: 26px;
  color: #0f172a;
}

.metric-item span {
  font-weight: 600;
  color: #1e293b;
}

.metric-item p,
.panel-note,
.recent-item p,
.distribution-label,
.warning-text,
.success-text,
.form-alert p {
  margin: 0;
  color: #5b6b7c;
  line-height: 1.6;
}

.hub-links,
.paper-summary-strip,
.distribution-strip,
.table-action-group {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hub-links {
  margin-bottom: 12px;
}

.recent-list {
  display: grid;
  gap: 12px;
}

.recent-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 0;
  border-bottom: 1px solid #e7eef6;
}

.recent-item--active,
.evidence-section-highlight {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.14);
  border-radius: 18px;
  padding: 14px 16px;
}

.recent-item:last-child {
  border-bottom: none;
}

.recent-meta {
  display: grid;
  justify-items: end;
  gap: 8px;
  text-align: right;
}

.recent-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.hero-actions,
.card-header,
.actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-header-wrap {
  align-items: flex-start;
}

.header-tools {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}

.filter-input {
  width: min(280px, 100%);
}

.filter-select {
  width: 150px;
}

.filter-select-wide {
  width: 190px;
}

.eyebrow {
  margin: 0 0 8px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

h1 {
  margin: 0;
}

.hero-text {
  margin: 12px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.88);
  line-height: 1.8;
}

.entry-tabs {
  margin-top: 0;
}

.entry-tabs :deep(.el-tabs__header) {
  margin-bottom: 18px;
}

.entry-tabs :deep(.el-tabs__nav-wrap) {
  padding: 0 6px;
}

.entry-tabs :deep(.el-tabs__item) {
  height: 42px;
  font-weight: 600;
}

.content-shell {
  max-width: 1180px;
  margin: 0 auto;
}

.entry-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 20px;
}

.double-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.triple-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.actions {
  justify-content: flex-end;
  margin-top: 8px;
}

.form-alert {
  margin-bottom: 16px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.paper-summary-strip {
  margin-bottom: 12px;
}

.distribution-strip {
  justify-content: space-between;
  margin-bottom: 16px;
}

.distribution-group {
  display: grid;
  gap: 8px;
}

.paper-title-cell {
  display: grid;
  gap: 8px;
}

.warning-text {
  color: #b45309;
}

.success-text {
  color: #047857;
}

@media (max-width: 1080px) {
  .overview-grid,
  .entry-grid,
  .double-grid,
  .triple-grid {
    grid-template-columns: 1fr;
    display: grid;
  }

  .actions {
    display: flex;
  }

  .header-tools {
    justify-content: flex-start;
  }

  .distribution-strip,
  .recent-item {
    flex-direction: column;
  }

  .recent-meta {
    justify-items: start;
    text-align: left;
  }
}

@media (max-width: 768px) {
  .achievement-entry-page {
    padding: 16px;
  }

  .hero-panel,
  .hero-actions,
  .card-header,
  .header-tools {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-input,
  .filter-select {
    width: 100%;
  }
}
</style>
