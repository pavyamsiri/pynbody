project(
  'pynbody',
  ['c', 'cpp', 'cython'],
  version: '2.1.1',
  license: 'GPL-3.0-or-later',
  meson_version: '>=1.4.0',
  default_options: [
    'buildtype=debugoptimized',
    'cpp_std=c++14',
    'c_std=c11',
    'b_ndebug=if-release',
    'warning_level=3'
  ]
)

# Compilers
cc = meson.get_compiler('c')
cpp = meson.get_compiler('cpp')
# Cython compiler
cython = find_program('cython', required: true)

# Dependencies
py_mod = import('python')
py = py_mod.find_installation('python3', required: true, pure: false)
py_dep = py.dependency()

numpy_incdir = include_directories(run_command(py, '-c', 'import numpy; print(numpy.get_include())', check: true).stdout().strip())
np_dep = declare_dependency(include_directories: numpy_incdir)

# Common compiler and linker flags
openmp_dep = dependency('openmp', required: true)

_common_cpp_args = cpp.get_supported_arguments([
  '-ftree-vectorize',
  '-fno-omit-frame-pointer',
  '-funroll-loops',
  '-fprefetch-loop-arrays',
  '-fstrict-aliasing',
  '-fno-expensive-optimizations',
  '-g'
])
add_project_arguments(_common_cpp_args, language: 'cpp')

_common_c_args = cc.get_supported_arguments([
  '-g'
])
add_project_arguments(_common_c_args, language: 'cpp')

cython_c_args = ['--fast-fail', '--3', '@INPUT@', '-o', '@OUTPUT@']
cython_cpp_args = ['--fast-fail', '--3', '@INPUT@', '-o', '@OUTPUT@', '--cplus']
cython_compile_args = ['-fopenmp']
cython_link_args = ['-fopenmp', '-std=c++14']

# Summary
summary({
  'Python version': py.language_version(),
  'Install prefix': get_option('prefix'),
  'C++ standard': get_option('cpp_std'),
  'C standard': get_option('c_std'),
  'OpenMP support': openmp_dep.found(),
}, section: 'Configuration')

subdir('src/pynbody')
