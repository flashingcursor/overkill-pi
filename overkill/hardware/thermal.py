"""Thermal management for Raspberry Pi 5"""

import os
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ..core.logger import logger
from ..core.utils import create_systemd_service, run_command, atomic_write


@dataclass
class ThermalReading:
    """Temperature and fan reading"""
    temperature: float
    fan_speed: int
    timestamp: float


@dataclass
class FanCurvePoint:
    """Fan curve point definition"""
    temperature: int
    fan_speed: int


class ThermalManager:
    """Manage thermal control and monitoring"""
    
    def __init__(self):
        self.thermal_zone = Path("/sys/class/thermal/thermal_zone0/temp")
        self.cooling_device = Path("/sys/class/thermal/cooling_device0")
        self.history: List[ThermalReading] = []
        self.max_history = 100
        
    def get_temperature(self) -> float:
        """Get current CPU temperature in Celsius"""
        
        try:
            # Try vcgencmd first (Pi specific)
            ret, stdout, _ = run_command(["vcgencmd", "measure_temp"])
            if ret == 0 and "temp=" in stdout:
                temp_str = stdout.split("=")[1].replace("'C", "").strip()
                return float(temp_str)
        except:
            pass
        
        # Fallback to thermal zone
        try:
            if self.thermal_zone.exists():
                with open(self.thermal_zone, 'r') as f:
                    return float(f.read().strip()) / 1000.0
        except Exception as e:
            logger.error(f"Failed to read temperature: {e}")
        
        return 0.0
    
    def get_fan_speed(self) -> int:
        """Get current fan speed (0-255 or percentage)"""
        
        try:
            cur_state = self.cooling_device / "cur_state"
            max_state = self.cooling_device / "max_state"
            
            if cur_state.exists() and max_state.exists():
                with open(cur_state, 'r') as f:
                    current = int(f.read().strip())
                with open(max_state, 'r') as f:
                    maximum = int(f.read().strip())
                
                if maximum > 0:
                    return int((current / maximum) * 100)
        except Exception as e:
            logger.debug(f"Failed to read fan speed: {e}")
        
        return 0
    
    def set_fan_speed(self, speed: int) -> bool:
        """Set fan speed (0-100 percentage)"""
        
        try:
            cur_state = self.cooling_device / "cur_state"
            max_state = self.cooling_device / "max_state"
            
            if not cur_state.exists():
                logger.error("No cooling device found")
                return False
            
            # Get max state
            with open(max_state, 'r') as f:
                maximum = int(f.read().strip())
            
            # Convert percentage to state value
            state = int((speed / 100.0) * maximum)
            state = max(0, min(state, maximum))
            
            # Write new state
            with open(cur_state, 'w') as f:
                f.write(str(state))
            
            logger.debug(f"Set fan speed to {speed}% (state {state})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set fan speed: {e}")
            return False
    
    def record_reading(self) -> ThermalReading:
        """Record current thermal reading"""
        
        reading = ThermalReading(
            temperature=self.get_temperature(),
            fan_speed=self.get_fan_speed(),
            timestamp=time.time()
        )
        
        self.history.append(reading)
        
        # Limit history size
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
        
        return reading
    
    def get_average_temperature(self, seconds: int = 60) -> float:
        """Get average temperature over specified time period"""
        
        if not self.history:
            return self.get_temperature()
        
        cutoff_time = time.time() - seconds
        recent_readings = [r for r in self.history if r.timestamp > cutoff_time]
        
        if not recent_readings:
            return self.get_temperature()
        
        return sum(r.temperature for r in recent_readings) / len(recent_readings)
    
    def create_fan_control_script(self, fan_curve: List[FanCurvePoint]) -> str:
        """Generate fan control script"""
        
        script = """#!/usr/bin/env python3
# OVERKILL Intelligent Fan Control

import time
import sys

class FanController:
    def __init__(self):
        self.fan_curve = {curve_json}
        self.thermal_zone = "/sys/class/thermal/thermal_zone0/temp"
        self.cooling_device = "/sys/class/thermal/cooling_device0/cur_state"
        self.max_state = self._get_max_state()
        
    def _get_max_state(self):
        try:
            with open("/sys/class/thermal/cooling_device0/max_state", 'r') as f:
                return int(f.read().strip())
        except:
            return 5  # Default
    
    def get_temperature(self):
        try:
            # Try vcgencmd first
            import subprocess
            result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                temp_str = result.stdout.split('=')[1].replace("'C", "")
                return float(temp_str)
        except:
            pass
        
        # Fallback to thermal zone
        try:
            with open(self.thermal_zone, 'r') as f:
                return float(f.read()) / 1000.0
        except:
            return 50.0  # Safe default
    
    def calculate_fan_speed(self, temp):
        # Find appropriate speed from curve
        for i, point in enumerate(self.fan_curve):
            if temp <= point['temperature']:
                if i == 0:
                    return point['fan_speed']
                else:
                    # Interpolate between points
                    prev = self.fan_curve[i-1]
                    temp_range = point['temperature'] - prev['temperature']
                    speed_range = point['fan_speed'] - prev['fan_speed']
                    temp_offset = temp - prev['temperature']
                    
                    return int(prev['fan_speed'] + 
                             (temp_offset / temp_range) * speed_range)
        
        # Temperature above highest point
        return self.fan_curve[-1]['fan_speed']
    
    def set_fan_state(self, speed_percent):
        state = int((speed_percent / 100.0) * self.max_state)
        state = max(0, min(state, self.max_state))
        
        try:
            with open(self.cooling_device, 'w') as f:
                f.write(str(state))
        except Exception as e:
            print(f"Failed to set fan state: {{e}}", file=sys.stderr)
    
    def run(self):
        print("OVERKILL Fan Control started")
        
        while True:
            try:
                temp = self.get_temperature()
                speed = self.calculate_fan_speed(temp)
                self.set_fan_state(speed)
                
                # Log every 30 seconds
                if int(time.time()) % 30 == 0:
                    print(f"Temp: {{temp:.1f}}°C, Fan: {{speed}}%")
                
            except Exception as e:
                print(f"Error in fan control: {{e}}", file=sys.stderr)
            
            time.sleep(5)

if __name__ == "__main__":
    controller = FanController()
    controller.run()
"""
        
        # Convert fan curve to JSON
        curve_data = [{"temperature": p.temperature, "fan_speed": p.fan_speed} 
                      for p in fan_curve]
        
        return script.format(curve_json=json.dumps(curve_data))
    
    def install_fan_control(self, mode: str = "auto", 
                           fan_curve: Optional[List[FanCurvePoint]] = None) -> bool:
        """Install fan control service"""
        
        try:
            # Default fan curve if not provided
            if fan_curve is None:
                fan_curve = [
                    FanCurvePoint(40, 0),
                    FanCurvePoint(50, 30),
                    FanCurvePoint(60, 50),
                    FanCurvePoint(70, 80),
                    FanCurvePoint(80, 100)
                ]
            
            # Create control script
            script_path = Path("/usr/local/bin/overkill-fancontrol")
            script_content = self.create_fan_control_script(fan_curve)
            
            if not atomic_write(script_path, script_content):
                return False
            
            os.chmod(script_path, 0o755)
            
            # Create systemd service
            service_created = create_systemd_service(
                name="overkill-thermal",
                description="OVERKILL Intelligent Thermal Management",
                exec_start="/usr/local/bin/overkill-fancontrol",
                restart="always"
            )
            
            if not service_created:
                return False
            
            # Enable and start service
            run_command(["systemctl", "enable", "overkill-thermal"])
            run_command(["systemctl", "start", "overkill-thermal"])
            
            logger.info("Fan control service installed and started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install fan control: {e}")
            return False
    
    def get_thermal_throttle_status(self) -> Dict[str, bool]:
        """Check thermal throttle status"""
        
        status = {
            "throttled": False,
            "temperature_limit": False,
            "undervoltage": False,
            "frequency_capped": False
        }
        
        try:
            # Use vcgencmd get_throttled
            ret, stdout, _ = run_command(["vcgencmd", "get_throttled"])
            if ret == 0 and "throttled=" in stdout:
                throttled = int(stdout.split("=")[1], 16)
                
                # Decode throttle bits
                status["undervoltage"] = bool(throttled & 0x1)
                status["frequency_capped"] = bool(throttled & 0x2)
                status["throttled"] = bool(throttled & 0x4)
                status["temperature_limit"] = bool(throttled & 0x8)
                
        except Exception as e:
            logger.debug(f"Failed to get throttle status: {e}")
        
        return status
    
    def optimize_for_profile(self, overclock_profile: str) -> List[FanCurvePoint]:
        """Get optimized fan curve for overclock profile"""
        
        curves = {
            "safe": [
                FanCurvePoint(45, 0),
                FanCurvePoint(55, 20),
                FanCurvePoint(65, 40),
                FanCurvePoint(75, 70),
                FanCurvePoint(80, 100)
            ],
            "balanced": [
                FanCurvePoint(40, 0),
                FanCurvePoint(50, 25),
                FanCurvePoint(60, 45),
                FanCurvePoint(70, 75),
                FanCurvePoint(80, 100)
            ],
            "performance": [
                FanCurvePoint(35, 10),
                FanCurvePoint(45, 30),
                FanCurvePoint(55, 50),
                FanCurvePoint(65, 80),
                FanCurvePoint(75, 100)
            ],
            "extreme": [
                FanCurvePoint(30, 20),
                FanCurvePoint(40, 40),
                FanCurvePoint(50, 60),
                FanCurvePoint(60, 85),
                FanCurvePoint(70, 100)
            ]
        }
        
        return curves.get(overclock_profile, curves["balanced"])