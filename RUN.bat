@echo off
python -m hb_downloader --links "%~dp0links.txt" --config "%~dp0config.toml" --output "%~dp0downloads"
pause
