import numpy as np
import h5py
import pandas
from pathlib import Path

class McHDF(object):
    """Helper functions for HDF5 storage of items"""

    nxsEntryPoint = '/entry1/'
    def __init__(self):
        pass

    def _HDFloadKV(self, filename=None, path=None, datatype=None, default=None):
        if datatype is None:
            with h5py.File(filename, "r") as h5f:
                if path not in h5f:
                    return default
                # print("picking out value from path {}".format(path))
                value = h5f[path][()]

        elif datatype is "dict" or datatype is "dictToPandas":
            # these *may* have to be cast into the right datatype, h5py seems to assume int for much of this data
            value = dict()
            with h5py.File(filename, "r") as h5f:
                if path not in h5f:
                    return default
                for key, keyValue in h5f[path].items():
                    # print("Key: {}, Value: {}".format(key, value.value))
                    value.update({key: keyValue[()]})

        if datatype is "dictToPandas":
            cols, idx, vals = (
                value.pop("columns"),
                value.pop("index"),
                value.pop("data"),
            )
            value = pandas.DataFrame(data=vals, columns=cols, index=idx)

        return value

    def _HDFstoreKV(self, filename=None, path=None, key=None, value=None):
        assert filename is not None, "filename (output filename) cannot be empty"
        assert path is not None, "HDF5 path cannot be empty"
        assert key is not None, "key cannot be empty"

        """stores the settings in an output file (HDF5)"""
        if isinstance(value, pandas.DataFrame):
            # special case, iterate over keys.
            for pkey in value.keys():
                self._HDFstoreKV(filename = filename, path = f'{path}{key}/', key = pkey, value = value[pkey].values)
            return

        if isinstance(value, dict):
            # special case, iterate over keys.
            for dkey, dvalue in value.items():
                self._HDFstoreKV(filename = filename, path = f'{path}{key}/', key = dkey, value = dvalue)
            return

        with h5py.File(filename, "a") as h5f:
            h5g = h5f.require_group(path)

            # store arrays:
            # convert all compatible data types to arrays:
            if type(value) is tuple or type(value) is list:
                value = np.array(value)
            if isinstance(value, Path):
                value = value.as_posix()
            if value is not None and type(value) is np.ndarray:
                # HDF cannot store unicode string arrays, these need to be stored as a special type:
                if str(value.dtype).startswith("<U"):
                    value = value.astype(h5py.special_dtype(vlen=str))
                # store the data in the prefiously defined group:
                try:
                    h5g.require_dataset(
                        key, data=value, shape=value.shape, dtype=value.dtype
                    )
                except TypeError: 
                    #if it exists, but isn't of the right shape or compatible dtype:
                    del h5g[key]
                    h5g.require_dataset(
                        key, data=value, shape=value.shape, dtype=value.dtype
                    )


            # non-array values are stored here:
            elif value is not None:
                # try and see if the destination already exists.. This can be done by require_dataset, but that requires shape and dtype to be specified. This method doesn't:
                dset = h5g.get(key, None)
                if dset is None:
                    h5g.create_dataset(key, data=value)
                else:
                    dset[()] = value

            # we are skipping None values for now, that case should be caught on load.
