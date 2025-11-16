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
    
    def __repr__(self):
        return f'<ApprovedCandidate {self.usn} - {self.name}>'
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'usn': self.usn,
            'application_id': self.application_id,
            'name': self.name,
            'email': self.email,
            'phone_number': self.phone_number,
            'year': self.year,
            'qualification': self.qualification,
            'branch': self.branch,
            'college': self.college,
            'domain': self.domain,
            'mode_of_interview': self.mode_of_interview,
            'resume_name': self.resume_name,
            'resume_content': self.resume_content,
            'project_document_name': self.project_document_name,
            'project_document_content': self.project_document_content,
            'id_proof_name': self.id_proof_name,
            'id_proof_content': self.id_proof_content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
