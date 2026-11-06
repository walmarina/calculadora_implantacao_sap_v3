-- =====================================================================
-- 04  Views  MySQL 8.0
-- Consultas armazenadas no banco (jobs de consulta) consumidas pelo
-- dashboard. O usuário da aplicação acessa somente as views, nunca as
-- tabelas diretamente.
-- =====================================================================

USE calculadora_dw;

CREATE OR REPLACE VIEW vw_projetos_analitico AS
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

CREATE OR REPLACE VIEW vw_horas_por_fase AS
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
