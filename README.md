
Build to app MacOs

B1: terminal
pip install pyinstaller

B2: terminal
pyinstaller --windowed --onefile --add-data "servers.json:."  --icon icon.icns download_backups.py

B3: 
In the 'dist' folder, run download_backups app

B4: Password -> 'LvQuy'