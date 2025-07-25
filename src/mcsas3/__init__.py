# -*- coding: utf-8 -*-
# __init__.py

"""
Refactored McSAS implementation
"""

__version__ = "1.0.5"

from pint import UnitRegistry, set_application_registry

ureg = UnitRegistry(system="SI")
Q_ = ureg.Quantity
# recommended for pickling and unpickling:
set_application_registry(ureg)
ureg.formatter.default_format = "~P"
ureg.setup_matplotlib(True)

# vim: set ts=4 sts=4 sw=4 tw=0:
