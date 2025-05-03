python_sources = [
  '__init__.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/bridge',
)

cython_gen_bridge = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_bridge',
  cython_gen_bridge.process('_bridge.pyx'),
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/bridge'
)
