###########################################################################
# Contains miscellaneous utility functions for sch-scripts.
#
# Copyright (C) 2010 Alkis Georgopoulos <alkisg@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# On Debian GNU/Linux systems, the complete text of the GNU General
# Public License can be found in `/usr/share/common-licenses/GPL'.
###########################################################################

# Prevent multiple inclusions
test -z "$INCLUDED_COMMON" || return 0

# Halt on errors.
set -e

# Allow tracing of the file that sources common.sh
# by specifying its name in the "xtrace" environment variable.
if [ "$xtrace" = "$(basename "$0")" ]; then
    set -x
fi

echo_bold() {
    if [ -z "$printbold_first_time" ]; then
        printbold_first_time=true
        bold_face=$(tput bold 2>/dev/null) || true
        normal_face=$(tput sgr0 2>/dev/null) || true
    fi
    echo "${bold_face}$@${normal_face}"
}

log() {
    echo "$@" >> /var/log/sch-scripts.log
}

# Outputs a message to stderr and aborts execution.
die() {
    log "$@"
    echo_bold "ERROR in $(basename "$0"):" >&2
    echo "$@" >&2
    exit 1
}

# Also contains the greek letters for Yes/No
is_true() {
    case "$1" in
        [YyΝν]|[Tt][Rr][Uu][Ee]|[Yy][Ee][Ss])
            return 0
        ;;
        *)
            return 1
        ;;
    esac
}

confirm() {
    local answer

    read -p "$1" answer
    test -n "$answer" || answer="true"
    if ! is_true "$answer"; then
        echo "Ακυρώθηκε από το χρήστη." >&2
        exit 2
    fi
}

# Prints the IP of the interface that has the default gateway.
get_ip() {
    local def_iface
    
    def_iface=$(route -n | sed -n '/^0.0.0.0/s/.* //p')
    test -n "$def_iface" || return 1
    ip -oneline -family inet addr show dev "$def_iface" | sed -n '/inet 127\./! {s,.* \(.*\)/.*,\1,p;q}'
}

# Update "server" and "wpad" entries in /etc/hosts.
# If they don't exist, add them at the end,
# otherwise update them inline if $DYNAMIC_SERVER_IP is set.
# If they're commented out, respect that and don't add them again.
update_etc_hosts() {
    local server_ip
    local entries
    local found

    server_ip="$1"
    [ -n "$server_ip" ] || return 1
    # If this is the server, don't add a "server" entry.
    if [ "$(hostname)" = "server" ]; then
        entries="wpad"
    else
        entries="server wpad"
    fi
    found=$(sed -ne '/^[#[:space:]]*[0-9\.]*[[:space:]]*'"$entries"'[[:space:]]*$/{p;q}' /etc/hosts)
    if [ -z "$found" ]; then
        echo "$server_ip server wpad" >> /etc/hosts
    elif [ -n "$DYNAMIC_SERVER_IP" ]; then
        sed -ie 's/^\([#[:space:]]*\)[0-9\.]*[[:space:]]*'"$entries"'[[:space:]]*$/\1'"$server_ip $entries/" /etc/hosts
    fi
}

# Copies an example to the destination, while gunzipping it, and, if #3 is
# true, while expanding any vars.
install_example() {
    local src="$1"
    local dst="$2"
    local expand="$3"

    # If the destination already exists, don't overwrite it.
    [ -f "$dst" ] && return 0

    mkdir -p "$(dirname "$dst")"

    if [ -f "$src" ]; then
        cmd="cat"
    elif [ -f "$src.gz" ]; then
        src="$src.gz"
        cmd="zcat"
    else
        return 1
    fi

    if is_true "$expand"; then
        # Remove any lines starting with '## ' from the src example file, 
        # evaluate any variables, and generate the resulting configuration file:
        # TODO: keep or remove `set -u`?
        # TODO: don't strip quotes
        echo "$(set -u; eval "echo \"$($cmd "$src" | grep -v '^## ')\"")" > "$dst"
    else
        $cmd "$src" > "$dst"
    fi
}

default_values(){
    SERVER=${SERVER:-$(get_ip)}
    SERVER=${SERVER:-10.160.31.10}
    if [ -z "$CHROOT" ]; then
        for f in /opt/ltsp/*/usr/bin/getltscfg; do
            if [ -x "$f" ]; then
                CHROOT=${f%/usr/bin/getltscfg}
                CHROOT=${CHROOT#/opt/ltsp/}
                break
            fi
        done
        CHROOT=${CHROOT:-i386}
    fi
    ROOT=${ROOT:-"/opt/ltsp/$CHROOT"}
    TFTP=${TFTP:-"/var/lib/tftpboot/ltsp/$CHROOT"}
    if [ -z "$DNS_SERVER" ]; then
        DNS_SERVER=$(echo $(sed -n 's/^[[:space:]]*nameserver[[:space:]]\([^[:space:]]*\).*/\1/p' /etc/resolv.conf))
        DNS_SERVER=${DNS_SERVER:-$SERVER}
    fi
    if [ -z "$SEARCH_DOMAIN" ]; then
        SEARCH_DOMAIN=$(sed '/^[[:space:]]*search[[:space:]]\([^[:space:]]*\).*/!d;s//\1/;q' /etc/resolv.conf)
        SEARCH_DOMAIN=${SEARCH_DOMAIN:-local}
    fi
}

# TODO: remove this when the libsoup bug is solved
unset http_proxy

# Source sch-scripts.conf, if it's available
if [ -f /etc/sch-scripts/sch-scripts.conf ]; then
    . /etc/sch-scripts/sch-scripts.conf
fi

# Then, set some default values for unset vars.
default_values

# Prevent multiple inclusions
INCLUDED_COMMON=true
