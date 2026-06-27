"""
Database layer — Supabase PostgREST + SQL via HTTP (sem TCP).
Funciona em qualquer ambiente serverless (Vercel, AWS Lambda, etc.).
"""
import os
import re
import requests
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

_PROJECT_REF = os.getenv('SUPABASE_PROJECT_REF', 'tuyivjgueaicevgitiyx')
_SQL_URL     = f"https://api.supabase.com/v1/projects/{_PROJECT_REF}/database/query"
_MGMT_TOKEN  = os.getenv('SUPABASE_ACCESS_TOKEN', '')

_SESS = requests.Session()
_SESS.headers.update({"Content-Type": "application/json"})


def _sql_to_str(sql, params):
    """Substitui %s por valores escapados (para a Management API)."""
    if not params:
        return sql
    parts = re.split(r'(%s)', sql)
    result = []
    pi = 0
    for part in parts:
        if part == '%s':
            v = params[pi]; pi += 1
            if v is None:
                result.append('NULL')
            elif isinstance(v, bool):
                result.append('TRUE' if v else 'FALSE')
            elif isinstance(v, (int, float)):
                result.append(str(v))
            else:
                escaped = str(v).replace("'", "''")
                result.append(f"'{escaped}'")
        else:
            result.append(part)
    return ''.join(result)


def _run(sql, params=()):
    """Executa SQL via Supabase Management API (HTTPS porta 443)."""
    query = _sql_to_str(sql, params)
    headers = {"Authorization": f"Bearer {_MGMT_TOKEN}", "Content-Type": "application/json"}
    r = _SESS.post(_SQL_URL, headers=headers, json={"query": query}, timeout=20)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"DB error {r.status_code}: {r.text[:300]}")
    data = r.json()
    if isinstance(data, list):
        return data
    return []


class _FakeCursor:
    """Cursor compatível com a interface PyMySQL usada em app.py."""
    def __init__(self):
        self._rows = []
        self._last_id = None

    def execute(self, sql, params=None):
        self._rows = _run(sql, params or ())
        # Captura RETURNING id
        if self._rows and 'id' in self._rows[0]:
            self._last_id = self._rows[0]['id']

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def executemany(self, sql, seq):
        for p in seq:
            _run(sql, p)

    @property
    def rowcount(self):
        return len(self._rows)

    def __enter__(self): return self
    def __exit__(self, *_): pass


class _FakeConn:
    """Conexão compatível com a interface PyMySQL usada em app.py."""
    def cursor(self): return _FakeCursor()
    def commit(self): pass   # Management API auto-commit
    def close(self):  pass


def get_db():
    return _FakeConn()


def init_db():
    """Insere dados iniciais se o banco estiver vazio."""
    rows = _run("SELECT COUNT(*) AS n FROM usuarios")
    if rows and rows[0].get('n', 0) == 0:
        senha = generate_password_hash("admin123")
        _run("INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s,%s,%s,%s)",
             ("Administrador", "admin@clinica.com", senha, "admin"))

    rows = _run("SELECT COUNT(*) AS n FROM dentistas")
    if rows and rows[0].get('n', 0) == 0:
        for row in [
            ("Dr. Carlos Souza",     "CRO-12345", "Clínico Geral",  "(11) 99999-0001", "carlos@clinica.com"),
            ("Dra. Ana Lima",        "CRO-23456", "Ortodontia",     "(11) 99999-0002", "ana@clinica.com"),
            ("Dr. Pedro Martins",    "CRO-34567", "Implantodontia", "(11) 99999-0003", "pedro@clinica.com"),
            ("Dra. Maria Fernandes", "CRO-45678", "Endodontia",     "(11) 99999-0004", "maria@clinica.com"),
        ]:
            _run("INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)", row)
