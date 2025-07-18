"""Custom overclock profile creator with validation"""

import re
import curses
from pathlib import Path
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from ..core.logger import logger
from ..core.config import OverclockProfile, Config
from ..core.system import get_system_detector
from ..ui.tui import OverkillTUI


@dataclass 
class ProfileValidator:
    """Validate overclock profile parameters"""
    
    # Safe ranges for Pi 5
    ARM_FREQ_MIN = 600
    ARM_FREQ_MAX = 3200
    ARM_FREQ_SAFE = 2800
    
    GPU_FREQ_MIN = 500
    GPU_FREQ_MAX = 1100
    GPU_FREQ_SAFE = 1000
    
    VOLTAGE_MIN = 0
    VOLTAGE_MAX = 8
    VOLTAGE_SAFE = 6
    
    VOLTAGE_DELTA_MAX = 100000
    
    def validate_arm_freq(self, freq: int) -> Tuple[bool, Optional[str]]:
        """Validate ARM frequency"""
        if freq < self.ARM_FREQ_MIN:
            return False, f"ARM frequency too low (minimum {self.ARM_FREQ_MIN} MHz)"
        elif freq > self.ARM_FREQ_MAX:
            return False, f"ARM frequency too high (maximum {self.ARM_FREQ_MAX} MHz)"
        elif freq > self.ARM_FREQ_SAFE:
            return True, f"WARNING: ARM frequency above {self.ARM_FREQ_SAFE} MHz requires excellent cooling"
        else:
            return True, None
    
    def validate_gpu_freq(self, freq: int) -> Tuple[bool, Optional[str]]:
        """Validate GPU frequency"""
        if freq < self.GPU_FREQ_MIN:
            return False, f"GPU frequency too low (minimum {self.GPU_FREQ_MIN} MHz)"
        elif freq > self.GPU_FREQ_MAX:
            return False, f"GPU frequency too high (maximum {self.GPU_FREQ_MAX} MHz)"
        elif freq > self.GPU_FREQ_SAFE:
            return True, f"WARNING: GPU frequency above {self.GPU_FREQ_SAFE} MHz may cause instability"
        else:
            return True, None
    
    def validate_voltage(self, voltage: int) -> Tuple[bool, Optional[str]]:
        """Validate over voltage"""
        if voltage < self.VOLTAGE_MIN:
            return False, f"Voltage cannot be negative"
        elif voltage > self.VOLTAGE_MAX:
            return False, f"Voltage too high (maximum {self.VOLTAGE_MAX})"
        elif voltage > self.VOLTAGE_SAFE:
            return True, f"WARNING: Voltage above {self.VOLTAGE_SAFE} may damage your Pi!"
        else:
            return True, None
    
    def validate_voltage_delta(self, delta: int) -> Tuple[bool, Optional[str]]:
        """Validate voltage delta"""
        if delta < 0:
            return False, "Voltage delta cannot be negative"
        elif delta > self.VOLTAGE_DELTA_MAX:
            return False, f"Voltage delta too high (maximum {self.VOLTAGE_DELTA_MAX})"
        else:
            return True, None
    
    def calculate_power_estimate(self, arm_freq: int, voltage: int) -> float:
        """Estimate power consumption"""
        # Rough estimate: base + frequency factor + voltage factor
        base_power = 5.0  # Base Pi 5 power
        freq_factor = (arm_freq - 2400) / 1000.0 * 2.0  # ~2W per GHz over stock
        voltage_factor = voltage * 0.5  # ~0.5W per voltage step
        
        return base_power + freq_factor + voltage_factor
    
    def get_cooling_requirement(self, arm_freq: int, voltage: int) -> str:
        """Determine cooling requirements"""
        power = self.calculate_power_estimate(arm_freq, voltage)
        
        if power < 8:
            return "Stock cooler sufficient"
        elif power < 12:
            return "Active cooling recommended"
        elif power < 15:
            return "High-performance cooling required"
        else:
            return "Extreme cooling required (tower cooler/water)"


class CustomProfileCreator:
    """Create and test custom overclock profiles"""
    
    def __init__(self, config: Config, tui: OverkillTUI):
        self.config = config
        self.tui = tui
        self.validator = ProfileValidator()
        self.system = get_system_detector()
        
    def create_profile(self) -> Optional[OverclockProfile]:
        """Interactive profile creation"""
        self.tui.draw_header()
        
        # Get profile name
        profile_name = self._get_profile_name()
        if not profile_name:
            return None
        
        # Get ARM frequency
        arm_freq = self._get_arm_frequency()
        if arm_freq is None:
            return None
        
        # Get GPU frequency
        gpu_freq = self._get_gpu_frequency()
        if gpu_freq is None:
            return None
        
        # Get over voltage
        voltage = self._get_voltage()
        if voltage is None:
            return None
        
        # Get voltage delta (optional)
        voltage_delta = self._get_voltage_delta()
        
        # Get description
        description = self._get_description()
        
        # Create profile
        profile = OverclockProfile(
            name=profile_name,
            arm_freq=arm_freq,
            gpu_freq=gpu_freq,
            over_voltage=voltage,
            over_voltage_delta=voltage_delta,
            description=description
        )
        
        # Show summary and warnings
        if self._show_profile_summary(profile):
            # Offer to test
            if self.tui.confirm("Test Profile", "Would you like to test this profile now?\n\nThis will apply the settings temporarily\nand run a quick stability test."):
                if self._test_profile(profile):
                    self.tui.show_success("Test Passed", "Profile appears stable!\n\nThe profile has been saved.")
                else:
                    if not self.tui.confirm("Test Failed", "The profile failed stability testing.\n\nSave it anyway?"):
                        return None
            
            # Save profile
            self.config.add_profile(profile)
            self.config.save_profiles()
            
            return profile
        
        return None
    
    def _get_profile_name(self) -> Optional[str]:
        """Get profile name from user"""
        while True:
            # Simple text input simulation
            self.tui.stdscr.clear()
            self.tui.draw_header()
            self.tui.stdscr.addstr(10, 10, "Enter profile name (letters, numbers, dash/underscore):")
            self.tui.stdscr.addstr(12, 10, "> ")
            self.tui.stdscr.refresh()
            
            curses.echo()
            name = self.tui.stdscr.getstr(12, 12, 30).decode('utf-8')
            curses.noecho()
            
            if not name:
                if self.tui.confirm("Cancel", "Cancel profile creation?"):
                    return None
                continue
                
            # Validate name
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{0,29}$', name):
                self.tui.show_error("Invalid Name", "Profile name must start with letter/number\nand contain only letters, numbers, dash, underscore")
                continue
            
            # Check if already exists
            if self.config.get_profile(name):
                if not self.tui.confirm("Overwrite?", f"Profile '{name}' already exists.\n\nOverwrite it?"):
                    continue
            
            return name
    
    def _get_arm_frequency(self) -> Optional[int]:
        """Get ARM frequency from user"""
        return self._get_numeric_value(
            "ARM Frequency (MHz)",
            f"Enter ARM frequency ({self.validator.ARM_FREQ_MIN}-{self.validator.ARM_FREQ_MAX} MHz):",
            f"Stock: 2400 MHz\nSafe: up to {self.validator.ARM_FREQ_SAFE} MHz",
            self.validator.validate_arm_freq,
            default=2600
        )
    
    def _get_gpu_frequency(self) -> Optional[int]:
        """Get GPU frequency from user"""
        return self._get_numeric_value(
            "GPU Frequency (MHz)",
            f"Enter GPU frequency ({self.validator.GPU_FREQ_MIN}-{self.validator.GPU_FREQ_MAX} MHz):",
            f"Stock: 910 MHz\nSafe: up to {self.validator.GPU_FREQ_SAFE} MHz",
            self.validator.validate_gpu_freq,
            default=950
        )
    
    def _get_voltage(self) -> Optional[int]:
        """Get over voltage from user"""
        return self._get_numeric_value(
            "Over Voltage",
            f"Enter over voltage ({self.validator.VOLTAGE_MIN}-{self.validator.VOLTAGE_MAX}):",
            f"Stock: 0\nSafe: up to {self.validator.VOLTAGE_SAFE}\nEach step ≈ 0.025V",
            self.validator.validate_voltage,
            default=0
        )
    
    def _get_voltage_delta(self) -> int:
        """Get voltage delta from user"""
        result = self._get_numeric_value(
            "Voltage Delta (Optional)",
            f"Enter voltage delta (0-{self.validator.VOLTAGE_DELTA_MAX}):",
            "Fine-tune voltage in microvolts\nPress Enter for 0 (none)",
            self.validator.validate_voltage_delta,
            default=0,
            optional=True
        )
        return result if result is not None else 0
    
    def _get_numeric_value(self, title: str, prompt: str, info: str, 
                          validator, default: int, optional: bool = False) -> Optional[int]:
        """Generic numeric input with validation"""
        import curses
        
        while True:
            self.tui.stdscr.clear()
            self.tui.draw_header()
            
            # Show title
            self.tui.stdscr.addstr(8, 10, title, curses.A_BOLD)
            
            # Show info
            y = 10
            for line in info.split('\n'):
                self.tui.stdscr.addstr(y, 10, line)
                y += 1
            
            # Show prompt
            self.tui.stdscr.addstr(y + 2, 10, prompt)
            self.tui.stdscr.addstr(y + 4, 10, f"> [{default}] ")
            self.tui.stdscr.refresh()
            
            # Get input
            curses.echo()
            value_str = self.tui.stdscr.getstr(y + 4, 10 + len(f"> [{default}] "), 10).decode('utf-8')
            curses.noecho()
            
            # Handle empty input
            if not value_str:
                if optional:
                    return default
                value_str = str(default)
            
            # Parse value
            try:
                value = int(value_str)
            except ValueError:
                self.tui.show_error("Invalid Input", "Please enter a number")
                continue
            
            # Validate
            valid, message = validator(value)
            if not valid:
                self.tui.show_error("Invalid Value", message)
                continue
            
            # Show warning if any
            if message:
                if not self.tui.confirm("Warning", f"{message}\n\nContinue anyway?"):
                    continue
            
            return value
    
    def _get_description(self) -> str:
        """Get profile description"""
        self.tui.stdscr.clear() 
        self.tui.draw_header()
        
        self.tui.stdscr.addstr(10, 10, "Enter profile description (optional):")
        self.tui.stdscr.addstr(12, 10, "> ")
        self.tui.stdscr.refresh()
        
        import curses
        curses.echo()
        description = self.tui.stdscr.getstr(12, 12, 60).decode('utf-8')
        curses.noecho()
        
        return description or "Custom overclock profile"
    
    def _show_profile_summary(self, profile: OverclockProfile) -> bool:
        """Show profile summary with warnings"""
        power = self.validator.calculate_power_estimate(profile.arm_freq, profile.over_voltage)
        cooling = self.validator.get_cooling_requirement(profile.arm_freq, profile.over_voltage)
        
        summary = f"""Profile Summary:
        
Name: {profile.name}
ARM Frequency: {profile.arm_freq} MHz
GPU Frequency: {profile.gpu_freq} MHz  
Over Voltage: {profile.over_voltage}
Voltage Delta: {profile.over_voltage_delta} µV

Estimated Power: {power:.1f}W
Cooling Required: {cooling}

Description: {profile.description}"""
        
        return self.tui.confirm("Save Profile?", summary + "\n\nSave this profile?")
    
    def _test_profile(self, profile: OverclockProfile) -> bool:
        """Quick stability test"""
        from .silicon_tester import SiliconTester
        
        self.tui.show_info("Testing", "Running quick stability test...\nThis will take about 60 seconds.")
        
        try:
            tester = SiliconTester()
            # Override test duration for quick test
            tester.test_duration = 60
            
            # Test just this profile
            result = tester._test_profile(profile)
            
            return result.stable and not result.throttled
            
        except Exception as e:
            logger.error(f"Profile test failed: {e}")
            return False