import pandas

import mcsas3.cli_tools as cli_tools


def test_cli_optimize_uses_processing_data_workflow(monkeypatch, tmp_path):
    data_file = tmp_path / "input.dat"
    data_file.write_text("0.1 1.0 0.1\n")
    result_file = tmp_path / "result.h5"
    read_config_file = tmp_path / "read.yaml"
    read_config_file.write_text("nbins: 5\ndataRange: [1.0, 4.0]\n")
    run_config_file = tmp_path / "run.yaml"
    run_config_file.write_text("modelName: sphere\nnRep: 3\n")

    processing = object()
    calls: dict[str, object] = {}

    def fake_prepare(filename, *, result_index, **read_config):
        calls["prepare"] = (filename, result_index, read_config)
        return processing

    def fake_optimize(processing_input, result_path, **kwargs):
        calls["optimize"] = (processing_input, result_path, kwargs)

    monkeypatch.setattr(cli_tools.workflows, "prepare_1d_processing_data_from_file", fake_prepare)
    monkeypatch.setattr(cli_tools.workflows, "optimize_processing_data", fake_optimize)

    cli_tools.McSAS3_cli_optimize(
        dataFile=data_file,
        resultFile=result_file,
        readConfigFile=read_config_file,
        runConfigFile=run_config_file,
        resultIndex=2,
        deleteIfExists=False,
        nThreads=4,
    )

    assert calls["prepare"] == (data_file, 2, {"nbins": 5, "dataRange": [1.0, 4.0]})
    optimize_processing, optimize_result, optimize_kwargs = calls["optimize"]
    assert optimize_processing is processing
    assert optimize_result == result_file
    assert optimize_kwargs["result_index"] == 2
    assert optimize_kwargs["seed"] is None
    assert optimize_kwargs["nCores"] == 4
    assert optimize_kwargs["modelName"] == "sphere"
    assert optimize_kwargs["nRep"] == 3
    assert optimize_kwargs["processing_metadata"]["filename"] == data_file
    assert optimize_kwargs["processing_metadata"]["nbins"] == 5


def test_cli_histogram_uses_processing_data_workflow(monkeypatch, tmp_path):
    result_file = tmp_path / "result.h5"
    result_file.write_text("placeholder")
    hist_config_file = tmp_path / "hist.yaml"
    hist_config_file.write_text("parameter: radius\nnBin: 20\n")

    processing = object()
    analysis_result = object()
    calls: dict[str, object] = {}

    def fake_load(filename, *, result_index):
        calls["load"] = (filename, result_index)
        return processing

    def fake_analysis(input_file, analysis_data, hist_ranges, store=False, resultIndex=1):
        calls["analysis"] = (input_file, analysis_data, hist_ranges.copy(), store, resultIndex)
        return analysis_result

    class FakePlot:
        def resultCard(self, mcres, saveHistFile=None):
            calls["plot"] = (mcres, saveHistFile)

    monkeypatch.setattr(cli_tools.workflows, "load_result_processing_data", fake_load)
    monkeypatch.setattr(cli_tools, "McAnalysis", fake_analysis)
    monkeypatch.setattr(cli_tools.mc_plot, "McPlot", FakePlot)

    cli_tools.McSAS3_cli_histogram(
        resultFile=result_file,
        histConfigFile=hist_config_file,
        resultIndex=3,
    )

    assert calls["load"] == (result_file, 3)
    analysis_input_file, analysis_processing, hist_ranges, store, result_index = calls["analysis"]
    assert analysis_input_file == result_file
    assert analysis_processing is processing
    assert isinstance(hist_ranges, pandas.DataFrame)
    assert hist_ranges.loc[0, "parameter"] == "radius"
    assert hist_ranges.loc[0, "nBin"] == 20
    assert store is True
    assert result_index == 3
    assert calls["plot"] == (analysis_result, result_file.with_suffix(".pdf"))
