from datetime import datetime
from core import db


class UserFileStore(db.Model):
    """"Stores links for sensitive user files"""
    __tablename__ = 'userfilestore'

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.String(length=60))
    file_key = db.Column(db.String(length=1024))
    file_category = db.Column(db.String(length=60))
    file_content_type = db.Column(db.String(length=70))
    original_file_name = db.Column(db.String(length=1024))
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=datetime.now
    )
    updated_at = db.Column(
        db.DateTime(timezone=True), nullable=False,
        default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self):
        return f"{self.id}"
