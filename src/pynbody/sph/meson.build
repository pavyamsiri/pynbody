python_sources = [
  '__init__.py',
  'kernels.py',
  'renderers.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/sph',
)


cython_gen_sph = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_render',
  [
    cython_gen_sph.process('_render.pyx'),
    'healpix.c'
  ],
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/sph'
)
