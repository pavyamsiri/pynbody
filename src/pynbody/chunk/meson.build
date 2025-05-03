python_sources = [
  '__init__.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/chunk',
)

cython_gen_chunk = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('scan',
  cython_gen_chunk.process('scan.pyx'),
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/chunk'
)

