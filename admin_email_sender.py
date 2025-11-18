from flask_mail import Mail, Message
from flask import current_app
import time

mail = Mail()

# Rate limiting: Hostinger allows ~15 emails per minute
# Set delay to 15 seconds between emails to stay WELL under the limit
# This means max 4 emails per minute (15 limit / 4 = safe margin)
HOSTINGER_MIN_EMAIL_DELAY = 15  # seconds
last_email_time = 0


def rate_limit_email():
    """Apply rate limiting to prevent hitting Hostinger's email limit."""
    global last_email_time
    current_time = time.time()
    time_since_last = current_time - last_email_time
    
    if time_since_last < HOSTINGER_MIN_EMAIL_DELAY:
        sleep_time = HOSTINGER_MIN_EMAIL_DELAY - time_since_last
        print(f"[RATE LIMIT] Sleeping for {sleep_time:.2f}s to comply with Hostinger limits")
        time.sleep(sleep_time)
    
    last_email_time = time.time()


def send_accept_email(recipient_email, recipient_name, details=None, interview_link=None, internship_type='free'):
    """Send a selection/acceptance email to the applicant.

    If `details` is provided (a dict), the email will include key applicant fields
    in both the plain-text and HTML body so the applicant has a record of their
    submitted information.
    
    If `interview_link` is provided, it will be included as a link to schedule the interview.
    
    `internship_type` can be 'free' or 'paid' to customize the email message.
    """
    try:
        # Apply rate limiting
        rate_limit_email()
        
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


def send_offer_letter_email(recipient_email, recipient_name, offer_letter_pdf_bytes, offer_letter_reference):
    """Send offer letter as email attachment to candidate.
    
    This function is called when an offer letter is generated for an approved candidate.
    The PDF is stored in binary format in the database and is sent as an attachment.
    
    Args:
        recipient_email: Email address of the candidate
        recipient_name: Name of the candidate
        offer_letter_pdf_bytes: Binary PDF data of the offer letter
        offer_letter_reference: Reference number of the offer letter (for filename)
    """
    try:
        # Validate inputs
        if not recipient_email:
            print(f"[ERROR] No email provided for offer letter")
            return False
        
        if not offer_letter_pdf_bytes:
            print(f"[ERROR] No PDF data for offer letter")
            return False
        
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        
        subject = "Swizosoft — Your Internship Offer Letter"
        
        body = f"""Hi {recipient_name},

Congratulations!

We are delighted to extend an offer for an internship position at Swizosoft. Please find your detailed offer letter attached to this email.

Please review the offer letter carefully and get back to us with your acceptance/confirmation at your earliest convenience.

If you have any questions regarding the offer or need any clarifications, please feel free to reach out to us.

We look forward to your positive response.

Best regards,
Swizosoft Pvt. Ltd."""

        html = f"""<p>Hi {recipient_name},</p>

<p><strong>Congratulations!</strong></p>

<p>We are delighted to extend an offer for an internship position at <strong>Swizosoft</strong>. Please find your detailed offer letter attached to this email.</p>

<p>Please review the offer letter carefully and get back to us with your acceptance/confirmation at your earliest convenience.</p>

<p>If you have any questions regarding the offer or need any clarifications, please feel free to reach out to us.</p>

<p>We look forward to your positive response.</p>

<p>Best regards,<br/><strong>Swizosoft Pvt. Ltd.</strong></p>"""

        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        
        # Attach the PDF - ensure it's bytes
        filename = f"SZS_OFFR_{offer_letter_reference.replace('/', '_')}.pdf"
        if isinstance(offer_letter_pdf_bytes, bytes):
            msg.attach(filename, "application/pdf", offer_letter_pdf_bytes)
        else:
            print(f"[ERROR] PDF data is not bytes type: {type(offer_letter_pdf_bytes)}")
            return False
        
        mail.send(msg)
        current_app.logger.info(f"✓ Offer letter email sent to {recipient_email} with reference {offer_letter_reference}")
        print(f"✓ Offer letter email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.exception(f'Failed to send offer letter email to {recipient_email}: {str(e)}')
        print(f"[ERROR] Failed to send offer letter email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def send_certificate_email(recipient_email, recipient_name, certificate_pdf_bytes, certificate_id):
    """Send issued certificate as email attachment to candidate.
    
    This function is called when a certificate is issued for a completed internship.
    The PDF is stored in binary format in the database and is sent as an attachment.
    
    Args:
        recipient_email: Email address of the candidate
        recipient_name: Name of the candidate
        certificate_pdf_bytes: Binary PDF data of the certificate
        certificate_id: ID of the certificate (for filename)
    """
    try:
        # Validate inputs
        if not recipient_email:
            print(f"[ERROR] No email provided for certificate")
            current_app.logger.error(f"Certificate email - no email provided")
            return False
        
        if not certificate_pdf_bytes:
            print(f"[ERROR] No PDF data for certificate")
            current_app.logger.error(f"Certificate email - no PDF data provided")
            return False
        
        if not isinstance(certificate_pdf_bytes, bytes):
            print(f"[ERROR] PDF data is not bytes type: {type(certificate_pdf_bytes)}")
            current_app.logger.error(f"Certificate email - PDF data is not bytes: {type(certificate_pdf_bytes)}")
            return False
        
        sender = current_app.config.get('MAIL_DEFAULT_SENDER')
        print(f"[DEBUG] Mail sender: {sender}, Mail server: {current_app.config.get('MAIL_SERVER')}")
        
        subject = "Swizosoft — Your Internship Completion Certificate"
        
        body = f"""Hi {recipient_name},

Congratulations on completing your internship at Swizosoft!

You have successfully completed all the requirements of the internship program. Please find your internship completion certificate attached to this email.

This certificate recognizes your dedication and contributions during your time with us. We appreciate your hard work and wish you all the best for your future endeavors.

Feel free to share this certificate with your college/university and include it in your academic records.

If you have any questions, please feel free to reach out to us.

Best regards,
Swizosoft Pvt. Ltd."""

        html = f"""<p>Hi {recipient_name},</p>

<p><strong>Congratulations on completing your internship at Swizosoft!</strong></p>

<p>You have successfully completed all the requirements of the internship program. Please find your internship completion certificate attached to this email.</p>

<p>This certificate recognizes your dedication and contributions during your time with us. We appreciate your hard work and wish you all the best for your future endeavors.</p>

<p>Feel free to share this certificate with your college/university and include it in your academic records.</p>

<p>If you have any questions, please feel free to reach out to us.</p>

<p>Best regards,<br/><strong>Swizosoft Pvt. Ltd.</strong></p>"""

        print(f"[DEBUG] Creating message for {recipient_email}")
        msg = Message(subject=subject, sender=sender, recipients=[recipient_email])
        msg.body = body
        msg.html = html
        
        # Attach the PDF
        filename = f"{certificate_id}.pdf"
        print(f"[DEBUG] Attaching PDF: {filename}, size: {len(certificate_pdf_bytes)} bytes")
        msg.attach(filename, "application/pdf", certificate_pdf_bytes)
        
        print(f"[DEBUG] Sending mail message...")
        mail.send(msg)
        
        current_app.logger.info(f"✓ Certificate email sent to {recipient_email} with certificate ID {certificate_id}")
        print(f"✓ Certificate email sent successfully to {recipient_email}")
        return True
    except Exception as e:
        current_app.logger.exception(f'Failed to send certificate email to {recipient_email}: {str(e)}')
        print(f"[ERROR] Failed to send certificate email: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

