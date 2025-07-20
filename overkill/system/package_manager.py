"""Package management for OVERKILL system setup"""

import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from ..core.logger import logger
from ..core.utils import run_command


class PackageManager:
    """Manage system package installation"""
    
    def __init__(self):
        # Essential packages for OVERKILL
        self.packages = {
            "build": [
                "build-essential",
                "cmake",
                "git",
                "pkg-config",
                "autoconf",
                "automake",
                "libtool",
                "gcc",
                "g++",
                "make",
                "ninja-build"
            ],
            "python": [
                "python3-dev",
                "python3-pip",
                "python3-venv",
                "python3-setuptools",
                "python3-wheel"
            ],
            "libraries": [
                "libssl-dev",
                "libcurl4-openssl-dev",
                "libffi-dev",
                "libbz2-dev",
                "libreadline-dev",
                "libsqlite3-dev",
                "libncurses5-dev",
                "libncursesw5-dev",
                "libxml2-dev",
                "libxslt1-dev",
                "liblzma-dev"
            ],
            "media": [
                "ffmpeg",
                "libavcodec-dev",
                "libavformat-dev",
                "libavutil-dev",
                "libswscale-dev",
                "libavfilter-dev",
                "libavdevice-dev",
                # CEC and remote control
                "cec-utils",
                "libcec6",
                "v4l-utils",
                "lirc",
                "ir-keytable"
            ],
            "mesa": [
                # Mesa drivers from RPi unstable repo
                "libgl1-mesa-dri",
                "libglapi-mesa",
                "libgbm1",
                "libegl1-mesa",
                "mesa-vulkan-drivers",
                # RPi firmware updater
                "rpi-update"
            ],
            "kodi_build": [
                "libgl1-mesa-dev",
                "libgles2-mesa-dev",
                "libgbm-dev",
                "libdrm-dev",
                "libdrm2",
                "libdrm-common",
                "libegl1-mesa-dev",
                "libwayland-dev",
                "libxkbcommon-dev",
                "libinput-dev",
                "libudev-dev",
                "libpulse-dev",
                "libasound2-dev",
                "libdbus-1-dev",
                "libglib2.0-dev",
                "libavahi-client-dev",
                "libmicrohttpd-dev",
                "libcec-dev",
                "libbluray-dev",
                "libsmbclient-dev",
                "libnfs-dev",
                "libiso9660-dev",
                "libcdio-dev",
                "libfmt-dev",
                "libspdlog-dev",
                "libgtest-dev",
                "rapidjson-dev",
                "flatbuffers-compiler"
            ],
            "system": [
                "docker.io",
                "docker-compose",
                "stress-ng",
                "cpufrequtils",
                "lm-sensors",
                "nvme-cli",
                "hdparm",
                "iotop",
                "htop",
                "ncdu",
                "tmux",
                "screen"
            ],
            "network": [
                "curl",
                "wget"
            ],
            "network_extra": [
                "net-tools",
                "iperf3"
            ],
            "optional": [
                "nmap",
                "avahi-daemon",
                "samba",
                "samba-common-bin",
                "fbset",
                "console-setup",
                "console-data"
            ]
        }
    
    def update_package_list(self) -> bool:
        """Update package list"""
        logger.info("Updating package database...")
        ret, _, err = run_command(["apt-get", "update"], timeout=300)
        
        if ret != 0:
            logger.error(f"Failed to update package list: {err}")
            return False
        
        return True
    
    def add_rpi_unstable_repo(self) -> bool:
        """Add Raspberry Pi unstable repository for latest Mesa drivers"""
        logger.info("Adding Raspberry Pi unstable repository...")
        
        try:
            # Ensure keyrings directory exists first
            keyring_dir = Path("/etc/apt/keyrings")
            keyring_dir.mkdir(parents=True, exist_ok=True)
            
            keyring_path = "/etc/apt/keyrings/raspi.gpg"
            
            # Add the Raspberry Pi GPG key
            logger.info("Adding Raspberry Pi GPG key...")
            
            # Download and install GPG key using non-interactive method
            gpg_key_url = "https://archive.raspberrypi.org/debian/raspberrypi.gpg.key"
            
            # Download the key
            ret, key_data, err = run_command(["curl", "-fsSL", gpg_key_url], timeout=30)
            if ret != 0:
                logger.error(f"Failed to download GPG key: {err}")
                return False
            
            # Convert to binary format and save
            try:
                import subprocess
                proc = subprocess.Popen(
                    ["gpg", "--dearmor", "-o", keyring_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                _, stderr = proc.communicate(input=key_data.encode())
                
                if proc.returncode != 0:
                    logger.error(f"Failed to dearmor GPG key: {stderr.decode()}")
                    return False
                
                # Ensure proper permissions
                Path(keyring_path).chmod(0o644)
                
            except Exception as e:
                logger.error(f"Failed to process GPG key: {e}")
                return False
            
            # Add RPi Foundation's official unstable repo with signed-by option
            repo_content = f"deb [signed-by={keyring_path}] http://archive.raspberrypi.org/debian/ bookworm main\n"
            with open("/etc/apt/sources.list.d/raspi.list", "w") as f:
                f.write(repo_content)
            
            # Pin Mesa packages to RPi repo
            logger.info("Configuring package priorities...")
            pin_content = """Package: libgl1-mesa-dri libglapi-mesa libgbm1 libegl1-mesa mesa-vulkan-drivers
Pin: origin "archive.raspberrypi.org"
Pin-Priority: 1001
"""
            with open("/etc/apt/preferences.d/99-raspi-mesa.pref", "w") as f:
                f.write(pin_content)
            
            # Update package cache
            logger.info("Updating package cache with new repository...")
            ret, _, err = run_command(["apt-get", "update"], timeout=300)
            if ret != 0:
                logger.warning(f"Package update had issues: {err}")
            
            # Upgrade existing packages to get latest versions from RPi repo
            logger.info("Upgrading system packages...")
            ret, _, err = run_command(["apt-get", "upgrade", "-y"], timeout=900)
            if ret != 0:
                logger.warning(f"Package upgrade had issues: {err}")
            
            logger.info("Raspberry Pi unstable repository added successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add RPi repository: {e}")
            return False
    
    def wait_for_dpkg_lock(self, max_wait: int = 300) -> bool:
        """Wait for dpkg lock to be released"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            # Check if dpkg is locked
            ret1, _, _ = run_command(["fuser", "/var/lib/dpkg/lock-frontend"], timeout=5)
            ret2, _, _ = run_command(["fuser", "/var/cache/debconf/config.dat"], timeout=5)
            
            if ret1 != 0 and ret2 != 0:
                # No locks found
                return True
            
            logger.info("Waiting for package manager lock to be released...")
            time.sleep(5)
        
        return False
    
    def install_packages(self, packages: List[str]) -> bool:
        """Install a list of packages"""
        if not packages:
            return True
        
        # Wait for dpkg lock
        if not self.wait_for_dpkg_lock():
            logger.error("Package manager is locked by another process")
            return False
        
        logger.info(f"Installing {len(packages)} packages...")
        
        # Filter out already installed packages
        to_install = []
        for pkg in packages:
            if not self.check_package_installed(pkg):
                to_install.append(pkg)
        
        if not to_install:
            logger.info("All packages already installed")
            return True
        
        # Install with better error handling
        cmd = ["apt-get", "install", "-y", "--no-install-recommends"] + to_install
        ret, stdout, err = run_command(cmd, timeout=900)  # 15 min timeout
        
        if ret != 0:
            logger.error(f"Failed to install packages: {err}")
            # Try to install packages one by one to identify failures
            failed = []
            for package in to_install:
                if not self.wait_for_dpkg_lock(60):
                    failed.append(package)
                    continue
                    
                ret, _, err = run_command(
                    ["apt-get", "install", "-y", "--no-install-recommends", package], 
                    timeout=600  # 10 minutes for individual packages
                )
                if ret != 0:
                    # Check if package exists
                    ret2, _, _ = run_command(["apt-cache", "show", package], timeout=10)
                    if ret2 != 0:
                        logger.warning(f"Package '{package}' not found in repositories")
                    else:
                        logger.error(f"Failed to install '{package}': {err}")
                    failed.append(package)
            
            if failed:
                logger.error(f"Failed to install: {', '.join(failed)}")
            
            return len(failed) < len(to_install) / 2  # Success if >50% installed
        
        return True
    
    def install_category(self, category: str) -> bool:
        """Install all packages in a category"""
        if category not in self.packages:
            logger.error(f"Unknown package category: {category}")
            return False
        
        packages = self.packages[category]
        logger.info(f"Installing {category} packages ({len(packages)} packages)")
        
        return self.install_packages(packages)
    
    def install_all_packages(self) -> bool:
        """Install all OVERKILL packages"""
        # Update first
        if not self.update_package_list():
            return False
        
        # Install by category (skip optional packages that may not be available)
        categories = ["build", "python", "libraries", "media", 
                     "kodi_build", "system", "network"]
        
        for category in categories:
            logger.info(f"Installing {category} packages...")
            if not self.install_category(category):
                logger.warning(f"Some {category} packages failed to install")
        
        # Enable Docker service
        run_command(["systemctl", "enable", "docker"])
        run_command(["systemctl", "start", "docker"])
        
        # Add overkill user to docker group
        run_command(["usermod", "-aG", "docker", "overkill"])
        
        return True
    
    def check_package_installed(self, package: str) -> bool:
        """Check if a package is installed"""
        ret, _, _ = run_command(["dpkg", "-l", package])
        return ret == 0
    
    def get_missing_packages(self) -> List[str]:
        """Get list of missing packages"""
        missing = []
        
        for category, packages in self.packages.items():
            for package in packages:
                if not self.check_package_installed(package):
                    missing.append(package)
        
        return missing