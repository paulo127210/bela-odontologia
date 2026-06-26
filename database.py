"""
Database layer — MySQL via PyMySQL.
Para migrar para Supabase (PostgreSQL) basta trocar o driver
por psycopg2 e ajustar os placeholders de %s para $1,$2,…
"""
import os
import pymysql
import pymysql.cursors
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

_CFG = dict(
    host     = os.getenv('DB_HOST',     'localhost'),
    port     = int(os.getenv('DB_PORT', 3306)),
    user     = os.getenv('DB_USER',     'root'),
    password = os.getenv('DB_PASSWORD', 'root'),
    db       = os.getenv('DB_NAME',     'bela_odontologia'),
    charset  = 'utf8mb4',
    cursorclass = pymysql.cursors.DictCursor,
    autocommit  = False,
)


def get_db():
    """Abre (ou retorna) uma conexão MySQL para o request atual."""
    conn = pymysql.connect(**_CFG)
    return conn


def init_db():
    """Insere dados iniciais (admin + dentistas de exemplo) se o banco estiver vazio."""
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # Admin padrão
            cur.execute("SELECT COUNT(*) AS n FROM usuarios")
            if cur.fetchone()['n'] == 0:
                cur.execute(
                    "INSERT INTO usuarios (nome, email, senha, perfil) VALUES (%s,%s,%s,%s)",
                    ("Administrador", "admin@clinica.com",
                     generate_password_hash("admin123"), "admin")
                )

            # Dentistas de exemplo
            cur.execute("SELECT COUNT(*) AS n FROM dentistas")
            if cur.fetchone()['n'] == 0:
                dentistas = [
                    ("Dr. Carlos Souza",    "CRO-12345", "Clínico Geral",     "(11) 99999-0001", "carlos@clinica.com"),
                    ("Dra. Ana Lima",       "CRO-23456", "Ortodontia",        "(11) 99999-0002", "ana@clinica.com"),
                    ("Dr. Pedro Martins",   "CRO-34567", "Implantodontia",    "(11) 99999-0003", "pedro@clinica.com"),
                    ("Dra. Maria Fernandes","CRO-45678", "Endodontia",        "(11) 99999-0004", "maria@clinica.com"),
                ]
                cur.executemany(
                    "INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
                    dentistas
                )
        conn.commit()
    finally:
        conn.close()
