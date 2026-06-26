"""
Database layer — PostgreSQL (Supabase).
Usa pg8000 (Python puro, compatível com Python 3.14+).
Para produção em Python 3.11/3.12 pode trocar por psycopg2-binary.
"""
import os
import pg8000.dbapi
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

_DATABASE_URL = os.getenv('DATABASE_URL', '')


def _parse_url(url):
    """Extrai componentes de uma DATABASE_URL postgresql://user:pass@host:port/db"""
    import re
    m = re.match(
        r'postgresql://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)', url
    )
    if not m:
        raise ValueError(f"DATABASE_URL inválida: {url}")
    return dict(user=m.group(1), password=m.group(2),
                host=m.group(3), port=int(m.group(4) or 5432),
                database=m.group(5))


def get_db():
    """Abre conexão com o Supabase (PostgreSQL via pg8000)."""
    params = _parse_url(_DATABASE_URL)
    conn = pg8000.dbapi.connect(**params, timeout=15, ssl_context=True)
    return conn


class DictCursor:
    """Wrapper que faz o cursor do pg8000 retornar dicts."""
    def __init__(self, conn):
        self._cur = conn.cursor()

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

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._cur.close()


# Monkey-patch: faz conn.cursor() retornar DictCursor
_orig_connect = get_db


def get_db():
    params = _parse_url(_DATABASE_URL)
    conn = pg8000.dbapi.connect(**params, timeout=15, ssl_context=True)
    _orig_cursor = conn.cursor

    def dict_cursor():
        return DictCursor(conn)

    conn.cursor = dict_cursor
    return conn


def init_db():
    """Insere dados iniciais se o banco estiver vazio."""
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
                dentistas = [
                    ("Dr. Carlos Souza",    "CRO-SP 12345", "Clínico Geral",    "(11) 98800-1001", "carlos@clinica.com"),
                    ("Dra. Ana Lima",       "CRO-SP 23456", "Ortodontia",       "(11) 98800-1002", "ana@clinica.com"),
                    ("Dr. Pedro Martins",   "CRO-SP 34567", "Implantodontia",   "(11) 98800-1003", "pedro@clinica.com"),
                    ("Dra. Maria Fernandes","CRO-SP 45678", "Endodontia",       "(11) 98800-1004", "maria@clinica.com"),
                    ("Dr. Lucas Oliveira",  "CRO-SP 56789", "Cirurgia Bucomaxilofacial","(11) 98800-1005","lucas@clinica.com"),
                ]
                cur.executemany(
                    "INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
                    dentistas
                )
        conn.commit()
    finally:
        conn.close()
