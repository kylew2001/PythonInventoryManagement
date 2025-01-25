from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(80))
    username = db.Column(db.String(80), unique=True)
    role = db.Column(db.String(20))
    # Add other fields as needed, e.g., password, email, etc.

    def __repr__(self):
        return f"<User {self.username}>"
