"""
Database models for Swizosoft internship application system
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class ApprovedCandidate(db.Model):
    """Model for approved candidates"""
    __tablename__ = 'approved_candidates'
    
    # Primary key
    usn = db.Column(db.String(50), primary_key=True, nullable=False)
    
    # Basic information
    application_id = db.Column(db.String(20), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, unique=True, nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    
    # Academic information
    year = db.Column(db.String(20),nullable=False)
    qualification = db.Column(db.String(50),nullable=False)
    branch = db.Column(db.String(100),nullable=False)
    college = db.Column(db.String(200),nullable=False)
    
    # Professional information
    domain = db.Column(db.String(100),nullable=False)
    mode_of_interview = db.Column(db.String(20), default='online')
    mode_of_internship = db.Column(db.String(50), nullable=True)  # free, paid, remote-based opportunity, hybrid-based opportunity, on-site based opportunity
    
    # Resume
    resume_name = db.Column(db.String(255), nullable=True)
    # Use MEDIUMBLOB for larger files
    resume_content = db.Column(db.LargeBinary(length=16777215), nullable=True)  # MEDIUMBLOB max size
    
    # Project document
    project_document_name = db.Column(db.String(255), nullable=True)
    project_document_content = db.Column(db.LargeBinary(length=16777215), nullable=True)
    
    # ID proof
    id_proof_name = db.Column(db.String(255), nullable=True)
    id_proof_content = db.Column(db.LargeBinary(length=16777215), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Cached job description snapshot for the candidate's domain (optional)
    job_description = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<ApprovedCandidate {self.usn} - {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'usn': self.usn,
            'application_id': self.application_id,
            'user_id': self.user_id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'year': self.year,
            'qualification': self.qualification,
            'branch': self.branch,
            'college': self.college,
            'domain': self.domain,
            'mode_of_interview': self.mode_of_interview,
            'mode_of_internship': self.mode_of_internship,
            'resume_name': self.resume_name,
            'resume_content': self.resume_content,
            'project_document_name': self.project_document_name,
            'project_document_content': self.project_document_content,
            'id_proof_name': self.id_proof_name,
            'id_proof_content': self.id_proof_content,
            'job_description': self.job_description,
        }


class Selected(db.Model):
    """Model for selected/ongoing internship candidates"""
    __tablename__ = 'Selected'
    
    # Primary key
    usn = db.Column(db.String(20), primary_key=True, nullable=False)
    
    # Unique identifier
    id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    candidate_id = db.Column(db.String(10), unique=True, nullable=False)
    
    # Basic information
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    
    # Academic information
    year = db.Column(db.String(50), nullable=False)
    qualification = db.Column(db.String(50), nullable=False)
    branch = db.Column(db.String(100), nullable=False)
    college = db.Column(db.String(200), nullable=False)
    
    # Professional information
    domain = db.Column(db.String(100), nullable=False)
    roles = db.Column(db.String(30), nullable=False)
    mode_of_internship = db.Column(db.String(255), nullable=True)
    
    # Project information
    project_description = db.Column(db.String(255), nullable=True)
    internship_project_name = db.Column(db.String(255), nullable=True)
    internship_project_content = db.Column(db.LargeBinary(length=16777215), nullable=True)  # MEDIUMBLOB
    project_title = db.Column(db.String(50), nullable=True)
    
    # Dates and status
    approved_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    completion_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='ongoing')  # ongoing or completed
    internship_duration = db.Column(db.String(20), nullable=False)  # 1 month, 2 months, 3 months, 4 months
    resend_count = db.Column(db.Integer, nullable=True, default=0)
    created_at = db.Column(db.DateTime, nullable=True, default=datetime.utcnow)
    
    # Offer letter information
    offer_letter_pdf = db.Column(db.LargeBinary(length=4294967295), nullable=True)  # LONGBLOB
    offer_letter_reference = db.Column(db.String(50), nullable=True)
    offer_letter_generated_date = db.Column(db.DateTime, nullable=True)
    
    # Certificate information
    certificate_pdf = db.Column(db.LargeBinary(length=4294967295), nullable=True)  # LONGBLOB
    certificate_id = db.Column(db.String(50), nullable=True)
    certificate_generated_date = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Selected {self.usn} - {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'usn': self.usn,
            'candidate_id': self.candidate_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'year': self.year,
            'qualification': self.qualification,
            'branch': self.branch,
            'college': self.college,
            'domain': self.domain,
            'roles': self.roles,
            'mode_of_internship': self.mode_of_internship,
            'project_description': self.project_description,
            'internship_project_name': self.internship_project_name,
            'project_title': self.project_title,
            'approved_date': self.approved_date.isoformat() if self.approved_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'status': self.status,
            'internship_duration': self.internship_duration,
            'resend_count': self.resend_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'offer_letter_reference': self.offer_letter_reference,
            'offer_letter_generated_date': self.offer_letter_generated_date.isoformat() if self.offer_letter_generated_date else None,
            'certificate_id': self.certificate_id,
            'certificate_generated_date': self.certificate_generated_date.isoformat() if self.certificate_generated_date else None,
        }

