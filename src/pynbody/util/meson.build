python_sources = [
  '__init__.py',
  'hdf_vds.py',
  'indexing_tricks.py',
  'iter_subclasses.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/util',
)

cython_gen_util = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_util',
  [
    cython_gen_util.process('_util.pyx'),
    '../sph/healpix.c',
  ],
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/util'
)


