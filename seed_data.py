"""
Popula o banco MySQL com dados de teste realistas para a Bela Odontologia.
Execute: python seed_data.py
"""
from database import get_db
from werkzeug.security import generate_password_hash
from datetime import datetime, date, timedelta
import random

conn = get_db()
cur  = conn.cursor()

print("Limpando dados antigos...")
cur.execute("SET FOREIGN_KEY_CHECKS=0")
for t in ("pagamentos","prontuarios","consultas","pacientes","dentistas","usuarios"):
    cur.execute(f"TRUNCATE TABLE {t}")
cur.execute("SET FOREIGN_KEY_CHECKS=1")

# ── Usuários ────────────────────────────────────────────────────────────────
print("Inserindo usuários...")
usuarios = [
    ("Administrador",     "admin@clinica.com",       "admin123",    "admin"),
    ("Recepcionista Ana", "ana.recep@clinica.com",   "senha123",    "recepcionista"),
]
for nome, email, senha, perfil in usuarios:
    cur.execute(
        "INSERT INTO usuarios (nome,email,senha,perfil) VALUES (%s,%s,%s,%s)",
        (nome, email, generate_password_hash(senha), perfil)
    )

# ── Dentistas ────────────────────────────────────────────────────────────────
print("Inserindo dentistas...")
dentistas = [
    ("Dr. Carlos Souza",     "CRO-SP 12345", "Clínico Geral",              "(11) 98800-1001", "carlos@clinica.com"),
    ("Dra. Ana Lima",        "CRO-SP 23456", "Ortodontia",                 "(11) 98800-1002", "ana@clinica.com"),
    ("Dr. Pedro Martins",    "CRO-SP 34567", "Implantodontia",             "(11) 98800-1003", "pedro@clinica.com"),
    ("Dra. Maria Fernandes", "CRO-SP 45678", "Endodontia",                 "(11) 98800-1004", "maria@clinica.com"),
    ("Dr. Lucas Oliveira",   "CRO-SP 56789", "Cirurgia Bucomaxilofacial",  "(11) 98800-1005", "lucas@clinica.com"),
]
for row in dentistas:
    cur.execute(
        "INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
        row
    )

# ── Pacientes ────────────────────────────────────────────────────────────────
print("Inserindo pacientes...")
pacientes = [
    ("João Silva",        "1990-03-15", "123.456.789-00", "Rua das Flores, 123 — São Paulo/SP",  "(11) 91111-0001", "joao@email.com",    "Unimed",          "Hipertenso. Uso de losartana 50mg."),
    ("Maria Oliveira",    "1985-07-22", "234.567.890-11", "Av. Paulista, 456 — São Paulo/SP",    "(11) 91111-0002", "maria@email.com",   "Particular",      "Alergia a penicilina."),
    ("Pedro Santos",      "1978-11-05", "345.678.901-22", "Rua Augusta, 789 — São Paulo/SP",     "(11) 91111-0003", "pedro@email.com",   "SulAmérica",      "Diabético tipo 2. Uso de metformina."),
    ("Ana Costa",         "1995-01-30", "456.789.012-33", "Rua Oscar Freire, 321 — São Paulo/SP","(11) 91111-0004", "ana@email.com",     "Bradesco Saúde",  "Sem restrições."),
    ("Carlos Pereira",    "1970-08-18", "567.890.123-44", "Av. Faria Lima, 654 — São Paulo/SP",  "(11) 91111-0005", "carlos@email.com",  "Particular",      "Ansiedade. Solicita anestesia reforçada."),
    ("Fernanda Lima",     "2000-05-12", "678.901.234-55", "Rua Haddock Lobo, 987 — São Paulo/SP","(11) 91111-0006", "fernanda@email.com","Amil",            "Sem restrições."),
    ("Ricardo Alves",     "1988-09-25", "789.012.345-66", "Av. Rebouças, 147 — São Paulo/SP",    "(11) 91111-0007", "ricardo@email.com", "Unimed",          "Histórico de gengivite crônica."),
    ("Juliana Martins",   "1993-04-08", "890.123.456-77", "Rua Consolação, 258 — São Paulo/SP",  "(11) 91111-0008", "juliana@email.com", "SulAmérica",      "Grávida — 2º trimestre. Evitar Rx."),
    ("Marcos Rodrigues",  "1965-12-01", "901.234.567-88", "Av. Brigadeiro, 369 — São Paulo/SP",  "(11) 91111-0009", "marcos@email.com",  "Particular",      "Cardiopata. Uso de AAS e estatina."),
    ("Patrícia Souza",    "1982-06-14", "012.345.678-99", "Rua da Consolação, 741 — São Paulo/SP","(11) 91111-0010","patricia@email.com","Bradesco Saúde",  "Sem restrições."),
    ("Bruno Carvalho",    "1997-02-20", "111.222.333-44", "Rua Teodoro Sampaio, 852 — SP",       "(11) 91111-0011", "bruno@email.com",   "Particular",      "Bruxismo. Usa placa de mordida."),
    ("Camila Ferreira",   "2003-10-09", "222.333.444-55", "Rua Estados Unidos, 963 — SP",        "(11) 91111-0012", "camila@email.com",  "Amil",            "Paciente jovem. Faz ortodontia."),
]
for row in pacientes:
    cur.execute(
        "INSERT INTO pacientes (nome,data_nascimento,cpf,endereco,telefone,email,convenio,historico_medico) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", row
    )

# ── Helpers ──────────────────────────────────────────────────────────────────
def dt(days_offset, hour=9, minute=0):
    d = datetime.now() + timedelta(days=days_offset)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0)

procedimentos = [
    "Consulta de Avaliação", "Limpeza / Profilaxia", "Restauração",
    "Extração Simples", "Tratamento de Canal", "Implante",
    "Ortodontia — Manutenção", "Clareamento Dental", "Prótese",
    "Extração de Siso",
]
formas_pag   = ["PIX", "Cartão de Débito", "Cartão de Crédito", "Dinheiro", "Convênio"]
valores_proc = {
    "Consulta de Avaliação":   150.00,
    "Limpeza / Profilaxia":    200.00,
    "Restauração":             350.00,
    "Extração Simples":        300.00,
    "Tratamento de Canal":     900.00,
    "Implante":               2800.00,
    "Ortodontia — Manutenção": 250.00,
    "Clareamento Dental":      800.00,
    "Prótese":                1500.00,
    "Extração de Siso":        600.00,
}

random.seed(42)

# ── Consultas passadas (realizadas + pagas) ──────────────────────────────────
print("Inserindo consultas passadas...")
consultas_passadas = []
for i in range(1, 13):          # 12 pacientes
    pac_id  = i
    dent_id = random.randint(1, 5)
    proc    = random.choice(procedimentos)
    data    = dt(random.randint(-90, -3), hour=random.randint(8, 17))
    cur.execute(
        "INSERT INTO consultas (paciente_id,dentista_id,data_hora,tipo_procedimento,status) "
        "VALUES (%s,%s,%s,%s,'realizada')",
        (pac_id, dent_id, data, proc)
    )
    consultas_passadas.append((cur.lastrowid, proc))

# segunda rodada de consultas passadas (alguns pacientes têm 2)
for pac_id in [1, 3, 5, 7, 9]:
    dent_id = random.randint(1, 5)
    proc    = random.choice(procedimentos)
    data    = dt(random.randint(-60, -5), hour=random.randint(8, 17))
    cur.execute(
        "INSERT INTO consultas (paciente_id,dentista_id,data_hora,tipo_procedimento,status) "
        "VALUES (%s,%s,%s,%s,'realizada')",
        (pac_id, dent_id, data, proc)
    )
    consultas_passadas.append((cur.lastrowid, proc))

# ── Prontuários para as realizadas ──────────────────────────────────────────
print("Inserindo prontuários...")
anotacoes_modelos = [
    "Paciente compareceu sem queixas agudas. Procedimento realizado sem intercorrências.",
    "Limpeza completa realizada. Orientações de higiene bucal fornecidas.",
    "Restauração em resina composta na face vestibular do dente 14. Bom resultado estético.",
    "Extração realizada sob anestesia local. Hemostasia satisfatória.",
    "Preparo biomecânico dos canais realizado. Selamento temporário aplicado.",
    "Instalação do implante sem complicações. Pós-operatório orientado.",
    "Manutenção de aparelho fixo. Troca de fios e ligaduras.",
    "Aplicação de gel clareador. Paciente orientado sobre alimentação.",
]
prescricoes_modelos = [
    "Amoxicilina 500mg — 1 cápsula de 8/8h por 7 dias.\nIbuprofeno 600mg — se dor.",
    "Paracetamol 750mg — 1 comprimido de 6/6h se necessário.",
    "Sem prescrição. Manter higiene bucal rigorosa.",
    "Clorexidina 0,12% — bochecho 2x/dia por 7 dias.",
    "Dipirona 500mg — 1 comprimido de 6/6h se dor. Gelo local nas primeiras 24h.",
]
for cid, proc in consultas_passadas:
    cur.execute(
        "INSERT INTO prontuarios (consulta_id,anotacoes,prescricao) VALUES (%s,%s,%s)",
        (cid, random.choice(anotacoes_modelos), random.choice(prescricoes_modelos))
    )

# ── Pagamentos para as realizadas ────────────────────────────────────────────
print("Inserindo pagamentos...")
cur.execute("SELECT id,tipo_procedimento,data_hora,paciente_id FROM consultas WHERE status='realizada'")
realizadas = cur.fetchall()
cur.execute("SELECT id,convenio FROM pacientes")
pacs = {r['id']: r['convenio'] for r in cur.fetchall()}

for c in realizadas:
    valor   = valores_proc.get(c['tipo_procedimento'], 300.00)
    conv    = pacs.get(c['paciente_id'], 'Particular')
    forma   = "Convênio" if conv and conv != "Particular" else random.choice(formas_pag[:-1])
    data_pag = (c['data_hora'] if isinstance(c['data_hora'], date)
                else c['data_hora'].date()) if hasattr(c['data_hora'], 'date') else c['data_hora']
    cur.execute(
        "INSERT INTO pagamentos (consulta_id,valor,data_pagamento,forma_pagamento,convenio,status) "
        "VALUES (%s,%s,%s,%s,%s,'pago')",
        (c['id'], valor, data_pag, forma, conv if conv != 'Particular' else '')
    )

# ── Consultas futuras (agendadas) ─────────────────────────────────────────────
print("Inserindo consultas futuras...")
futuras = [
    (1,  1, dt(1,  9, 0),  "Limpeza / Profilaxia",    "agendada"),
    (2,  2, dt(1, 10, 30), "Ortodontia — Manutenção", "confirmada"),
    (3,  3, dt(2,  8, 0),  "Implante",                "agendada"),
    (4,  1, dt(2, 14, 0),  "Restauração",             "confirmada"),
    (5,  4, dt(3, 11, 0),  "Tratamento de Canal",     "agendada"),
    (6,  2, dt(3, 15, 30), "Ortodontia — Manutenção", "agendada"),
    (7,  5, dt(5,  9, 0),  "Extração de Siso",        "confirmada"),
    (8,  1, dt(5, 16, 0),  "Consulta de Avaliação",   "agendada"),
    (9,  3, dt(7, 10, 0),  "Implante",                "confirmada"),
    (10, 4, dt(7, 14, 30), "Clareamento Dental",      "agendada"),
    (11, 1, dt(10, 8, 30), "Limpeza / Profilaxia",    "agendada"),
    (12, 2, dt(10,13, 0),  "Ortodontia — Manutenção", "agendada"),
]
for pac_id, dent_id, data, proc, status in futuras:
    cur.execute(
        "INSERT INTO consultas (paciente_id,dentista_id,data_hora,tipo_procedimento,status) "
        "VALUES (%s,%s,%s,%s,%s)",
        (pac_id, dent_id, data, proc, status)
    )

# ── Uma consulta de hoje ──────────────────────────────────────────────────────
cur.execute(
    "INSERT INTO consultas (paciente_id,dentista_id,data_hora,tipo_procedimento,status) "
    "VALUES (%s,%s,%s,%s,%s)",
    (1, 1, dt(0, 9, 0), "Limpeza / Profilaxia", "confirmada")
)

conn.commit()
cur.close()
conn.close()

print("\n[OK] Dados inseridos com sucesso!")
print("   Usuarios    : 2  (admin + recepcionista)")
print("   Dentistas   : 5")
print("   Pacientes   : 12")
print(f"   Consultas   : {len(consultas_passadas) + len(futuras) + 1}  ({len(consultas_passadas)} realizadas, {len(futuras)+1} futuras/hoje)")
print(f"   Prontuarios : {len(consultas_passadas)}")
print(f"   Pagamentos  : {len(consultas_passadas)}")
