# Sourced by all ltsp-manager shell scripts, provides some common functions.
# Copyright (C) 2017 Alkis Georgopoulos <alkisg@gmail.com>
# License GNU GPL version 3 or newer <http://gnu.org/licenses/gpl.html>

# We're not using /usr/bin/gettext.sh at all.
# Always call this gettext function like this:
# echo "`gettext "Translated message with various %s params" "params go here"`"
gettext() {
    text="$1"
    shift
    if [ -x "/usr/bin/gettext" ]; then
        printf "`/usr/bin/gettext -d ltsp-manager "$text"`" "$@"
    else
        printf "$text" "$@"
    fi
}

bold() {
    if [ -z "$printbold_first_time" ]; then
        printbold_first_time=true
        bold_face=$(tput bold 2>/dev/null) || true
        normal_face=$(tput sgr0 2>/dev/null) || true
    fi
    printf "%s\n" "${bold_face}$*${normal_face}"
}

log() {
    logger -t ltsp-manager -p syslog.err "$@"
}

# Output a message to stderr and abort execution
die() {
    log "$@"
    bold "ERROR in ${0##*/}:" >&2
    echo "$@" >&2
    pause_exit 1
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
        gettext "Cancelled by the user." >&2
        pause_exit 2
    fi
}
