@echo off
cd /d D:\Aether\Aether_V0
call venv\Scripts\activate
python pipelines/loading/migrate_to_azure.py
echo Done %date% %time% >> logs/migration.log