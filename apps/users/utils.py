from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_signup_otp_email(user):
    subject = "Signup OTP"

    html_content = render_to_string(
        "otp.html",
        {
            "name": user.name,
            "otp": user.otp,
        }
    )

    email = EmailMultiAlternatives(
        subject=subject,
        body=f"Your OTP is {user.otp}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
    )

    email.attach_alternative(html_content, "text/html")
    email.send()