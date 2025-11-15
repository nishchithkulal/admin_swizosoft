from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def send_accept_email(recipient_email, recipient_name):
    """Send a selection/acceptance email to the applicant."""
    try:
        subject = "Swizosoft Internship — Congratulations! You're Selected"
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        body = f"Hi {recipient_name},\n\nCongratulations! We are pleased to inform you that you have been selected for the internship at Swizosoft.\n\nWe will contact you with next steps shortly.\n\nBest regards,\nSwizosoft Team"
        html = f"<p>Hi {recipient_name},</p><p>Congratulations! We are pleased to inform you that you have been <strong>selected</strong> for the internship at <strong>Swizosoft</strong>.</p><p>We will contact you with next steps shortly.</p><p>Best regards,<br/>Swizosoft Team</p>"

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send accept email')
        return False


def send_reject_email(recipient_email, recipient_name):
    """Send a rejection email to the applicant."""
    try:
        subject = "Swizosoft Internship — Application Update"
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        body = f"Hi {recipient_name},\n\nThank you for applying to the Swizosoft internship. We appreciate your interest, but we are unable to offer you a position at this time.\n\nWe encourage you to apply again in the future.\n\nBest wishes,\nSwizosoft Team"
        html = f"<p>Hi {recipient_name},</p><p>Thank you for applying to the <strong>Swizosoft</strong> internship. We appreciate your interest, but we are unable to offer you a position at this time.</p><p>We encourage you to apply again in the future.</p><p>Best wishes,<br/>Swizosoft Team</p>"

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send reject email')
        return False
