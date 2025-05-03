python_sources = [
  '__init__.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/kdtree',
)

py.extension_module('kdmain',
  [
    'kdmain.cpp',
    'kd.cpp',
  ],
  dependencies: np_dep,
  link_args: ['-fopenmp'],
  install: true,
  subdir: 'pynbody/kdtree'
)

