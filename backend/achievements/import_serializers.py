from rest_framework import serializers


class BibtexPreviewRequestSerializer(serializers.Serializer):
    file = serializers.FileField(required=False)
    content = serializers.CharField(required=False, allow_blank=False)

    def validate(self, attrs):
        has_file = bool(attrs.get('file'))
        has_content = bool(attrs.get('content'))
        if has_file == has_content:
            raise serializers.ValidationError('请上传一个 BibTeX 文件，或提供 BibTeX 文本内容。')
        return attrs


class BibtexIssueDetailSerializer(serializers.Serializer):
    code = serializers.CharField()
    category = serializers.CharField()
    field = serializers.CharField(required=False, allow_blank=True)
    severity = serializers.CharField(required=False, allow_blank=True, default='warning')
    message = serializers.CharField()


class BibtexImportEntrySerializer(serializers.Serializer):
    source_index = serializers.IntegerField(required=False)
    citation_key = serializers.CharField(required=False, allow_blank=True)
    entry_type = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(allow_blank=True)
    abstract = serializers.CharField(required=False, allow_blank=True, default='')
    date_acquired = serializers.CharField(allow_blank=True)
    paper_type = serializers.ChoiceField(choices=('JOURNAL', 'CONFERENCE'))
    journal_name = serializers.CharField(allow_blank=True)
    journal_level = serializers.CharField(required=False, allow_blank=True, default='')
    published_volume = serializers.CharField(required=False, allow_blank=True, default='')
    published_issue = serializers.CharField(required=False, allow_blank=True, default='')
    pages = serializers.CharField(required=False, allow_blank=True, default='')
    source_url = serializers.CharField(required=False, allow_blank=True, default='')
    citation_count = serializers.IntegerField(required=False, min_value=0, default=0)
    is_first_author = serializers.BooleanField(required=False, default=True)
    is_representative = serializers.BooleanField(required=False, default=False)
    doi = serializers.CharField(required=False, allow_blank=True, default='')
    coauthors = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    preview_status = serializers.CharField(required=False, allow_blank=True)
    issues = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list,
    )
    issue_details = BibtexIssueDetailSerializer(many=True, required=False, default=list)


class BibtexConfirmImportSerializer(serializers.Serializer):
    entries = BibtexImportEntrySerializer(many=True)


class BibtexRevalidateSerializer(serializers.Serializer):
    entries = BibtexImportEntrySerializer(many=True)
