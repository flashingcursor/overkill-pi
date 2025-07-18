"""OVERKILL - Professional Media Center Configuration for Raspberry Pi 5"""

__version__ = "3.0.0"
__author__ = "OVERKILL Team"
__description__ = "UNLIMITED POWER. ZERO RESTRICTIONS."

from .configurator import OverkillConfigurator
from .installer import OverkillInstaller

__all__ = ["OverkillConfigurator", "OverkillInstaller"]