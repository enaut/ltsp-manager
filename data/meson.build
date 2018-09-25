autostartdir = join_paths(sysconfdir, 'xdg', 'autostart')
desktopdir = join_paths(datadir, 'applications')
polkitdir = join_paths(datadir, 'polkit-1', 'actions')
gnome = import('gnome')

subdir('icons')

lmdesktop = configure_file(
  input: 'ltsp-manager.desktop.in.in',
  output: project_id + '.desktop.in',
  configuration: conf,
  install: false,
)

desktop_file = i18n.merge_file(
  input: lmdesktop,
  output: project_id + '.desktop',
  type: 'desktop',
  po_dir: '../po',
  install: true,
  install_dir: desktopdir
)

lsfdesktop = configure_file(
  input: 'ltsp-shared-folders.desktop.in.in',
  output: project_id + '-shared-folders.desktop.in',
  configuration: conf,
  install: false,
)

desktop_shared_file = i18n.merge_file(
  input: lsfdesktop,
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


lmpolicy = configure_file(
  input: 'org.ltsp.ltsp-manager.policy.in.in',
  output: 'org.ltsp.ltsp-manager.policy.in',
  configuration: conf,
  install: false,
)

i18n.merge_file(
  input: lmpolicy,
  output: project_id + '.policy',
  install: true,
  install_dir: polkitdir,
  type: 'xml',
  po_dir: join_paths(meson.source_root(), 'po')
)

help2man = find_program('help2man', required: false)
if help2man.found()
  help2man_opts = [
    '--no-info',
    '--section=8',
    '--help-option=--help',
  ]
  lmfile = files('../src/ltsp-manager.py')
  custom_target('man-ltsp-manager',
                output: 'ltsp-manager.8',
                command: [
                  help2man, help2man_opts, '--output=@OUTPUT@', '--name=LTSP-Manager', lmfile
                ],
                install: true,
                install_dir: join_paths(datadir, 'man/man8'))

  lsfile = files('../src/ltsp_shared_folders.py')
  custom_target('man-ltsp-shared-folders',
                output: 'ltsp-shared-folders.8',
                command: [
                  help2man, help2man_opts, '--output=@OUTPUT@', '--name=LTSP-Shared-Folders', lsfile
                ],
                install: true,
                install_dir: join_paths(datadir, 'man/man8'))
endif
