python_sources = [
  '__init__.py',
  'luminosity.py',
  'morphology.py',
  'profile.py',
  'hifrac.py',
  'cosmology.py',
  'ramses_util.py',
  'ionfrac.py',
  'angmom.py',
  'halo.py',
  'hmf.py',
  'theoretical_profiles.py',
  # Data files
  'cmdlum.npz',
  'default_ssp.txt',
  'lsst_ssp.txt',
  'h1.hdf5',
  'ionfracs.npz',
  'CAMB_WMAP7',
  'CAMB_Planck18',
  'cambtemplate.ini',
]

py.install_sources(
  python_sources,
  subdir: 'pynbody/analysis',
)

cython_gen_analysis = generator(
  cython,
  output: '@BASENAME@.c',
  arguments: cython_c_args,
)

py.extension_module('_com',
  cython_gen_analysis.process('_com.pyx'),
  dependencies: np_dep,
  c_args: cython_compile_args,
  link_args: cython_link_args,
  install: true,
  subdir: 'pynbody/analysis'
)

