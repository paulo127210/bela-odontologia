-- ============================================================
--  BELA ODONTOLOGIA — Schema MySQL
--  Compatível com migração para Supabase (PostgreSQL)
-- ============================================================

CREATE DATABASE IF NOT EXISTS bela_odontologia
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE bela_odontologia;

-- ----------------------------------------------------------
--  USUÁRIOS DO SISTEMA
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS usuarios (
    id        INT          NOT NULL AUTO_INCREMENT,
    nome      VARCHAR(120) NOT NULL,
    email     VARCHAR(120) NOT NULL UNIQUE,
    senha     VARCHAR(255) NOT NULL,
    perfil    VARCHAR(30)  NOT NULL DEFAULT 'recepcionista',
    ativo     TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
--  DENTISTAS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS dentistas (
    id            INT          NOT NULL AUTO_INCREMENT,
    nome          VARCHAR(120) NOT NULL,
    cro           VARCHAR(30),
    especialidade VARCHAR(80),
    telefone      VARCHAR(20),
    email         VARCHAR(120),
    ativo         TINYINT(1)   NOT NULL DEFAULT 1,
    criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
--  PACIENTES
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pacientes (
    id               INT          NOT NULL AUTO_INCREMENT,
    nome             VARCHAR(120) NOT NULL,
    data_nascimento  DATE,
    cpf              VARCHAR(14),
    endereco         VARCHAR(200),
    telefone         VARCHAR(20),
    email            VARCHAR(120),
    convenio         VARCHAR(80),
    historico_medico TEXT,
    criado_em        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_nome   (nome),
    INDEX idx_cpf    (cpf)
) ENGINE=InnoDB;

-- ----------------------------------------------------------
--  CONSULTAS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS consultas (
    id                INT          NOT NULL AUTO_INCREMENT,
    paciente_id       INT          NOT NULL,
    dentista_id       INT          NOT NULL,
    data_hora         DATETIME     NOT NULL,
    tipo_procedimento VARCHAR(100),
    status            VARCHAR(20)  NOT NULL DEFAULT 'agendada',
    observacoes       TEXT,
    criado_em         DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_data    (data_hora),
    INDEX idx_status  (status),
    CONSTRAINT fk_cons_paciente FOREIGN KEY (paciente_id)
        REFERENCES pacientes (id) ON DELETE RESTRICT,
    CONSTRAINT fk_cons_dentista FOREIGN KEY (dentista_id)
        REFERENCES dentistas (id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ----------------------------------------------------------
--  PRONTUÁRIOS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS prontuarios (
    id          INT      NOT NULL AUTO_INCREMENT,
    consulta_id INT      NOT NULL UNIQUE,
    anotacoes   TEXT,
    prescricao  TEXT,
    criado_em   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                           ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_pront_consulta FOREIGN KEY (consulta_id)
        REFERENCES consultas (id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ----------------------------------------------------------
--  PAGAMENTOS
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS pagamentos (
    id              INT           NOT NULL AUTO_INCREMENT,
    consulta_id     INT           NOT NULL UNIQUE,
    valor           DECIMAL(10,2) NOT NULL,
    data_pagamento  DATE          NOT NULL,
    forma_pagamento VARCHAR(50),
    convenio        VARCHAR(80),
    status          VARCHAR(20)   NOT NULL DEFAULT 'pago',
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_data_pag (data_pagamento),
    CONSTRAINT fk_pag_consulta FOREIGN KEY (consulta_id)
        REFERENCES consultas (id) ON DELETE RESTRICT
) ENGINE=InnoDB;
