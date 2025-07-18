"""Configuration management for OVERKILL"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import yaml
from dataclasses import dataclass, asdict


@dataclass
class OverclockProfile:
    """Overclock configuration profile"""
    name: str
    arm_freq: int
    gpu_freq: int
    over_voltage: int
    over_voltage_delta: int = 0
    description: str = ""


class Config:
    """Centralized configuration management"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path("/etc/overkill")
        self.config_file = self.config_dir / "config.json"
        self.profiles_file = self.config_dir / "profiles.yaml"
        
        # Default configuration
        self.defaults = {
            "version": "3.0.0",
            "profile": "balanced",
            "hardware": {
                "model": "Unknown",
                "memory_gb": 8,
                "nvme_device": None,
                "cooling_type": "unknown",
                "silicon_grade": "unknown"
            },
            "overclock": {
                "enabled": False,
                "current_profile": "safe",
                "custom_settings": {}
            },
            "thermal": {
                "fan_mode": "auto",
                "target_temp": 65,
                "max_temp": 80,
                "fan_curve": [
                    {"temp": 40, "speed": 0},
                    {"temp": 50, "speed": 30},
                    {"temp": 60, "speed": 50},
                    {"temp": 70, "speed": 80},
                    {"temp": 80, "speed": 100}
                ]
            },
            "media": {
                "kodi": {
                    "installed": False,
                    "version": None,
                    "build_type": "stable",
                    "addons": [],
                    "cache_size": 524288000,
                    "buffer_mode": 1
                },
                "services": {
                    "samba": False,
                    "dlna": False,
                    "airplay": False,
                    "bluetooth": True
                }
            },
            "network": {
                "wifi_country": "US",
                "performance_mode": True,
                "wake_on_lan": True
            },
            "display": {
                "resolution": "auto",
                "refresh_rate": 60,
                "hdr": True,
                "overscan": 0
            }
        }
        
        # Default overclock profiles
        self.default_profiles = {
            "safe": OverclockProfile(
                name="safe",
                arm_freq=2400,
                gpu_freq=900,
                over_voltage=2,
                description="Conservative settings for stability"
            ),
            "balanced": OverclockProfile(
                name="balanced",
                arm_freq=2600,
                gpu_freq=950,
                over_voltage=3,
                description="Good performance with reasonable temps"
            ),
            "performance": OverclockProfile(
                name="performance",
                arm_freq=2700,
                gpu_freq=975,
                over_voltage=4,
                description="High performance, requires good cooling"
            ),
            "extreme": OverclockProfile(
                name="extreme",
                arm_freq=2800,
                gpu_freq=1000,
                over_voltage=5,
                over_voltage_delta=50000,
                description="Maximum performance, excellent cooling required"
            )
        }
        
        self._config = {}
        self._profiles = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from files"""
        # Load main config
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                self._config = self.defaults.copy()
        else:
            self._config = self.defaults.copy()
            self.save()
        
        # Load profiles
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r') as f:
                    profiles_data = yaml.safe_load(f)
                    self._profiles = {
                        name: OverclockProfile(**data)
                        for name, data in profiles_data.items()
                    }
            except Exception as e:
                print(f"Error loading profiles: {e}")
                self._profiles = self.default_profiles.copy()
        else:
            self._profiles = self.default_profiles.copy()
            self.save_profiles()
    
    def save(self) -> None:
        """Save configuration to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def save_profiles(self) -> None:
        """Save overclock profiles to file"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        profiles_data = {
            name: asdict(profile)
            for name, profile in self._profiles.items()
        }
        
        try:
            with open(self.profiles_file, 'w') as f:
                yaml.dump(profiles_data, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving profiles: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with dot notation support"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value with dot notation support"""
        keys = key.split('.')
        config = self._config
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self.save()
    
    def get_profile(self, name: str) -> Optional[OverclockProfile]:
        """Get an overclock profile by name"""
        return self._profiles.get(name)
    
    def add_profile(self, profile: OverclockProfile) -> None:
        """Add or update an overclock profile"""
        self._profiles[profile.name] = profile
        self.save_profiles()
    
    def get_all_profiles(self) -> Dict[str, OverclockProfile]:
        """Get all available overclock profiles"""
        return self._profiles.copy()
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to defaults"""
        self._config = self.defaults.copy()
        self._profiles = self.default_profiles.copy()
        self.save()
        self.save_profiles()