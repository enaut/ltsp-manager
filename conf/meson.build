import('python3')

sysconfdefaultdir = join_paths(sysconfdir, 'default')
systemddir = join_paths('/', 'lib', 'systemd', 'system')
ldmdir = join_paths(datadir, 'ldm')

install_data('ltsp-shared-folders', install_dir: sysconfdefaultdir)
install_data('io.github.ltsp-manager.policy', install_dir:'/usr/share/polkit-1/actions')
install_data('io.github.ltsp-manager.conf', install_dir:'/usr/share/dbus-1/system.d')

configure_file(
  input: 'X50-shared-folders.in',
  output: 'X50-shared-folders',
  configuration: conf,
  install: true,
  install_dir: ldmdir
)
configure_file(
  input: 'io.github.ltsp-manager.service.in',
  output: 'io.github.ltsp-manager.service',
  configuration: conf,
  install: true,
  install_dir: '/usr/share/dbus-1/system-services'
)

configure_file(
  input: 'ltsp-shared-folders.service.in',
  output: 'ltsp-shared-folders.service',
  configuration: conf,
  install: true,
  install_dir: systemddir
)
