pkgdatadir = join_paths(datadir, meson.project_name())
autostartdir = join_paths(sysconfdir, 'xdg', 'autostart')
gnome = import('gnome')

message(project_id)

desktop_file = i18n.merge_file(
  input: 'ltsp-manager.desktop.in',
  output: project_id + '.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: join_paths(get_option('datadir'), 'applications')
)

desktop_shared_file = i18n.merge_file(
  input: 'ltsp-shared-folders.desktop.in',
  output: project_id + '-shared-folders.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: autostartdir
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
  test('Validate desktop file', desktop_utils,
    args: [desktop_shared_file]
  )
endif

gnome.compile_resources(meson.project_name(),
  'ltsp-manager.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

icondir = join_paths('icons')
install_data(
  join_paths(icondir, 'ltsp-manager.svg'),
  install_dir: join_paths(pkgdatadir, icondir),
  rename: '@0@.svg'.format(project_id)
)

i18n.merge_file(
  input: 'org.ltsp.ltsp-manager.policy.in',
  output: 'org.ltsp.ltsp-manager.policy',
  install: true,
  install_dir: join_paths(datadir, 'polkit-1', 'actions') ,
  type: 'xml',
  po_dir: join_paths(meson.source_root(), 'po')
)
