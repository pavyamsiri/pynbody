"""
Ionisation fraction estimations from grids of *cloudy* models

This module provides a way to estimate the ionisation fractions of various ions in a gas particle based on a grid of
*cloudy* models. The grid is defined by redshift, temperature and density, and the ionisation fractions are interpolated
from this grid. The grid can be generated by running *cloudy* with a given radiation table and parameters, or loaded from
a pre-existing file.

.. note::
 *Cloudy* can be downloaded from https://www.nublado.org/. You will need to compile it yourself if you want to
 calculate new tables. The tables provided with pynbody are calculated using *cloudy* version 23.01.

By default, *cloudy* is run with a fixed metallicity of 1/10th solar. In principle, metallicity variations can change
the ionization state of the gas, but this is not currently implemented on the basis it will be a small correction.
Also by default, there is no correction for the self-shielding of the gas or for local source of ionising radiation.
If ionisation states are crucial for your science, consider using a radiative transfer code and ensure you use
its own reported ionisation states.

Information about available tables is provided in the function :func:`use_custom_ion_table`. The default table is
HM12, which is calculated based on the Haardt & Madau 2012 ionising background.


"""

import abc
import logging
import os
import subprocess

import h5py
import numpy as np
from scipy.interpolate import RegularGridInterpolator

from .. import util

logger = logging.getLogger('pynbody.analysis.ionfrac')

from .interpolate import interpolate3d


def _cloudy_output_line_to_dictionary(line):
    """Process a single line from the cloudy ionisation output.

    Turn its raw output into a dictionary of ionisation fractions, e.g. HeI: 0.1, HeII: 0.2, HeIII: 0.8.

    The ionisation fractions for a given element sum to one.
    """
    element_symbols = {
        "Hydrogen": "H",
        "Helium": "He",
        "Lithium": "Li",
        "Beryllium": "Be",
        "Boron": "B",
        "Carbon": "C",
        "Nitrogen": "N",
        "Oxygen": "O",
        "Fluorine": "F",
        "Neon": "Ne",
        "Sodium": "Na",
        "Magnesium": "Mg",
        "Aluminium": "Al",
        "Silicon": "Si",
        "Phosphorus": "P",
        "Sulphur": "S",
        "Chlorine": "Cl",
        "Argon": "Ar",
        "Potassium": "K",
        "Calcium": "Ca",
        "Scandium": "Sc",
        "Titanium": "Ti",
        "Vanadium": "V",
        "Chromium": "Cr",
        "Manganese": "Mn",
        "Iron": "Fe",
        "Cobalt": "Co",
        "Nickel": "Ni",
        "Copper": "Cu",
        "Zinc": "Zn"
    }

    ion_stages = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII",
                  "XIII", "XIV", "XV", "XVI", "XVII"]

    element_name = line[1:11].strip()
    ion_fracs = []
    for i in range(17):
        this_ion = line[11 + i * 7:18 + i * 7].strip()
        try:
            ion_fracs.append(10.**float(this_ion))
        except ValueError:
            break

    if element_name not in element_symbols:
        return {}

    element_symbol = element_symbols[element_name]

    if element_symbol == "H":
        # Hydrogen has a special case of outputting molecular hydrogen
        ion_stages[2] = "2"

    ion_fracs = np.asarray(ion_fracs)
    ion_fracs /= ion_fracs.sum() # correct any rounding errors

    return {element_symbol + ion_stage: float(ion_frac) for ion_stage, ion_frac in zip(ion_stages, ion_fracs)}

def _run_cloudy(redshift, log_temp, log_den, table, cloudy_path, metallicity=0.1):
    """
    Run cloudy and return the output ionisation fractions
    """
    template = """title pynbody_grid_run
    cmb z={redshift}
    table {table} z = {redshift}
    hden {log_hden}
    metals {metallicity}
    constant temperature {temperature}
    stop zone 1
    """

    # correct from total density to hydrogen density on the assumption of 1/10th solar metallicity
    Y_over_X = 0.245/0.755 # primordial helium over hydrogen mass fraction
    Z_over_X = metallicity * 0.0187 # metals mass fraction, https://www.aanda.org/articles/aa/pdf/2024/01/aa46928-23.pdf
    X =1./(1+Y_over_X+Z_over_X)

    input = template.format(redshift=redshift, log_hden=log_den + np.log10(X), temperature=10**log_temp, table=table,
                            metallicity=metallicity)

    # cloudy is fussy about its input -- remove any indentation and replace newlines with '\n'
    input = '\n'.join([x.strip() for x in input.split('\n')])



    # Start the subprocess
    process = subprocess.Popen(
        [cloudy_path],  # Replace with your command and arguments
        stdin=subprocess.PIPE,  # Allows writing to stdin
        stdout=subprocess.PIPE,  # Allows reading from stdout
        stderr=subprocess.PIPE,  # Capture stderr (optional)
        text=True  # Ensures that communication is in string format (instead of bytes)
    )

    process.stdin.write(input)
    process.stdin.flush()  # Flush the input to ensure it is sent

    stdout, stderr = process.communicate()  # Waits for the process to complete and fetches output

    # search for "Log10 Mean Ionisation" in the output
    table_start_line_number = None
    out_lines = stdout.split('\n')
    for i, line in enumerate(out_lines):
        if "Log10 Mean Ionisation (over radius)" in line:
            table_start_line_number = i
            break

    if table_start_line_number is None:
        raise ValueError("Could not find ionisation table in cloudy output")

    result = {}

    for i in range(0, 29):
        result.update(_cloudy_output_line_to_dictionary(
            out_lines[table_start_line_number + i]
        ))

    return result

def _run_cloudy_task_wrapper(args):
    """Wrapper for _run_cloudy that can be called by multiprocessing.Pool"""
    return _run_cloudy(*args)


class IonFractionTableBase(abc.ABC):
    """Abstract base class for ionization fraction tables"""

    @abc.abstractmethod
    def __init__(self):
        pass

    @abc.abstractmethod
    def calculate(self, simulation, ion='ovi'):
        """Calculate the ion fraction for a given ion in the gas particles of a simulation.

        Parameters
        ----------
        simulation : pynbody.snapshot.SimSnap
            The simulation snapshot to calculate the ion fractions for. The gas particles must have 'rho' and 'temp'
            fields.

        ion : str
            The name of the ion to calculate the fraction for. The default is 'ovi'. Case insensitive.

        Returns
        -------
        array-like
            The ion fraction for each gas particle in the simulation, according to the table.

        """
        pass

    def _clamp_values(self, array, vmin, vmax):
        """Modify the array in place to clamp values to the range [vmin, vmax]"""
        np.clip(array, vmin, vmax, out=array)

class IonFractionTable(IonFractionTableBase):
    """Class for calculating ion fractions from a grid of *cloudy* models.

    Rather than use this class directly, for many uses it is simpler to use :func:`calculate` which will use the
    currently loaded or default table.
    """

    def __init__(self, redshift_values, log_temp_values, log_den_values, tables):
        """Initialise an ion fraction table from raw data.

        Most users will instead want to use :meth:`load` to load a pre-existing table, or :meth:`from_cloudy` to
        generate a new table by executing cloudy.

        Parameters
        ----------
        redshift_values : array_like
            Redshift values at which the tables are defined

        log_temp_values : array_like
            Log10 temperature values at which the tables are defined

        log_den_values : array_like
            Log10 density values at which the tables are defined

        tables : dict
            Dictionary of tables, with keys being ion names and values being 3D numpy arrays of ion fraction values.
            The shape of each array should be (len(redshift_values), len(log_temp_values), len(log_den_values)).
        """
        self._redshift_values = redshift_values
        self._log_temp_values = log_temp_values
        self._log_den_values = log_den_values
        self._tables = {k.upper(): v for k, v in tables.items()}
        self._interpolators = {ion: RegularGridInterpolator(
            (self._redshift_values, self._log_temp_values, self._log_den_values),
            np.log10(np.maximum(self._tables[ion], np.nextafter(0.0, 1.0)))
        ) for ion in self._tables.keys()}

    def calculate(self, simulation, ion='ovi'):
        """Calculate the ionisation fraction for the gas particles of a given simulation

        Values are interpolated from the (rho,T) table at the appropriate redshift, and any values outside the
        range of the table are clamped to the nearest valid value.

        Parameters
        ----------

        simulation : pynbody.snapshot.SimSnap
            The simulation snapshot to calculate the ion fractions for. The gas particles must have 'rho' and 'temp'
            fields.

        ion : str
            The name of the ion to calculate the fraction for, e.g. HI, MgII, OVI etc. The only molecular fraction
            available is H2. The default is 'ovi'. Case insensitive.

        Returns
        -------
        array-like
            The ion fraction for each gas particle in the simulation, according to the table.

        """
        den_values = np.log10(simulation.gas['rho'].in_units('m_p cm^-3')).view(np.ndarray)
        temp_values = np.log10(simulation.gas['temp'].in_units('K')).view(np.ndarray)
        redshift_values = np.repeat(simulation.properties['z'], len(simulation.gas))
        self._clamp_values(temp_values, np.min(self._log_temp_values), np.max(self._log_temp_values))
        self._clamp_values(den_values, np.min(self._log_den_values), np.max(self._log_den_values))
        return 10 ** self._interpolators[ion.upper()]((redshift_values, temp_values, den_values))

    def save(self, filename):
        """Save the table to a numpy .npz file"""
        np.savez(filename, redshift_values=self._redshift_values, log_temp_values=self._log_temp_values,
                 log_den_values=self._log_den_values, **self._tables)

    def plot(self, ion='ovi', redshift=0.0):
        """Use matplotlib to plot the ion fraction table for a given ion at a given redshift"""
        import matplotlib.pyplot as plt
        plt.imshow(self._tables[ion.upper()][np.searchsorted(self._redshift_values, redshift)][::-1],
                     extent=(self._log_den_values[0], self._log_den_values[-1],
                                self._log_temp_values[0], self._log_temp_values[-1]),
                        aspect='auto')
        plt.xlabel('log10(Density/$m_p$ cm$^{-3}$)')
        plt.ylabel('log10(Temperature/K)')
        plt.title(ion + ' ion fraction at z=' + str(redshift))

    @classmethod
    def load(cls, filename):
        """Load a table from a numpy .npz file, generated using :meth:`save`

        If the file is not found, it is assumed to be a pynbody-provided table. If such a built-in table exists,
        the path is modified automatically to point at it. If it does not exist, an attempt is made to download it
        from a zenodo repository."""

        if not os.path.exists(filename):
            if not os.path.exists(cls._table_to_path(filename)):
                cls._download_ionfracs(filename)
                # this will raise an exception if the download fails, so now we can try again:
            filename = cls._table_to_path(filename)

        tables = np.load(filename)
        return cls(tables['redshift_values'], tables['log_temp_values'], tables['log_den_values'],
                   {k: tables[k] for k in tables.files
                    if k not in ['redshift_values', 'log_temp_values', 'log_den_values']})

    @classmethod
    def _table_to_path(cls, name):
        return os.path.join(os.path.dirname(__file__), name + '.npz')

    @classmethod
    def _download_ionfracs(cls, name):
        """Download an ion fraction table from the pynbody data repository"""
        import subprocess

        logger.warning("Downloading ion fraction table %s" % name)

        url = "https://zenodo.org/TK/" + name + ".npz?download=1"
        filename = cls._table_to_path(name)

        # ideally we'd use urllib for this but on macos it fails with a certificate error
        subprocess.run(["wget", "-O", filename, url], check=True)

    @classmethod
    def from_cloudy(cls, cloudy_path,
                          table='hm12',
                          redshift_range = (0, 15), num_redshifts = 10,
                          log_temp_range = (2.0, 8.0), num_temps = 10,
                          log_den_range = (-8.0, 2.0), num_dens = 10):
        """Generate a table by running *cloudy* with the specified ionising radiation table and parameters.

        This can take a long time, but the resulting table can then be saved using the :meth:`save` method and reused
        by calling :meth:`load`. The grid is computed in parallel using the default number of processors detected
        by ``multiprocessing.Pool``. A progress bar is displayed using ``tqdm``.

        Parameters
        ----------
        cloudy_path : str
            Path to the *cloudy* executable

        table : str
            Name of the *cloudy* radiation table to use. The default is 'hm12'.

        redshift_range : tuple
            Minimum and maximum redshift values to use

        num_redshifts : int
            Number of redshift values to use. These are spaced equally in log(1+z).

        log_temp_range : tuple
            Minimum and maximum log10 temperature values to use

        num_temps : int
            Number of temperature values to use, spaced equally in log space

        log_den_range : tuple
            Minimum and maximum log10 density values to use

        num_dens : int
            Number of density values to use, spaced equally in log space

        """

        tables = {}
        # space redshifts z equally in log(1+z):
        redshift_values = np.exp(
            np.linspace(np.log(1 + redshift_range[0]), np.log(1 + redshift_range[1]), num_redshifts)) - 1.0
        log_temp_values = np.linspace(log_temp_range[0], log_temp_range[1], num_temps)
        log_den_values = np.linspace(log_den_range[0], log_den_range[1], num_dens)

        from multiprocessing import Pool

        from tqdm import tqdm

        with Pool() as pool:
            tasks = [(redshift, log_temp, log_den, table, cloudy_path)
                     for redshift in redshift_values for log_temp in log_temp_values for log_den in log_den_values]
            results = list(tqdm(pool.imap(_run_cloudy_task_wrapper, tasks), total=len(tasks)))

        for task_index, (redshift, log_temp, log_den, _, _) in enumerate(tasks):
            result = results[task_index]
            for ion in result.keys():
                if ion not in tables:
                    tables[ion] = np.zeros((len(redshift_values), len(log_temp_values), len(log_den_values)))
                redshift_index = np.searchsorted(redshift_values, redshift, side='left')
                temp_index = np.searchsorted(log_temp_values, log_temp, side='left')
                den_index = np.searchsorted(log_den_values, log_den, side='left')
                tables[ion][redshift_index, temp_index, den_index] = result[ion]

        return cls(redshift_values, log_temp_values, log_den_values, tables)



class V1IonFractionTable(IonFractionTableBase):
    """Calculates ion fractions from an archived pynbody v1 table"""
    def __init__(self, filename=None):
        if filename is None:
            filename = os.path.join(os.path.dirname(__file__), "ionfracs.npz")
        if os.path.exists(filename):
            # import data
            logger.info("Loading %s" % filename)
            self._table = np.load(filename)
        else:
            raise OSError("ionfracs.npz (Ion Fraction table) not found")

    def calculate(self, simulation, ion='ovi'):
        x_vals = self._table['redshiftvals'].view(np.ndarray)
        y_vals = self._table['tempvals'].view(np.ndarray)
        z_vals = self._table['denvals'].view(np.ndarray)
        vals = self._table[ion + 'if'].view(np.ndarray)
        return self._calculate_with_table(simulation, x_vals, y_vals, z_vals, vals)

    def _calculate_with_table(self, simulation, x_vals, y_vals, z_vals, vals):
        x = np.zeros(len(simulation.gas))
        x[:] = simulation.properties['z']
        y = np.log10(simulation.gas['temp']).view(np.ndarray)
        z = np.log10(simulation.gas['rho'].in_units('m_p cm^-3')).view(np.ndarray)

        self._clamp_values(x, np.min(x_vals), np.max(x_vals))
        self._clamp_values(y, np.min(y_vals), np.max(y_vals))
        self._clamp_values(z, np.min(z_vals), np.max(z_vals))

        # interpolate
        result_array = interpolate3d(x, y, z, x_vals, y_vals, z_vals, vals)

        return 10 ** result_array

class V1DuffyIonFractionTable(V1IonFractionTable):
    """Calculates HI ion fractions using Alan Duffy's archived pynbody v1 table with self-shielding.

    Only HI fractions are available in this table. It is not recommended for new work."""

    def __init__(self, selfshield = False):
        """Initialise the table

        If selfshield is True, self-shielding from Duffy et al 2012 is applied."""
        filename = os.path.join(os.path.dirname(__file__), "h1.hdf5")
        if os.path.exists(filename):
            logger.info("Loading %s" % filename)
            self._table = h5py.File(filename, 'r')
        else:
            raise FileNotFoundError("h1.hdf5 (HI Fraction table) not found")

        self._selfshield = selfshield

    def calculate(self, simulation, ion='ovi'):
        if ion.lower()!='hi':
            raise ValueError("This table only contains HI fractions")

        hi = self._calculate_with_table(simulation, np.asarray(self._table['logd']), np.asarray(self._table['logt']),
                                        np.asarray(self._table['redshift']), np.log10(self._table['ionbal']))

        if self._selfshield:
            # NB this is currently untested and only retained for (probable) backward compatibility
            # However, it looks like it sets HI fraction to zero in high density, low T regions; is that right?

            ## Selfshield criteria from Duffy et al 2012a for EoS gas
            hi[simulation.gas['OnEquationOfState'] == 1.] = 0.
            hi[(simulation.gas['p'].in_units('K k cm**-3') > 150.)
               & (simulation.gas['temp'].in_units('K') < 10.**(4.5))] = 0.

        return hi



_ion_table = None
_default_ion_table = 'hm12'

class IonTableContext(util.SettingControl):
    """Context manager for temporarily using a custom ionisation fraction table"""
    def __init__(self, ion_table):
        super().__init__(globals(), "_ion_table", ion_table)

def get_current_ion_table() -> IonFractionTableBase:
    """Get the currently loaded ionisation table. If none is loaded, the default is loaded and returned.

    Returns
    -------
    IonFractionTableBase
        The currently loaded ionisation table.
    """
    global _ion_table
    if _ion_table is None:
        use_custom_ion_table(_default_ion_table)
    return _ion_table

def use_custom_ion_table(path_or_table):
    """Select an ionisation table to use for subsequent calculations.

    The specified table will be used for all subsequent calls to :func:`calculate`. A context manager is returned,
    so you can use this function in a ``with`` block to temporarily use a custom table, i.e.:

    >>> with use_custom_ion_table('FG20'):
    ...     civ_fg20 = calculate(sim, 'CIV')
    >>> civ_hm12 = calculate(sim, 'CIV')

    Here the first calculation uses the FG20 table, while the second uses the HM12 table. However, you do not
    need to use a context manager if you want to use the custom table indefinitely.

    Available tables are:

    * HM12: calculated using cloudy 23.01 with the HM12 background.

    * FG20: calculated by replacing the HM12 background in cloudy with the FG20 table. Unfortunately this
      involves some hacking due to the architecture of cloudy. One needs to download the FG20 table from
      https://galaxies.northwestern.edu/uvb-fg20/, and follow the instructions in the readme file.

    * v1: gives results calculated by Greg Stinson for pynbody v1. It is retained only for backwards compatibility
      and we do not recommend using it for new work.

    * v1_duffy: gives results for hydrogen only, calculated by Alan Duffy for pynbody v1. It is retained only for
      backwards compatibility and we do not recommend using it for new work.

    * v1_duffy_shielded: gives results for hydrogen only, calculated by Alan Duffy for pynbody v1, with self-shielding
      prescription turned on. It is retained only for backwards compatibility and we do not recommend using it for new
      work.

    Parameters
    ----------

    path_or_table : str or IonFractionTableBase
        If a string, the name of the table to use. If an instance of IonFractionTableBase, the table to use.
        Built-in tables are 'v1', 'v1_duffy', 'v1_duffy_shielded', 'hm12', 'fg20' and are case-insensitive.
        See above for the origins of these tables.

    Returns
    -------
    IonTableContext
        A context manager that can be used to control the lifetime of the table. See above for usage guidance.

    """
    if isinstance(path_or_table, IonFractionTableBase):
        table = path_or_table
    elif path_or_table.lower() == 'v1':
        table = V1IonFractionTable()
    elif path_or_table.lower() == 'v1_duffy':
        table = V1DuffyIonFractionTable()
    elif path_or_table.lower() == 'v1_duffy_shielded':
        table = V1DuffyIonFractionTable(selfshield=True)
    else:
        table = IonFractionTable.load(path_or_table)

    return IonTableContext(table)

def calculate(sim, ion='OVI'):
    """Calculate the fractions for the specified ion in the given simulation.

    Uses the currently loaded ion fraction table. If no table is loaded, the default is used. See
    :func:`use_custom_ion_table` for how to load a custom table.

    For important notes on the way that ion fractions are estimated, see the module documentation
    (:mod:`pynbody.analysis.ionfrac`).

    Parameters
    ----------

    sim : pynbody.snapshot.SimSnap
        The simulation snapshot to calculate the ion fractions for. The gas particles must have 'rho' and 'temp'
        fields.

    ion : str
        The name of the ion to calculate the fraction for, e.g. "HI", "CIV", "MgII" etc. Molecular hydrogen is "H2".
        The default is 'OVI'. Case insensitive.

    Returns
    -------

    array-like
        The ion fraction for each gas particle in the simulation, according to the table. This is defined as the
        number density of the specified ion divided by the number density of the element it is derived from. As
        such, the ion fractions for a particular element sum to 1.

    """
    return get_current_ion_table().calculate(sim, ion)
