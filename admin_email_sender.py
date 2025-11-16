from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def send_accept_email(recipient_email, recipient_name, details=None, interview_link=None):
    """Send a selection/acceptance email to the applicant.

    If `details` is provided (a dict), the email will include key applicant fields
    in both the plain-text and HTML body so the applicant has a record of their
    submitted information.
    
    If `interview_link` is provided, it will be included as a link to schedule the interview.
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

        # Build plain-text message
        body_lines = [f"Hi {recipient_name},", "",
                      "Congratulations! You have been selected for the internship at Swizosoft.", ""]

        if details_lines:
            body_lines.append("Here are the details we have on file for you:")
            body_lines.extend(details_lines)
            body_lines.append("")

        # Schedule link placed after details/message (so it appears below the details)
        if interview_link:
            body_lines.append(f"Please schedule your interview using the following link:")
            body_lines.append(interview_link)
            body_lines.append("")

        body_lines.append("We will contact you with any further instructions.\n")
        body_lines.append("Best regards,\nSwizosoft Team")
        body = "\n".join(body_lines)

        # Build HTML message
        html_parts = [f"<p>Hi {recipient_name},</p>",
                      "<p>Congratulations! You have been <strong>selected</strong> for the internship at <strong>Swizosoft</strong>.</p>"]

        if details_html:
            html_parts.append(details_html)

        # Place schedule button/link below the details
        if interview_link:
            html_parts.append(
                f"<p><a href=\"{interview_link}\" style=\"background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; display: inline-block;\">Schedule Your Interview</a></p>"
            )

        html_parts.append("<p>We will contact you with any further instructions.</p>")
        html_parts.append("<p>Best regards,<br/>Swizosoft Team</p>")
        html = "".join(html_parts)

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
