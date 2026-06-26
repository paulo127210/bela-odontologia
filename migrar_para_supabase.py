"""
Migra a Bela Odontologia de MySQL para Supabase (PostgreSQL).
Execute este script NA SUA MÁQUINA após configurar o .env.

Pré-requisito: DATABASE_URL preenchida no .env
"""
import os, sys, shutil, subprocess, re

BASE   = os.path.dirname(os.path.abspath(__file__))
SUB    = os.path.join(BASE, 'supabase')
PYTHON = sys.executable


def run(cmd, **kw):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        print(f"  [ERRO] código: {r.returncode}")
        sys.exit(1)
    return r


def passo(n, txt):
    print(f"\n{'='*55}\n  PASSO {n}: {txt}\n{'='*55}")


# ── 1. Verificar .env ───────────────────────────────────────
passo(1, "Verificando .env")
env_path = os.path.join(BASE, '.env')
if not os.path.exists(env_path):
    print("  [ERRO] .env não encontrado"); sys.exit(1)
content = open(env_path).read()
if 'DATABASE_URL' not in content or not re.search(r'DATABASE_URL=postgresql://.+', content):
    print("  [ERRO] DATABASE_URL não configurada"); sys.exit(1)
print("  .env OK")

# ── 2. Instalar pg8000 ──────────────────────────────────────
passo(2, "Instalando pg8000 (driver PostgreSQL puro Python)")
run([PYTHON, '-m', 'pip', 'install', 'pg8000', 'python-dotenv',
     '--break-system-packages', '-q'])
print("  pg8000 instalado")

# ── 3. Copiar arquivos supabase/ → raiz ────────────────────
passo(3, "Copiando arquivos para a raiz do projeto")
for arq in ['app.py', 'database.py', 'requirements.txt']:
    src = os.path.join(SUB, arq)
    dst = os.path.join(BASE, arq)
    bkp = dst + '.mysql.bak'
    if os.path.exists(dst):
        shutil.copy2(dst, bkp)
        print(f"  Backup: {arq}.mysql.bak")
    shutil.copy2(src, dst)
    print(f"  Copiado: supabase/{arq} → {arq}")

# ── 4. Testar conexão ───────────────────────────────────────
passo(4, "Testando conexão com Supabase")
test = subprocess.run(
    [PYTHON, '-c',
     "from database import get_db; c=get_db(); "
     "cur=c.cursor(); cur.execute('SELECT 1 AS ok'); "
     "print('Conexao OK:', cur.fetchone()); c.close()"],
    cwd=BASE, capture_output=True, text=True
)
if test.returncode != 0:
    print(f"  [ERRO] {test.stderr.strip()}")
    print("\n  Verifique a DATABASE_URL no .env e tente novamente.")
    sys.exit(1)
print(f"  {test.stdout.strip()}")

# ── 5. Dados iniciais ───────────────────────────────────────
passo(5, "Inserindo dados iniciais")
init = subprocess.run(
    [PYTHON, '-c', "from database import init_db; init_db(); print('OK')"],
    cwd=BASE, capture_output=True, text=True
)
print(f"  {init.stdout.strip() or init.stderr.strip()}")

print(f"""
{'='*55}
  MIGRACAO CONCLUIDA!
{'='*55}

  Banco: Supabase (PostgreSQL)
  Inicie: python app.py  ou  iniciar.bat
  Login:  admin@clinica.com / admin123

  Backups MySQL salvos como *.mysql.bak
""")
