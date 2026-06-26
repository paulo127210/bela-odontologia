"""
Bela Odontologia — Aplicação Flask com MySQL
"""
import os
from datetime import datetime
from flask import (Flask, render_template, request, redirect,
                   url_for, session, flash, g)
from werkzeug.security import check_password_hash
from functools import wraps
from dotenv import load_dotenv
from database import get_db, init_db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))


@app.template_filter('dt')
def fmt_dt(value, fmt='%d/%m/%Y %H:%M'):
    """Formata datetime/date/str para exibição."""
    if value is None:
        return '—'
    if hasattr(value, 'strftime'):
        return value.strftime(fmt)
    return str(value)[:16]


@app.template_filter('dt_input')
def fmt_dt_input(value):
    """Formata datetime para uso em <input type='datetime-local'>."""
    if value is None:
        return ''
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%dT%H:%M')
    return str(value)[:16]


@app.template_filter('brl')
def fmt_brl(value):
    """Formata número como moeda BRL."""
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return 'R$ 0,00'


# ---------------------------------------------------------------------------
# Helpers de conexão
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def db():
    """Retorna a conexão MySQL do request atual (abre uma vez por request)."""
    if 'mysql_conn' not in g:
        g.mysql_conn = get_db()
    return g.mysql_conn


def q(sql, params=()):
    """Executa SELECT e retorna lista de dicts."""
    with db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def q1(sql, params=()):
    """Executa SELECT e retorna primeira linha (dict) ou None."""
    with db().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def exe(sql, params=()):
    """Executa INSERT/UPDATE/DELETE e retorna lastrowid."""
    with db().cursor() as cur:
        cur.execute(sql, params)
    db().commit()
    with db().cursor() as cur:
        cur.execute("SELECT LAST_INSERT_ID() AS lid")
        return cur.fetchone()['lid']


@app.teardown_appcontext
def close_db(e=None):
    conn = g.pop('mysql_conn', None)
    if conn:
        conn.close()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'usuario_id' in session:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        row = q1("SELECT * FROM usuarios WHERE email=%s AND ativo=1",
                 (request.form['email'].strip(),))
        if row and check_password_hash(row['senha'], request.form['senha']):
            session['usuario_id']     = row['id']
            session['usuario_nome']   = row['nome']
            session['usuario_perfil'] = row['perfil']
            return redirect(url_for('dashboard'))
        error = "E-mail ou senha incorretos."
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route('/dashboard')
@login_required
def dashboard():
    total_pacientes = q1("SELECT COUNT(*) AS n FROM pacientes")['n']
    total_hoje      = q1("SELECT COUNT(*) AS n FROM consultas WHERE DATE(data_hora)=CURDATE()")['n']
    total_mes       = q1("SELECT COUNT(*) AS n FROM consultas WHERE YEAR(data_hora)=YEAR(NOW()) AND MONTH(data_hora)=MONTH(NOW())")['n']
    fat_mes_row     = q1("SELECT COALESCE(SUM(valor),0) AS s FROM pagamentos WHERE YEAR(data_pagamento)=YEAR(NOW()) AND MONTH(data_pagamento)=MONTH(NOW())")
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
    return render_template('dashboard.html',
                           total_pacientes=total_pacientes,
                           total_hoje=total_hoje,
                           total_mes=total_mes,
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
        rows = q("SELECT * FROM pacientes WHERE nome LIKE %s OR cpf LIKE %s OR telefone LIKE %s ORDER BY nome",
                 (like, like, like))
    else:
        rows = q("SELECT * FROM pacientes ORDER BY nome")
    return render_template('pacientes/lista.html', pacientes=rows, q=busca)


@app.route('/pacientes/novo', methods=['GET', 'POST'])
@login_required
def pacientes_novo():
    if request.method == 'POST':
        f = request.form
        exe("INSERT INTO pacientes (nome,data_nascimento,cpf,endereco,telefone,email,convenio,historico_medico) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (f['nome'], f['data_nascimento'] or None, f['cpf'],
             f['endereco'], f['telefone'], f['email'],
             f['convenio'], f['historico_medico']))
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
        exe("UPDATE pacientes SET nome=%s,data_nascimento=%s,cpf=%s,endereco=%s,"
            "telefone=%s,email=%s,convenio=%s,historico_medico=%s WHERE id=%s",
            (f['nome'], f['data_nascimento'] or None, f['cpf'],
             f['endereco'], f['telefone'], f['email'],
             f['convenio'], f['historico_medico'], pid))
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
        sql += " AND DATE(c.data_hora)=%s"; params.append(data_f)
    sql += " ORDER BY c.data_hora DESC"
    rows = q(sql, params)
    return render_template('consultas/lista.html',
                           consultas=rows,
                           status_filtro=status_f,
                           data_filtro=data_f)


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
    pid = request.args.get('paciente_id', '')
    return render_template('consultas/form.html',
                           consulta=None, pacientes=pacientes,
                           dentistas=dentistas, pre_paciente=pid)


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
                           consulta=c, pacientes=pacientes,
                           dentistas=dentistas, pre_paciente='')


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
    mes    = request.args.get('mes', '')
    status = request.args.get('status', '')
    forma  = request.args.get('forma', '')
    sql = ("SELECT pg.*, c.tipo_procedimento, p.nome AS paciente "
           "FROM pagamentos pg "
           "JOIN consultas c ON c.id=pg.consulta_id "
           "JOIN pacientes p ON p.id=c.paciente_id WHERE 1=1 ")
    params = []
    if mes:
        sql += " AND DATE_FORMAT(pg.data_pagamento,'%%Y-%%m')=%s"; params.append(mes)
    if status:
        sql += " AND pg.status=%s"; params.append(status)
    if forma:
        sql += " AND pg.forma_pagamento=%s"; params.append(forma)
    sql += " ORDER BY pg.data_pagamento DESC"
    rows = q(sql, params)
    total = sum(float(r['valor']) for r in rows)
    return render_template('faturamento/lista.html',
                           pagamentos=rows, total=total, mes=mes, status=status, forma=forma)


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
        forma = f.get('forma_pagamento', '')
        # Campos específicos por método
        bandeira  = f.get('bandeira_credito') or f.get('bandeira_debito') or ''
        parcelas  = int(f.get('parcelas', 1)) if 'Crédito' in forma else 1
        chave_pix = f.get('chave_pix', '') if forma == 'PIX' else ''
        convenio  = f.get('convenio', '')
        exe(
            "INSERT INTO pagamentos "
            "(consulta_id,valor,data_pagamento,forma_pagamento,convenio,status,"
            " parcelas,bandeira,chave_pix) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (cid, f['valor'], f['data_pagamento'], forma, convenio,
             f.get('status','pago'), parcelas, bandeira, chave_pix))
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
    from datetime import datetime as _dt
    pg = _get_pagamento_completo(pgid)
    if not pg:
        flash('Pagamento não encontrado.', 'danger')
        return redirect(url_for('faturamento_lista'))
    # Gera número de NF se ainda não tem
    if not pg.get('numero_nf'):
        max_row = q1("SELECT COALESCE(MAX(numero_nf),0)+1 AS prox FROM pagamentos")
        prox_nf = max_row['prox']
        now = _dt.now()
        exe("UPDATE pagamentos SET numero_nf=%s, nf_emitida=1, nf_emitida_em=%s WHERE id=%s",
            (prox_nf, now, pgid))
        pg['numero_nf']     = prox_nf
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
                   "WHERE YEAR(data_hora)=YEAR(NOW()) AND MONTH(data_hora)=MONTH(NOW()) "
                   "GROUP BY status")

    fat_mensal = q("SELECT DATE_FORMAT(data_pagamento,'%%Y-%%m') AS mes, "
                   "SUM(valor) AS total, COUNT(*) AS qtd "
                   "FROM pagamentos "
                   "WHERE data_pagamento >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH) "
                   "GROUP BY mes ORDER BY mes")

    top_proc = q("SELECT tipo_procedimento, COUNT(*) AS total "
                 "FROM consultas WHERE tipo_procedimento IS NOT NULL AND tipo_procedimento != '' "
                 "GROUP BY tipo_procedimento ORDER BY total DESC LIMIT 5")

    top_dentistas = q("SELECT d.nome, COUNT(*) AS total "
                      "FROM consultas c JOIN dentistas d ON d.id=c.dentista_id "
                      "GROUP BY d.nome ORDER BY total DESC LIMIT 5")

    novos_pac = q("SELECT DATE_FORMAT(criado_em,'%%Y-%%m') AS mes, COUNT(*) AS total "
                  "FROM pacientes "
                  "WHERE criado_em >= DATE_SUB(NOW(), INTERVAL 6 MONTH) "
                  "GROUP BY mes ORDER BY mes")

    return render_template('relatorios/index.html',
                           por_status=por_status,
                           fat_mensal=fat_mensal,
                           top_proc=top_proc,
                           top_dentistas=top_dentistas,
                           novos_pac=novos_pac)


# ---------------------------------------------------------------------------
# Dentistas
# ---------------------------------------------------------------------------

@app.route('/dentistas')
@login_required
def dentistas_lista():
    rows = q(
        "SELECT d.*, "
        "  COUNT(c.id)                                             AS total_consultas, "
        "  SUM(c.status='concluida')                              AS consultas_concluidas, "
        "  SUM(c.status='agendada')                               AS consultas_agendadas "
        "FROM dentistas d "
        "LEFT JOIN consultas c ON c.dentista_id=d.id "
        "GROUP BY d.id ORDER BY d.ativo DESC, d.nome"
    )
    return render_template('dentistas/lista.html', dentistas=rows)


@app.route('/dentistas/novo', methods=['GET', 'POST'])
@login_required
def dentistas_novo():
    if request.method == 'POST':
        f = request.form
        exe("INSERT INTO dentistas (nome,cro,especialidade,telefone,email) VALUES (%s,%s,%s,%s,%s)",
            (f['nome'], f['cro'], f['especialidade'], f['telefone'], f['email']))
        flash('Dentista cadastrado!', 'success')
        return redirect(url_for('dentistas_lista'))
    return render_template('dentistas/form.html', dentista=None)


@app.route('/dentistas/<int:did>/editar', methods=['GET', 'POST'])
@login_required
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
@login_required
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
    novo = 0 if dentista['ativo'] else 1
    exe("UPDATE dentistas SET ativo=%s WHERE id=%s", (novo, did))
    status = 'ativado' if novo else 'desativado'
    flash(f'{dentista["nome"]} {status}.', 'success')
    return redirect(url_for('dentistas_lista'))


# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
