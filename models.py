from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy without binding to app yet
db = SQLAlchemy()

class WatchedShow(db.Model):
    __tablename__ = 'watched_shows'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(255))
    category = db.Column(db.String(255))
    added_on = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<WatchedShow {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'genre': self.genre,
            'category': self.category,
            'added_on': self.added_on.strftime('%Y-%m-%d %H:%M:%S') if self.added_on else None
        }