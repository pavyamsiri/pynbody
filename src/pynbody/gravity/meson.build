python_sources = [
  '__init__.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/gravity',
)

cython_gen_gravity = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_gravity',
  cython_gen_gravity.process('_gravity.pyx'),
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/gravity'
)

