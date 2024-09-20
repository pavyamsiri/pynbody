"""
Deprecated module for calculating HI fractions with optional self-shielding.

New code should use :mod:`pynbody.analysis.ionfrac` instead.

"""


def calculate(sim, selfshield=False) :
    """Deprecated method for calculating HI fractions with optional self-shielding.

    This method is retained for backward compatibility with pynbody v1 and uses table of HI fractions. Unlike
    :meth:`pynbody.analysis.ionfrac.calculate`, this method returns HI as a fraction of total gas, not just hydrogen.

    """

    from . import ionfrac
    if selfshield:
        table = ionfrac.use_custom_ion_table('v1_duffy_shielded')
    else:
        table = ionfrac.use_custom_ion_table('v1_duffy')

    with table:
        result_array = ionfrac.calculate(sim, 'hi')

    # convert to fraction of total gas, not just of hydrogen
    result_array *= sim.gas['hydrogen']

    return result_array
