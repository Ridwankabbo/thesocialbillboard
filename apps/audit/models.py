from django.db import models
from datetime import datetime
from apps.users.models import User
class ChannelAuditReport(models.Model):
    """
    Model to store generated audit reports.
    """
    user=models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_audit_reports', null=True, blank=True)
    channel_id = models.CharField(max_length=255, help_text="YouTube Channel ID")
    report_type = models.CharField(max_length=50, choices=[
        ('overall', 'Overall Audit'),
        ('sentiment', 'Comment Sentiment Audit'),
        ('engagement', 'Engagement Quality Audit'),
        ('ai_score', 'AI Score Evaluation'),
        ('niche_alignment', 'Niche Alignment Audit'),
    ])
    
    CHANNEL_TYPE_CHOICES = [
        ('business', 'Business / Educational'),
        ('entertainment', 'Entertainment / Lifestyle'),
    ]   
    
    AUDIT_SCOPE_CHOICES = [
        ('last_10', 'Last 10 Videos'),
        ('last_30', 'Last 30 Videos'),
        ('last_90_days', 'Last 90 Days'),
    ]
    
    channel_type = models.CharField(
        max_length=50, 
        choices=CHANNEL_TYPE_CHOICES,
        default='business',
        help_text="The selected or inferred channel type that adapts the audit logic."
    )
    
    audit_scope = models.CharField(
        max_length=50,
        choices=AUDIT_SCOPE_CHOICES,
        default='last_10',
        help_text="Scope of the audit (e.g., last 10 videos, last 30 videos, or last 90 days)."
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    report_data = models.JSONField(
        default=dict,
        help_text="JSON data containing the audit results, summaries, and insights."
    )
    pdf_report = models.FileField(
        upload_to='audit_reports/',
        null=True, blank=True,
        help_text="Generated PDF report file."
    )
    custom_prompt_used = models.TextField(
        null=True, blank=True,
        help_text="Optional custom prompt used for AI generation."
    )

    def __str__(self):
        return f"{self.report_type} report for {self.channel_id} on {self.generated_at.strftime('%Y-%m-%d %H:%M')}"

    class Meta:
        ordering = ['-generated_at']
        verbose_name = "Channel Audit Report"
        verbose_name_plural = "Channel Audit Reports"

