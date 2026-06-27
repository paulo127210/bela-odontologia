"""
Database layer — PostgreSQL via psycopg2 (Supabase connection pooler).
Usa DATABASE_URL do ambiente. RealDictCursor retorna rows como dict.
"""
import os
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()


def get_db():
    conn = psycopg2.connect(
        os.getenv('DATABASE_URL', ''),
        cursor_factory=psycopg2.extras.RealDictCursor,
        connect_timeout=10,
        sslmode='require',
    )
    conn.autocommit = False
    return conn


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
