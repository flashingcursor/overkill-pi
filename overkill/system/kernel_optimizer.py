"""Kernel optimization for OVERKILL performance"""

from pathlib import Path
from typing import Dict, List
from ..core.logger import logger
from ..core.utils import atomic_write, backup_file


class KernelOptimizer:
    """Apply kernel optimizations for maximum performance"""
    
    def __init__(self):
        self.sysctl_file = Path("/etc/sysctl.d/99-overkill-extreme.conf")
        self.udev_file = Path("/etc/udev/rules.d/99-overkill-nvme.rules")
        
        # Extreme kernel parameters for performance
        self.sysctl_params = {
            # Memory management
            "vm.swappiness": "1",
            "vm.vfs_cache_pressure": "50",
            "vm.dirty_ratio": "40",
            "vm.dirty_background_ratio": "5",
            "vm.dirty_writeback_centisecs": "1500",
            "vm.dirty_expire_centisecs": "3000",
            
            # Network optimization
            "net.core.rmem_max": "16777216",
            "net.core.wmem_max": "16777216",
            "net.core.rmem_default": "8388608",
            "net.core.wmem_default": "8388608",
            "net.core.optmem_max": "65536",
            "net.core.netdev_max_backlog": "5000",
            "net.ipv4.tcp_rmem": "4096 87380 16777216",
            "net.ipv4.tcp_wmem": "4096 65536 16777216",
            "net.ipv4.tcp_congestion_control": "bbr",
            "net.ipv4.tcp_fastopen": "3",
            "net.ipv4.tcp_mtu_probing": "1",
            "net.ipv4.tcp_timestamps": "0",
            
            # Scheduler optimization
            "kernel.sched_latency_ns": "20000000",
            "kernel.sched_min_granularity_ns": "2500000",
            "kernel.sched_wakeup_granularity_ns": "5000000",
            "kernel.sched_migration_cost_ns": "500000",
            
            # File system
            "fs.file-max": "2097152",
            "fs.nr_open": "1048576",
            "fs.inotify.max_user_watches": "524288"
        }
        
        # NVMe optimization rules
        self.nvme_rules = [
            '# OVERKILL NVMe OPTIMIZATION',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/read_ahead_kb}="1024"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/nr_requests}="512"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rotational}="0"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/rq_affinity}="2"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/nomerges}="0"',
            'ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/add_random}="0"'
        ]
    
    def create_sysctl_config(self) -> bool:
        """Create sysctl configuration file"""
        try:
            content = "# OVERKILL KERNEL CONFIGURATION\n"
            content += "# Maximum performance settings for Raspberry Pi 5\n\n"
            
            for param, value in self.sysctl_params.items():
                content += f"{param}={value}\n"
            
            # Backup existing file if present
            if self.sysctl_file.exists():
                backup_file(self.sysctl_file)
            
            # Write new configuration
            if atomic_write(self.sysctl_file, content):
                logger.info("Created kernel optimization configuration")
                return True
            
        except Exception as e:
            logger.error(f"Failed to create sysctl config: {e}")
        
        return False
    
    def create_udev_rules(self) -> bool:
        """Create udev rules for NVMe optimization"""
        try:
            content = "\n".join(self.nvme_rules) + "\n"
            
            # Backup existing file if present
            if self.udev_file.exists():
                backup_file(self.udev_file)
            
            # Write new rules
            if atomic_write(self.udev_file, content):
                logger.info("Created NVMe optimization rules")
                return True
            
        except Exception as e:
            logger.error(f"Failed to create udev rules: {e}")
        
        return False
    
    def apply_runtime_params(self) -> bool:
        """Apply kernel parameters at runtime"""
        try:
            # Apply sysctl parameters
            for param, value in self.sysctl_params.items():
                sysctl_path = f"/proc/sys/{param.replace('.', '/')}"
                
                try:
                    with open(sysctl_path, 'w') as f:
                        f.write(value)
                except Exception as e:
                    logger.warning(f"Failed to set {param}: {e}")
            
            logger.info("Applied runtime kernel parameters")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply runtime params: {e}")
            return False
    
    def optimize_cpu_governor(self) -> bool:
        """Set CPU governor for performance"""
        try:
            # Check available governors
            gov_path = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors")
            if not gov_path.exists():
                logger.warning("CPU frequency scaling not available")
                return False
            
            with open(gov_path, 'r') as f:
                available = f.read().strip().split()
            
            # Prefer performance governor
            governor = "performance"
            if governor not in available:
                governor = "ondemand" if "ondemand" in available else available[0]
            
            # Apply to all CPUs
            cpu_count = 0
            while Path(f"/sys/devices/system/cpu/cpu{cpu_count}").exists():
                gov_file = Path(f"/sys/devices/system/cpu/cpu{cpu_count}/cpufreq/scaling_governor")
                if gov_file.exists():
                    with open(gov_file, 'w') as f:
                        f.write(governor)
                cpu_count += 1
            
            logger.info(f"Set CPU governor to {governor} for {cpu_count} CPUs")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set CPU governor: {e}")
            return False
    
    def apply_all_optimizations(self) -> bool:
        """Apply all kernel optimizations"""
        success = True
        
        # Create configuration files
        if not self.create_sysctl_config():
            success = False
        
        if not self.create_udev_rules():
            success = False
        
        # Apply runtime parameters
        if not self.apply_runtime_params():
            success = False
        
        # Optimize CPU governor
        if not self.optimize_cpu_governor():
            success = False
        
        return success