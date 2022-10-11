import numpy as np
import h5py
import pandas
from pathlib import Path
import inspect


class McHDF(object):
    """Helper functions for HDF5 storage of items. Appears as base class of many McSAS3 methods"""

    resultIndex = 1  # per default number 1, but can be changed.
    nxsEntryPoint = f"/analyses/MCResult{resultIndex}/"  # changed to full path to result, not sure if this can work like this

    def __init__(self)->None:
        pass

    def _HDFSetResultIndex(self, resultIndex:int=None)->None:
        # resultIndex = -1 should go to the last existing one
        #
        assert (
            resultIndex is not None
        ), "setting resultIndex to None (append new result) is not implemented yet"
        assert (
            resultIndex >= 0
        ), 'resultIndex should be positive, "set to last existing" (resultIndex = -1) is not implemented yet'
        self.resultIndex = resultIndex
        self.nxsEntryPoint = f"/analyses/MCResult{self.resultIndex}/"

    def _HDFloadKV(self, filename:Path=None, path: str = None, datatype=None, default=None): # outputs any hdf5 value type
        with h5py.File(filename, "r") as h5f:
            if path not in h5f:
                return default

        if datatype is None or datatype == "str" or inspect.isclass(datatype):
            # print("picking out value from path {}".format(path))
            with h5py.File(filename, "r") as h5f:
                value = h5f[path][()]
            if (datatype == "str" or datatype == Path) and not isinstance(value, str):
                if isinstance(value, bytes) or isinstance(value, bytearray):
                    value = value.decode()
                else:
                    # try this:
                    value = str(value)
            if inspect.isclass(
                datatype
            ):  # assuming it is something like Path, int or float here..
                value = datatype(value)

        elif datatype == "dict" or datatype == "dictToPandas":
            # these *may* have to be cast into the right datatype, h5py seems to assume int for much of this data
            value = dict()
            with h5py.File(filename, "r") as h5f:
                # not sure why the following doesn't work for h5py Groups,
                for key, keyValue in h5f[path].items():
                    # print("Key: {}, Value: {}".format(key, keyValue))
                    if isinstance(
                        keyValue, h5py.Group
                    ):  # it's a group, so needs to be unpacked too. This should probably be a recursive function
                        subDict = {}
                        for gkey, gValue in keyValue.items():
                            subDict.update({gkey: gValue[()]})
                        value.update({key: subDict})
                    else:
                        value.update({key: keyValue[()]})
                        # special case: array of bytes objects that should've been strings:
                        if isinstance(keyValue[()], np.ndarray):
                            if isinstance(keyValue[()][0], bytes):
                                value.update(
                                    {key: np.array([i.decode() for i in keyValue[()]])}
                                )
                        elif isinstance(keyValue[()], bytes):
                            value.update({key: keyValue[()].decode()})

        if datatype == "dictToPandas":
            cols, idx, vals = (
                value.pop("columns"),
                value.pop("index"),
                value.pop("data"),
            )
            value = pandas.DataFrame(data=vals, columns=cols, index=idx)
            # ensure column names are str:
            value.columns = [
                (colname.decode("utf8") if isinstance(colname, bytes) else colname)
                for colname in value.columns
            ]

        return value

    def _HDFstoreKV(self, filename:Path=None, path:str=None, key:str=None, value=None)->None:
        assert filename is not None, "filename (output filename) cannot be empty"
        assert path is not None, "HDF5 path cannot be empty"
        assert key is not None, "key cannot be empty"

        """stores the settings in an output file (HDF5)"""
        if isinstance(value, pandas.DataFrame):
            # special case, iterate over keys.
            for pkey in value.keys():
                self._HDFstoreKV(
                    filename=filename,
                    path=f"{path}{key}/",
                    key=pkey,
                    value=value[pkey].values,
                )
            return

        if isinstance(value, dict):
            # special case, iterate over keys.
            for dkey, dvalue in value.items():
                self._HDFstoreKV(
                    filename=filename, path=f"{path}{key}/", key=dkey, value=dvalue
                )
            return

        with h5py.File(filename, "a") as h5f:
            h5g = h5f.require_group(path)

            # store arrays:
            # convert all compatible data types to arrays:
            if type(value) is tuple or type(value) is list:
                value = np.array(value)
            if isinstance(value, Path):
                value = value.as_posix()
            if value is not None and type(value) in (np.ndarray, pandas.Series):
                # HDF cannot store unicode string arrays, these need to be stored as a special type:
                if str(value.dtype).startswith("<U"):
                    value = value.astype(h5py.special_dtype(vlen=str))
                if str(value.dtype).startswith(
                    "object"
                ):  # try casting it into str class
                    value = value.astype(h5py.special_dtype(vlen=str))

                # store the data in the prefiously defined group:
                try:
                    h5g.require_dataset(
                        key, data=value, shape=value.shape, dtype=value.dtype
                    )
                except TypeError:
                    # if it exists, but isn't of the right shape or compatible dtype:
                    del h5g[key]
                    h5g.require_dataset(
                        key, data=value, shape=value.shape, dtype=value.dtype
                    )

            # non-array values are stored here:
            elif value is not None:
                # try and see if the destination already exists.. This can be done by require_dataset, but that requires shape and dtype to be specified. This method doesn't:
                dset = h5g.get(key, None)

                # if str(value.dtype).startswith("object"): # try casting it into str class
                #     value = value.astype(h5py.special_dtype(vlen=str))

                if dset is None:
                    h5g.create_dataset(key, data=value)
                else:
                    dset[()] = value

            # we are skipping None values for now, that case should be caught on load.
