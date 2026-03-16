from django.utils import timezone
from rest_framework import serializers

from .models import CoAuthor, Paper, PaperKeyword


class CoAuthorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoAuthor
        fields = ('id', 'name', 'organization', 'is_internal', 'internal_teacher')


class PaperSerializer(serializers.ModelSerializer):
    coauthors = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list,
    )
    coauthor_details = CoAuthorDetailSerializer(source='coauthors', many=True, read_only=True)
    keywords = serializers.SerializerMethodField()
    teacher_name = serializers.SerializerMethodField()
    paper_type_display = serializers.CharField(source='get_paper_type_display', read_only=True)

    class Meta:
        model = Paper
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'abstract',
            'date_acquired',
            'paper_type',
            'paper_type_display',
            'journal_name',
            'journal_level',
            'citation_count',
            'is_first_author',
            'doi',
            'created_at',
            'coauthors',
            'coauthor_details',
            'keywords',
        )
        read_only_fields = ('id', 'teacher', 'teacher_name', 'created_at', 'coauthor_details', 'keywords')

    def validate_title(self, value):
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError('论文标题至少需要 3 个字符。')
        return cleaned

    def validate_journal_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('期刊或会议名称不能为空。')
        return cleaned

    def validate_citation_count(self, value):
        if value < 0:
            raise serializers.ValidationError('引用次数不能为负数。')
        return value

    def validate_coauthors(self, value):
        normalized = []
        for item in value:
            name = item.strip()
            if name and name not in normalized:
                normalized.append(name)
        return normalized[:20]

    def validate(self, attrs):
        request = self.context.get('request')
        date_acquired = attrs.get('date_acquired')

        if date_acquired and date_acquired > timezone.now().date():
            raise serializers.ValidationError({'date_acquired': '发表日期不能晚于今天。'})

        doi = (attrs.get('doi') or '').strip()
        if doi and request and request.user and request.user.is_authenticated:
            existing = Paper.objects.filter(teacher=request.user, doi=doi)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({'doi': '当前账号下已存在相同 DOI 的论文。'})
            attrs['doi'] = doi

        if 'journal_level' in attrs and attrs['journal_level']:
            attrs['journal_level'] = attrs['journal_level'].strip()

        return attrs

    def create(self, validated_data):
        coauthor_names = validated_data.pop('coauthors', [])
        paper = Paper.objects.create(**validated_data)
        self._replace_coauthors(paper, coauthor_names)
        return paper

    def update(self, instance, validated_data):
        coauthor_names = validated_data.pop('coauthors', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if coauthor_names is not None:
            self._replace_coauthors(instance, coauthor_names)

        return instance

    def get_keywords(self, obj):
        keyword_relations = PaperKeyword.objects.filter(paper=obj).select_related('keyword')
        return [relation.keyword.name for relation in keyword_relations]

    def get_teacher_name(self, obj):
        return obj.teacher.real_name or obj.teacher.username

    def _replace_coauthors(self, paper, coauthor_names):
        paper.coauthors.all().delete()
        for name in coauthor_names:
            CoAuthor.objects.create(paper=paper, name=name)
