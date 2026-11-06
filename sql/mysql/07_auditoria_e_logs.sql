-- =====================================================================
-- 07  Auditoria e logs  MySQL 8.0
-- Trilha de auditoria por triggers na tabela de projetos e ativação dos
-- logs usados no monitoramento e no backup incremental
-- (Albuquerque e Reis, 2021).
-- =====================================================================

USE calculadora_oltp;

CREATE TABLE auditoria_projeto (
    id_auditoria     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    id_projeto       VARCHAR(10)     NOT NULL,
    operacao         VARCHAR(10)     NOT NULL,
    horas_anterior   DECIMAL(7,1)    NULL,
    horas_nova       DECIMAL(7,1)    NULL,
    usuario_banco    VARCHAR(100)    NOT NULL,
    data_hora        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT pk_auditoria_projeto PRIMARY KEY (id_auditoria)
) ENGINE = InnoDB;

CREATE TRIGGER trg_projeto_auditoria_update
AFTER UPDATE ON projeto
FOR EACH ROW
    INSERT INTO auditoria_projeto (id_projeto, operacao, horas_anterior, horas_nova, usuario_banco)
    VALUES (OLD.id_projeto, 'UPDATE', OLD.horas_totais_implantacao, NEW.horas_totais_implantacao, CURRENT_USER());

CREATE TRIGGER trg_projeto_auditoria_delete
AFTER DELETE ON projeto
FOR EACH ROW
    INSERT INTO auditoria_projeto (id_projeto, operacao, horas_anterior, horas_nova, usuario_banco)
    VALUES (OLD.id_projeto, 'DELETE', OLD.horas_totais_implantacao, NULL, CURRENT_USER());

-- Logs (persistidos na configuração do servidor)
-- Slow query log: consultas acima de 2 segundos, para ajuste de índices
SET PERSIST slow_query_log = ON;
SET PERSIST long_query_time = 2;

-- O binary log já vem habilitado por padrão no MySQL 8.0 e é a base do
-- backup incremental e da replicação. Retenção de 14 dias:
SET PERSIST binlog_expire_logs_seconds = 1209600;

SHOW VARIABLES LIKE 'log%';
SHOW VARIABLES LIKE 'slow_query%';
