import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

def send_otp_email(to_email: str, otp: str) -> bool:
    """
    Sends a beautifully styled HTML verification OTP email using SMTP.
    If SMTP credentials are not set in the .env file, it falls back to console logging.
    """
    subject = "SmartStudy Verification OTP Code"
    
    # Premium, responsive HTML template matching the app's theme
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SmartStudy Verification Code</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f7f9fa; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; -webkit-font-smoothing: antialiased;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f7f9fa; padding: 40px 20px;">
    <tr>
      <td align="center">
        <!-- Main Container Card -->
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 500px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #eef2f4;">
          <!-- Elegant Teal Header -->
          <tr>
            <td align="center" style="background: linear-gradient(135deg, #0D7A5F 0%, #1D9E75 100%); padding: 32px 20px;">
              <table border="0" cellpadding="0" cellspacing="0">
                <tr>
                  <td align="center" style="color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: 0.5px; padding-bottom: 4px;">
                    SmartStudy
                  </td>
                </tr>
                <tr>
                  <td align="center" style="color: rgba(255,255,255,0.85); font-size: 12px; font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">
                    Secure User Onboarding
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <!-- Body Content -->
          <tr>
            <td style="padding: 40px 32px; text-align: left;">
              <h2 style="margin: 0 0 16px 0; color: #1e293b; font-size: 18px; font-weight: 700; line-height: 1.4;">
                Account Verification Code
              </h2>
              <p style="margin: 0 0 24px 0; color: #64748b; font-size: 14px; line-height: 1.6;">
                Welcome to SmartStudy! An account has been provisioned for you. Use the secure one-time verification code below to verify your email and set up your login password:
              </p>
              
              <!-- Styled OTP Box -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4fbf7; border: 1.5px dashed #1d9e75; border-radius: 12px; margin-bottom: 24px;">
                <tr>
                  <td align="center" style="padding: 20px 10px; font-family: monospace, Courier, monospace; font-size: 32px; font-weight: 800; letter-spacing: 6px; color: #0D7A5F;">
                    {otp}
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 8px 0; color: #64748b; font-size: 13px; line-height: 1.5;">
                ⏰ This code is valid for <strong>5 minutes</strong>.
              </p>
              <p style="margin: 0; color: #94a3b8; font-size: 12px; line-height: 1.5;">
                If you did not request this verification code, you can safely ignore this email.
              </p>
            </td>
          </tr>
          <!-- Footer Info -->
          <tr>
            <td style="background-color: #f8fafc; padding: 24px 32px; text-align: center; border-top: 1px solid #f1f5f9;">
              <p style="margin: 0; color: #94a3b8; font-size: 11px; line-height: 1.4;">
                This is an automated system email. Please do not reply directly to this address.
              </p>
              <p style="margin: 4px 0 0 0; color: #64748b; font-size: 11px; font-weight: 600;">
                SmartStudy Instructeer &copy; 2026
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    # Check if SMTP credentials are set
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print("\n" + "═" * 50)
        print(f"📧 [DEV ONLY - SMTP NOT CONFIGURED] OTP Code for {to_email}: {otp}")
        print("═" * 50 + "\n")
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM or settings.SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach HTML content
        msg.attach(MIMEText(html_content, 'html'))
        
        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        
        server.sendmail(msg['From'], to_email, msg.as_string())
        server.quit()
        print(f"✅ Beautiful HTML OTP email successfully sent to {to_email} via SMTP.")
        return True
    except Exception as e:
        print(f"❌ Failed to send HTML SMTP email to {to_email}: {str(e)}")
        print("\n" + "═" * 50)
        print(f"📧 [FALLBACK] OTP Code for {to_email}: {otp}")
        print("═" * 50 + "\n")
        return False
