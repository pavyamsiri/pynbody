import copy

from .simsnap import SimSnap


class UnderlyingClassMixin:
    def __init__(self, underlying_class, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._underlying_class = underlying_class

    def _find_deriving_function(self, name):
        cl = self._underlying_class
        if cl in self._derived_quantity_registry \
                and name in self._derived_quantity_registry[cl]:
            return self._derived_quantity_registry[cl][name]
        else:
            return super()._find_deriving_function(name)

class CopyOnAccessSimSnap(UnderlyingClassMixin, SimSnap):
    """Behaves like an IndexedSubSnap but copies data instead of pointing towards it"""

    def __init__(self, base: SimSnap, underlying_class=None):
        self._copy_from = base
        if underlying_class is None:
            underlying_class = type(base.ancestor)

        super().__init__(underlying_class)

        self._unifamily = base._unifamily
        self._file_units_system = base._file_units_system
        self._num_particles = len(base)
        self._family_slice = copy.deepcopy(base._family_slice)
        self._filename = base._filename+":copied_on_access"
        self.properties = copy.deepcopy(base.properties)


    def _load_array(self, array_name, fam=None):
        try:
            with self._copy_from.lazy_derive_off:
                if fam is None:
                    self[array_name] = self._copy_from[array_name]
                else:
                    self[fam][array_name] = self._copy_from[fam][array_name]
        except KeyError as e:
            raise OSError("Not found in underlying snapshot") from e

    def loadable_keys(self, fam=None):
        if fam is None:
            loaded_keys_in_parent = self._copy_from.keys()
        else:
            loaded_keys_in_parent = self._copy_from.family_keys(fam)
        return set(self._copy_from.loadable_keys(fam)).union(loaded_keys_in_parent)


