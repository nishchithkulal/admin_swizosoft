from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def send_accept_email(recipient_email, recipient_name, details=None, interview_link=None, internship_type='free'):
    """Send a selection/acceptance email to the applicant.

    If `details` is provided (a dict), the email will include key applicant fields
    in both the plain-text and HTML body so the applicant has a record of their
    submitted information.
    
    If `interview_link` is provided, it will be included as a link to schedule the interview.
    
    `internship_type` can be 'free' or 'paid' to customize the email message.
    """
    try:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')

        if internship_type == 'paid':
            # Paid internship acceptance email
            subject = "Swizosoft Internship — Congratulations! You're Selected"
            
            body = f"""Hi {recipient_name},

We are pleased to inform you that you have been selected for the Paid Internship Program at Swizosoft. Your application and performance matched our requirements, and we look forward to having you contribute to our ongoing projects.

Our team will reach out shortly with onboarding instructions, required documents, and your reporting details.

If you have any immediate questions, feel free to contact us.

Regards,
Swizosoft Pvt. Ltd."""

            html = f"""<p>Hi {recipient_name},</p>

<p>We are pleased to inform you that you have been selected for the <strong>Paid Internship Program</strong> at <strong>Swizosoft</strong>. Your application and performance matched our requirements, and we look forward to having you contribute to our ongoing projects.</p>

<p>Our team will reach out shortly with onboarding instructions, required documents, and your reporting details.</p>

<p>If you have any immediate questions, feel free to contact us.</p>

<p>Regards,<br/>Swizosoft Pvt. Ltd.</p>"""

        else:
            # Free internship acceptance email (original behavior)
            subject = "Swizosoft Internship — Congratulations! You're Selected"

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

            # Build plain-text message with clear instruction for slot booking
            body_lines = [f"Hi {recipient_name},", "",
                          "Congratulations! You have been selected for the internship at Swizosoft.", "",
                          "Please book your interview slot using the link below at your earliest convenience. Slots are limited, so we recommend booking within 48 hours.", ""]

            if details_lines:
                body_lines.append("Here are the details we have on file for you:")
                body_lines.extend(details_lines)
                body_lines.append("")

            # Schedule link placed after details/message (so it appears below the details)
            if interview_link:
                body_lines.append(f"Book your interview slot here:")
                body_lines.append(interview_link)
                body_lines.append("")

            body_lines.append("If you have any questions, reply to this email and our team will assist you.")
            body_lines.append("")
            body_lines.append("Best regards,\nSwizosoft Team")
            body = "\n".join(body_lines)

            # Build HTML message with a prominent booking button
            html_parts = [f"<p>Hi {recipient_name},</p>",
                          "<p>Congratulations! You have been <strong>selected</strong> for the internship at <strong>Swizosoft</strong>.</p>",
                          "<p>Please <strong>book your interview slot</strong> using the link below at your earliest convenience. Slots are limited, so we recommend booking within 48 hours.</p>"]

            if details_html:
                html_parts.append(details_html)

            # Place schedule button/link below the details
            if interview_link:
                html_parts.append(
                    f"<p><a href=\"{interview_link}\" style=\"background-color: #007bff; color: white; padding: 12px 22px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight:600;\">Book Interview Slot</a></p>"
                )

            html_parts.append("<p>If you have any questions, reply to this email and our team will assist you.</p>")
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


def send_report_form_email(recipient_email, recipient_name):
    """Send report form submission email to candidate who has completed their internship.
    
    This email asks the candidate to fill out the completion form and upload project documents.
    """
    try:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        subject = "Swizosoft Internship — Complete Your Project Report"
        
        body = f"""Hi {recipient_name},

Congratulations! You have completed your internship at Swizosoft!

Please fill out the completion form and upload all relevant documents (project report, deliverables, etc.) using the link below:

📋 Complete Your Internship Form & Upload Documents:
http://127.0.0.1:5000/report-form

Please ensure all documents are uploaded and the form is completed before the deadline.

If you have any questions, feel free to reach out to us.

Best regards,
Swizosoft Internship Management System"""

        html = f"""<p>Hi {recipient_name},</p>

<p>Congratulations! You have completed your internship at <strong>Swizosoft</strong>!</p>

<p>Please fill out the completion form and upload all relevant documents (project report, deliverables, etc.) using the link below:</p>

<p><a href="http://127.0.0.1:5000/report-form" style="background-color: #28a745; color: white; padding: 12px 22px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight:600;">📋 Complete Your Internship Form & Upload Documents</a></p>

<p>Please ensure all documents are uploaded and the form is completed before the deadline.</p>

<p>If you have any questions, feel free to reach out to us.</p>

<p>Best regards,<br/>Swizosoft Internship Management System</p>"""

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.exception('Failed to send report form email')
        return False


def send_reject_email(recipient_email, recipient_name, reason='', internship_type='free'):
    """Send a rejection email to the applicant.
    
    `internship_type` can be 'free' or 'paid' to customize the email message.
    """
    try:
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        if internship_type == 'paid':
            # Paid internship rejection email
            subject = "Swizosoft Internship — Application Update"
            
            reason_text = f"Reason: {reason}" if reason else "Based on our current requirements and the overall competitiveness of the applicants."
            
            body = f"""Hi {recipient_name},

Thank you for your interest in the Paid Internship Program at Swizosoft. After reviewing your application and performance, we will not be moving forward with your selection.

This decision is based on our current requirements and the overall competitiveness of the applicants.

We appreciate the time and effort you invested in the process, and we encourage you to apply again in the future.

{reason_text}

Regards,
Swizosoft Pvt. Ltd."""

            html = f"""<p>Hi {recipient_name},</p>

<p>Thank you for your interest in the <strong>Paid Internship Program</strong> at <strong>Swizosoft</strong>. After reviewing your application and performance, we will not be moving forward with your selection.</p>

<p>This decision is based on our current requirements and the overall competitiveness of the applicants.</p>

<p>We appreciate the time and effort you invested in the process, and we encourage you to apply again in the future.</p>

<p><strong>{reason_text}</strong></p>

<p>Regards,<br/>Swizosoft Pvt. Ltd.</p>"""

        else:
            # Free internship rejection email (original behavior)
            subject = "Swizosoft Internship — Application Update"
            
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
