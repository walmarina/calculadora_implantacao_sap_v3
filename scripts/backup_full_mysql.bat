@echo off
REM =====================================================================
REM Backup FULL (lógico) das bases calculadora_oltp e calculadora_dw
REM Agendado no Agendador de Tarefas do Windows aos domingos, 02h00.
REM
REM A senha NÃO fica neste arquivo. Ela é lida do arquivo de opções
REM C:\BackupBD\backup.cnf (acesso restrito ao administrador), no formato
REM   [client]
REM   user=backup_operador
REM   password=********
REM
REM --single-transaction  cópia consistente sem bloquear as tabelas InnoDB
REM --flush-logs          inicia um novo binary log, ponto de partida dos
REM                       backups incrementais da semana
REM =====================================================================

for /f "tokens=1-3 delims=/ " %%a in ('DATE /T') do (set DATA=%%c%%b%%a)
for /f "tokens=1-2 delims=: " %%a in ('TIME /T') do (set HORA=%%ah%%bm)

SET MYSQL_BIN="C:\Program Files\MySQL\MySQL Server 8.0\bin"
SET OPCOES=--defaults-extra-file=C:\BackupBD\backup.cnf
SET DESTINO=C:\BackupBD\full
SET ARQUIVO=%DESTINO%\full_%DATA%_%HORA%.sql

if not exist %DESTINO% mkdir %DESTINO%

echo Iniciando backup full...
%MYSQL_BIN%\mysqldump.exe %OPCOES% --single-transaction --flush-logs --routines --triggers --events --databases calculadora_oltp calculadora_dw --result-file=%ARQUIVO%

REM Compactação do arquivo (gzip copiado para a pasta bin do MySQL)
%MYSQL_BIN%\gzip.exe %ARQUIVO%

echo Backup full concluido em %ARQUIVO%.gz
