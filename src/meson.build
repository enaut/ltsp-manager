pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'ltsp-manager')
gnome = import('gnome')

python3 = import('python3')

conf = configuration_data()
conf.set('PYTHON', python3.find_python().path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

#configure_file(
#  input: 'pigle.in',
#  output: 'pigle',
#  configuration: conf,
#  install: true,
#  install_dir: get_option('bindir')
#)

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
  'ltsp_shared_folders.py',
  'parsers.py',
  'signup.py',
  'signup_server.py',
  'user_form.py',
]


install_data(ltsp_manager_sources, install_dir: moduledir)