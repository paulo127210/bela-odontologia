"""
Database layer — PostgreSQL (Supabase) via pg8000.
Compativel com Python 3.14+. Le DATABASE_URL do .env.
"""
import os
import re
from urllib.parse import unquote
import pg8000.dbapi
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

_DATABASE_URL = os.getenv('DATABASE_URL', '')


def _parse_url(url):
    m = re.match(
        r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', url
    )
    if not m:
        raise ValueError(f"DATABASE_URL invalida: {url}")
    return dict(
        user=unquote(m.group(1)),
        password=unquote(m.group(2)),
        host=m.group(3),
        port=int(m.group(4) or 5432),
        database=m.group(5),
    )


class DictCursor:
    """Cursor que retorna dicts (equivalente ao DictCursor do PyMySQL)."""

    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, sql, params=None):
        self._cur.execute(sql, params or ())
        return self

    def executemany(self, sql, seq):
        for p in seq:
            self._cur.execute(sql, p)
        return self

    def fetchone(self):
        row = self._cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self._cur.description]
        return dict(zip(cols, row))

    def fetchall(self):
        cols = [d[0] for d in self._cur.description]
        return [dict(zip(cols, row)) for row in self._cur.fetchall()]

    @property
    def rowcount(self):
        return self._cur.rowcount

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cur.close()


def get_db():
    """Abre conexao PostgreSQL com DictCursor injetado."""
    params = _parse_url(_DATABASE_URL)
    conn = pg8000.dbapi.connect(**params, timeout=15, ssl_context=True)

    _orig_cursor = conn.cursor

    def dict_cursor():
        return DictCursor(_orig_cursor())

    conn.cursor = dict_cursor
    return conn


def init_db():
    """Insere dados iniciais se o banco estiver vazio."""
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS n FROM usuarios")
        if cur.fetchone()['n'] == 0:
            cur.execute(
                "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s,%s,%s,%s)",
                ("Administrador", "admin@clinica.com",
                 generate_password_hash("admin123"), "admin")
            )
        cur.execute("SELECT COUNT(*) AS n FROM dentistas")
        if cur.fetchone()['n'] == 0:
            dentistas = [
                ("Dr. Carlos Souza",     "CRO-SP 12345", "Clinico Geral",             "(11) 98800-1001", "carlos@clinica.com"),
                ("Dra. Ana Lima",        "CRO-SP 23456", "Ortodontia",                "(11) 98800-1002", "ana@clinica.com"),
                ("Dr. Pedro Martins",    "CRO-SP 34567", "Implantodontia",            "(11) 98800-1003", "pedro@clinica.com"),
                ("Dra. Maria Fernandes", "CRO-SP 45678", "Endodontia",                "(11) 98800-1004", "maria@clinica.com"),
                ("Dr. Lucas Oliveira",   "CRO-SP 56789", "Cirurgia Bucomaxilofacial", "(11) 98800-1005", "lucas@clinica.com"),
            ]
            for d in dentistas:
                cur.execute(
                    "INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
                    d
                )
        conn.commit()
    finally:
        conn.close()
