from django.db import models
from django.conf import settings

"""
教师扩展信息
"""
class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    department = models.CharField(max_length=200, verbose_name="所属学院")
    discipline = models.CharField(max_length=200, verbose_name="所属学科")
    title = models.CharField(max_length=100, verbose_name="职称")
    research_interests = models.TextField(
        blank=True,
        verbose_name="研究方向"
    )
    h_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}-教师画像"


"""
科研成果基类
"""
class BaseAchievement(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)ss"
    )
    title = models.CharField(max_length=300)
    date_acquired = models.DateField(
        verbose_name="发表/立项时间"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


"""
论文表
"""
class Paper(BaseAchievement):
    PAPER_TYPES = (
        ('JOURNAL', '期刊论文'),
        ('CONFERENCE', '会议论文'),
    )
    paper_type = models.CharField(
        max_length=20,
        choices=PAPER_TYPES
    )
    journal_name = models.CharField(max_length=300)
    journal_level = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="期刊等级（SCI/EI/CCF等）"
    )
    citation_count = models.IntegerField(default=0)
    is_first_author = models.BooleanField(
        default=True,
        verbose_name="是否第一作者/通讯作者"
    )
    doi = models.CharField(
        max_length=200,
        blank=True
    )
    abstract = models.TextField(blank=True)

    def __str__(self):
        return f"[论文] {self.title}"


"""
论文关键词（支持跨学科分析）
"""
class ResearchKeyword(models.Model):
    name = models.CharField(max_length=100, unique=True)
    discipline = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="所属学科"
    )

    def __str__(self):
        return self.name


class PaperKeyword(models.Model):
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE
    )
    keyword = models.ForeignKey(
        ResearchKeyword,
        on_delete=models.CASCADE
    )
    
    def __str__(self):
        return f"{self.paper.title} - {self.keyword.name}"


"""
论文合作者 (用于构建合作网络)
"""
class CoAuthor(models.Model):
    paper = models.ForeignKey(
        Paper,
        on_delete=models.CASCADE,
        related_name="coauthors"
    )
    name = models.CharField(max_length=200)
    organization = models.CharField(
        max_length=300,
        blank=True
    )
    is_internal = models.BooleanField(
        default=False,
        verbose_name="是否本校教师"
    )

    def __str__(self):
        return f"{self.name} ({self.paper.title})"


"""
科研项目
"""
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
    level = models.CharField(
        max_length=20,
        choices=PROJECT_LEVELS
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_TYPES
    )
    funding_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="经费金额(万元)"
    )
    status = models.CharField(
        max_length=50,
        default="ONGOING",
        verbose_name="项目状态"
    )

    def __str__(self):
        return f"[项目] {self.title}"


"""
知识产权
"""
class IntellectualProperty(BaseAchievement):
    IP_TYPES = (
        ('PATENT_INVENTION', '发明专利'),
        ('PATENT_UTILITY', '实用新型'),
        ('SOFTWARE_COPYRIGHT', '软件著作权'),
    )
    ip_type = models.CharField(
        max_length=50,
        choices=IP_TYPES
    )
    registration_number = models.CharField(
        max_length=200
    )
    is_transformed = models.BooleanField(
        default=False,
        verbose_name="是否成果转化"
    )

    def __str__(self):
        return f"[知识产权] {self.title}"


"""
教学与人才培养
"""
class TeachingAchievement(BaseAchievement):
    TYPES = (
        ('COMPETITION', '学生竞赛'),
        ('TEACHING_REFORM', '教改项目'),
        ('COURSE', '精品课程'),
        ('THESIS', '优秀论文指导'),
    )
    achievement_type = models.CharField(
        max_length=50,
        choices=TYPES
    )
    level = models.CharField(
        max_length=100,
        verbose_name="级别"
    )

    def __str__(self):
        return f"[教学成果] {self.title}"


"""
学术服务
"""
class AcademicService(BaseAchievement):
    SERVICE_TYPES = (
        ('EDITOR', '期刊编委'),
        ('REVIEWER', '期刊审稿'),
        ('COMMITTEE', '学术委员会'),
        ('INVITED_TALK', '特邀报告'),
    )
    service_type = models.CharField(
        max_length=50,
        choices=SERVICE_TYPES
    )
    organization = models.CharField(
        max_length=300,
        verbose_name="服务机构"
    )

    def __str__(self):
        return f"[学术服务] {self.title}"