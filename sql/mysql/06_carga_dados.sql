-- =====================================================================
-- 06  Carga de dados  MySQL 8.0
-- Importação do arquivo exportado dos handovers para a staging area com
-- LOAD DATA INFILE e inserção nas tabelas definitivas.
-- O arquivo deve estar na pasta indicada por secure_file_priv.
-- A carga do Data Warehouse (dimensões e fatos) é feita pelo src/etl.py.
-- =====================================================================

USE calculadora_oltp;

SHOW VARIABLES LIKE 'secure_file_priv';

TRUNCATE TABLE stg_projetos;

LOAD DATA INFILE '/var/lib/mysql-files/projetos_implantacao.csv'
INTO TABLE stg_projetos
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

-- Transferência da staging para a tabela definitiva, convertendo tipos e
-- substituindo descrições por chaves. Registros que violarem as restrições
-- de integridade são recusados pelo próprio SGBD.
INSERT INTO projeto (
    id_projeto, data_proposta, numero_usuarios, numero_filiais,
    id_tipo_ambiente, id_modalidade, usa_van_bancaria, qtd_addons,
    plano_contas_customizado, qtd_modulos, complexidade_importacao,
    notas_mensal, id_faixa, horas_totais_implantacao
)
SELECT
    s.projeto_id,
    STR_TO_DATE(s.data_proposta, '%Y-%m-%d'),
    CAST(s.numero_usuarios AS UNSIGNED),
    CAST(s.numero_filiais AS UNSIGNED),
    ta.id_tipo_ambiente,
    mo.id_modalidade,
    s.usa_van_bancaria = 'Sim',
    CAST(s.qtd_addons AS UNSIGNED),
    s.plano_contas_customizado = 'Sim',
    CAST(s.qtd_modulos AS UNSIGNED),
    CAST(s.complexidade_importacao AS UNSIGNED),
    CAST(s.notas_mensal_num AS UNSIGNED),
    fx.id_faixa,
    CAST(s.horas_totais_implantacao AS DECIMAL(7,1))
FROM stg_projetos s
JOIN tipo_ambiente ta ON ta.descricao = s.tipo_ambiente
JOIN modalidade    mo ON mo.descricao = s.modalidade
JOIN faixa_volume_notas fx
  ON CAST(s.notas_mensal_num AS UNSIGNED) >= fx.limite_inferior
 AND (fx.limite_superior IS NULL OR CAST(s.notas_mensal_num AS UNSIGNED) <= fx.limite_superior);

-- Reconciliação com a origem (quantidade de registros)
SELECT
    (SELECT COUNT(*) FROM stg_projetos) AS registros_staging,
    (SELECT COUNT(*) FROM projeto)      AS registros_carregados;

-- Exportação de conferência em CSV (separador ponto e vírgula)
SELECT * FROM projeto
INTO OUTFILE '/var/lib/mysql-files/projeto_conferencia.csv'
FIELDS TERMINATED BY ';'
LINES TERMINATED BY '\n';
