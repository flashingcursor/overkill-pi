"""Overclocking management for Raspberry Pi 5"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from ..core.logger import logger
from ..core.utils import backup_file, atomic_write, run_command
from ..core.config import OverclockProfile


@dataclass
class OverclockResult:
    """Result of overclock operation"""
    success: bool
    message: str
    reboot_required: bool = True


class OverclockManager:
    """Manage Raspberry Pi 5 overclocking"""
    
    def __init__(self, config_file: Path = Path("/boot/config.txt"),
                 armbian_env: Path = Path("/boot/armbianEnv.txt")):
        self.config_file = config_file
        self.armbian_env = armbian_env
        self.is_armbian = armbian_env.exists()
        
    def get_current_settings(self) -> Dict[str, int]:
        """Get current overclock settings"""
        settings = {
            "arm_freq": 2400,  # Default
            "gpu_freq": 900,   # Default
            "over_voltage": 0,
            "over_voltage_delta": 0
        }
        
        try:
            # Check config.txt
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    content = f.read()
                    
                    # Extract values using regex
                    for key in settings.keys():
                        match = re.search(f'^{key}=(\d+)', content, re.MULTILINE)
                        if match:
                            settings[key] = int(match.group(1))
            
            # Also check vcgencmd if available
            ret, stdout, _ = run_command(["vcgencmd", "get_config", "arm_freq"])
            if ret == 0 and "=" in stdout:
                settings["arm_freq"] = int(stdout.split("=")[1])
                
        except Exception as e:
            logger.error(f"Failed to get current overclock settings: {e}")
        
        return settings
    
    def validate_profile(self, profile: OverclockProfile) -> Tuple[bool, str]:
        """Validate overclock profile settings"""
        
        # Check ARM frequency
        if profile.arm_freq < 600 or profile.arm_freq > 3000:
            return False, f"Invalid ARM frequency: {profile.arm_freq}MHz"
        
        # Check GPU frequency
        if profile.gpu_freq < 300 or profile.gpu_freq > 1100:
            return False, f"Invalid GPU frequency: {profile.gpu_freq}MHz"
        
        # Check voltage
        if profile.over_voltage < -16 or profile.over_voltage > 8:
            return False, f"Invalid over_voltage: {profile.over_voltage}"
        
        # Check voltage delta
        if profile.over_voltage_delta < 0 or profile.over_voltage_delta > 100000:
            return False, f"Invalid over_voltage_delta: {profile.over_voltage_delta}"
        
        return True, "Profile validated"
    
    def apply_profile(self, profile: OverclockProfile) -> OverclockResult:
        """Apply an overclock profile"""
        
        # Validate profile
        valid, message = self.validate_profile(profile)
        if not valid:
            return OverclockResult(False, message, False)
        
        try:
            # Backup current config
            if not backup_file(self.config_file):
                return OverclockResult(False, "Failed to backup config.txt", False)
            
            # Read current config
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Check if we have OVERKILL section
            if "# OVERKILL PI 5 CONFIGURATION" not in content:
                # Add new section
                content += self._generate_overclock_section(profile)
            else:
                # Update existing section
                content = self._update_overclock_section(content, profile)
            
            # Write updated config
            if not atomic_write(self.config_file, content):
                return OverclockResult(False, "Failed to write config.txt", False)
            
            # Update Armbian env if needed
            if self.is_armbian:
                self._update_armbian_env()
            
            logger.info(f"Applied overclock profile: {profile.name}")
            return OverclockResult(True, 
                f"Successfully applied {profile.name} profile. Reboot required.", 
                True)
            
        except Exception as e:
            logger.error(f"Failed to apply overclock profile: {e}")
            return OverclockResult(False, f"Error: {str(e)}", False)
    
    def _generate_overclock_section(self, profile: OverclockProfile) -> str:
        """Generate overclock configuration section"""
        
        section = f"""

# OVERKILL PI 5 CONFIGURATION
# Profile: {profile.name}
# {profile.description}
dtparam=pciex1_gen=3
gpu_mem=1024
dtoverlay=vc4-kms-v3d-pi5
max_framebuffers=3
hdmi_enable_4kp60=1
force_turbo=1
arm_freq={profile.arm_freq}
gpu_freq={profile.gpu_freq}
over_voltage={profile.over_voltage}
"""
        
        if profile.over_voltage_delta > 0:
            section += f"over_voltage_delta={profile.over_voltage_delta}\n"
        
        return section
    
    def _update_overclock_section(self, content: str, profile: OverclockProfile) -> str:
        """Update existing overclock section in config"""
        
        # Define patterns to update
        updates = {
            r'^arm_freq=\d+': f'arm_freq={profile.arm_freq}',
            r'^gpu_freq=\d+': f'gpu_freq={profile.gpu_freq}',
            r'^over_voltage=\d+': f'over_voltage={profile.over_voltage}',
            r'^# Profile: .*': f'# Profile: {profile.name}'
        }
        
        for pattern, replacement in updates.items():
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Handle over_voltage_delta
        if profile.over_voltage_delta > 0:
            if 'over_voltage_delta=' in content:
                content = re.sub(
                    r'^over_voltage_delta=\d+', 
                    f'over_voltage_delta={profile.over_voltage_delta}',
                    content, 
                    flags=re.MULTILINE
                )
            else:
                # Add it after over_voltage
                content = re.sub(
                    r'(^over_voltage=\d+)$',
                    f'\\1\nover_voltage_delta={profile.over_voltage_delta}',
                    content,
                    flags=re.MULTILINE
                )
        
        return content
    
    def _update_armbian_env(self) -> bool:
        """Update Armbian environment for overclocking"""
        
        try:
            # Read current env
            with open(self.armbian_env, 'r') as f:
                content = f.read()
            
            # Check if we have OVERKILL settings
            if "# OVERKILL ARMBIAN CONFIGURATION" not in content:
                content += """

# OVERKILL ARMBIAN CONFIGURATION
extraargs=cma=512M coherent_pool=2M
"""
            
            return atomic_write(self.armbian_env, content)
            
        except Exception as e:
            logger.error(f"Failed to update Armbian env: {e}")
            return False
    
    def remove_overclock(self) -> OverclockResult:
        """Remove overclock settings"""
        
        try:
            # Backup current config
            if not backup_file(self.config_file):
                return OverclockResult(False, "Failed to backup config.txt", False)
            
            with open(self.config_file, 'r') as f:
                content = f.read()
            
            # Remove OVERKILL section
            if "# OVERKILL PI 5 CONFIGURATION" in content:
                # Find section boundaries
                start = content.find("# OVERKILL PI 5 CONFIGURATION")
                end = content.find("\n\n", start)
                
                if end == -1:
                    # Section goes to end of file
                    content = content[:start].rstrip()
                else:
                    # Remove section
                    content = content[:start] + content[end+2:]
            
            if atomic_write(self.config_file, content):
                return OverclockResult(True, 
                    "Overclock settings removed. Reboot required.", True)
            else:
                return OverclockResult(False, "Failed to write config.txt", False)
                
        except Exception as e:
            logger.error(f"Failed to remove overclock: {e}")
            return OverclockResult(False, f"Error: {str(e)}", False)
    
    def test_stability(self, duration: int = 60) -> Tuple[bool, str]:
        """Run stability test with current settings"""
        
        logger.info(f"Running stability test for {duration} seconds...")
        
        try:
            # Check if stress-ng is available
            ret, _, _ = run_command(["which", "stress-ng"])
            if ret != 0:
                return False, "stress-ng not installed"
            
            # Run stress test
            ret, stdout, stderr = run_command([
                "stress-ng",
                "--cpu", "0",  # Use all CPUs
                "--cpu-method", "all",
                "--verify",
                "--metrics",
                "--timeout", f"{duration}s"
            ], timeout=duration + 10)
            
            if ret == 0:
                # Check temperature during test
                temp = self._get_max_temperature()
                if temp > 85:
                    return False, f"Temperature too high during test: {temp}°C"
                
                return True, f"Stability test passed. Max temp: {temp}°C"
            else:
                return False, f"Stability test failed: {stderr}"
                
        except Exception as e:
            logger.error(f"Stability test error: {e}")
            return False, f"Test error: {str(e)}"
    
    def _get_max_temperature(self) -> float:
        """Get maximum temperature reached"""
        
        try:
            # Try vcgencmd first
            ret, stdout, _ = run_command(["vcgencmd", "measure_temp"])
            if ret == 0 and "temp=" in stdout:
                temp_str = stdout.split("=")[1].replace("'C", "")
                return float(temp_str)
            
            # Fallback to thermal zone
            with open("/sys/class/thermal/thermal_zone0/temp", 'r') as f:
                return float(f.read()) / 1000.0
                
        except:
            return 0.0
    
    def get_safe_profile_for_cooling(self, cooling_type: str) -> str:
        """Recommend safe profile based on cooling type"""
        
        cooling_profiles = {
            "none": "safe",
            "passive": "safe",
            "active_small": "balanced",
            "active_medium": "performance",
            "active_large": "extreme",
            "water": "extreme"
        }
        
        return cooling_profiles.get(cooling_type, "safe")