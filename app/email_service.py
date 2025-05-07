
import resend
from typing import Optional

resend.api_key = "re_5ngCXyig_8pZAwUmqXKPVxmr9HUFQhYD8"

def send_email(
    to: str,
    subject: str,
    html_content: str,
    from_email: str = "support@aifreevideo.com"
) -> Optional[str]:
    try:
        params: resend.Emails.SendParams = {
        "from": from_email,
        "to": to,
        "subject": subject,
        "html": html_content
        }

        email = resend.Emails.send(params)
        print(email)
        return email["id"]
    except Exception as e:
        print(f"Failed to send email: {str(e)}")
        return None

# 使用示例
if __name__ == "__main__":
    result = send_email(
        to="promaverickzzz@gmail.com",
        subject="Test Email",
        html_content="<h1>Hello!</h1><p>This is a test email.</p>"
    )
    
    if result:
        print(f"Email sent successfully, ID: {result}")
    else:
        print("Failed to send email")