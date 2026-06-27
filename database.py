"""
Database layer — PostgreSQL via pg8000 (Supabase).
Usa DATABASE_URL do ambiente. Compatível com PyMySQL DictCursor (rows como dict).
"""
import os
from urllib.parse import urlparse

import pg8000.dbapi
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

_DATABASE_URL = os.getenv('DATABASE_URL', '')


def _connect():
    p = urlparse(_DATABASE_URL)
    return pg8000.dbapi.connect(
        host=p.hostname,
        user=p.username,
        password=p.password,
        database=(p.path or '/postgres').lstrip('/'),
        port=p.port or 5432,
        ssl_context=True,
    )


class _DictCursor:
    """Cursor que retorna rows como dict — mesma interface do PyMySQL DictCursor."""

    def __init__(self, cur):
        self._c = cur

    def execute(self, sql, params=None):
        self._c.execute(sql, params or ())

    def fetchone(self):
        row = self._c.fetchone()
        if row is None:
            return None
        return dict(zip([d[0] for d in self._c.description], row))

    def fetchall(self):
        rows = self._c.fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self._c.description]
        return [dict(zip(cols, r)) for r in rows]

    def executemany(self, sql, seq):
        self._c.executemany(sql, seq)

    @property
    def rowcount(self):
        return self._c.rowcount

    @property
    def description(self):
        return self._c.description

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


class _DictConn:
    def __init__(self):
        self._cn = _connect()

    def cursor(self):
        return _DictCursor(self._cn.cursor())

    def commit(self):
        self._cn.commit()

    def close(self):
        self._cn.close()


def get_db():
    return _DictConn()


def init_db():
    """Insere dados iniciais (admin + dentistas de exemplo) se o banco estiver vazio."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS n FROM usuarios")
            if cur.fetchone()['n'] == 0:
                cur.execute(
                    "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s,%s,%s,%s)",
                    ("Administrador", "admin@clinica.com",
                     generate_password_hash("admin123"), "admin")
                )
            cur.execute("SELECT COUNT(*) AS n FROM dentistas")
            if cur.fetchone()['n'] == 0:
                for row in [
                    ("Dr. Carlos Souza",     "CRO-12345", "Clínico Geral",  "(11) 99999-0001", "carlos@clinica.com"),
                    ("Dra. Ana Lima",        "CRO-23456", "Ortodontia",     "(11) 99999-0002", "ana@clinica.com"),
                    ("Dr. Pedro Martins",    "CRO-34567", "Implantodontia", "(11) 99999-0003", "pedro@clinica.com"),
                    ("Dra. Maria Fernandes", "CRO-45678", "Endodontia",     "(11) 99999-0004", "maria@clinica.com"),
                ]:
                    cur.execute(
                        "INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
                        row
                    )
        conn.commit()
    finally:
        conn.close()
