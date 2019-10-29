icon_sizes = [
  '16x16',
  '22x22',
  '32x32',
  '48x48',
  '256x256',
  '512x512',
]

foreach icon_size: icon_sizes
  message('installing ' + icon_size)
  install_data(
    join_paths(icon_size, 'apps', 'ltsp-manager.png'),
    install_dir: join_paths(datadir, 'icons', 'hicolor', icon_size, 'apps')
  )
endforeach

foreach icon_size: ['scalable', 'symbolic']
  message('installing ' + icon_size)
  install_data(
    join_paths(icon_size, 'apps', 'ltsp-manager.svg'),
    install_dir: join_paths(datadir, 'icons', 'hicolor', icon_size, 'apps')
  )
endforeach