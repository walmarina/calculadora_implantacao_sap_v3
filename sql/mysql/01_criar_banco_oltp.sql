-- =====================================================================
-- 01  Camada operacional (OLTP)  MySQL 8.0
-- Base de projetos de implantação registrados a partir do handover
-- técnico-comercial. Modelo normalizado, otimizado para gravação.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS calculadora_oltp
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE calculadora_oltp;

CREATE TABLE tipo_ambiente (
    id_tipo_ambiente   TINYINT UNSIGNED NOT NULL,
    descricao          VARCHAR(30)      NOT NULL,
    CONSTRAINT pk_tipo_ambiente PRIMARY KEY (id_tipo_ambiente),
    CONSTRAINT uq_tipo_ambiente_descricao UNIQUE (descricao)
) ENGINE = InnoDB;

CREATE TABLE modalidade (
    id_modalidade      TINYINT UNSIGNED NOT NULL,
    descricao          VARCHAR(30)      NOT NULL,
    CONSTRAINT pk_modalidade PRIMARY KEY (id_modalidade),
    CONSTRAINT uq_modalidade_descricao UNIQUE (descricao)
) ENGINE = InnoDB;

CREATE TABLE faixa_volume_notas (
    id_faixa           TINYINT UNSIGNED NOT NULL,
    descricao          VARCHAR(30)      NOT NULL,
    limite_inferior    INT UNSIGNED     NOT NULL,
    limite_superior    INT UNSIGNED     NULL,
    CONSTRAINT pk_faixa_volume_notas PRIMARY KEY (id_faixa),
    CONSTRAINT uq_faixa_descricao UNIQUE (descricao)
) ENGINE = InnoDB;

CREATE TABLE fase_aip (
    id_fase            TINYINT UNSIGNED NOT NULL,
    nome               VARCHAR(40)      NOT NULL,
    ordem              TINYINT UNSIGNED NOT NULL,
    percentual_horas   DECIMAL(4,2)     NOT NULL,
    CONSTRAINT pk_fase_aip PRIMARY KEY (id_fase),
    CONSTRAINT uq_fase_nome UNIQUE (nome),
    CONSTRAINT uq_fase_ordem UNIQUE (ordem),
    CONSTRAINT ck_fase_percentual CHECK (percentual_horas > 0 AND percentual_horas <= 1)
) ENGINE = InnoDB;

CREATE TABLE projeto (
    id_projeto                 VARCHAR(10)       NOT NULL,
    data_proposta              DATE              NOT NULL,
    numero_usuarios            SMALLINT UNSIGNED NOT NULL,
    numero_filiais             SMALLINT UNSIGNED NOT NULL,
    id_tipo_ambiente           TINYINT UNSIGNED  NOT NULL,
    id_modalidade              TINYINT UNSIGNED  NOT NULL,
    usa_van_bancaria           BOOLEAN           NOT NULL,
    qtd_addons                 TINYINT UNSIGNED  NOT NULL,
    plano_contas_customizado   BOOLEAN           NOT NULL,
    qtd_modulos                TINYINT UNSIGNED  NOT NULL,
    complexidade_importacao    TINYINT UNSIGNED  NOT NULL,
    notas_mensal               INT UNSIGNED      NOT NULL,
    id_faixa                   TINYINT UNSIGNED  NOT NULL,
    horas_totais_implantacao   DECIMAL(7,1)      NOT NULL,
    CONSTRAINT pk_projeto PRIMARY KEY (id_projeto),
    CONSTRAINT fk_projeto_ambiente   FOREIGN KEY (id_tipo_ambiente) REFERENCES tipo_ambiente (id_tipo_ambiente),
    CONSTRAINT fk_projeto_modalidade FOREIGN KEY (id_modalidade)    REFERENCES modalidade (id_modalidade),
    CONSTRAINT fk_projeto_faixa      FOREIGN KEY (id_faixa)         REFERENCES faixa_volume_notas (id_faixa),
    CONSTRAINT ck_projeto_usuarios     CHECK (numero_usuarios > 0),
    CONSTRAINT ck_projeto_filiais      CHECK (numero_filiais > 0),
    CONSTRAINT ck_projeto_modulos      CHECK (qtd_modulos BETWEEN 1 AND 6),
    CONSTRAINT ck_projeto_complexidade CHECK (complexidade_importacao BETWEEN 1 AND 10),
    CONSTRAINT ck_projeto_horas        CHECK (horas_totais_implantacao > 0)
) ENGINE = InnoDB;

-- Área de preparação (staging area) que recebe o arquivo do handover
-- antes da validação e da carga nas tabelas definitivas
CREATE TABLE stg_projetos (
    projeto_id                 VARCHAR(10),
    numero_usuarios            VARCHAR(10),
    numero_filiais             VARCHAR(10),
    tipo_ambiente              VARCHAR(30),
    modalidade                 VARCHAR(30),
    usa_van_bancaria           VARCHAR(5),
    qtd_addons                 VARCHAR(10),
    plano_contas_customizado   VARCHAR(5),
    qtd_modulos                VARCHAR(10),
    complexidade_importacao    VARCHAR(10),
    volume_notas_mensal        VARCHAR(30),
    notas_mensal_num           VARCHAR(10),
    horas_totais_implantacao   VARCHAR(10),
    data_proposta              VARCHAR(10)
) ENGINE = InnoDB;

-- Dados de domínio
INSERT INTO tipo_ambiente (id_tipo_ambiente, descricao) VALUES
    (1, 'Dedicado'), (2, 'Compartilhado');

INSERT INTO modalidade (id_modalidade, descricao) VALUES
    (1, 'Cloud'), (2, 'On Premise');

INSERT INTO faixa_volume_notas (id_faixa, descricao, limite_inferior, limite_superior) VALUES
    (1, 'Até 1.000',        0,     1000),
    (2, '1.001 a 4.000',    1001,  4000),
    (3, '4.001 a 8.000',    4001,  8000),
    (4, '8.001 a 15.000',   8001,  15000),
    (5, 'Acima de 15.000',  15001, NULL);

INSERT INTO fase_aip (id_fase, nome, ordem, percentual_horas) VALUES
    (1, 'Project Preparation', 1, 0.10),
    (2, 'Business Blueprint',  2, 0.20),
    (3, 'Project Realization', 3, 0.35),
    (4, 'Final Preparation',   4, 0.25),
    (5, 'Go-Live and Support', 5, 0.10);
