from app import db, config
from datetime import datetime


class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128), nullable=False, default='')
    domain = db.Column(db.String(128), nullable=False, default='')
    content_length = db.Column(db.Integer, nullable=False, default='')
    expires = db.Column(db.DateTime, nullable=True, default=None)
    created = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return '<Image %s>' % self.id

    def get_path(self):
        return '/bucket/%s%s%s' % (
            self.domain,
            self.created.strftime('/%Y/%m/%d/'),
            self.filename
        )

    def get_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'created': self.created,
            'content_length': self.content_length,
            'expires': self.expires,
            'uri': '%si/%s/%s/%s' % (
                config.settings.get('uri'),
                self.domain,
                self.id,
                self.filename
            )
        }