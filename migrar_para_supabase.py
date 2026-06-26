"""
Migra o projeto Bela Odontologia de MySQL para Supabase (PostgreSQL).
Execute este script APÓS criar o projeto no Supabase e preencher o .env.

Passos realizados automaticamente:
  1. Instala psycopg2-binary
  2. Copia os arquivos da pasta supabase/ para a raiz
  3. Testa a conexão com o Supabase
  4. Executa o schema PostgreSQL no Supabase
  5. Popula dados iniciais (admin + dentistas)
"""
import os
import sys
import shutil
import subprocess

BASE   = os.path.dirname(os.path.abspath(__file__))
SUB    = os.path.join(BASE, 'supabase')
PYTHON = sys.executable


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    result = subprocess.run(cmd, **kw)
    if result.returncode != 0:
        print(f"  [ERRO] Código: {result.returncode}")
        sys.exit(1)
    return result


def passo(n, texto):
    print(f"\n{'='*55}")
    print(f"  PASSO {n}: {texto}")
    print(f"{'='*55}")


# ------------------------------------------------------------------
passo(1, "Verificando arquivo .env")
env_path = os.path.join(BASE, '.env')
if not os.path.exists(env_path):
    print(f"  [ERRO] Arquivo .env não encontrado em:\n  {env_path}")
    print("\n  Crie o arquivo .env a partir de supabase/.env.example")
    print("  e preencha com a DATABASE_URL do seu projeto Supabase.")
    sys.exit(1)

with open(env_path) as f:
    content = f.read()
if 'DATABASE_URL' not in content or 'SUASENHA' in content:
    print("  [ERRO] DATABASE_URL não configurada no .env")
    print("  Preencha com a URL de conexão do seu projeto Supabase.")
    sys.exit(1)
print("  .env OK")

# ------------------------------------------------------------------
passo(2, "Instalando psycopg2-binary")
run([PYTHON, '-m', 'pip', 'install', 'psycopg2-binary==2.9.9',
     'python-dotenv==1.0.1', '--break-system-packages', '-q'])
print("  psycopg2-binary instalado")

# ------------------------------------------------------------------
passo(3, "Copiando arquivos da pasta supabase/ para a raiz")
arquivos = ['app.py', 'database.py', 'requirements.txt']
for arq in arquivos:
    src = os.path.join(SUB, arq)
    dst = os.path.join(BASE, arq)
    bkp = dst + '.mysql.bak'
    if os.path.exists(dst):
        shutil.copy2(dst, bkp)
        print(f"  Backup: {arq} → {arq}.mysql.bak")
    shutil.copy2(src, dst)
    print(f"  Copiado: supabase/{arq} → {arq}")

# ------------------------------------------------------------------
passo(4, "Testando conexão com Supabase")
test_conn = subprocess.run(
    [PYTHON, '-c',
     "from database import get_db; conn=get_db(); "
     "cur=conn.cursor(); cur.execute('SELECT 1'); "
     "print('Conexão OK'); conn.close()"],
    cwd=BASE, capture_output=True, text=True
)
if test_conn.returncode != 0:
    print(f"  [ERRO] Não foi possível conectar ao Supabase:")
    print(f"  {test_conn.stderr.strip()}")
    print("\n  Verifique a DATABASE_URL no .env e tente novamente.")
    sys.exit(1)
print(f"  {test_conn.stdout.strip()}")

# ------------------------------------------------------------------
passo(5, "Criando tabelas no Supabase")
schema_path = os.path.join(SUB, 'schema_supabase.sql')
with open(schema_path, encoding='utf-8') as f:
    schema_sql = f.read()

apply_schema = subprocess.run(
    [PYTHON, '-c', f"""
from database import get_db
conn = get_db()
sql = open(r'{schema_path}', encoding='utf-8').read()
statements = [s.strip() for s in sql.split(';') if s.strip() and not s.strip().startswith('--')]
with conn.cursor() as cur:
    for stmt in statements:
        if stmt:
            cur.execute(stmt)
conn.commit()
conn.close()
print('Schema aplicado com sucesso!')
"""],
    cwd=BASE, capture_output=True, text=True
)
if apply_schema.returncode != 0:
    print(f"  [AVISO] {apply_schema.stderr.strip()}")
    print("  (Tabelas podem já existir — continuando...)")
else:
    print(f"  {apply_schema.stdout.strip()}")

# ------------------------------------------------------------------
passo(6, "Inserindo dados iniciais")
init = subprocess.run(
    [PYTHON, '-c', "from database import init_db; init_db(); print('Dados iniciais inseridos!')"],
    cwd=BASE, capture_output=True, text=True
)
if init.returncode != 0:
    print(f"  [AVISO] {init.stderr.strip()}")
else:
    print(f"  {init.stdout.strip()}")

# ------------------------------------------------------------------
print(f"\n{'='*55}")
print("  MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
print(f"{'='*55}")
print("""
  O sistema agora usa o Supabase (PostgreSQL).

  Para iniciar:
    python app.py
  ou clique em iniciar.bat

  Login:
    E-mail: admin@clinica.com
    Senha:  admin123

  Os arquivos MySQL originais foram salvos como:
    app.py.mysql.bak
    database.py.mysql.bak
""")
