from xhtml2pdf import pisa
from django.template.loader import render_to_string
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFGenerator:
    """
    Service class to generate PDF reports using xhtml2pdf.
    """
    def generate_html_for_pdf(self, channel_data, ai_insights, report_type, custom_prompt):
        report_title_map = {
            'overall': 'Overall Channel Audit Report',
            'sentiment': 'Comment Sentiment Audit Report',
            'engagement': 'Engagement Quality Audit Report',
            'ai_score': 'AI Score Evaluation Report',
        }
        title = report_title_map.get(report_type, 'YouTube Channel Audit Report')

        rating_analysis = channel_data.get("RatingAnalysis", {})
        rating_table = ""
        if rating_analysis:
            rows = ""
            for key, val in rating_analysis.items():
                if isinstance(val, dict):
                    score = val.get("score", "N/A")
                    rated = val.get("parents_rated", "N/A")
                    rows += f"<tr><td>{key.replace('_',' ').title()}</td><td>{score}</td><td>{rated}</td></tr>"
                else:
                    rows += f"<tr><td>{key.replace('_',' ').title()}</td><td colspan='2'>{val}</td></tr>"
            rating_table = f"""
            <div class="section">
                <h2>Rating Analysis</h2>
                <table>
                    <tr><th>Category</th><th>Score</th><th>Parents Rated</th></tr>
                    {rows}
                </table>
            </div>
            """

        age_analysis = channel_data.get("AgeRangeAnalysis", {})
        age_section = ""
        if age_analysis:
            age_section = f"""
            <div class="section">
                <h2>Age Range Analysis</h2>
                <p><strong>Recommended Age:</strong> {age_analysis.get("recommended_age_range", "N/A")}</p>
                <p><strong>Reason:</strong> {age_analysis.get("reason", "N/A")}</p>
            </div>
            """

        tags = channel_data.get("tags", [])
        tags_section = ""
        if tags:
            tags_list = ", ".join(tags)
            tags_section = f"""
            <div class="section">
                <h2>Tags</h2>
                <p>{tags_list}</p>
            </div>
            """

        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Helvetica, sans-serif; margin: 30px; font-size: 12px; color: #333; }}
                h1 {{ text-align: center; font-size: 18px; color: #c00; }}
                h2 {{ font-size: 14px; margin-top: 20px; border-bottom: 1px solid #ccc; }}
                .section {{ margin-bottom: 15px; }}
                .metric {{ width: 48%; display: inline-block; margin-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 11px; }}
                th, td {{ border: 1px solid #ddd; padding: 5px; }}
                th {{ background-color: #f2f2f2; }}
                .footer {{ text-align: center; font-size: 10px; color: #888; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <h1>{title}</h1>

            <div class="section">
                <h2>Channel Overview</h2>
                <p class="metric"><strong>Channel Name:</strong> {channel_data.get('title', 'N/A')}</p>
                <p class="metric"><strong>Channel ID:</strong> {channel_data.get('channelId', 'N/A')}</p>
                <p class="metric"><strong>Subscribers:</strong> {channel_data.get('subscriberCount', 'N/A')}</p>
                <p class="metric"><strong>Total Views:</strong> {channel_data.get('viewCount', 'N/A')}</p>
                <p class="metric"><strong>Total Videos:</strong> {channel_data.get('videoCount', 'N/A')}</p>
                <p class="metric"><strong>Avg Views/Video:</strong> {channel_data.get('avgViewsPerVideo', 'N/A')}</p>
                <p class="metric"><strong>Engagement Rate:</strong> {channel_data.get('engagementRate', 'N/A')}%</p>
                <p class="metric"><strong>AI Score:</strong> {channel_data.get('ai_score', 'N/A')}</p>
                <p class="metric"><strong>Badge:</strong> {channel_data.get('badge', 'N/A')}</p>
                <p><strong>Description:</strong> {channel_data.get('description', 'N/A')}</p>
                <p><strong>Badge Reason:</strong> {channel_data.get('badge_reason', 'N/A')}</p>
            </div>

            {rating_table}
            {age_section}
            {tags_section}

            <div class="section">
                <h2>AI Insights ({report_type.replace('_', ' ').title()} Audit)</h2>
                <p>{ai_insights.get('report_summary', 'No AI insights generated.')}</p>
                {f'<p><strong>Custom Prompt Used:</strong> {custom_prompt}</p>' if custom_prompt else ''}
            </div>

            <div class="footer">
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        return html_content

    def generate_pdf_from_html(self, html_content):
        try:
            result = io.BytesIO()
            pisa_status = pisa.CreatePDF(
                html_content, dest=result, encoding='utf-8'
            )
            if pisa_status.err:
                raise Exception("PDF generation failed.")
            return result
        except Exception as e:
            logger.error(f"Error generating PDF: {e}")
            raise
