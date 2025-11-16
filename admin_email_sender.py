from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def send_accept_email(recipient_email, recipient_name, details=None):
    """Send a selection/acceptance email to the applicant.

    If `details` is provided (a dict), the email will include key applicant fields
    in both the plain-text and HTML body so the applicant has a record of their
    submitted information.
    """
    try:
        subject = "Swizosoft Internship — Congratulations! You're Selected"
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')

        # Build a details section if provided
        details_lines = []
        details_html = ''
        if isinstance(details, dict) and details:
            for k, v in details.items():
                # avoid including large binary data in email
                if k.lower().endswith('_content'):
                    continue
                details_lines.append(f"{k}: {v}")
            # small HTML table for readability
            rows = ''.join(f"<tr><td><strong>{k}</strong></td><td>{v}</td></tr>" for k, v in details.items() if not k.lower().endswith('_content'))
            if rows:
                details_html = f"<h4>Application details</h4><table>{rows}</table>"

        body = f"Hi {recipient_name},\n\nCongratulations! We are pleased to inform you that you have been selected for the internship at Swizosoft.\n\nWe will contact you with next steps shortly.\n\n"
        if details_lines:
            body += "Here are the details we have on file for you:\n"
            body += "\n".join(details_lines)
            body += "\n\n"

        body += "Best regards,\nSwizosoft Team"

        html = f"<p>Hi {recipient_name},</p><p>Congratulations! We are pleased to inform you that you have been <strong>selected</strong> for the internship at <strong>Swizosoft</strong>.</p>"
        if details_html:
            html += details_html
        html += "<p>We will contact you with next steps shortly.</p><p>Best regards,<br/>Swizosoft Team</p>"

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send accept email')
        return False


def send_reject_email(recipient_email, recipient_name, reason=''):
    """Send a rejection email to the applicant."""
    try:
        subject = "Swizosoft Internship — Application Update"
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        
        body = f"Hi {recipient_name},\n\nThank you for applying to the Swizosoft internship. We appreciate your interest, but we are unable to offer you a position at this time.\n\n{f'Reason: {reason}' if reason else ''}\n\nWe encourage you to apply again in the future.\n\nBest wishes,\nSwizosoft Team"
        html = f"<p>Hi {recipient_name},</p><p>Thank you for applying to the <strong>Swizosoft</strong> internship. We appreciate your interest, but we are unable to offer you a position at this time.</p>{reason_text}<p>We encourage you to apply again in the future.</p><p>Best wishes,<br/>Swizosoft Team</p>"

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send reject email')
        return False
