from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from app.models.user import db, User

class PendingVideo(db.Model):
    __tablename__ = 'pending_video'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(255))
    privacy_status = db.Column(db.String(20), nullable=False, default='private')  # ✅ NEW
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    review_notes = db.Column(db.Text)

    # Relationships
    uploader = db.relationship('User', foreign_keys=[uploader_id], backref='uploaded_videos')
    creator = db.relationship('User', foreign_keys=[creator_id], backref='created_videos')

    def __repr__(self):
        return f'<PendingVideo {self.title}>'

    def to_dict(self):
        """Convert video object to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'filename': self.filename,
            'filepath': self.filepath,
            'privacy_status': self.privacy_status,  # ✅ NEW
            'status': self.status,
            'uploader_id': self.uploader_id,
            'creator_id': self.creator_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'review_notes': self.review_notes
        }
