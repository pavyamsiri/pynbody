python_sources = [
  '__init__.py',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/filt',
)

cython_gen_filt = generator(
  cython,
  output: '@BASENAME@.cpp',
  arguments: cython_cpp_args,
)

py.extension_module('geometry_selection',
  cython_gen_filt.process('geometry_selection.pyx'),
  dependencies: np_dep,
  cpp_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/filt'
)

