import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    get_db()


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')



def insert(df, table, con=None, overwrite=False):
    con = con or g.db
    if overwrite:
        df.to_sql(table, con=con, if_exists='replace')
    else:
        df.to_sql(table, con=con, if_exists='append')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)