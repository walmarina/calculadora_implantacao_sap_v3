-- =====================================================================
-- Calculadora de Estimativa de Horas de Implantação de ERP
-- Schema SQLite usado pela prova de conceito (arquivo data/calculadora.db)
--
-- O modelo é o mesmo especificado para o MySQL 8.0 (pasta sql/mysql).
-- O SQLite é usado apenas na prova de conceito publicada no Streamlit
-- Cloud, que não oferece servidor MySQL no plano gratuito.
--
-- Camada 1  Operacional (OLTP)  tabelas normalizadas de projetos
-- Camada 2  Data Warehouse      esquema estrela com duas tabelas fato
--                               (constelação de fatos) e dimensões
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- CAMADA OPERACIONAL (OLTP)
-- ---------------------------------------------------------------------

CREATE TABLE tipo_ambiente (
    id_tipo_ambiente   INTEGER PRIMARY KEY,
    descricao          TEXT    NOT NULL UNIQUE
);

CREATE TABLE modalidade (
    id_modalidade      INTEGER PRIMARY KEY,
    descricao          TEXT    NOT NULL UNIQUE
);

CREATE TABLE faixa_volume_notas (
    id_faixa           INTEGER PRIMARY KEY,
    descricao          TEXT    NOT NULL UNIQUE,
    limite_inferior    INTEGER NOT NULL,
    limite_superior    INTEGER            -- NULL = sem limite superior
);

CREATE TABLE fase_aip (
    id_fase            INTEGER PRIMARY KEY,
    nome               TEXT    NOT NULL UNIQUE,
    ordem              INTEGER NOT NULL UNIQUE,
    percentual_horas   REAL    NOT NULL CHECK (percentual_horas > 0 AND percentual_horas <= 1)
);

CREATE TABLE projeto (
    id_projeto                 TEXT    PRIMARY KEY,
    data_proposta              TEXT    NOT NULL,
    numero_usuarios            INTEGER NOT NULL CHECK (numero_usuarios > 0),
    numero_filiais             INTEGER NOT NULL CHECK (numero_filiais > 0),
    id_tipo_ambiente           INTEGER NOT NULL REFERENCES tipo_ambiente (id_tipo_ambiente),
    id_modalidade              INTEGER NOT NULL REFERENCES modalidade (id_modalidade),
    usa_van_bancaria           INTEGER NOT NULL CHECK (usa_van_bancaria IN (0, 1)),
    qtd_addons                 INTEGER NOT NULL CHECK (qtd_addons >= 0),
    plano_contas_customizado   INTEGER NOT NULL CHECK (plano_contas_customizado IN (0, 1)),
    qtd_modulos                INTEGER NOT NULL CHECK (qtd_modulos > 0),
    complexidade_importacao    INTEGER NOT NULL CHECK (complexidade_importacao BETWEEN 1 AND 10),
    notas_mensal               INTEGER NOT NULL CHECK (notas_mensal >= 0),
    id_faixa                   INTEGER NOT NULL REFERENCES faixa_volume_notas (id_faixa),
    horas_totais_implantacao   REAL    NOT NULL CHECK (horas_totais_implantacao > 0)
);

CREATE INDEX idx_projeto_ambiente   ON projeto (id_tipo_ambiente);
CREATE INDEX idx_projeto_modalidade ON projeto (id_modalidade);
CREATE INDEX idx_projeto_data       ON projeto (data_proposta);

-- ---------------------------------------------------------------------
-- DATA WAREHOUSE (esquema estrela)
-- ---------------------------------------------------------------------

CREATE TABLE dw_dim_tempo (
    sk_tempo     INTEGER PRIMARY KEY,      -- formato AAAAMMDD
    data         TEXT    NOT NULL UNIQUE,
    ano          INTEGER NOT NULL,
    semestre     INTEGER NOT NULL,
    trimestre    INTEGER NOT NULL,
    mes          INTEGER NOT NULL,
    nome_mes     TEXT    NOT NULL
);

CREATE TABLE dw_dim_ambiente (
    sk_ambiente     INTEGER PRIMARY KEY,
    tipo_ambiente   TEXT    NOT NULL UNIQUE
);

CREATE TABLE dw_dim_modalidade (
    sk_modalidade   INTEGER PRIMARY KEY,
    modalidade      TEXT    NOT NULL UNIQUE
);

CREATE TABLE dw_dim_porte (
    sk_porte         INTEGER PRIMARY KEY,
    porte            TEXT    NOT NULL UNIQUE,
    usuarios_min     INTEGER NOT NULL,
    usuarios_max     INTEGER                -- NULL = sem limite superior
);

CREATE TABLE dw_dim_faixa_notas (
    sk_faixa_notas   INTEGER PRIMARY KEY,
    faixa            TEXT    NOT NULL UNIQUE,
    ordem            INTEGER NOT NULL
);

-- Junk dimension (Kimball): reúne os indicadores Sim/Não do handover
CREATE TABLE dw_dim_indicadores (
    sk_indicadores             INTEGER PRIMARY KEY,
    usa_van_bancaria           TEXT    NOT NULL,
    plano_contas_customizado   TEXT    NOT NULL,
    UNIQUE (usa_van_bancaria, plano_contas_customizado)
);

CREATE TABLE dw_dim_fase (
    sk_fase            INTEGER PRIMARY KEY,
    fase               TEXT    NOT NULL UNIQUE,
    ordem              INTEGER NOT NULL,
    percentual_horas   REAL    NOT NULL
);

-- Fato 1  grão = um projeto de implantação
CREATE TABLE dw_fato_projeto (
    id_projeto                 TEXT    PRIMARY KEY,   -- dimensão degenerada
    sk_tempo                   INTEGER NOT NULL REFERENCES dw_dim_tempo (sk_tempo),
    sk_ambiente                INTEGER NOT NULL REFERENCES dw_dim_ambiente (sk_ambiente),
    sk_modalidade              INTEGER NOT NULL REFERENCES dw_dim_modalidade (sk_modalidade),
    sk_porte                   INTEGER NOT NULL REFERENCES dw_dim_porte (sk_porte),
    sk_faixa_notas             INTEGER NOT NULL REFERENCES dw_dim_faixa_notas (sk_faixa_notas),
    sk_indicadores             INTEGER NOT NULL REFERENCES dw_dim_indicadores (sk_indicadores),
    numero_usuarios            INTEGER NOT NULL,
    numero_filiais             INTEGER NOT NULL,
    qtd_addons                 INTEGER NOT NULL,
    qtd_modulos                INTEGER NOT NULL,
    complexidade_importacao    INTEGER NOT NULL,
    notas_mensal               INTEGER NOT NULL,
    horas_totais_implantacao   REAL    NOT NULL       -- medida aditiva
);

-- Fato 2  grão = um projeto em uma fase da metodologia SAP AIP
CREATE TABLE dw_fato_horas_fase (
    id_projeto      TEXT    NOT NULL,
    sk_fase         INTEGER NOT NULL REFERENCES dw_dim_fase (sk_fase),
    sk_tempo        INTEGER NOT NULL REFERENCES dw_dim_tempo (sk_tempo),
    sk_ambiente     INTEGER NOT NULL REFERENCES dw_dim_ambiente (sk_ambiente),
    sk_modalidade   INTEGER NOT NULL REFERENCES dw_dim_modalidade (sk_modalidade),
    sk_porte        INTEGER NOT NULL REFERENCES dw_dim_porte (sk_porte),
    horas_fase      REAL    NOT NULL,                 -- medida aditiva
    PRIMARY KEY (id_projeto, sk_fase)
);

CREATE INDEX idx_fato_projeto_tempo      ON dw_fato_projeto (sk_tempo);
CREATE INDEX idx_fato_projeto_ambiente   ON dw_fato_projeto (sk_ambiente);
CREATE INDEX idx_fato_projeto_modalidade ON dw_fato_projeto (sk_modalidade);
CREATE INDEX idx_fato_projeto_porte      ON dw_fato_projeto (sk_porte);
CREATE INDEX idx_fato_fase_fase          ON dw_fato_horas_fase (sk_fase);

-- ---------------------------------------------------------------------
-- VIEWS consumidas pelo dashboard e pelo modelo
-- ---------------------------------------------------------------------

-- Visão analítica completa de cada projeto (fato + dimensões)
CREATE VIEW vw_projetos_analitico AS
SELECT
    f.id_projeto,
    t.data            AS data_proposta,
    t.ano,
    t.trimestre,
    a.tipo_ambiente,
    m.modalidade,
    p.porte,
    fn.faixa          AS volume_notas_mensal,
    i.usa_van_bancaria,
    i.plano_contas_customizado,
    f.numero_usuarios,
    f.numero_filiais,
    f.qtd_addons,
    f.qtd_modulos,
    f.complexidade_importacao,
    f.notas_mensal,
    f.horas_totais_implantacao
FROM dw_fato_projeto f
JOIN dw_dim_tempo       t  ON t.sk_tempo        = f.sk_tempo
JOIN dw_dim_ambiente    a  ON a.sk_ambiente     = f.sk_ambiente
JOIN dw_dim_modalidade  m  ON m.sk_modalidade   = f.sk_modalidade
JOIN dw_dim_porte       p  ON p.sk_porte        = f.sk_porte
JOIN dw_dim_faixa_notas fn ON fn.sk_faixa_notas = f.sk_faixa_notas
JOIN dw_dim_indicadores i  ON i.sk_indicadores  = f.sk_indicadores;

-- Horas por fase da metodologia SAP AIP (drill-down do total por fase)
CREATE VIEW vw_horas_por_fase AS
SELECT
    hf.id_projeto,
    d.fase,
    d.ordem,
    a.tipo_ambiente,
    m.modalidade,
    p.porte,
    hf.horas_fase
FROM dw_fato_horas_fase hf
JOIN dw_dim_fase        d ON d.sk_fase       = hf.sk_fase
JOIN dw_dim_ambiente    a ON a.sk_ambiente   = hf.sk_ambiente
JOIN dw_dim_modalidade  m ON m.sk_modalidade = hf.sk_modalidade
JOIN dw_dim_porte       p ON p.sk_porte      = hf.sk_porte;
