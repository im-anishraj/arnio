"""Integration helpers for the Python data ecosystem."""

from .pandas import ArnioPandasAccessor

__all__ = ["ArnioPandasAccessor"]

from .frame import ArFrame
from_dict = ArFrame.from_dict

