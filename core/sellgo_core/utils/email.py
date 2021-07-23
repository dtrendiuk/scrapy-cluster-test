import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SellgoEmailClient(object):
    """
        Sellgo email client.
    """

    def __init__(self, smtp, port, username, password):
        self.smtp = smtp
        self.username = username
        self.password = password
        self.port = port

    def send_email(self, from_address, to_addresses, content):
        with smtplib.SMTP_SSL(self.smtp, port=self.port, context=ssl.create_default_context()) as server:
            server.login(self.username, self.password)
            server.sendmail(from_address, to_addresses, content)

    def send_html_email(self, from_address, to_addresses, sender_name, subject, content):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f'"{sender_name}"'

        html_message = MIMEText(content, 'html')
        msg.attach(html_message)
        self.send_email(from_address, to_addresses, msg.as_string())
