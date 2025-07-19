"""Package management for OVERKILL system setup"""

import subprocess
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
                "libavdevice-dev"
            ],
            "kodi_build": [
                "libgl1-mesa-dev",
                "libgles2-mesa-dev",
                "libgbm-dev",
                "libdrm-dev",
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
                "wget",
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
                    timeout=300
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