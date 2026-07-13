import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def send_email(to, subject, body):
    """Sends email via SMTP using configuration credentials."""
    sender_email = config.EMAIL_ADDRESS
    sender_password = config.EMAIL_PASSWORD
    
    placeholder_creds = (
        not sender_email or not sender_password or
        "your_app_password" in sender_password or
        "your.email" in sender_email or
        "@gmail.com" not in sender_email.lower()  # only Gmail SMTP configured
    )
    if placeholder_creds:
        return ("Error: Email credentials not configured. Please set "
                "EMAIL_ADDRESS (Gmail) and EMAIL_PASSWORD (App Password) in .env file.")

    try:
        # Create message container
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to
        msg['Subject'] = subject
        
        # Attach email body
        msg.attach(MIMEText(body, 'plain'))
        
        # Configure SMTP server connection
        # Default is Gmail, but can work with other SMTP services
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Connect to SMTP server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Upgrade connection to secure TLS
        server.login(sender_email, sender_password)
        
        # Send mail
        server.sendmail(sender_email, to, msg.as_string())
        server.quit()
        
        return f"Email sent successfully to '{to}' (Subject: '{subject}')."
    except Exception as e:
        return f"Error sending email to '{to}': {str(e)}"
