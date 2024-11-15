import inspect
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

import h5py
import numpy as np
import pandas
import pint
import attrs
from attrs import validators


@attrs.define
class ResultIndex(object):
    """
    Index of the result in the NXentry.
    """
    
    resultIndex: int = attrs.field(
        default=1,
        validator=[
            validators.instance_of(int),
            validators.ge(0),
            ]
    )

    def __attrs_post_init__(self, resultIndex: int = 1):
        self.resultIndex = resultIndex

    @property
    def nxsEntryPoint(self):
        return PurePosixPath(f"/analyses/MCResult{self.resultIndex}")

def loadKVPairs(filename: Path, path: PurePosixPath, keys: Iterable) -> Iterable:
    """Load key-value pairs from HDF5 file"""
    assert filename is not None
    assert path is not None
    with h5py.File(filename, "r") as h5f:
        for key in keys:
            yield key, h5f[str(path / key)][()]

def loadKV(filename: Path, path: PurePosixPath, datatype=None, default=None, dbg=False):
    """Load a single key-value pair from HDF5 file"""
    path = str(path)
    if dbg:
        print(f"loadKV({path})")
    with h5py.File(filename, "r") as h5f:
        if path not in h5f:
            return default

    if datatype is None or datatype == "str" or inspect.isclass(datatype):
        with h5py.File(filename, "r") as h5f:
            value = h5f[path][()]
        if (datatype == "str" or datatype == Path) and not isinstance(value, str):
            if isinstance(value, (bytes, bytearray)):
                value = value.decode()
            else:
                value = str(value)
        if inspect.isclass(datatype):
            value = datatype(value)

    elif datatype in ("dict", "dictToPandas"):
        value = {}
        with h5py.File(filename, "r") as h5f:
            for key, keyValue in h5f[path].items():
                if isinstance(keyValue, h5py.Group):
                    subDict = {}
                    for gkey, gValue in keyValue.items():
                        subDict.update({gkey: gValue[()]})
                    value.update({key: subDict})
                else:
                    value.update({key: keyValue[()]})
                    if isinstance(keyValue[()], np.ndarray):
                        if isinstance(keyValue[()][0], bytes):
                            value.update({key: np.array([i.decode() for i in keyValue[()]])})

    if datatype == "dictToPandas":
        cols, idx, vals = (
            value.pop("columns"),
            value.pop("index"),
            value.pop("data"),
        )
        value = pandas.DataFrame(data=vals, columns=cols, index=idx)
        value.columns = [
            (colname.decode("utf8") if isinstance(colname, bytes) else colname)
            for colname in value.columns
        ]

    return value

def storeKVPairs(filename: Path, path: PurePosixPath, pairs: Iterable) -> None:
    assert filename is not None
    assert path is not None
    try:
        for key, value in pairs:
            storeKV(filename=filename, path=path / key, value=value)
    except Exception:
        print(f"Error for path {key} and value '{value}' of type {type(value)}.")
        raise

def storeKV(filename: Path, path: PurePosixPath, value=None) -> None:
    assert filename is not None, "filename (output filename) cannot be empty"
    assert path is not None, "HDF5 path cannot be empty"

    if isinstance(value, (dict, pandas.DataFrame)):
        storeKVPairs(filename, path, value.items())
        return

    path, key = path.parent, path.name
    with h5py.File(filename, "a") as h5f:
        h5g = h5f.require_group(str(path))
        dset, unit = None, None
        if isinstance(value, pint.Quantity):
            value, unit = value.m, value.u
        if isinstance(value, Path):
            value = value.as_posix()
        if isinstance(value, pandas.Timestamp):
            value = value.timestamp()
        if isinstance(value, (list, tuple)):
            value = np.array(value)
        if isinstance(value, (np.ndarray, pandas.Series)):
            if str(value.dtype).startswith("<U") or str(value.dtype).startswith("object"):
                value = value.astype(h5py.special_dtype(vlen=str))

            try:
                dset = h5g.require_dataset(key, data=value, shape=value.shape, dtype=value.dtype)
            except TypeError:
                del h5g[key]
                dset = h5g.require_dataset(key, data=value, shape=value.shape, dtype=value.dtype)

        elif value is not None:
            dset = h5g.get(key, None)
            if dset is None:
                dset = h5g.create_dataset(key, data=value)
            else:
                dset[()] = value

        if unit is not None:
            dset.attrs["unit"] = str(unit)