import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext


def get_db(name='db'):
    """
    :param name: (db|data|result)
    :returns: an open database (connection)
    """
    if name.lower() =='db':
        if name not in g:
            g.db = sqlite3.connect(
                current_app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
        return g.db
    name = name.upper()
    if name not in g:
        db = sqlite3.connect(
            current_app.config[f'DATABASE_{name}'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    get_db()
    # get_db('DATA')
    # get_db('RESULT')


@click.command('init-db')
@with_appcontext
def init_db_command():
    init_db()
    click.echo('Initialized the database.')



def insert(df, table, con=None, overwrite=False, unique_worker=False, unique_fields=None):
    """
    Insert rows in df to into the given table
    :param df: (DataFrame)
    :param table: (str) table name
    :param con: (sqlite|sqlachemy- Connection)
    :param overwrite: (bool)
    :param unique_worker: (bool) if True, an unique index is add to the table
    :param unique_fiedls: (str|list[str]) create unique index for the grouped fields
    """
    
    con = con or g.db
    table_already_created = table_exists(con, table)
    #sql_unique_worker = f"CREATE UNIQUE INDEX IF NOT EXISTS unique_worker_index_{table} ON {table}(worker_id)"
    if unique_fields is not None:
        if isinstance(unique_fields, str):
            unique_fields = (unique_fields,)
        else:
            unique_fields = tuple(unique_fields)
        sql_unique_fields = f"CREATE UNIQUE INDEX IF NOT EXISTS unique_worker_index_{table} ON {table}({','.join(unique_fields)})"
    if overwrite:
        df.to_sql(table, con=con, if_exists='replace', index=False)
        if unique_fields:
            with con:
                con.execute(sql_unique_fields)
    else:
        df.to_sql(table, con=con, if_exists='append', index=False)
        if not table_already_created:
            if unique_fields:
                with con:
                    con.execute(sql_unique_fields)



def table_exists(con, table):
    """
    :param con: sqlite3/sqlalchemy connection
    :param table: (str) table name
    :returns: True if the table exists and False otherwise
    """
    return bool(con.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone())

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)