"""Infrastructure setup for OVERKILL"""

from pathlib import Path
from datetime import datetime
from typing import List, Dict
from ..core.logger import logger
from ..core.utils import ensure_directory, atomic_write


class InfrastructureManager:
    """Create and manage OVERKILL directory infrastructure"""
    
    def __init__(self):
        self.overkill_home = Path("/opt/overkill")
        self.overkill_config = Path("/etc/overkill")
        self.media_root = Path("/media")
        
        # Directory structure
        self.directories = {
            "home": [
                self.overkill_home / "bin",
                self.overkill_home / "lib",
                self.overkill_home / "config",
                self.overkill_home / "themes",
                self.overkill_home / "tools",
                self.overkill_home / "scripts",
                self.overkill_home / "services",
                self.overkill_home / "build",
                self.overkill_home / "build" / "kodi",
                self.overkill_home / "kodi",
                self.overkill_home / "addons",
                self.overkill_home / "repos"
            ],
            "config": [
                self.overkill_config / "network",
                self.overkill_config / "display",
                self.overkill_config / "audio",
                self.overkill_config / "remote",
                self.overkill_config / "overclocking",
                self.overkill_config / "thermal",
                self.overkill_config / "recovery",
                self.overkill_config / "profiles",
                self.overkill_config / "templates"
            ],
            "logging": [
                Path("/var/log/overkill"),
                Path("/var/log/overkill/builds"),
                Path("/var/log/overkill/thermal"),
                Path("/var/log/overkill/system")
            ],
            "state": [
                Path("/var/lib/overkill"),
                Path("/var/lib/overkill/cache"),
                Path("/var/lib/overkill/state"),
                Path("/var/lib/overkill/backups"),
                Path("/var/lib/overkill/downloads"),
                Path("/var/lib/overkill/temp")
            ],
            "media": [
                self.media_root / "Videos",
                self.media_root / "Music",
                self.media_root / "Pictures",
                self.media_root / "Games",
                self.media_root / "Downloads"
            ]
        }
    
    def create_all_directories(self) -> bool:
        """Create all OVERKILL directories"""
        success = True
        
        for category, dirs in self.directories.items():
            logger.info(f"Creating {category} directories...")
            for directory in dirs:
                if not ensure_directory(directory):
                    logger.error(f"Failed to create {directory}")
                    success = False
                else:
                    # Set appropriate permissions
                    if category in ["logging", "state"]:
                        directory.chmod(0o755)
        
        # Set ownership for user directories
        import subprocess
        subprocess.run(["chown", "-R", "overkill:overkill", str(self.media_root)], 
                      capture_output=True)
        
        return success
    
    def create_version_file(self) -> bool:
        """Create OVERKILL version file"""
        version_content = f"""OVERKILL_VERSION="3.0.0"
OVERKILL_CODENAME="PYTHON_POWER"
OVERKILL_BUILD_DATE="{datetime.now().strftime('%Y-%m-%d')}"
OVERKILL_BUILD_TIME="{datetime.now().strftime('%H:%M:%S')}"
OVERKILL_MOTTO="UNLIMITED POWER. ZERO RESTRICTIONS."
OVERKILL_FEATURES="overclock,thermal,kodi_builder,docker,addons"
"""
        
        version_file = self.overkill_home / "VERSION"
        return atomic_write(version_file, version_content)
    
    def create_default_configs(self) -> bool:
        """Create default configuration templates"""
        templates = {
            "network/interfaces.conf": """# OVERKILL Network Configuration
# Optimized for media streaming

# Ethernet
auto eth0
iface eth0 inet dhcp
  pre-up ethtool -s eth0 speed 1000 duplex full autoneg on
  post-up echo 2 > /proc/sys/net/ipv4/tcp_ecn
  post-up echo 1 > /proc/sys/net/ipv4/tcp_sack
  post-up echo 1 > /proc/sys/net/ipv4/tcp_dsack
""",
            "display/hdmi.conf": """# OVERKILL Display Configuration
# Optimized for 4K HDR

hdmi_enable_4kp60=1
hdmi_force_hotplug=1
disable_overscan=1
hdmi_pixel_freq_limit=600000000
hdmi_cvt=3840 2160 60 3 0 0 1
""",
            "audio/asound.conf": """# OVERKILL Audio Configuration
# High quality audio output

pcm.!default {
    type hw
    card 0
    device 0
}

ctl.!default {
    type hw
    card 0
}
""",
            "remote/lircd.conf": """# OVERKILL Remote Control Configuration
# CEC and IR support

# Placeholder for remote configuration
"""
        }
        
        success = True
        for relative_path, content in templates.items():
            file_path = self.overkill_config / relative_path
            if not atomic_write(file_path, content):
                success = False
        
        return success
    
    def create_scripts(self) -> bool:
        """Create utility scripts"""
        scripts = {
            "backup-overkill.sh": """#!/bin/bash
# OVERKILL Backup Script

BACKUP_DIR="/var/lib/overkill/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/overkill_backup_$TIMESTAMP.tar.gz"

echo "Creating OVERKILL backup..."
tar -czf "$BACKUP_FILE" \\
    /etc/overkill \\
    /opt/overkill/config \\
    /home/overkill/.kodi/userdata \\
    /boot/config.txt \\
    /boot/armbianEnv.txt 2>/dev/null

echo "Backup created: $BACKUP_FILE"
""",
            "restore-defaults.sh": """#!/bin/bash
# OVERKILL Restore Defaults Script

echo "Restoring OVERKILL to default settings..."

# Restore config.txt
if [ -f /boot/config.txt.pre-overkill ]; then
    cp /boot/config.txt.pre-overkill /boot/config.txt
    echo "Restored original config.txt"
fi

# Remove overclock settings
sed -i '/# OVERKILL PI 5 CONFIGURATION/,/^$/d' /boot/config.txt

echo "Default settings restored. Please reboot."
""",
            "monitor-temps.sh": """#!/bin/bash
# OVERKILL Temperature Monitor

while true; do
    TEMP=$(vcgencmd measure_temp | cut -d= -f2 | cut -d. -f1)
    FREQ=$(vcgencmd get_config arm_freq | cut -d= -f2)
    THROTTLE=$(vcgencmd get_throttled | cut -d= -f2)
    
    printf "\\rTemp: %s°C | Freq: %sMHz | Throttle: %s" "$TEMP" "$FREQ" "$THROTTLE"
    
    sleep 1
done
"""
        }
        
        success = True
        for script_name, content in scripts.items():
            script_path = self.overkill_home / "scripts" / script_name
            if atomic_write(script_path, content):
                script_path.chmod(0o755)
            else:
                success = False
        
        return success
    
    def setup_all(self) -> bool:
        """Setup complete infrastructure"""
        if not self.create_all_directories():
            return False
        
        if not self.create_version_file():
            return False
        
        if not self.create_default_configs():
            return False
        
        if not self.create_scripts():
            return False
        
        logger.info("OVERKILL infrastructure setup complete")
        return True