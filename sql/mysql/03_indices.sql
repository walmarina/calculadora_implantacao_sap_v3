-- =====================================================================
-- 03  Índices  MySQL 8.0
-- Criados apenas nas colunas usadas em filtros e junções do dashboard,
-- para não sobrecarregar as operações de carga (Albuquerque e Reis, 2021).
-- A efetividade de cada índice deve ser conferida com EXPLAIN.
-- =====================================================================

USE calculadora_oltp;

CREATE INDEX idx_projeto_ambiente   ON projeto (id_tipo_ambiente);
CREATE INDEX idx_projeto_modalidade ON projeto (id_modalidade);
CREATE INDEX idx_projeto_data       ON projeto (data_proposta);

USE calculadora_dw;

CREATE INDEX idx_fato_projeto_tempo      ON dw_fato_projeto (sk_tempo);
CREATE INDEX idx_fato_projeto_ambiente   ON dw_fato_projeto (sk_ambiente);
CREATE INDEX idx_fato_projeto_modalidade ON dw_fato_projeto (sk_modalidade);
CREATE INDEX idx_fato_projeto_porte      ON dw_fato_projeto (sk_porte);
CREATE INDEX idx_fato_fase_fase          ON dw_fato_horas_fase (sk_fase);

-- Conferência do plano de execução (deve indicar uso de idx_fato_projeto_porte)
EXPLAIN FORMAT=JSON
SELECT AVG(horas_totais_implantacao)
FROM dw_fato_projeto
WHERE sk_porte = 3;
