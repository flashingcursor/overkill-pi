"""Real-time thermal monitoring with hardware fan speed reading"""

import time
import shutil
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from collections import deque
from ..core.logger import logger
from ..core.utils import run_command
from ..core.system import get_system_detector


class ThermalMonitor:
    """Monitor thermal status with real hardware readings"""
    
    def __init__(self):
        self.system = get_system_detector()
        self.history = deque(maxlen=300)  # 5 minutes at 1 second intervals
        self.update_interval = 1.0
        
        # Detect fan type and PWM paths
        self.fan_type = self._detect_fan_type()
        self.pwm_paths = self._find_pwm_paths()
        
    def get_thermal_status(self) -> Dict:
        """Get comprehensive thermal status"""
        data = {
            'timestamp': time.time(),
            'cpu_temp': self._get_cpu_temp(),
            'gpu_temp': self._get_gpu_temp(),
            'fan_speed_rpm': None,
            'fan_speed_pct': None,
            'fan_mode': self._get_fan_mode(),
            'pwm_freq': None,
            'throttle_status': self._get_throttle_status(),
            'thermal_state': 'Normal',
            'power_draw': self._get_power_draw()
        }
        
        # Get fan speed using appropriate method
        fan_data = self._get_fan_speed()
        data.update(fan_data)
        
        # Determine thermal state
        if data['cpu_temp'] > 80:
            data['thermal_state'] = 'Critical'
        elif data['cpu_temp'] > 70:
            data['thermal_state'] = 'High'
        elif data['cpu_temp'] > 60:
            data['thermal_state'] = 'Moderate'
        
        # Add to history
        self.history.append(data)
        
        return data
    
    def _detect_fan_type(self) -> str:
        """Detect type of fan control available"""
        # Check for official Pi 5 fan
        if Path('/sys/class/thermal/cooling_device0/type').exists():
            try:
                fan_type = Path('/sys/class/thermal/cooling_device0/type').read_text().strip()
                if 'pwm-fan' in fan_type or 'gpio-fan' in fan_type:
                    return 'official_pi5'
            except:
                pass
        
        # Check for PWM fan
        if any(Path(f'/sys/class/pwm/pwmchip{i}').exists() for i in range(4)):
            return 'generic_pwm'
        
        # Check for I2C fan controller
        if Path('/sys/class/i2c-adapter').exists():
            ret, out, _ = run_command(['i2cdetect', '-l'])
            if ret == 0 and 'i2c' in out:
                return 'i2c_controller'
        
        return 'unknown'
    
    def _find_pwm_paths(self) -> List[Path]:
        """Find all available PWM paths"""
        paths = []
        
        # Standard PWM paths
        for i in range(4):
            chip_path = Path(f'/sys/class/pwm/pwmchip{i}')
            if chip_path.exists():
                # Check for exported PWM channels
                for pwm in chip_path.glob('pwm*'):
                    if pwm.is_dir():
                        paths.append(pwm)
        
        # Armbian/Pi 5 specific paths
        specific_paths = [
            '/sys/devices/platform/soc/fe20c000.pwm/pwm/pwmchip0/pwm0',
            '/sys/devices/platform/soc/fec00000.pwm/pwm/pwmchip1/pwm0',
        ]
        
        for path_str in specific_paths:
            path = Path(path_str)
            if path.exists():
                paths.append(path)
        
        return paths
    
    def _get_cpu_temp(self) -> float:
        """Get CPU temperature"""
        return self.system.get_temperature() or 0.0
    
    def _get_gpu_temp(self) -> Optional[float]:
        """Get GPU temperature if available"""
        # Try thermal zones
        for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
            try:
                zone_type = (zone / 'type').read_text().strip()
                if 'gpu' in zone_type.lower():
                    temp = int((zone / 'temp').read_text().strip()) / 1000.0
                    return temp
            except:
                continue
        
        return None
    
    def _get_fan_speed(self) -> Dict[str, Optional[float]]:
        """Get fan speed using available methods"""
        result = {'fan_speed_rpm': None, 'fan_speed_pct': None, 'pwm_freq': None}
        
        # Method 1: Read PWM duty cycle
        if self.pwm_paths:
            for pwm_path in self.pwm_paths:
                try:
                    duty_path = pwm_path / 'duty_cycle'
                    period_path = pwm_path / 'period'
                    
                    if duty_path.exists() and period_path.exists():
                        duty = int(duty_path.read_text().strip())
                        period = int(period_path.read_text().strip())
                        
                        if period > 0:
                            result['fan_speed_pct'] = (duty / period) * 100
                            result['pwm_freq'] = int(1e9 / period)  # Convert ns to Hz
                            break
                except Exception as e:
                    logger.debug(f"PWM read error: {e}")
        
        # Method 2: Cooling device state (Armbian)
        if result['fan_speed_pct'] is None:
            try:
                cooling_path = Path('/sys/class/thermal/cooling_device0')
                if cooling_path.exists():
                    cur_state = int((cooling_path / 'cur_state').read_text().strip())
                    max_state = int((cooling_path / 'max_state').read_text().strip())
                    
                    if max_state > 0:
                        result['fan_speed_pct'] = (cur_state / max_state) * 100
            except:
                pass
        
        # Method 3: Read tachometer (if available)
        rpm = self._read_fan_tachometer()
        if rpm:
            result['fan_speed_rpm'] = rpm
            # Estimate percentage (assume 5000 RPM = 100%)
            if result['fan_speed_pct'] is None:
                result['fan_speed_pct'] = min(100, (rpm / 5000) * 100)
        
        return result
    
    def _read_fan_tachometer(self) -> Optional[int]:
        """Read fan tachometer if available"""
        # This would require GPIO access or specific hardware
        # For now, return None as tach reading requires hardware setup
        return None
    
    def _get_fan_mode(self) -> str:
        """Get current fan control mode"""
        # Check for fan control service
        ret, out, _ = run_command(['systemctl', 'is-active', 'overkill-fan-control'])
        if ret == 0:
            return 'OVERKILL Controlled'
        
        # Check thermal governor
        try:
            gov_path = Path('/sys/class/thermal/thermal_zone0/policy')
            if gov_path.exists():
                policy = gov_path.read_text().strip()
                return f'System ({policy})'
        except:
            pass
        
        return 'Unknown'
    
    def _get_throttle_status(self) -> Dict[str, bool]:
        """Get CPU throttling status"""
        status = {
            'throttled': False,
            'under_voltage': False,
            'freq_capped': False,
            'soft_temp_limit': False
        }
        
        # Use vcgencmd if available
        if shutil.which('vcgencmd'):
            ret, out, _ = run_command(['vcgencmd', 'get_throttled'])
            if ret == 0 and '=' in out:
                try:
                    throttled_hex = out.strip().split('=')[1]
                    throttled_int = int(throttled_hex, 16)
                    
                    status['under_voltage'] = bool(throttled_int & 0x1)
                    status['freq_capped'] = bool(throttled_int & 0x2)
                    status['throttled'] = bool(throttled_int & 0x4)
                    status['soft_temp_limit'] = bool(throttled_int & 0x8)
                except:
                    pass
        
        return status
    
    def _get_power_draw(self) -> Optional[float]:
        """Estimate power draw if possible"""
        # This would require INA219 or similar power monitoring
        # For now, estimate based on frequency and voltage
        try:
            # Get current CPU frequency
            freq_path = Path('/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq')
            if freq_path.exists():
                freq_khz = int(freq_path.read_text().strip())
                freq_ghz = freq_khz / 1000000.0
                
                # Very rough estimation: ~5W base + 3W per GHz
                power = 5.0 + (freq_ghz * 3.0)
                
                # Add fan power if running
                if self._get_fan_speed()['fan_speed_pct']:
                    power += 0.5  # Typical fan power
                
                return power
        except:
            pass
        
        return None
    
    def get_temperature_history(self, duration_seconds: int = 300) -> List[Tuple[float, float]]:
        """Get temperature history for graphing"""
        history = []
        cutoff = time.time() - duration_seconds
        
        for entry in self.history:
            if entry['timestamp'] > cutoff:
                history.append((entry['timestamp'], entry['cpu_temp']))
        
        return history
    
    def start_monitoring(self, callback=None):
        """Start continuous monitoring with optional callback"""
        import threading
        
        def monitor_loop():
            while self._monitoring:
                data = self.get_thermal_status()
                if callback:
                    callback(data)
                time.sleep(self.update_interval)
        
        self._monitoring = True
        self._monitor_thread = threading.Thread(target=monitor_loop)
        self._monitor_thread.start()
    
    def stop_monitoring(self):
        """Stop continuous monitoring"""
        self._monitoring = False
        if hasattr(self, '_monitor_thread'):
            self._monitor_thread.join()