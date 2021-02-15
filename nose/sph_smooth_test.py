
import pynbody, numpy as np
import numpy.testing as npt
import pylab as p
import nose.tools

def setup():
    global f
    f = pynbody.load("testdata/g15784.lr.01024")

    # for compatibility with original results, pretend the box
    # is not periodic
    del f.properties['boxsize']

def teardown():
    global f
    del f

def test_smooth():
    global f
    """
    np.save('test_smooth.npy', f.dm['smooth'][::100])
    np.save('test_rho.npy', f.dm['rho'][::100])
    np.save('test_v_mean.npy',f.dm['v_mean'][::100])
    np.save('test_v_disp.npy',f.dm['v_disp'][::100])
    """

    npt.assert_allclose(f.dm['smooth'][::100],
                         np.load('test_smooth.npy'),rtol=1e-5)

    npt.assert_allclose(f.dm['rho'][::100],
                         np.load('test_rho.npy'),rtol=1e-5)



    npt.assert_allclose(np.load('test_v_mean.npy'),f.dm['v_mean'][::100],rtol=1e-3)
    npt.assert_allclose(np.load('test_v_disp.npy'),f.dm['v_disp'][::100],rtol=1e-3)

    # check 1D smooth works too
    vz_mean = f.dm.kdtree.sph_mean(f.dm['vz'],32)
    npt.assert_allclose(np.load('test_v_mean.npy')[:,2],vz_mean[::100],rtol=1e-3)

    # check 1D dispersions
    v_disp = f.dm.kdtree.sph_dispersion(f.dm['vx'],32)**2+ \
             f.dm.kdtree.sph_dispersion(f.dm['vy'],32)**2+ \
             f.dm.kdtree.sph_dispersion(f.dm['vz'],32)**2

    npt.assert_allclose(np.load('test_v_disp.npy')**2,v_disp[::100],rtol=1e-3)

def test_kd_delete():
    global f
    f.dm['smooth']

    assert hasattr(f.dm,'kdtree')

    f.physical_units()

    # position array has been updated - kdtree should be auto-deleted
    assert not hasattr(f.dm,'kdtree')


def test_kd_issue_88() :
    # number of particles less than number of smoothing neighbours
    f = pynbody.new(gas=16)
    f['pos'] = np.random.uniform(size=(16,3))
    trigger_fn = lambda : f['smooth']
    nose.tools.assert_raises(ValueError, trigger_fn)

def test_float_kd():
    f = pynbody.load("testdata/test_g2_snap")
    del f.properties['boxsize']

    assert f.dm['mass'].dtype==f.dm['pos'].dtype==np.float32
    assert f.dm['smooth'].dtype==np.float32

    # make double copy
    g = pynbody.new(len(f.dm))
    g.dm['pos']=f.dm['pos']
    g.dm['mass']=f.dm['mass']

    assert g.dm['mass'].dtype==g.dm['pos'].dtype==g.dm['smooth'].dtype==np.float64

    # check smoothing lengths agree (they have been calculated differently
    # using floating/double routines)

    npt.assert_allclose(f.dm['smooth'],g.dm['smooth'],rtol=1e-4)
    npt.assert_allclose(f.dm['rho'],g.dm['rho'],rtol=1e-4)

    # check all combinations of float/double smoothing
    double_ar = np.ones(len(f.dm),dtype=np.float64)
    float_ar = np.ones(len(f.dm),dtype=np.float32)

    double_double = g.dm.kdtree.sph_mean(double_ar,32)
    double_float = g.dm.kdtree.sph_mean(float_ar,32)
    float_double = f.dm.kdtree.sph_mean(double_ar,32)
    float_float = f.dm.kdtree.sph_mean(float_ar,32)

    # take double-double as 'gold standard' (though of course if any of these
    # fail it could also be a problem with the double-double case)

    npt.assert_allclose(double_double,double_float,rtol=1e-4)
    npt.assert_allclose(double_double,float_double,rtol=1e-4)
    npt.assert_allclose(double_double,float_float,rtol=1e-4)

def test_periodic_smoothing():
    f = pynbody.load("testdata/g15784.lr.01024")

    """
    np.save('test_rho_periodic.npy', f.dm['rho'][::100])
    np.save('test_smooth_periodic.npy', f.dm['smooth'][::100])
    """
    npt.assert_allclose(f.dm['rho'][::100],
                         np.load('test_rho_periodic.npy'),rtol=1e-5)
    npt.assert_allclose(f.dm['smooth'][::100],
                         np.load('test_smooth_periodic.npy'),rtol=1e-5)

def test_neighbour_list():
    f = pynbody.load("testdata/test_g2_snap")
    pynbody.sph._get_smooth_array_ensuring_compatibility(f.g)  # actual smoothing
    t = f.g.kdtree
    n_neigh = 32

    generator_nn = t.nn(n_neigh)
    n = next(generator_nn)
    # print(n)

    p_idx = n[0]       # particle index in snapshot arrays
    hsml = n[1]        # smoothing length
    neigh_list = n[2]  # neighbours list
    dist2 = n[3]       # squared distances from neighbours
    assert p_idx == 9
    assert hsml == f.g['smooth'][p_idx]
    npt.assert_allclose(hsml,np.sqrt(np.max(dist2))/2, rtol=1e-6)
    assert hsml == 128.19053649902344
    assert neigh_list == [0, 1, 2, 37, 4, 5, 70, 38, 8, 9, 10, 69, 12, 71, 14, 15, 16,
                          17, 67, 33, 109, 76, 96, 64, 74, 39, 65, 40, 28, 97, 30, 31]
    assert dist2 == [0.0, 39369.51953125, 24460.677734375, 31658.59375, 58536.9765625, 57026.3984375, 51718.3515625,
                     47861.25390625, 59311.27734375, 34860.97265625, 36082.15234375, 65731.2578125, 16879.42578125,
                     52811.79296875, 16521.751953125, 17574.501953125, 24489.19140625, 29066.84765625, 36883.796875,
                     41815.23046875, 60706.04296875, 31192.068359375, 58157.92578125, 60277.04296875, 61944.99609375,
                     45676.2578125, 54654.58984375, 59870.70703125, 20319.2890625, 35900.76953125, 30422.66796875, 56239.8828125]

    neighbour_list_all = t.all_nn(n_neigh)
    assert n == neighbour_list_all[0]
    for nl in neighbour_list_all:
        assert len(nl[2]) == n_neigh


if __name__=="__main__":
    test_float_kd()
