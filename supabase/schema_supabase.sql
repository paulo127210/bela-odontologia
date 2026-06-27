-- ============================================================
--  BELA ODONTOLOGIA — Schema PostgreSQL (Supabase)
--  Cole este arquivo inteiro no Supabase SQL Editor e execute.
-- ============================================================

-- Usuários do sistema
CREATE TABLE IF NOT EXISTS usuarios (
    id        SERIAL       PRIMARY KEY,
    nome      VARCHAR(120) NOT NULL,
    email     VARCHAR(120) NOT NULL UNIQUE,
    senha     VARCHAR(255) NOT NULL,
    perfil    VARCHAR(30)  NOT NULL DEFAULT 'recepcionista',
    ativo     BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Dentistas
CREATE TABLE IF NOT EXISTS dentistas (
    id            SERIAL       PRIMARY KEY,
    nome          VARCHAR(120) NOT NULL,
    cro           VARCHAR(30),
    especialidade VARCHAR(80),
    telefone      VARCHAR(20),
    email         VARCHAR(120),
    ativo         BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Pacientes
CREATE TABLE IF NOT EXISTS pacientes (
    id               SERIAL       PRIMARY KEY,
    nome             VARCHAR(120) NOT NULL,
    data_nascimento  DATE,
    cpf              VARCHAR(14),
    endereco         VARCHAR(200),
    telefone         VARCHAR(20),
    email            VARCHAR(120),
    convenio         VARCHAR(80),
    historico_medico TEXT,
    criado_em        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    atualizado_em    TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Consultas
CREATE TABLE IF NOT EXISTS consultas (
    id                SERIAL      PRIMARY KEY,
    paciente_id       INTEGER     NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    dentista_id       INTEGER     NOT NULL REFERENCES dentistas(id) ON DELETE RESTRICT,
    data_hora         TIMESTAMPTZ NOT NULL,
    tipo_procedimento VARCHAR(100),
    status            VARCHAR(20) NOT NULL DEFAULT 'agendada',
    observacoes       TEXT,
    criado_em         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Prontuários
CREATE TABLE IF NOT EXISTS prontuarios (
    id            SERIAL      PRIMARY KEY,
    consulta_id   INTEGER     NOT NULL UNIQUE REFERENCES consultas(id) ON DELETE CASCADE,
    anotacoes     TEXT,
    prescricao    TEXT,
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Pagamentos
CREATE TABLE IF NOT EXISTS pagamentos (
    id              SERIAL        PRIMARY KEY,
    consulta_id     INTEGER       NOT NULL UNIQUE REFERENCES consultas(id) ON DELETE RESTRICT,
    valor           NUMERIC(10,2) NOT NULL,
    data_pagamento  DATE          NOT NULL,
    forma_pagamento VARCHAR(50),
    convenio        VARCHAR(80),
    status          VARCHAR(20)   NOT NULL DEFAULT 'pago',
    parcelas        SMALLINT      NOT NULL DEFAULT 1,
    bandeira        VARCHAR(30),
    chave_pix       VARCHAR(100),
    numero_nf       INTEGER,
    nf_emitida      SMALLINT      NOT NULL DEFAULT 0,
    nf_emitida_em   TIMESTAMPTZ,
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- Estoque
CREATE TABLE IF NOT EXISTS estoque (
    id                SERIAL       PRIMARY KEY,
    produto           VARCHAR(120) NOT NULL,
    categoria         VARCHAR(60)  NOT NULL DEFAULT 'Geral',
    quantidade        INTEGER      NOT NULL DEFAULT 0,
    quantidade_minima INTEGER      NOT NULL DEFAULT 1,
    unidade           VARCHAR(20)  NOT NULL DEFAULT 'unidade',
    criado_em         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_pacientes_nome  ON pacientes (nome);
CREATE INDEX IF NOT EXISTS idx_pacientes_cpf   ON pacientes (cpf);
CREATE INDEX IF NOT EXISTS idx_consultas_data  ON consultas (data_hora);
CREATE INDEX IF NOT EXISTS idx_consultas_status ON consultas (status);
CREATE INDEX IF NOT EXISTS idx_pagamentos_data ON pagamentos (data_pagamento);

-- Trigger: atualiza atualizado_em automaticamente (equivale ao ON UPDATE no MySQL)
CREATE OR REPLACE FUNCTION set_atualizado_em()
RETURNS TRIGGER AS $$
BEGIN
    NEW.atualizado_em = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER trg_pacientes_updated
    BEFORE UPDATE ON pacientes
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

CREATE OR REPLACE TRIGGER trg_consultas_updated
    BEFORE UPDATE ON consultas
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();

CREATE OR REPLACE TRIGGER trg_prontuarios_updated
    BEFORE UPDATE ON prontuarios
    FOR EACH ROW EXECUTE FUNCTION set_atualizado_em();
