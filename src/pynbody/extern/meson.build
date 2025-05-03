python_sources = [
  '__init__.py',
  'cython_fortran_utils.py'
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/extern',
)

cython_gen_extern = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_cython_fortran_utils',
  cython_gen_extern.process('_cython_fortran_utils.pyx'),
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/extern'
)

