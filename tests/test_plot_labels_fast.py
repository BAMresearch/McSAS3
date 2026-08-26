from mcsas3.parameter_units import is_size_fit_parameter
from mcsas3.plot_labels import fit_parameter_axis_label


def test_fit_parameter_axis_label_adds_nm_for_size_parameters():
    assert fit_parameter_axis_label("radius") == "radius (nm)"
    assert fit_parameter_axis_label("A_radius") == "A_radius (nm)"
    assert fit_parameter_axis_label("length") == "length (nm)"
    assert fit_parameter_axis_label("thick_shell") == "thick_shell (nm)"
    assert fit_parameter_axis_label("rg") == "rg (nm)"
    assert fit_parameter_axis_label("d_spacing") == "d_spacing (nm)"


def test_fit_parameter_axis_label_leaves_non_size_parameters_unchanged():
    assert fit_parameter_axis_label("factor") == "factor"
    assert fit_parameter_axis_label("phi") == "phi"
    assert fit_parameter_axis_label("radius_effective_mode") == "radius_effective_mode"
    assert fit_parameter_axis_label("radius_pd_type") == "radius_pd_type"
    assert not is_size_fit_parameter("radius_effective_mode")
    assert not is_size_fit_parameter("radius_pd_type")
