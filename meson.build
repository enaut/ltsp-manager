project('ltsp-manager',
  version: '18.04.2',
  meson_version: '>= 0.46.0',
)
i18n = import('i18n')
project_id = 'org.ltsp.ltsp-manager'

prefix = get_option('prefix')

bindir = join_paths(prefix, get_option('bindir'))
libdir = join_paths(prefix, get_option('libdir'))
datadir = join_paths(prefix, get_option('datadir'))
libexecdir = join_paths(prefix, get_option('libexecdir'))
sysconfdir = join_paths(prefix, get_option('sysconfdir'))
localstatedir = join_paths(prefix, get_option('localstatedir'))
mandir = join_paths(prefix, get_option('mandir'))
localedir = join_paths(prefix, get_option('localedir'))

subdir('data')
subdir('src')
subdir('conf')
subdir('po')
#subdir('test')
#meson.add_install_script('meson_post_install.py')