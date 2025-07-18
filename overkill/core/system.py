"""System detection and information for OVERKILL"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import psutil
from dataclasses import dataclass
from .logger import logger


@dataclass
class SystemInfo:
    """System information container"""
    model: str
    cpu: str
    memory_gb: float
    storage_devices: List[Dict[str, str]]
    nvme_devices: List[str]
    kernel: str
    os_name: str
    os_version: str
    temperature: Optional[float]
    cpu_freq: Optional[Dict[str, float]]
    gpu_freq: Optional[int]


class SystemDetector:
    """Detect and gather system information"""
    
    def __init__(self):
        self.is_pi = self._detect_raspberry_pi()
        self.is_pi5 = False
        self.model = "Unknown"
        
        if self.is_pi:
            self.model = self._get_pi_model()
            self.is_pi5 = "Raspberry Pi 5" in self.model
    
    def _detect_raspberry_pi(self) -> bool:
        """Check if running on Raspberry Pi"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                model = f.read().strip()
                return "Raspberry Pi" in model
        except:
            return False
    
    def _get_pi_model(self) -> str:
        """Get Raspberry Pi model"""
        try:
            with open('/proc/device-tree/model', 'r') as f:
                return f.read().strip().replace('\x00', '')
        except:
            return "Unknown Raspberry Pi"
    
    def _run_command(self, cmd: List[str]) -> Optional[str]:
        """Run a command and return output"""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.debug(f"Command {' '.join(cmd)} failed: {e}")
        return None
    
    def get_cpu_info(self) -> str:
        """Get CPU information"""
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if line.startswith('model name'):
                        return line.split(':')[1].strip()
        except:
            pass
        
        # Fallback for ARM systems
        if self.is_pi:
            return "BCM2712 Cortex-A76"
        
        return platform.processor() or "Unknown CPU"
    
    def get_memory_info(self) -> float:
        """Get total memory in GB"""
        return psutil.virtual_memory().total / (1024 ** 3)
    
    def get_storage_devices(self) -> List[Dict[str, str]]:
        """Get all storage devices"""
        devices = []
        
        try:
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    devices.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total_gb": usage.total / (1024 ** 3),
                        "used_gb": usage.used / (1024 ** 3),
                        "free_gb": usage.free / (1024 ** 3),
                        "percent": usage.percent
                    })
                except:
                    continue
        except Exception as e:
            logger.error(f"Error getting storage devices: {e}")
        
        return devices
    
    def get_nvme_devices(self) -> List[str]:
        """Get NVMe devices"""
        nvme_devices = []
        
        try:
            # Check /sys/block for nvme devices
            block_dir = Path("/sys/block")
            for device in block_dir.iterdir():
                if device.name.startswith("nvme"):
                    nvme_devices.append(f"/dev/{device.name}")
        except Exception as e:
            logger.error(f"Error detecting NVMe devices: {e}")
        
        return nvme_devices
    
    def get_temperature(self) -> Optional[float]:
        """Get CPU temperature"""
        # Try thermal zone (standard Linux)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except:
            pass
        
        # Try vcgencmd (Raspberry Pi specific)
        if self.is_pi:
            output = self._run_command(['vcgencmd', 'measure_temp'])
            if output:
                try:
                    temp_str = output.split('=')[1].rstrip('\'C')
                    return float(temp_str)
                except:
                    pass
        
        return None
    
    def get_cpu_frequency(self) -> Optional[Dict[str, float]]:
        """Get CPU frequency information"""
        try:
            freq = psutil.cpu_freq()
            if freq:
                return {
                    "current": freq.current,
                    "min": freq.min,
                    "max": freq.max
                }
        except:
            pass
        
        # Raspberry Pi specific
        if self.is_pi:
            current = self._run_command(['vcgencmd', 'get_config', 'arm_freq'])
            if current:
                try:
                    freq_mhz = int(current.split('=')[1])
                    return {
                        "current": freq_mhz,
                        "min": 600,
                        "max": freq_mhz
                    }
                except:
                    pass
        
        return None
    
    def get_gpu_frequency(self) -> Optional[int]:
        """Get GPU frequency (Pi specific)"""
        if not self.is_pi:
            return None
        
        output = self._run_command(['vcgencmd', 'get_config', 'gpu_freq'])
        if output:
            try:
                return int(output.split('=')[1])
            except:
                pass
        
        return None
    
    def get_full_info(self) -> SystemInfo:
        """Get complete system information"""
        return SystemInfo(
            model=self.model,
            cpu=self.get_cpu_info(),
            memory_gb=self.get_memory_info(),
            storage_devices=self.get_storage_devices(),
            nvme_devices=self.get_nvme_devices(),
            kernel=platform.release(),
            os_name=platform.system(),
            os_version=platform.version(),
            temperature=self.get_temperature(),
            cpu_freq=self.get_cpu_frequency(),
            gpu_freq=self.get_gpu_frequency()
        )
    
    def check_requirements(self) -> Tuple[bool, List[str]]:
        """Check if system meets OVERKILL requirements"""
        issues = []
        
        # Check if Pi 5
        if not self.is_pi5:
            issues.append(f"Not a Raspberry Pi 5 (detected: {self.model})")
        
        # Check memory
        memory_gb = self.get_memory_info()
        if memory_gb < 4:
            issues.append(f"Insufficient memory: {memory_gb:.1f}GB (minimum 4GB)")
        
        # Check for NVMe
        nvme_devices = self.get_nvme_devices()
        if not nvme_devices:
            issues.append("No NVMe storage detected")
        
        # Check for cooling (look for fan control)
        if not Path("/sys/class/thermal/cooling_device0").exists():
            issues.append("No active cooling detected")
        
        return len(issues) == 0, issues
    
    def get_silicon_grade(self) -> str:
        """Get silicon grade from last test or return untested"""
        if not self.is_pi5:
            return "unknown"
        
        # Check for saved test results
        grade_file = Path('/etc/overkill/silicon_grade.json')
        if grade_file.exists():
            try:
                import json
                with open(grade_file, 'r') as f:
                    data = json.load(f)
                    return data.get('grade', 'untested')
            except:
                pass
        
        return "untested"


# Global system detector instance
_system_detector = None


def get_system_detector() -> SystemDetector:
    """Get or create the global system detector"""
    global _system_detector
    
    if _system_detector is None:
        _system_detector = SystemDetector()
    
    return _system_detector


def is_raspberry_pi_5() -> bool:
    """Quick check if running on Pi 5"""
    return get_system_detector().is_pi5


def get_system_info() -> SystemInfo:
    """Get full system information"""
    return get_system_detector().get_full_info()