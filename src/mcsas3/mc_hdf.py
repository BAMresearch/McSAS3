import inspect
import logging
from collections.abc import Iterable
from pathlib import Path, PurePosixPath

import attrs
import h5py
import numpy as np
import pandas
import pint
from attrs import validators

from .data_model import BaseData, DataBundle, ProcessingData

PROCESSING_DATA_GROUP = "processingData"
PROCESSING_DATA_SCHEMA = "mcsas3.processing_data"
PROCESSING_DATA_SCHEMA_VERSION = 1

logger = logging.getLogger(__name__)


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
        ],
    )

    def __attrs_post_init__(self):
        self.resultIndex = int(self.resultIndex)

    @property
    def nxsEntryPoint(self):
        return PurePosixPath(f"/analyses/MCResult{self.resultIndex}")


def loadKVPairs(filename: Path, path: PurePosixPath, keys: Iterable) -> Iterable:
    """Load key-value pairs from HDF5 file"""
    if filename is None:
        raise ValueError("filename cannot be empty")
    if path is None:
        raise ValueError("HDF5 path cannot be empty")
    with h5py.File(filename, "r") as h5f:
        for key in keys:
            yield key, h5f[str(path / key)][()]


def loadKV(filename: Path, path: PurePosixPath, datatype=None, default=None, dbg=False):
    """Load a single key-value pair from HDF5 file"""
    path = str(path)
    if dbg:
        logger.debug("loadKV(%s)", path)
    if not Path(filename).is_file():
        return default
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
            (colname.decode("utf8") if isinstance(colname, bytes) else colname) for colname in value.columns
        ]

    return value


def storeKVPairs(filename: Path, path: PurePosixPath, pairs: Iterable) -> None:
    if filename is None:
        raise ValueError("filename cannot be empty")
    if path is None:
        raise ValueError("HDF5 path cannot be empty")
    try:
        for key, value in pairs:
            storeKV(filename=filename, path=path / key, value=value)
    except Exception:
        logger.exception("Error storing HDF5 value for %s of type %s.", path / key, type(value))
        raise


def storeKV(filename: Path, path: PurePosixPath, value=None) -> None:
    if filename is None:
        raise ValueError("filename (output filename) cannot be empty")
    if path is None:
        raise ValueError("HDF5 path cannot be empty")

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


def _decode_hdf_value(value):
    if isinstance(value, (bytes, bytearray, np.bytes_)):
        return value.decode()
    if isinstance(value, np.ndarray) and value.shape == ():
        return _decode_hdf_value(value[()])
    return value


def _require_clean_group(h5f: h5py.File, path: PurePosixPath | str) -> h5py.Group:
    path_str = str(path)
    if path_str in h5f:
        del h5f[path_str]
    return h5f.require_group(path_str)


def _store_basedata_group(group: h5py.Group, basedata: BaseData) -> None:
    group.attrs["units"] = str(basedata.units)
    group.attrs["rank_of_data"] = int(basedata.rank_of_data)
    group.create_dataset("signal", data=np.array(basedata.signal, copy=True))
    group.create_dataset("weights", data=np.array(basedata.weights, copy=True))
    uncertainties_group = group.create_group("uncertainties")
    for key, uncertainty in basedata.uncertainties.items():
        uncertainties_group.create_dataset(key, data=np.array(uncertainty, copy=True))


def _load_basedata_group(group: h5py.Group) -> BaseData:
    uncertainties = {}
    if "uncertainties" in group:
        uncertainties = {key: np.array(dataset[()], copy=True) for key, dataset in group["uncertainties"].items()}

    return BaseData(
        signal=np.array(group["signal"][()], copy=True),
        units=str(_decode_hdf_value(group.attrs.get("units", "dimensionless"))),
        uncertainties=uncertainties,
        weights=np.array(group["weights"][()], copy=True) if "weights" in group else np.array(1.0),
        rank_of_data=int(group.attrs.get("rank_of_data", 0)),
    )


def storeDataBundle(filename: Path, path: PurePosixPath, bundle: DataBundle) -> None:
    with h5py.File(filename, "a") as h5f:
        group = _require_clean_group(h5f, path)
        if getattr(bundle, "default_plot", None) is not None:
            group.attrs["default_plot"] = str(bundle.default_plot)
        if getattr(bundle, "description", None) is not None:
            group.attrs["description"] = str(bundle.description)
        for key, basedata in bundle.items():
            basedata_group = group.create_group(key)
            _store_basedata_group(basedata_group, basedata)


def loadDataBundle(filename: Path, path: PurePosixPath, default=None):
    if not Path(filename).is_file():
        return default

    with h5py.File(filename, "r") as h5f:
        path_str = str(path)
        if path_str not in h5f:
            return default

        group = h5f[path_str]
        bundle = DataBundle()
        if "default_plot" in group.attrs:
            bundle.default_plot = str(_decode_hdf_value(group.attrs["default_plot"]))
        if "description" in group.attrs:
            bundle.description = str(_decode_hdf_value(group.attrs["description"]))
        for key, value in group.items():
            if isinstance(value, h5py.Group):
                bundle[key] = _load_basedata_group(value)
        return bundle


def storeProcessingData(filename: Path, path: PurePosixPath, processing: ProcessingData) -> None:
    with h5py.File(filename, "a") as h5f:
        group = _require_clean_group(h5f, path)
        group.attrs["schema"] = PROCESSING_DATA_SCHEMA
        group.attrs["schema_version"] = PROCESSING_DATA_SCHEMA_VERSION
        analysis_stage = getattr(processing, "analysis_stage", None)
        if analysis_stage is not None:
            group.attrs["analysis_stage"] = str(analysis_stage)
        for stage_name, bundle in processing.items():
            stage_group = group.create_group(stage_name)
            if getattr(bundle, "default_plot", None) is not None:
                stage_group.attrs["default_plot"] = str(bundle.default_plot)
            if getattr(bundle, "description", None) is not None:
                stage_group.attrs["description"] = str(bundle.description)
            for key, basedata in bundle.items():
                basedata_group = stage_group.create_group(key)
                _store_basedata_group(basedata_group, basedata)


def loadProcessingData(filename: Path, path: PurePosixPath, default=None):
    if not Path(filename).is_file():
        return default

    with h5py.File(filename, "r") as h5f:
        path_str = str(path)
        if path_str not in h5f:
            return default

        group = h5f[path_str]
        processing = ProcessingData()
        if "analysis_stage" in group.attrs:
            setattr(processing, "analysis_stage", str(_decode_hdf_value(group.attrs["analysis_stage"])))

        for stage_name, stage_group in group.items():
            if not isinstance(stage_group, h5py.Group):
                continue
            bundle = DataBundle()
            if "default_plot" in stage_group.attrs:
                bundle.default_plot = str(_decode_hdf_value(stage_group.attrs["default_plot"]))
            if "description" in stage_group.attrs:
                bundle.description = str(_decode_hdf_value(stage_group.attrs["description"]))
            for key, basedata_group in stage_group.items():
                if isinstance(basedata_group, h5py.Group):
                    bundle[key] = _load_basedata_group(basedata_group)
            processing[stage_name] = bundle

        return processing
