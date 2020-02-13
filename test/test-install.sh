
cd build
sudo ninja install;
dbus-send --system  --type=method_call --dest=io.github.ltsp-manager --print-reply /io/github/Ltsp/Manager/AccountManager io.github.ltsp.manager.AccountManager.Exit;
sudo systemctl restart polkit;
python3 /usr/local/share/ltsp-manager/ltsp19.py
