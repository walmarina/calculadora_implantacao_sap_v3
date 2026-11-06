@echo off
REM =====================================================================
REM Backup INCREMENTAL pelo binary log
REM Agendado no Agendador de Tarefas do Windows de segunda a sábado, 02h00.
REM
REM FLUSH BINARY LOGS fecha o binary log atual e abre um novo. Os arquivos
REM fechados contêm apenas as alterações desde a cópia anterior e são
REM copiados para a pasta de backup.
REM
REM Restauração: aplicar o último backup full e, em seguida, os binary
REM logs em ordem cronológica com o utilitário mysqlbinlog.
REM =====================================================================

SET MYSQL_BIN="C:\Program Files\MySQL\MySQL Server 8.0\bin"
SET OPCOES=--defaults-extra-file=C:\BackupBD\backup.cnf
SET ORIGEM="C:\ProgramData\MySQL\MySQL Server 8.0\Data"
SET DESTINO=C:\BackupBD\incremental

if not exist %DESTINO% mkdir %DESTINO%

echo Fechando o binary log atual...
%MYSQL_BIN%\mysql.exe %OPCOES% -e "FLUSH BINARY LOGS;"

echo Copiando binary logs ainda nao copiados...
xcopy %ORIGEM%\binlog.0* %DESTINO%\ /D /Y

echo Backup incremental concluido.
