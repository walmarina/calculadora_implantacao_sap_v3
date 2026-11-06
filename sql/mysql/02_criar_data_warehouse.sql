-- =====================================================================
-- 02  Data Warehouse (esquema estrela)  MySQL 8.0
-- Duas tabelas fato que compartilham dimensões (constelação de fatos)
--   dw_fato_projeto     grão = um projeto de implantação
--   dw_fato_horas_fase  grão = um projeto em uma fase da SAP AIP
-- =====================================================================

CREATE DATABASE IF NOT EXISTS calculadora_dw
    DEFAULT CHARACTER SET utf8mb4
    DEFAULT COLLATE utf8mb4_0900_ai_ci;

USE calculadora_dw;

CREATE TABLE dw_dim_tempo (
    sk_tempo     INT UNSIGNED     NOT NULL,   -- formato AAAAMMDD
    data         DATE             NOT NULL,
    ano          SMALLINT         NOT NULL,
    semestre     TINYINT          NOT NULL,
    trimestre    TINYINT          NOT NULL,
    mes          TINYINT          NOT NULL,
    nome_mes     VARCHAR(15)      NOT NULL,
    CONSTRAINT pk_dim_tempo PRIMARY KEY (sk_tempo),
    CONSTRAINT uq_dim_tempo_data UNIQUE (data)
) ENGINE = InnoDB;

CREATE TABLE dw_dim_ambiente (
    sk_ambiente     TINYINT UNSIGNED NOT NULL,
    tipo_ambiente   VARCHAR(30)      NOT NULL,
    CONSTRAINT pk_dim_ambiente PRIMARY KEY (sk_ambiente)
) ENGINE = InnoDB;

CREATE TABLE dw_dim_modalidade (
    sk_modalidade   TINYINT UNSIGNED NOT NULL,
    modalidade      VARCHAR(30)      NOT NULL,
    CONSTRAINT pk_dim_modalidade PRIMARY KEY (sk_modalidade)
) ENGINE = InnoDB;

CREATE TABLE dw_dim_porte (
    sk_porte        TINYINT UNSIGNED  NOT NULL,
    porte           VARCHAR(40)       NOT NULL,
    usuarios_min    SMALLINT UNSIGNED NOT NULL,
    usuarios_max    SMALLINT UNSIGNED NULL,
    CONSTRAINT pk_dim_porte PRIMARY KEY (sk_porte)
) ENGINE = InnoDB;

CREATE TABLE dw_dim_faixa_notas (
    sk_faixa_notas  TINYINT UNSIGNED NOT NULL,
    faixa           VARCHAR(30)      NOT NULL,
    ordem           TINYINT UNSIGNED NOT NULL,
    CONSTRAINT pk_dim_faixa_notas PRIMARY KEY (sk_faixa_notas)
) ENGINE = InnoDB;

-- Junk dimension: indicadores Sim/Não do handover
CREATE TABLE dw_dim_indicadores (
    sk_indicadores             TINYINT UNSIGNED NOT NULL,
    usa_van_bancaria           VARCHAR(3)       NOT NULL,
    plano_contas_customizado   VARCHAR(3)       NOT NULL,
    CONSTRAINT pk_dim_indicadores PRIMARY KEY (sk_indicadores)
) ENGINE = InnoDB;

CREATE TABLE dw_dim_fase (
    sk_fase            TINYINT UNSIGNED NOT NULL,
    fase               VARCHAR(40)      NOT NULL,
    ordem              TINYINT UNSIGNED NOT NULL,
    percentual_horas   DECIMAL(4,2)     NOT NULL,
    CONSTRAINT pk_dim_fase PRIMARY KEY (sk_fase)
) ENGINE = InnoDB;

CREATE TABLE dw_fato_projeto (
    id_projeto                 VARCHAR(10)       NOT NULL,   -- dimensão degenerada
    sk_tempo                   INT UNSIGNED      NOT NULL,
    sk_ambiente                TINYINT UNSIGNED  NOT NULL,
    sk_modalidade              TINYINT UNSIGNED  NOT NULL,
    sk_porte                   TINYINT UNSIGNED  NOT NULL,
    sk_faixa_notas             TINYINT UNSIGNED  NOT NULL,
    sk_indicadores             TINYINT UNSIGNED  NOT NULL,
    numero_usuarios            SMALLINT UNSIGNED NOT NULL,
    numero_filiais             SMALLINT UNSIGNED NOT NULL,
    qtd_addons                 TINYINT UNSIGNED  NOT NULL,
    qtd_modulos                TINYINT UNSIGNED  NOT NULL,
    complexidade_importacao    TINYINT UNSIGNED  NOT NULL,
    notas_mensal               INT UNSIGNED      NOT NULL,
    horas_totais_implantacao   DECIMAL(7,1)      NOT NULL,   -- medida aditiva
    CONSTRAINT pk_fato_projeto PRIMARY KEY (id_projeto),
    CONSTRAINT fk_fp_tempo       FOREIGN KEY (sk_tempo)       REFERENCES dw_dim_tempo (sk_tempo),
    CONSTRAINT fk_fp_ambiente    FOREIGN KEY (sk_ambiente)    REFERENCES dw_dim_ambiente (sk_ambiente),
    CONSTRAINT fk_fp_modalidade  FOREIGN KEY (sk_modalidade)  REFERENCES dw_dim_modalidade (sk_modalidade),
    CONSTRAINT fk_fp_porte       FOREIGN KEY (sk_porte)       REFERENCES dw_dim_porte (sk_porte),
    CONSTRAINT fk_fp_faixa_notas FOREIGN KEY (sk_faixa_notas) REFERENCES dw_dim_faixa_notas (sk_faixa_notas),
    CONSTRAINT fk_fp_indicadores FOREIGN KEY (sk_indicadores) REFERENCES dw_dim_indicadores (sk_indicadores)
) ENGINE = InnoDB;

CREATE TABLE dw_fato_horas_fase (
    id_projeto      VARCHAR(10)      NOT NULL,
    sk_fase         TINYINT UNSIGNED NOT NULL,
    sk_tempo        INT UNSIGNED     NOT NULL,
    sk_ambiente     TINYINT UNSIGNED NOT NULL,
    sk_modalidade   TINYINT UNSIGNED NOT NULL,
    sk_porte        TINYINT UNSIGNED NOT NULL,
    horas_fase      DECIMAL(7,2)     NOT NULL,                -- medida aditiva
    CONSTRAINT pk_fato_horas_fase PRIMARY KEY (id_projeto, sk_fase),
    CONSTRAINT fk_fhf_fase       FOREIGN KEY (sk_fase)       REFERENCES dw_dim_fase (sk_fase),
    CONSTRAINT fk_fhf_tempo      FOREIGN KEY (sk_tempo)      REFERENCES dw_dim_tempo (sk_tempo),
    CONSTRAINT fk_fhf_ambiente   FOREIGN KEY (sk_ambiente)   REFERENCES dw_dim_ambiente (sk_ambiente),
    CONSTRAINT fk_fhf_modalidade FOREIGN KEY (sk_modalidade) REFERENCES dw_dim_modalidade (sk_modalidade),
    CONSTRAINT fk_fhf_porte      FOREIGN KEY (sk_porte)      REFERENCES dw_dim_porte (sk_porte)
) ENGINE = InnoDB;
