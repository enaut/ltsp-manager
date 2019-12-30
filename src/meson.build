pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
gnome = import('gnome')

python3 = import('python3')

subdir('scripts')

configure_file(
  input: 'commands/ltsp-manager.in',
  output: 'ltsp-manager',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

configure_file(
  input: 'commands/ltsp-shared-folders.in',
  output: 'ltsp-shared-folders',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

configure_file(
  input: 'commands/ltsp-signup.in',
  output: 'ltsp-signup',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir')
)

configure_file(
  input: 'paths.ini.in',
  output: 'paths.ini',
  configuration: conf,
  install: true,
  install_dir: pkgdatadir
)

ltsp_manager_sources = [
  'version.py',
  'about_dialog.py',
  'dialogs.py',
  'common.py',
  'config.py',
  'create_users.py',
  'export_dialog.py',
  'group_form.py',
  'import_dialog.py',
  'iso843.py',
  'libuser.py',
  'ip_dialog.py',
  'ltsp_info.py',
  'ltsp-manager.py',
  'ltsp19.py',
  'ltsp_shared_folders.py',
  'parsers.py',
  'paths.py',
  'signup.py',
  'signup_server.py',
  'user_elements.py',
  'user_form.py',
  'dbus_account_service.py'
]


install_data(ltsp_manager_sources, install_dir: pkgdatadir)
