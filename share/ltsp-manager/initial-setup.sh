# Contains some actions that the sysadmin should run after installation.
# Copyright (C) 2017 Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

. /usr/share/ltsp-manager/common.sh

printfn "`gettext "This will perform an initial setup to ensure that LTSP runs optimally."`"
printf "%s " "`gettext "Press [Enter] to continue or Ctrl+C to abort:"`"
read dummy

# Create "teachers" group and add the current user to epoptes,teachers groups
test -f /etc/default/ltsp-shared-folders && . /etc/default/ltsp-shared-folders
if [ -n "$TEACHERS" ]; then
    # If the group already exists, don't do anything
    if ! getent group "$TEACHERS" >/dev/null; then
        addgroup --system "$TEACHERS"
        user=$(id -un)
        if [ "$user" = "root" ]; then
            # Try to find the user that ran sudo or su
            user=$(loginctl user-status | awk '{ print $1; exit 0 }')
        fi
        if [ -n "$user" ] && [ "$user" != "root" ]; then
            gpasswd -a "$user" "$TEACHERS"
            gpasswd -a "$user" epoptes
            bold "`gettext "You will need to logout in order for the group changes to take effect!"`"
        fi
    fi
fi

# Create an lts.conf
for f in /var/lib/tftpboot/ltsp/*/lts.conf; do
    if [ ! -f "$f" ]; then
        ltsp-config lts.conf
        break
    fi
done

# Ensure that "server" is resolvable by DNS.
if ! getent hosts server >/dev/null; then
    search_and_replace "^127.0.0.1[[:space:]]*localhost$" "& server" \
        /etc/hosts || true
fi & # Background it in case the DNS resolve takes a long time.

# Divert some files that have a bad effect in LTSP installations
mkdir -p /var/lib/ltsp-manager/diverted
while read file temp; do
    if [ -f "$file" ] && [ ! -f "/var/lib/ltsp-manager/diverted/${file##*/}" ]; then
        dpkg-divert --package ltsp-manager --divert "/var/lib/ltsp-manager/diverted/${file##*/}" --rename "$file"
    fi
done <<EOF
    /etc/dnsmasq.d/network-manager  # Makes dnsmasq malfunction sometimes
    /etc/init.d/nbd-client  # Break ordering cycle with n-m (LP: #1487679)
    /etc/skel/.config/autostart/ubuntu-mate-welcome.desktop  # Welcome screen
    /usr/share/mate/autostart/tilda.desktop  # Useless terminal that opens with F12
EOF

# Manually run update-kernels until it's moved to ltsp-client-core.postinst
if [ ! -d /boot/pxelinux.cfg ]; then
    /usr/share/ltsp/update-kernels
fi

# Remove the local resolver (LP: #959037), we want a real DNS server.
if search_and_replace "^dns=dnsmasq" "" /etc/NetworkManager/NetworkManager.conf; then
    printfn "`gettext "Restarting network-manager to remove its spawned dnsmasq..."`" >&2
    service network-manager restart
fi

# Install the dnsmasq configuration file and restart dnsmasq.
if [ ! -f /etc/dnsmasq.d/ltsp-server-dnsmasq.conf ]; then
    ltsp-config dnsmasq
    # TODO: better way?
    sed 's/^port=0/#port=0/' -i /etc/dnsmasq.d/ltsp-server-dnsmasq.conf
    service dnsmasq restart
fi

# Allow more simultaneous SSH connections from the local network.
search_and_replace "^#MaxStartups 10:30:60$" "MaxStartups 20:30:60" \
    /etc/ssh/sshd_config true

# If mate is installed, use its mimeapps for root
if [ ! -f /usr/local/share/applications/mimeapps.list ] &&
  [ -f /usr/share/mate/applications/defaults.list ]; then
    mkdir -p /usr/local/share/applications
    ln -rsf /usr/share/mate/applications/defaults.list /usr/local/share/applications/mimeapps.list || true
fi
