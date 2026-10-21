from rest_framework import serializers
from .models import ChannelAuditReport

class ChannelDataSerializer(serializers.Serializer):
    """
    Serializer for inputting a YouTube Channel ID to fetch data.
    """
    channel_id = serializers.CharField(
        max_length=255,
        help_text="The YouTube Channel ID (e.g., UC_x5XG1OV2P6wRIMd-ohLwg)"
    )

class AuditRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting an AI audit report.
    """
    channel_id = serializers.CharField(
        max_length=255,
        help_text="The YouTube Channel ID for which to generate the audit."
    )
    report_type = serializers.ChoiceField(
        choices=[
            ('overall', 'Overall Audit'),
            ('sentiment', 'Comment Sentiment Audit'),
            ('engagement', 'Engagement Quality Audit'),
            ('ai_score', 'AI Score Evaluation'),
        ],
        help_text="Type of audit report to generate."
    )
    custom_prompt = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional custom prompt to guide the AI audit (e.g., 'Focus on content strategy')."
    )

class ChannelAuditReportSerializer(serializers.ModelSerializer):
    """
    Serializer for outputting ChannelAuditReport instances.
    """
    pdf_report = serializers.SerializerMethodField()

    class Meta:
        model = ChannelAuditReport
        fields = ["id", "channel_id", "report_type", "channel_type", "audit_scope", "generated_at", "report_data", "pdf_report"]
        # read_only_fields = ('generated_at', 'report_data', 'pdf_report')

    def get_pdf_report(self, obj):
        request = self.context.get('request')

        return request.build_absolute_uri(obj.pdf_report.url)   
        
class AuditListSerializer(serializers.ModelSerializer):
    pdf_report = serializers.SerializerMethodField()
    class Meta:
        model = ChannelAuditReport
        fields = ['id', 'generated_at', 'report_type', 'channel_type', 'pdf_report']
        
    def get_pdf_report(self, obj):
        request = self.context.get('request')

        return request.build_absolute_uri(obj.pdf_report.url)

        

