import('python3')

sysconfdefaultdir = join_paths(sysconfdir, 'default')
systemddir = join_paths('/', 'lib', 'systemd', 'system')
ldmdir = join_paths(datadir, 'ldm')

install_data('ltsp-shared-folders', install_dir: sysconfdefaultdir)

configure_file(
  input: 'X50-shared-folders.in',
  output: 'X50-shared-folders',
  configuration: conf,
  install: true,
  install_dir: ldmdir
)

configure_file(
  input: 'ltsp-shared-folders.service.in',
  output: 'ltsp-shared-folders.service',
  configuration: conf,
  install: true,
  install_dir: systemddir
)