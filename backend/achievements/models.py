from __future__ import annotations

from django.conf import settings
from django.db import models


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    department = models.CharField(max_length=200, verbose_name='所属学院')
    discipline = models.CharField(max_length=200, verbose_name='所属学科')
    title = models.CharField(max_length=100, verbose_name='职称')
    research_interests = models.TextField(blank=True, verbose_name='研究方向')
    h_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f'{self.user.username}-教师画像'


class BaseAchievement(models.Model):
    REVIEW_STATUS_CHOICES = (
        ('DRAFT', '草稿'),
        ('PENDING_REVIEW', '待审核'),
        ('APPROVED', '已通过'),
        ('REJECTED', '已驳回'),
    )

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(class)ss',
    )
    title = models.CharField(max_length=300)
    date_acquired = models.DateField(verbose_name='发表/立项时间')
    status = models.CharField(
        max_length=20,
        choices=REVIEW_STATUS_CHOICES,
        default='DRAFT',
        verbose_name='审批状态',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class Paper(BaseAchievement):
    PAPER_TYPES = (
        ('JOURNAL', '期刊论文'),
        ('CONFERENCE', '会议论文'),
    )

    paper_type = models.CharField(max_length=20, choices=PAPER_TYPES)
    journal_name = models.CharField(max_length=300)
    journal_level = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='期刊等级（SCI/EI/CCF 等）',
    )
    published_volume = models.CharField(max_length=50, blank=True, verbose_name='卷号')
    published_issue = models.CharField(max_length=50, blank=True, verbose_name='期号')
    pages = models.CharField(max_length=50, blank=True, verbose_name='页码范围')
    source_url = models.URLField(blank=True, verbose_name='来源链接')
    citation_count = models.IntegerField(default=0)
    is_first_author = models.BooleanField(default=True, verbose_name='是否第一作者')
    is_corresponding_author = models.BooleanField(default=False, verbose_name='是否通讯作者')
    is_representative = models.BooleanField(default=False, verbose_name='是否代表作')
    doi = models.CharField(max_length=200, blank=True)
    abstract = models.TextField(blank=True)

    def __str__(self) -> str:
        return f'[论文] {self.title}'


class ResearchKeyword(models.Model):
    name = models.CharField(max_length=100, unique=True)
    discipline = models.CharField(max_length=200, blank=True, verbose_name='所属学科')

    def __str__(self) -> str:
        return self.name


class PaperKeyword(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE)
    keyword = models.ForeignKey(ResearchKeyword, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f'{self.paper.title} - {self.keyword.name}'


class CoAuthor(models.Model):
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name='coauthors',
    )
    name = models.CharField(max_length=200)
    author_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name='作者位次')
    is_corresponding = models.BooleanField(default=False, verbose_name='是否通讯作者')
    organization = models.CharField(max_length=300, blank=True)
    is_internal = models.BooleanField(default=False, verbose_name='是否本校教师')
    internal_teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coauthor_links',
        verbose_name='关联内部教师账号',
    )

    def __str__(self) -> str:
        return f'{self.name} ({self.paper.title})'

    @property
    def user(self):
        """Compatibility alias for business terms that call this relation `user`."""
        return self.internal_teacher

    @user.setter
    def user(self, value):
        self.internal_teacher = value


class AchievementClaim(models.Model):
    STATUS_CHOICES = (
        ('PENDING', '待认领'),
        ('ACCEPTED', '已认领'),
        ('REJECTED', '已拒绝'),
        ('CONFLICT', '存在争议'),
    )

    achievement = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name='claims',
        verbose_name='关联成果',
    )
    initiator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_achievement_claims',
        verbose_name='录入者',
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievement_claims',
        verbose_name='被邀请认领教师',
    )
    coauthor = models.ForeignKey(
        CoAuthor,
        on_delete=models.SET_NULL,
        related_name='claims',
        null=True,
        blank=True,
        verbose_name='关联合作者记录',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='认领状态')
    proposed_author_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name='发起位次')
    proposed_is_corresponding = models.BooleanField(default=False, verbose_name='发起通讯作者标记')
    confirmed_author_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name='确认位次')
    confirmed_is_corresponding = models.BooleanField(default=False, verbose_name='确认通讯作者标记')
    confirmation_note = models.TextField(blank=True, verbose_name='认领备注')
    rank_confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name='位次确认时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='邀请时间')

    class Meta:
        ordering = ('-created_at', '-id')
        constraints = [
            models.UniqueConstraint(fields=('achievement', 'target_user'), name='uniq_claim_achievement_target'),
        ]
        indexes = [
            models.Index(fields=('status', 'created_at')),
            models.Index(fields=('target_user', 'status')),
        ]

    def __str__(self) -> str:
        return f'{self.achievement.title} -> {self.target_user_id} ({self.status})'

    @property
    def proposed_order(self):
        """Compatibility alias used by business docs/tests."""
        return self.proposed_author_rank

    @proposed_order.setter
    def proposed_order(self, value):
        self.proposed_author_rank = value

    @property
    def actual_order(self):
        """Compatibility alias used by claim accept API naming."""
        return self.confirmed_author_rank

    @actual_order.setter
    def actual_order(self, value):
        self.confirmed_author_rank = value


class Project(BaseAchievement):
    PROJECT_LEVELS = (
        ('NATIONAL', '国家级'),
        ('PROVINCIAL', '省部级'),
        ('ENTERPRISE', '企业合作'),
    )
    ROLE_TYPES = (
        ('PI', '负责人'),
        ('CO_PI', '参与人'),
    )

    level = models.CharField(max_length=20, choices=PROJECT_LEVELS)
    role = models.CharField(max_length=20, choices=ROLE_TYPES)
    funding_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='经费金额(万元)')
    project_status = models.CharField(max_length=50, default='ONGOING', verbose_name='项目状态')

    def __str__(self) -> str:
        return f'[项目] {self.title}'

    def save(self, *args, **kwargs):
        valid_review_statuses = {choice[0] for choice in self.REVIEW_STATUS_CHOICES}
        if self.status not in valid_review_statuses:
            self.project_status = self.status
            self.status = 'DRAFT'
        super().save(*args, **kwargs)


class IntellectualProperty(BaseAchievement):
    IP_TYPES = (
        ('PATENT_INVENTION', '发明专利'),
        ('PATENT_UTILITY', '实用新型'),
        ('SOFTWARE_COPYRIGHT', '软件著作权'),
    )
    ROLE_TYPES = (
        ('PI', '负责人'),
        ('CO_PI', '参与人'),
    )

    ip_type = models.CharField(max_length=50, choices=IP_TYPES)
    role = models.CharField(max_length=20, choices=ROLE_TYPES, default='PI', verbose_name='承担角色')
    registration_number = models.CharField(max_length=200)
    is_transformed = models.BooleanField(default=False, verbose_name='是否成果转化')

    def __str__(self) -> str:
        return f'[知识产权] {self.title}'


class TeachingAchievement(BaseAchievement):
    TYPES = (
        ('COMPETITION', '学生竞赛'),
        ('TEACHING_REFORM', '教改项目'),
        ('COURSE', '精品课程'),
        ('THESIS', '优秀论文指导'),
    )
    ROLE_TYPES = (
        ('PI', '负责人'),
        ('CO_PI', '参与人'),
    )

    achievement_type = models.CharField(max_length=50, choices=TYPES)
    role = models.CharField(max_length=20, choices=ROLE_TYPES, default='PI', verbose_name='承担角色')
    level = models.CharField(max_length=100, verbose_name='级别')

    def __str__(self) -> str:
        return f'[教学成果] {self.title}'


class AcademicService(BaseAchievement):
    SERVICE_TYPES = (
        ('EDITOR', '期刊编委'),
        ('REVIEWER', '期刊审稿'),
        ('COMMITTEE', '学术委员会'),
        ('INVITED_TALK', '特邀报告'),
    )

    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES)
    organization = models.CharField(max_length=300, verbose_name='服务机构')

    def __str__(self) -> str:
        return f'[学术服务] {self.title}'


class AchievementOperationLog(models.Model):
    ACHIEVEMENT_TYPE_CHOICES = (
        ('papers', '论文成果'),
        ('projects', '科研项目'),
        ('intellectual-properties', '知识产权'),
        ('teaching-achievements', '教学成果'),
        ('academic-services', '学术服务'),
    )
    ACTION_CHOICES = (
        ('CREATE', '手工新增'),
        ('UPDATE', '编辑更新'),
        ('DELETE', '删除记录'),
        ('IMPORT', '批量导入'),
        ('SUBMIT_REVIEW', '提交审核'),
        ('APPROVE', '审核通过'),
        ('REJECT', '审核驳回'),
    )
    SOURCE_CHOICES = (
        ('manual', '手工维护'),
        ('bibtex', 'BibTeX 导入'),
        ('system', '系统生成'),
    )

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='achievement_operation_logs',
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='achievement_review_logs',
        null=True,
        blank=True,
    )
    achievement_type = models.CharField(max_length=40, choices=ACHIEVEMENT_TYPE_CHOICES)
    achievement_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    summary = models.CharField(max_length=300)
    changed_fields = models.JSONField(default=list, blank=True)
    change_details = models.JSONField(default=list, blank=True)
    title_snapshot = models.CharField(max_length=300, blank=True)
    detail_snapshot = models.CharField(max_length=300, blank=True)
    snapshot_payload = models.JSONField(default=dict, blank=True)
    review_comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self) -> str:
        return f"{self.get_achievement_type_display()} / {self.get_action_display()} / {self.title_snapshot or self.achievement_id or '已删除记录'}"


class PaperOperationLog(models.Model):
    ACTION_CHOICES = (
        ('CREATE', '手工新增'),
        ('UPDATE', '编辑更新'),
        ('DELETE', '删除记录'),
        ('IMPORT', 'BibTeX 导入'),
    )
    SOURCE_CHOICES = (
        ('manual', '手工维护'),
        ('bibtex', 'BibTeX 导入'),
        ('system', '系统生成'),
    )

    paper = models.ForeignKey(
        Paper,
        on_delete=models.SET_NULL,
        related_name='operation_logs',
        null=True,
        blank=True,
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='paper_operation_logs',
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='manual')
    summary = models.CharField(max_length=300)
    changed_fields = models.JSONField(default=list, blank=True)
    metadata_flags = models.JSONField(default=list, blank=True)
    paper_title_snapshot = models.CharField(max_length=300, blank=True)
    paper_doi_snapshot = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at', '-id')

    def __str__(self) -> str:
        return f"{self.get_action_display()} - {self.paper_title_snapshot or self.paper_id or '已删除论文'}"
