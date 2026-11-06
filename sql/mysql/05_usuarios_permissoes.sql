-- =====================================================================
-- 05  Usuários e privilégios  MySQL 8.0
-- Princípio do menor privilégio: cada função tem seu próprio usuário,
-- nenhum usuário de aplicação recebe acesso a todos os hosts, e os
-- privilégios FILE, PROCESS e SUPER ficam restritos ao DBA
-- (Albuquerque e Reis, 2021).
--
-- As senhas abaixo são marcadores e devem ser substituídas por senhas
-- fortes no momento da instalação. Nunca versionar senhas reais.
-- =====================================================================

-- Aplicação (dashboard Streamlit): somente leitura nas views do DW
CREATE USER 'app_dashboard'@'10.0.0.%' IDENTIFIED BY 'TROCAR_POR_SENHA_FORTE_1';
GRANT SELECT ON calculadora_dw.vw_projetos_analitico TO 'app_dashboard'@'10.0.0.%';
GRANT SELECT ON calculadora_dw.vw_horas_por_fase     TO 'app_dashboard'@'10.0.0.%';

-- Processo ETL: grava na staging e nas tabelas, sem poder alterar estrutura
CREATE USER 'etl_carga'@'localhost' IDENTIFIED BY 'TROCAR_POR_SENHA_FORTE_2';
GRANT SELECT, INSERT, DELETE ON calculadora_oltp.* TO 'etl_carga'@'localhost';
GRANT SELECT, INSERT, DELETE ON calculadora_dw.*   TO 'etl_carga'@'localhost';

-- Cientista de dados: leitura do DW para treino e avaliação do modelo
CREATE USER 'analista_dados'@'10.0.0.%' IDENTIFIED BY 'TROCAR_POR_SENHA_FORTE_3';
GRANT SELECT ON calculadora_dw.* TO 'analista_dados'@'10.0.0.%';

-- Usuário de backup: privilégios mínimos exigidos pelo mysqldump
CREATE USER 'backup_operador'@'localhost' IDENTIFIED BY 'TROCAR_POR_SENHA_FORTE_4';
GRANT SELECT, LOCK TABLES, SHOW VIEW, EVENT, TRIGGER, RELOAD
    ON *.* TO 'backup_operador'@'localhost';
GRANT BACKUP_ADMIN ON *.* TO 'backup_operador'@'localhost';

-- Conferência dos privilégios concedidos
SHOW GRANTS FOR 'app_dashboard'@'10.0.0.%';
SHOW GRANTS FOR 'etl_carga'@'localhost';
