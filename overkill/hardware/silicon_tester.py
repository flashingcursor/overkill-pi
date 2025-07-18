"""Silicon quality testing for Raspberry Pi 5"""

import os
import time
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from ..core.logger import logger
from ..core.utils import run_command, backup_file
from ..core.system import get_system_detector
from ..core.config import OverclockProfile
from .overclock import OverclockManager
from .thermal import ThermalManager


@dataclass
class StressTestResult:
    """Result of a stress test run"""
    profile_name: str
    stable: bool
    max_temp: float
    avg_temp: float
    throttled: bool
    errors: List[str]
    duration: float
    
    
@dataclass
class SiliconGrade:
    """Silicon quality grade"""
    grade: str  # S, A, B, C, D
    description: str
    max_stable_profile: str
    recommended_profile: str
    test_results: List[StressTestResult]


class SiliconTester:
    """Test silicon quality through progressive stress testing"""
    
    def __init__(self):
        self.system = get_system_detector()
        self.overclock = OverclockManager()
        self.thermal = ThermalManager()
        
        # Test configuration
        self.test_duration = 300  # 5 minutes per profile
        self.temp_threshold = 85  # Maximum safe temperature
        self.temp_abort = 90     # Abort temperature
        
        # Test profiles in order (progressive)
        self.test_profiles = [
            OverclockProfile(
                name="stock",
                arm_freq=2400,
                gpu_freq=910,
                over_voltage=0,
                over_voltage_delta=0,
                description="Stock settings"
            ),
            OverclockProfile(
                name="mild",
                arm_freq=2600,
                gpu_freq=950,
                over_voltage=2,
                over_voltage_delta=0,
                description="Mild overclock"
            ),
            OverclockProfile(
                name="moderate",
                arm_freq=2800,
                gpu_freq=1000,
                over_voltage=4,
                over_voltage_delta=0,
                description="Moderate overclock"
            ),
            OverclockProfile(
                name="aggressive",
                arm_freq=3000,
                gpu_freq=1050,
                over_voltage=6,
                over_voltage_delta=50000,
                description="Aggressive overclock"
            ),
            OverclockProfile(
                name="extreme",
                arm_freq=3200,
                gpu_freq=1100,
                over_voltage=8,
                over_voltage_delta=100000,
                description="Extreme overclock"
            )
        ]
        
        # Monitoring
        self._monitoring = False
        self._test_aborted = False
        self._temps = []
        self._errors = []
        
    def test_silicon_quality(self, progress_callback=None) -> SiliconGrade:
        """Run complete silicon quality test"""
        logger.info("Starting silicon quality testing")
        
        # Backup current settings
        backup_file(self.overclock.config_file)
        
        # Store original settings
        original_settings = self.overclock.get_current_settings()
        
        results = []
        max_stable_idx = -1
        
        try:
            for idx, profile in enumerate(self.test_profiles):
                if progress_callback:
                    progress_callback(
                        idx, 
                        len(self.test_profiles),
                        f"Testing {profile.name} profile..."
                    )
                
                logger.info(f"Testing profile: {profile.name}")
                result = self._test_profile(profile)
                results.append(result)
                
                if result.stable and not result.throttled:
                    max_stable_idx = idx
                else:
                    logger.info(f"Profile {profile.name} failed - stopping tests")
                    break
                    
                # Cool down between tests
                self._cooldown_period()
                
        finally:
            # Always restore original settings
            logger.info("Restoring original settings")
            self._restore_profile(original_settings)
        
        # Determine grade
        grade = self._calculate_grade(max_stable_idx, results)
        
        return grade
        
    def _test_profile(self, profile: OverclockProfile) -> StressTestResult:
        """Test a single overclock profile"""
        start_time = time.time()
        
        # Reset monitoring
        self._temps = []
        self._errors = []
        self._test_aborted = False
        
        # Apply profile
        try:
            result = self.overclock.apply_profile(profile)
            if not result.success:
                return StressTestResult(
                    profile_name=profile.name,
                    stable=False,
                    max_temp=0,
                    avg_temp=0,
                    throttled=False,
                    errors=[result.message],
                    duration=0
                )
        except Exception as e:
            return StressTestResult(
                profile_name=profile.name,
                stable=False,
                max_temp=0,
                avg_temp=0,
                throttled=False,
                errors=[str(e)],
                duration=0
            )
        
        # Wait for settings to apply
        time.sleep(5)
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self._monitor_system)
        self._monitoring = True
        monitor_thread.start()
        
        # Run stress test
        stress_proc = self._start_stress_test()
        
        # Wait for test duration or abort
        test_start = time.time()
        while (time.time() - test_start) < self.test_duration:
            if self._test_aborted:
                logger.warning("Test aborted due to high temperature or errors")
                break
            time.sleep(1)
        
        # Stop stress test
        if stress_proc:
            stress_proc.terminate()
            stress_proc.wait()
        
        # Stop monitoring
        self._monitoring = False
        monitor_thread.join()
        
        # Calculate results
        duration = time.time() - start_time
        max_temp = max(self._temps) if self._temps else 0
        avg_temp = sum(self._temps) / len(self._temps) if self._temps else 0
        
        # Check for throttling
        throttled = self._check_throttling()
        
        # Determine stability
        stable = (
            not self._test_aborted and
            len(self._errors) == 0 and
            max_temp < self.temp_threshold and
            not throttled
        )
        
        return StressTestResult(
            profile_name=profile.name,
            stable=stable,
            max_temp=max_temp,
            avg_temp=avg_temp,
            throttled=throttled,
            errors=self._errors,
            duration=duration
        )
    
    def _monitor_system(self):
        """Monitor system during stress test"""
        while self._monitoring:
            try:
                # Get temperature
                temp = self.system.get_temperature()
                if temp:
                    self._temps.append(temp)
                    
                    # Check abort condition
                    if temp >= self.temp_abort:
                        logger.error(f"Temperature too high: {temp}°C")
                        self._errors.append(f"Temperature exceeded {self.temp_abort}°C")
                        self._test_aborted = True
                
                # Check for system errors
                if self._check_system_errors():
                    self._test_aborted = True
                    
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                self._errors.append(f"Monitoring error: {e}")
                
            time.sleep(1)
    
    def _start_stress_test(self) -> Optional[subprocess.Popen]:
        """Start stress-ng process"""
        try:
            # Comprehensive stress test
            cmd = [
                'stress-ng',
                '--cpu', str(os.cpu_count()),
                '--cpu-method', 'all',
                '--cache', '0',
                '--vm', '2',
                '--vm-bytes', '256M',
                '--io', '2',
                '--timeout', f'{self.test_duration}s',
                '--metrics-brief'
            ]
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return proc
            
        except Exception as e:
            logger.error(f"Failed to start stress test: {e}")
            self._errors.append(f"Stress test failed: {e}")
            return None
    
    def _check_throttling(self) -> bool:
        """Check if CPU was throttled during test"""
        ret, output, _ = run_command(['vcgencmd', 'get_throttled'])
        if ret == 0:
            throttled_hex = output.strip().split('=')[1]
            throttled_int = int(throttled_hex, 16)
            
            # Check throttling bits
            # Bit 0: Under-voltage
            # Bit 1: Arm frequency capped
            # Bit 2: Currently throttled
            # Bit 3: Soft temperature limit
            
            return throttled_int != 0
        
        return False
    
    def _check_system_errors(self) -> bool:
        """Check for system errors in dmesg"""
        ret, output, _ = run_command(['dmesg', '-T', '--level=err,crit,alert,emerg'])
        
        # Look for recent errors (last 60 seconds)
        now = datetime.now()
        for line in output.split('\n'):
            if line.strip():
                # Try to parse timestamp
                try:
                    # dmesg -T format: [Mon Jan 1 00:00:00 2024]
                    if ']' in line:
                        timestamp_str = line.split(']')[0].strip('[')
                        # Simple check - if error appeared recently
                        if 'error' in line.lower() or 'fail' in line.lower():
                            self._errors.append(f"System error: {line}")
                            return True
                except:
                    pass
        
        return False
    
    def _cooldown_period(self):
        """Wait for system to cool down between tests"""
        logger.info("Cooling down...")
        target_temp = 50  # Cool down to 50°C
        
        while True:
            temp = self.system.get_temperature()
            if temp and temp <= target_temp:
                break
            time.sleep(5)
    
    def _restore_profile(self, original_settings: Dict[str, int]):
        """Restore original overclock settings"""
        profile = OverclockProfile(
            name="original",
            arm_freq=original_settings.get('arm_freq', 2400),
            gpu_freq=original_settings.get('gpu_freq', 910),
            over_voltage=original_settings.get('over_voltage', 0),
            over_voltage_delta=original_settings.get('over_voltage_delta', 0),
            description="Original settings"
        )
        
        self.overclock.apply_profile(profile)
    
    def _calculate_grade(self, max_stable_idx: int, results: List[StressTestResult]) -> SiliconGrade:
        """Calculate silicon grade based on test results"""
        grades = {
            -1: ("D", "Below Average - Stock only"),
            0: ("C", "Average - Mild overclock capable"),
            1: ("B", "Good - Moderate overclock capable"),
            2: ("A", "Excellent - Aggressive overclock capable"),
            3: ("S", "Golden Sample - Extreme overclock capable"),
            4: ("S+", "Exceptional - Maximum overclock achieved")
        }
        
        grade, description = grades.get(max_stable_idx, ("D", "Below Average"))
        
        # Determine recommended profile (one step below max for safety)
        if max_stable_idx > 0:
            recommended_idx = max_stable_idx - 1
            recommended_profile = self.test_profiles[recommended_idx].name
        else:
            recommended_profile = "stock"
        
        max_stable_profile = self.test_profiles[max_stable_idx].name if max_stable_idx >= 0 else "none"
        
        silicon_grade = SiliconGrade(
            grade=grade,
            description=description,
            max_stable_profile=max_stable_profile,
            recommended_profile=recommended_profile,
            test_results=results
        )
        
        # Save grade for future reference
        self._save_grade(silicon_grade)
        
        return silicon_grade
    
    def _save_grade(self, grade: SiliconGrade):
        """Save silicon grade to file"""
        try:
            import json
            from datetime import datetime
            
            grade_data = {
                'grade': grade.grade,
                'description': grade.description,
                'max_stable_profile': grade.max_stable_profile,
                'recommended_profile': grade.recommended_profile,
                'test_date': datetime.now().isoformat(),
                'test_results': [
                    {
                        'profile': r.profile_name,
                        'stable': r.stable,
                        'max_temp': r.max_temp,
                        'throttled': r.throttled
                    }
                    for r in grade.test_results
                ]
            }
            
            grade_file = Path('/etc/overkill/silicon_grade.json')
            grade_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(grade_file, 'w') as f:
                json.dump(grade_data, f, indent=2)
                
            logger.info(f"Saved silicon grade: {grade.grade}")
            
        except Exception as e:
            logger.error(f"Failed to save silicon grade: {e}")