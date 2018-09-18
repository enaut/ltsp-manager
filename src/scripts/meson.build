scripts = [
  'before-uninstall.sh',
  'common.sh',
  'create-symlinks.sh',
  'if-up.sh',
  'initial-setup.sh',
  'run-in-terminal.sh',
]

foreach script : scripts
    configure_file(
      input: script + '.in',
      output: script,
      configuration: conf,
      install: true,
      install_dir: scriptsdir,
    )
endforeach
