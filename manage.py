import os
from flask.cli import FlaskGroup
from core import create_app, db


app = create_app(os.environ.get('FLASK_CONFIG'))
cli = FlaskGroup(app)


@cli.command("create_db")
def create_db():
    """Creates database tables"""
    db.create_all()
    db.session.commit()


@cli.command("reset_db")
def reset_db():
    """Drops all existing database tables and recreates them"""
    if os.environ.get('FLASK_CONFIG') == "production":
        raise RuntimeError("reset_db is not allowed in production")
    db.drop_all()
    db.create_all()
    db.session.commit()


if __name__ == "__main__":
    cli()
