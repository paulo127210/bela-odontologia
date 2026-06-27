import os
import random
import string
from datetime import date, datetime
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from flask_wtf.csrf import CSRFProtect
from database import get_db, init_db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE='Lax',
    WTF_CSRF_TIME_LIMIT=3600,
)
csrf = CSRFProtect(app)


@app.template_filter('dt')
def fmt_dt(value, fmt='%d/%m/%Y %H:%M'):
    if value is None:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    return str(value)[:16]


@app.template_filter('dt_input')
def fmt_dt_input(value):
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%dT%H:%M')
    return str(value)[:16]


@app.template_filter('brl')
def fmt_brl(value):
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return 'R$ 0,00'


# ---------------------------------------------------------------------------
# Helpers de BD
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('admin_login'))
        if session.get('usuario_perfil') != 'admin':
            flash('Acesso restrito a administradores.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


def cliente_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'cliente_id' not in session:
            flash('Faça login para continuar.', 'warning')
            return redirect(url_for('portal') + '#agendar')
        return f(*args, **kwargs)
    return decorated


def db():
    if 'db_conn' not in g:
        g.db_conn = get_db()
    return g.db_conn


def q(sql, params=()):
    with db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def q1(sql, params=()):
    with db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def exe(sql, params=()):
    """Executa um statement; retorna o id gerado para INSERTs via RETURNING id."""
    is_insert = sql.strip().upper().startswith('INSERT')
    query = (sql + ' RETURNING id') if is_insert else sql
    with db().cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone() if is_insert else None
    db().commit()
    return row['id'] if row else None


@app.teardown_appcontext
def close_db(_e=None):
    conn = g.pop('db_conn', None)
    if conn:
        conn.close()


# ---------------------------------------------------------------------------
# Portal público (página inicial)
# ---------------------------------------------------------------------------

@app.route('/')
def portal():
    dentistas = q("SELECT id, nome, especialidade FROM dentistas WHERE ativo=TRUE ORDER BY nome")
    cliente = None
    if 'cliente_id' in session:
        cliente = q1("SELECT * FROM pacientes WHERE id=%s", (session['cliente_id'],))
    return render_template('portal.html', dentistas=dentistas, cliente=cliente)


@app.route('/cliente/acesso', methods=['POST'])
def cliente_acesso():
    cpf_raw = request.form.get('cpf', '').strip()
    cpf     = cpf_raw.replace('.', '').replace('-', '')
    nasc    = request.form.get('data_nascimento', '').strip()
    nome    = request.form.get('nome', '').strip()
    tel     = request.form.get('telefone', '').strip()
    email   = request.form.get('email', '').strip()

    if not cpf or not nasc:
        flash('CPF e data de nascimento são obrigatórios.', 'danger')
        return redirect(url_for('portal') + '#agendar')

    pac = q1("SELECT * FROM pacientes WHERE REPLACE(REPLACE(cpf,'.',''),'-','')=%s", (cpf,))

    if pac:
        nasc_db = str(pac['data_nascimento']) if pac['data_nascimento'] else ''
        if nasc_db != nasc:
            flash('Data de nascimento incorreta. Tente novamente.', 'danger')
            return redirect(url_for('portal') + '#agendar')
        session['cliente_id']   = pac['id']
        session['cliente_nome'] = pac['nome']
        session['cliente_cpf']  = pac['cpf']
        return redirect(url_for('cliente_agendar'))
    else:
        if not nome:
            flash('Cadastro não encontrado. Preencha seu nome para se cadastrar.', 'warning')
            return redirect(url_for('portal') + '#agendar')
        pid = exe("INSERT INTO pacientes (nome, cpf, data_nascimento, telefone, email) VALUES (%s,%s,%s,%s,%s)",
                  (nome, cpf_raw, nasc, tel, email))
        session['cliente_id']   = pid
        session['cliente_nome'] = nome
        session['cliente_cpf']  = cpf_raw
        flash(f'Bem-vindo(a), {nome}! Cadastro realizado com sucesso.', 'success')
        return redirect(url_for('cliente_agendar'))


@app.route('/cliente/agendar', methods=['GET', 'POST'])
@cliente_required
def cliente_agendar():
    dentistas = q("SELECT id, nome, especialidade FROM dentistas WHERE ativo=TRUE ORDER BY nome")
    if request.method == 'POST':
        exe("""INSERT INTO consultas (paciente_id, dentista_id, data_hora, tipo_procedimento, observacoes, status)
               VALUES (%s,%s,%s,%s,%s,'agendada')""",
            (session['cliente_id'],
             request.form.get('dentista_id'),
             request.form.get('data_hora'),
             request.form.get('tipo_procedimento', '').strip(),
             request.form.get('observacoes', '').strip()))
        flash('Consulta agendada com sucesso! Aguarde a confirmação da clínica.', 'success')
        return redirect(url_for('cliente_agendar'))
    consultas = q("""SELECT c.data_hora, c.tipo_procedimento, c.status, d.nome AS dentista
                     FROM consultas c JOIN dentistas d ON d.id=c.dentista_id
                     WHERE c.paciente_id=%s ORDER BY c.data_hora DESC LIMIT 10""",
                  (session['cliente_id'],))
    return render_template('cliente/agendamento.html', dentistas=dentistas, consultas=consultas)


@app.route('/cliente/sair')
def cliente_logout():
    session.pop('cliente_id', None)
    session.pop('cliente_nome', None)
    session.pop('cliente_cpf', None)
    return redirect(url_for('portal'))


# ---------------------------------------------------------------------------
# Auth — Administrador
# ---------------------------------------------------------------------------

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        row = q1("SELECT * FROM usuarios WHERE email=%s AND ativo=TRUE",
                 (request.form['email'].strip(),))
        if row and check_password_hash(row['senha'], request.form['senha']):
            session['usuario_id']     = row['id']
            session['usuario_nome']   = row['nome']
            session['usuario_perfil'] = row['perfil']
            return redirect(url_for('dashboard'))
        error = "E-mail ou senha incorretos."
    return render_template('login.html', error=error)


@app.route('/login')
def login():
    return redirect(url_for('admin_login'))


@app.route('/admin/recuperar', methods=['GET', 'POST'])
def admin_recuperar():
    temp_senha = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        row   = q1("SELECT id FROM usuarios WHERE email=%s AND ativo=TRUE", (email,))
        if row:
            temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
            exe("UPDATE usuarios SET senha=%s WHERE id=%s", (generate_password_hash(temp), row['id']))
            temp_senha = temp
        else:
            flash('E-mail não encontrado.', 'danger')
    return render_template('admin_recuperar.html', temp_senha=temp_senha)


@app.route('/cliente/recuperar', methods=['GET', 'POST'])
def cliente_recuperar():
    pac = None
    if request.method == 'POST':
        contato = request.form.get('contato', '').strip()
        pac = q1("""SELECT nome, cpf, data_nascimento FROM pacientes
                    WHERE email=%s
                       OR REPLACE(REPLACE(telefone,' ',''),'-','')=REPLACE(REPLACE(%s,' ',''),'-','')
                    LIMIT 1""", (contato, contato))
        if not pac:
            flash('Nenhum cadastro encontrado com esse e-mail ou celular.', 'danger')
    return render_template('cliente_recuperar.html', pac=pac)


@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    session.pop('usuario_nome', None)
    session.pop('usuario_perfil', None)
    return redirect(url_for('portal'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    total_pacientes = q1("SELECT COUNT(*) AS n FROM pacientes")['n']
    total_hoje      = q1("SELECT COUNT(*) AS n FROM consultas WHERE data_hora::date = CURRENT_DATE")['n']
    total_mes       = q1("SELECT COUNT(*) AS n FROM consultas WHERE date_trunc('month', data_hora) = date_trunc('month', NOW())")['n']
    fat_mes_row     = q1("SELECT COALESCE(SUM(valor),0) AS s FROM pagamentos WHERE date_trunc('month', data_pagamento) = date_trunc('month', CURRENT_DATE)")
    faturamento_mes = float(fat_mes_row['s']) if fat_mes_row else 0.0
    proximas = q(
        "SELECT c.id, p.nome AS paciente, d.nome AS dentista, "
        "c.data_hora, c.tipo_procedimento, c.status "
        "FROM consultas c "
        "JOIN pacientes p ON p.id=c.paciente_id "
        "JOIN dentistas d ON d.id=c.dentista_id "
        "WHERE c.data_hora >= NOW() AND c.status NOT IN ('cancelada') "
        "ORDER BY c.data_hora LIMIT 8"
    )
    estoque_alertas = q(
        "SELECT produto, quantidade, quantidade_minima, unidade "
        "FROM estoque WHERE quantidade <= quantidade_minima ORDER BY produto"
    )
    estoque_itens = q("SELECT * FROM estoque ORDER BY categoria, produto")
    estoque_cats  = q("SELECT DISTINCT categoria FROM estoque ORDER BY categoria")
    return render_template('dashboard.html',
                           total_pacientes=total_pacientes,
                           total_hoje=total_hoje,
                           total_mes=total_mes,
                           estoque_alertas=estoque_alertas,
                           estoque_itens=estoque_itens,
                           estoque_cats=estoque_cats,
                           faturamento_mes=faturamento_mes,
                           proximas=proximas)


# ---------------------------------------------------------------------------
# Pacientes
# ---------------------------------------------------------------------------

@app.route('/pacientes')
@login_required
def pacientes_lista():
    busca = request.args.get('q', '').strip()
    if busca:
        like = f'%{busca}%'
        rows = q("SELECT * FROM pacientes WHERE nome ILIKE %s OR cpf ILIKE %s OR telefone ILIKE %s ORDER BY nome",
                 (like, like, like))
    else:
        rows = q("SELECT * FROM pacientes ORDER BY nome")
    return render_template('pacientes/lista.html', pacientes=rows, q=busca)


def _montar_endereco(f):
    partes = []
    if f.get('logradouro'): partes.append(f['logradouro'])
    if f.get('numero'):     partes[-1] = partes[-1] + ', ' + f['numero'] if partes else f['numero']
    if f.get('complemento'): partes.append(f['complemento'])
    if f.get('bairro'):     partes.append(f['bairro'])
    cidade_uf = ' — '.join(filter(None, [f.get('cidade'), f.get('uf')]))
    if cidade_uf: partes.append(cidade_uf)
    if f.get('cep'):        partes.append('CEP ' + f['cep'])
    return ', '.join(partes)


@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def pacientes_novo():
    if request.method == 'POST':
        f = request.form
        endereco = _montar_endereco(f)
        exe("INSERT INTO pacientes "
            "(nome,data_nascimento,cpf,endereco,cep,logradouro,numero,complemento,bairro,cidade,uf,"
            " telefone,email,convenio,historico_medico) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (f['nome'], f['data_nascimento'] or None, f['cpf'],
             endereco, f.get('cep'), f.get('logradouro'), f.get('numero'),
             f.get('complemento'), f.get('bairro'), f.get('cidade'), f.get('uf'),
             f['telefone'], f['email'], f['convenio'], f['historico_medico']))
        flash('Paciente cadastrado com sucesso!', 'success')
        return redirect(url_for('pacientes_lista'))
    return render_template('pacientes/form.html', paciente=None)


@app.route('/pacientes/<int:pid>')
@login_required
def pacientes_detalhes(pid):
    p = q1("SELECT * FROM pacientes WHERE id=%s", (pid,))
    if not p:
        flash('Paciente não encontrado.', 'danger')
        return redirect(url_for('pacientes_lista'))
    consultas = q("SELECT c.*, d.nome AS dentista FROM consultas c "
                  "JOIN dentistas d ON d.id=c.dentista_id "
                  "WHERE c.paciente_id=%s ORDER BY c.data_hora DESC", (pid,))
    return render_template('pacientes/detalhes.html', paciente=p, consultas=consultas)


@app.route('/pacientes/<int:pid>/editar', methods=['GET', 'POST'])
@login_required
def pacientes_editar(pid):
    p = q1("SELECT * FROM pacientes WHERE id=%s", (pid,))
    if not p:
        flash('Paciente não encontrado.', 'danger')
        return redirect(url_for('pacientes_lista'))
    if request.method == 'POST':
        f = request.form
        endereco = _montar_endereco(f)
        exe("UPDATE pacientes SET nome=%s,data_nascimento=%s,cpf=%s,endereco=%s,"
            "cep=%s,logradouro=%s,numero=%s,complemento=%s,bairro=%s,cidade=%s,uf=%s,"
            "telefone=%s,email=%s,convenio=%s,historico_medico=%s WHERE id=%s",
            (f['nome'], f['data_nascimento'] or None, f['cpf'],
             endereco, f.get('cep'), f.get('logradouro'), f.get('numero'),
             f.get('complemento'), f.get('bairro'), f.get('cidade'), f.get('uf'),
             f['telefone'], f['email'], f['convenio'], f['historico_medico'], pid))
        flash('Paciente atualizado!', 'success')
        return redirect(url_for('pacientes_detalhes', pid=pid))
    return render_template('pacientes/form.html', paciente=p)


@app.route('/pacientes/<int:pid>/excluir', methods=['POST'])
@login_required
def pacientes_excluir(pid):
    exe("DELETE FROM pacientes WHERE id=%s", (pid,))
    flash('Paciente excluído.', 'info')
    return redirect(url_for('pacientes_lista'))


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

@app.route('/consultas')
@login_required
def consultas_lista():
    status_f = request.args.get('status', '')
    data_f   = request.args.get('data', '')
    sql = ("SELECT c.id, p.nome AS paciente, d.nome AS dentista, "
           "c.data_hora, c.tipo_procedimento, c.status "
           "FROM consultas c "
           "JOIN pacientes p ON p.id=c.paciente_id "
           "JOIN dentistas d ON d.id=c.dentista_id WHERE 1=1 ")
    params = []
    if status_f:
        sql += " AND c.status=%s"; params.append(status_f)
    if data_f:
        sql += " AND c.data_hora::date=%s"; params.append(data_f)
    sql += " ORDER BY c.data_hora DESC"
    rows = q(sql, params)
    return render_template('consultas/lista.html',
                           consultas=rows, status_filtro=status_f, data_filtro=data_f)


@app.route('/consultas/nova', methods=['GET', 'POST'])
@login_required
def consultas_nova():
    if request.method == 'POST':
        f = request.form
        exe("INSERT INTO consultas (paciente_id,dentista_id,data_hora,tipo_procedimento,status,observacoes) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (f['paciente_id'], f['dentista_id'], f['data_hora'],
             f['tipo_procedimento'], f['status'], f['observacoes']))
        flash('Consulta agendada com sucesso!', 'success')
        return redirect(url_for('consultas_lista'))
    pacientes = q("SELECT id,nome FROM pacientes ORDER BY nome")
    dentistas = q("SELECT id,nome,especialidade FROM dentistas ORDER BY nome")
    return render_template('consultas/form.html',
                           consulta=None, pacientes=pacientes,
                           dentistas=dentistas, pre_paciente=request.args.get('paciente_id', ''))


@app.route('/consultas/<int:cid>')
@login_required
def consultas_detalhes(cid):
    c = q1("SELECT c.*, p.nome AS paciente_nome, d.nome AS dentista_nome "
           "FROM consultas c "
           "JOIN pacientes p ON p.id=c.paciente_id "
           "JOIN dentistas d ON d.id=c.dentista_id "
           "WHERE c.id=%s", (cid,))
    if not c:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('consultas_lista'))
    prontuario = q1("SELECT * FROM prontuarios WHERE consulta_id=%s", (cid,))
    pagamento  = q1("SELECT * FROM pagamentos WHERE consulta_id=%s", (cid,))
    return render_template('consultas/detalhes.html',
                           consulta=c, prontuario=prontuario, pagamento=pagamento)


@app.route('/consultas/<int:cid>/editar', methods=['GET', 'POST'])
@login_required
def consultas_editar(cid):
    c = q1("SELECT * FROM consultas WHERE id=%s", (cid,))
    if not c:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('consultas_lista'))
    if request.method == 'POST':
        f = request.form
        exe("UPDATE consultas SET paciente_id=%s,dentista_id=%s,data_hora=%s,"
            "tipo_procedimento=%s,status=%s,observacoes=%s WHERE id=%s",
            (f['paciente_id'], f['dentista_id'], f['data_hora'],
             f['tipo_procedimento'], f['status'], f['observacoes'], cid))
        flash('Consulta atualizada!', 'success')
        return redirect(url_for('consultas_detalhes', cid=cid))
    pacientes = q("SELECT id,nome FROM pacientes ORDER BY nome")
    dentistas = q("SELECT id,nome,especialidade FROM dentistas ORDER BY nome")
    return render_template('consultas/form.html',
                           consulta=c, pacientes=pacientes, dentistas=dentistas, pre_paciente='')


@app.route('/consultas/<int:cid>/cancelar', methods=['POST'])
@login_required
def consultas_cancelar(cid):
    exe("UPDATE consultas SET status='cancelada' WHERE id=%s", (cid,))
    flash('Consulta cancelada.', 'warning')
    return redirect(url_for('consultas_lista'))


# ---------------------------------------------------------------------------
# Prontuários
# ---------------------------------------------------------------------------

@app.route('/prontuarios/<int:cid>', methods=['GET', 'POST'])
@login_required
def prontuarios_form(cid):
    consulta = q1("SELECT c.*, p.nome AS paciente_nome, dn.nome AS dentista_nome "
                  "FROM consultas c "
                  "JOIN pacientes p ON p.id=c.paciente_id "
                  "JOIN dentistas dn ON dn.id=c.dentista_id "
                  "WHERE c.id=%s", (cid,))
    if not consulta:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('consultas_lista'))
    prontuario = q1("SELECT * FROM prontuarios WHERE consulta_id=%s", (cid,))
    if request.method == 'POST':
        f = request.form
        if prontuario:
            exe("UPDATE prontuarios SET anotacoes=%s,prescricao=%s WHERE consulta_id=%s",
                (f['anotacoes'], f['prescricao'], cid))
        else:
            exe("INSERT INTO prontuarios (consulta_id,anotacoes,prescricao) VALUES (%s,%s,%s)",
                (cid, f['anotacoes'], f['prescricao']))
        exe("UPDATE consultas SET status='realizada' WHERE id=%s AND status='agendada'", (cid,))
        flash('Prontuário salvo com sucesso!', 'success')
        return redirect(url_for('consultas_detalhes', cid=cid))
    return render_template('prontuarios/form.html', consulta=consulta, prontuario=prontuario)


# ---------------------------------------------------------------------------
# Faturamento
# ---------------------------------------------------------------------------

@app.route('/faturamento')
@login_required
def faturamento_lista():
    from datetime import date, timedelta
    periodo = request.args.get('periodo', 'mes')
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    status   = request.args.get('status', '')
    forma    = request.args.get('forma', '')
    hoje     = date.today()

    # Calcula intervalo conforme período
    if periodo == 'hoje':
        data_ini = data_fim = hoje.isoformat()
    elif periodo == 'semana':
        data_ini = (hoje - timedelta(days=hoje.weekday())).isoformat()
        data_fim = hoje.isoformat()
    elif periodo == 'mes':
        data_ini = hoje.replace(day=1).isoformat()
        data_fim = hoje.isoformat()
    elif periodo == 'ano':
        data_ini = hoje.replace(month=1, day=1).isoformat()
        data_fim = hoje.isoformat()
    # 'custom' usa data_ini/data_fim do GET

    base = ("SELECT pg.*, c.tipo_procedimento, p.nome AS paciente "
            "FROM pagamentos pg "
            "JOIN consultas c ON c.id=pg.consulta_id "
            "JOIN pacientes p ON p.id=c.paciente_id WHERE 1=1 ")
    params = []
    if data_ini:
        base += " AND pg.data_pagamento >= %s"; params.append(data_ini)
    if data_fim:
        base += " AND pg.data_pagamento <= %s"; params.append(data_fim)
    if status:
        base += " AND pg.status=%s"; params.append(status)
    if forma:
        base += " AND pg.forma_pagamento=%s"; params.append(forma)
    base += " ORDER BY pg.data_pagamento DESC"
    rows  = q(base, params)
    total = sum(float(r['valor']) for r in rows)

    # Totais por forma de pagamento
    por_forma = {}
    for r in rows:
        f = r['forma_pagamento'] or 'Outros'
        por_forma[f] = por_forma.get(f, 0) + float(r['valor'])

    # Alerta de IR (31/dez)
    ir_alerta = (hoje.month == 12 and hoje.day == 31)
    ir_ano    = hoje.year

    return render_template('faturamento/lista.html',
                           pagamentos=rows, total=total, por_forma=por_forma,
                           periodo=periodo, data_ini=data_ini, data_fim=data_fim,
                           status=status, forma=forma,
                           ir_alerta=ir_alerta, ir_ano=ir_ano)


@app.route('/relatorios/imposto-de-renda/<int:ano>')
@login_required
def relatorio_ir(ano):
    # Receita bruta anual
    receita = q1(
        "SELECT COALESCE(SUM(valor),0) AS total, COUNT(*) AS qtd "
        "FROM pagamentos WHERE EXTRACT(YEAR FROM data_pagamento)=%s AND status='pago'", (ano,))
    # Por forma de pagamento
    por_forma = q(
        "SELECT forma_pagamento, SUM(valor) AS total, COUNT(*) AS qtd "
        "FROM pagamentos WHERE EXTRACT(YEAR FROM data_pagamento)=%s AND status='pago' "
        "GROUP BY forma_pagamento ORDER BY total DESC", (ano,))
    # Por mês
    por_mes = q(
        "SELECT TO_CHAR(data_pagamento,'MM') AS mes, TO_CHAR(data_pagamento,'Month') AS nome_mes, "
        "SUM(valor) AS total, COUNT(*) AS qtd "
        "FROM pagamentos WHERE EXTRACT(YEAR FROM data_pagamento)=%s AND status='pago' "
        "GROUP BY mes, nome_mes ORDER BY mes", (ano,))
    # Por procedimento
    por_proc = q(
        "SELECT c.tipo_procedimento, SUM(pg.valor) AS total, COUNT(*) AS qtd "
        "FROM pagamentos pg JOIN consultas c ON c.id=pg.consulta_id "
        "WHERE EXTRACT(YEAR FROM pg.data_pagamento)=%s AND pg.status='pago' "
        "AND c.tipo_procedimento IS NOT NULL "
        "GROUP BY c.tipo_procedimento ORDER BY total DESC", (ano,))
    # Por dentista
    por_dentista = q(
        "SELECT d.nome, d.cro, SUM(pg.valor) AS total, COUNT(*) AS qtd "
        "FROM pagamentos pg "
        "JOIN consultas c ON c.id=pg.consulta_id "
        "JOIN dentistas d ON d.id=c.dentista_id "
        "WHERE EXTRACT(YEAR FROM pg.data_pagamento)=%s AND pg.status='pago' "
        "GROUP BY d.id, d.nome, d.cro ORDER BY total DESC", (ano,))
    # Convênios separados (dedutíveis diferente)
    convenios = q(
        "SELECT convenio, SUM(valor) AS total, COUNT(*) AS qtd "
        "FROM pagamentos WHERE EXTRACT(YEAR FROM data_pagamento)=%s "
        "AND status='pago' AND convenio IS NOT NULL AND convenio != '' "
        "GROUP BY convenio ORDER BY total DESC", (ano,))

    anos_disponiveis = q(
        "SELECT DISTINCT EXTRACT(YEAR FROM data_pagamento)::int AS ano "
        "FROM pagamentos WHERE status='pago' ORDER BY ano DESC")

    return render_template('relatorios/imposto_renda.html',
                           ano=ano, receita=receita, por_forma=por_forma,
                           por_mes=por_mes, por_proc=por_proc,
                           por_dentista=por_dentista, convenios=convenios,
                           anos_disponiveis=anos_disponiveis,
                           hoje=date.today())


@app.route('/faturamento/novo/<int:cid>', methods=['GET', 'POST'])
@login_required
def faturamento_novo(cid):
    consulta = q1(
        "SELECT c.*, p.nome AS paciente_nome, d.nome AS dentista_nome "
        "FROM consultas c "
        "JOIN pacientes p ON p.id=c.paciente_id "
        "JOIN dentistas d ON d.id=c.dentista_id "
        "WHERE c.id=%s", (cid,))
    if not consulta:
        flash('Consulta não encontrada.', 'danger')
        return redirect(url_for('faturamento_lista'))
    if q1("SELECT id FROM pagamentos WHERE consulta_id=%s", (cid,)):
        flash('Esta consulta já possui pagamento.', 'warning')
        return redirect(url_for('consultas_detalhes', cid=cid))
    if request.method == 'POST':
        f = request.form
        forma     = f.get('forma_pagamento', '')
        bandeira  = f.get('bandeira_credito') or f.get('bandeira_debito') or ''
        parcelas  = int(f.get('parcelas', 1)) if 'Crédito' in forma else 1
        chave_pix = f.get('chave_pix', '') if forma == 'PIX' else ''
        exe(
            "INSERT INTO pagamentos "
            "(consulta_id,valor,data_pagamento,forma_pagamento,convenio,status,"
            " parcelas,bandeira,chave_pix) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (cid, f['valor'], f['data_pagamento'], forma, f.get('convenio', ''),
             f.get('status', 'pago'), parcelas, bandeira, chave_pix))
        flash('Pagamento registrado!', 'success')
        return redirect(url_for('consultas_detalhes', cid=cid))
    return render_template('faturamento/form.html', consulta=consulta)


@app.route('/faturamento/recibo/<int:pgid>')
@login_required
def faturamento_recibo(pgid):
    pg = _get_pagamento_completo(pgid)
    if not pg:
        flash('Recibo não encontrado.', 'danger')
        return redirect(url_for('faturamento_lista'))
    return render_template('faturamento/recibo.html', pg=pg)


@app.route('/faturamento/nota_fiscal/<int:pgid>')
@login_required
def faturamento_nota_fiscal(pgid):
    pg = _get_pagamento_completo(pgid)
    if not pg:
        flash('Pagamento não encontrado.', 'danger')
        return redirect(url_for('faturamento_lista'))
    if not pg.get('numero_nf'):
        max_row = q1("SELECT COALESCE(MAX(numero_nf),0)+1 AS prox FROM pagamentos")
        now = datetime.now()
        exe("UPDATE pagamentos SET numero_nf=%s, nf_emitida=TRUE, nf_emitida_em=%s WHERE id=%s",
            (max_row['prox'], now, pgid))
        pg['numero_nf']     = max_row['prox']
        pg['nf_emitida']    = 1
        pg['nf_emitida_em'] = now
    return render_template('faturamento/nota_fiscal.html', pg=pg,
                           now=datetime.now().strftime('%d/%m/%Y %H:%M'))


def _get_pagamento_completo(pgid):
    return q1(
        "SELECT pg.*, c.tipo_procedimento, c.data_hora, "
        "p.nome AS paciente, p.cpf, p.endereco, "
        "d.nome AS dentista, d.cro, d.especialidade "
        "FROM pagamentos pg "
        "JOIN consultas c ON c.id=pg.consulta_id "
        "JOIN pacientes p ON p.id=c.paciente_id "
        "JOIN dentistas d ON d.id=c.dentista_id "
        "WHERE pg.id=%s", (pgid,))


# ---------------------------------------------------------------------------
# Relatórios
# ---------------------------------------------------------------------------

@app.route('/relatorios')
@login_required
def relatorios():
    por_status = q("SELECT status, COUNT(*) AS total FROM consultas "
                   "WHERE date_trunc('month', data_hora) = date_trunc('month', NOW()) "
                   "GROUP BY status")
    fat_mensal = q("SELECT TO_CHAR(data_pagamento,'YYYY-MM') AS mes, "
                   "SUM(valor) AS total, COUNT(*) AS qtd "
                   "FROM pagamentos "
                   "WHERE data_pagamento >= CURRENT_DATE - INTERVAL '6 months' "
                   "GROUP BY mes ORDER BY mes")
    top_proc = q("SELECT tipo_procedimento, COUNT(*) AS total "
                 "FROM consultas WHERE tipo_procedimento IS NOT NULL AND tipo_procedimento != '' "
                 "GROUP BY tipo_procedimento ORDER BY total DESC LIMIT 5")
    top_dentistas = q("SELECT d.nome, COUNT(*) AS total "
                      "FROM consultas c JOIN dentistas d ON d.id=c.dentista_id "
                      "GROUP BY d.nome ORDER BY total DESC LIMIT 5")
    novos_pac = q("SELECT TO_CHAR(criado_em,'YYYY-MM') AS mes, COUNT(*) AS total "
                  "FROM pacientes "
                  "WHERE criado_em >= NOW() - INTERVAL '6 months' "
                  "GROUP BY mes ORDER BY mes")
    return render_template('relatorios/index.html',
                           por_status=por_status, fat_mensal=fat_mensal,
                           top_proc=top_proc, top_dentistas=top_dentistas, novos_pac=novos_pac)


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

@app.route('/estoque')
@login_required
def estoque_lista():
    itens      = q("SELECT * FROM estoque ORDER BY categoria, produto")
    alertas    = q("SELECT * FROM estoque WHERE quantidade <= quantidade_minima ORDER BY produto")
    categorias = q("SELECT DISTINCT categoria FROM estoque ORDER BY categoria")
    return render_template('estoque/lista.html', itens=itens, alertas=alertas, categorias=categorias)


def _estoque_redirect():
    """Volta para a página de origem (dashboard ou estoque) de forma segura."""
    nxt = request.form.get('next', '')
    if nxt == 'dashboard':
        return redirect(url_for('dashboard'))
    return redirect(url_for('estoque_lista'))


@app.route('/estoque/novo', methods=['POST'])
@admin_required
def estoque_novo():
    exe("INSERT INTO estoque (produto, categoria, quantidade, quantidade_minima, unidade) VALUES (%s,%s,%s,%s,%s)",
        (request.form['produto'].strip(),
         request.form.get('categoria', 'Geral').strip(),
         int(request.form.get('quantidade', 0)),
         int(request.form.get('quantidade_minima', 1)),
         request.form.get('unidade', 'unidade').strip()))
    flash(f'Produto "{request.form["produto"]}" cadastrado no estoque.', 'success')
    return _estoque_redirect()


@app.route('/estoque/<int:eid>/editar', methods=['POST'])
@admin_required
def estoque_editar(eid):
    exe("UPDATE estoque SET produto=%s, categoria=%s, quantidade=%s, quantidade_minima=%s, unidade=%s WHERE id=%s",
        (request.form['produto'].strip(),
         request.form.get('categoria', 'Geral').strip(),
         int(request.form.get('quantidade', 0)),
         int(request.form.get('quantidade_minima', 1)),
         request.form.get('unidade', 'unidade').strip(),
         eid))
    flash('Produto atualizado.', 'success')
    return _estoque_redirect()


@app.route('/estoque/<int:eid>/movimentar', methods=['POST'])
@login_required
def estoque_movimentar(eid):
    tipo = request.form.get('tipo')
    qtd  = int(request.form.get('quantidade', 0))
    if tipo == 'entrada':
        exe("UPDATE estoque SET quantidade = quantidade + %s WHERE id=%s", (qtd, eid))
        flash(f'+{qtd} unidades adicionadas.', 'success')
    elif tipo == 'saida':
        item = q1("SELECT quantidade FROM estoque WHERE id=%s", (eid,))
        if item and item['quantidade'] >= qtd:
            exe("UPDATE estoque SET quantidade = quantidade - %s WHERE id=%s", (qtd, eid))
            flash(f'-{qtd} unidades retiradas.', 'success')
        else:
            flash('Quantidade insuficiente em estoque.', 'danger')
    return _estoque_redirect()


@app.route('/estoque/<int:eid>/excluir', methods=['POST'])
@admin_required
def estoque_excluir(eid):
    item = q1("SELECT produto FROM estoque WHERE id=%s", (eid,))
    if item:
        exe("DELETE FROM estoque WHERE id=%s", (eid,))
        flash(f'Produto "{item["produto"]}" removido do estoque.', 'success')
    return _estoque_redirect()


# ---------------------------------------------------------------------------
# Dentistas
# ---------------------------------------------------------------------------

@app.route('/dentistas')
@login_required
def dentistas_lista():
    rows = q(
        "SELECT d.*, "
        "  COUNT(c.id) AS total_consultas, "
        "  COUNT(c.id) FILTER (WHERE c.status='concluida') AS consultas_concluidas, "
        "  COUNT(c.id) FILTER (WHERE c.status='agendada')  AS consultas_agendadas "
        "FROM dentistas d "
        "LEFT JOIN consultas c ON c.dentista_id=d.id "
        "GROUP BY d.id ORDER BY d.ativo DESC, d.nome"
    )
    return render_template('dentistas/lista.html', dentistas=rows)


@app.route('/dentistas/novo', methods=['GET', 'POST'])
@admin_required
def dentistas_novo():
    if request.method == 'POST':
        f = request.form
        exe("INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
            (f['nome'], f['cro'], f['especialidade'], f['telefone'], f['email']))
        flash('Dentista cadastrado!', 'success')
        return redirect(url_for('dentistas_lista'))
    return render_template('dentistas/form.html', dentista=None)


@app.route('/dentistas/<int:did>/editar', methods=['GET', 'POST'])
@admin_required
def dentistas_editar(did):
    dentista = q1("SELECT * FROM dentistas WHERE id=%s", (did,))
    if not dentista:
        flash('Dentista não encontrado.', 'danger')
        return redirect(url_for('dentistas_lista'))
    if request.method == 'POST':
        f = request.form
        exe("UPDATE dentistas SET nome=%s,cro=%s,especialidade=%s,telefone=%s,email=%s WHERE id=%s",
            (f['nome'], f['cro'], f['especialidade'], f['telefone'], f['email'], did))
        flash('Dentista atualizado!', 'success')
        return redirect(url_for('dentistas_lista'))
    return render_template('dentistas/form.html', dentista=dentista)


@app.route('/dentistas/<int:did>/excluir', methods=['POST'])
@admin_required
def dentistas_excluir(did):
    dentista = q1("SELECT nome FROM dentistas WHERE id=%s", (did,))
    if not dentista:
        flash('Dentista não encontrado.', 'danger')
        return redirect(url_for('dentistas_lista'))
    consultas = q1("SELECT COUNT(*) AS n FROM consultas WHERE dentista_id=%s", (did,))
    if consultas and consultas['n'] > 0:
        flash(f'Não é possível excluir {dentista["nome"]} — possui {consultas["n"]} consulta(s) vinculada(s). '
              f'Desative-o ao invés de excluir.', 'warning')
        return redirect(url_for('dentistas_lista'))
    exe("DELETE FROM dentistas WHERE id=%s", (did,))
    flash(f'Dentista {dentista["nome"]} excluído.', 'info')
    return redirect(url_for('dentistas_lista'))


@app.route('/dentistas/<int:did>/toggle', methods=['POST'])
@login_required
def dentistas_toggle(did):
    dentista = q1("SELECT nome, ativo FROM dentistas WHERE id=%s", (did,))
    if not dentista:
        flash('Dentista não encontrado.', 'danger')
        return redirect(url_for('dentistas_lista'))
    novo = not dentista['ativo']
    exe("UPDATE dentistas SET ativo=%s WHERE id=%s", (novo, did))
    flash(f'{dentista["nome"]} {"ativado" if novo else "desativado"}.', 'success')
    return redirect(url_for('dentistas_lista'))


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
