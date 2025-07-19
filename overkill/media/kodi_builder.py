"""Build Kodi from source with Pi 5 optimizations"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from ..core.logger import logger
from ..core.utils import run_command, ensure_directory


class KodiBuilder:
    """Build Kodi from source with MAXIMUM OPTIMIZATION"""
    
    def __init__(self, build_dir: Optional[Path] = None):
        self.build_dir = build_dir or Path("/opt/overkill/build/kodi")
        self.source_dir = self.build_dir / "xbmc"
        self.install_prefix = Path("/opt/overkill/kodi")
        self.kodi_repo = "https://github.com/xbmc/xbmc.git"
        self.build_type = "Release"
        self.cpu_count = os.cpu_count() or 4
        
        # Pi 5 specific optimizations
        self.cmake_flags = {
            "CMAKE_BUILD_TYPE": self.build_type,
            "CMAKE_INSTALL_PREFIX": str(self.install_prefix),
            "CMAKE_C_FLAGS": "-march=armv8.2-a+crypto+fp16+rcpc+dotprod -mtune=cortex-a76 -O3 -pipe",
            "CMAKE_CXX_FLAGS": "-march=armv8.2-a+crypto+fp16+rcpc+dotprod -mtune=cortex-a76 -O3 -pipe",
            "ENABLE_INTERNAL_FLATBUFFERS": "ON",
            "ENABLE_INTERNAL_RapidJSON": "ON",
            "ENABLE_INTERNAL_FMT": "ON",
            "ENABLE_INTERNAL_SPDLOG": "ON",
            "ENABLE_INTERNAL_CROSSGUID": "ON",
            "ENABLE_VAAPI": "OFF",  # Not available on Pi
            "ENABLE_VDPAU": "OFF",  # Not available on Pi
            "CORE_PLATFORM_NAME": "gbm",
            "GBM_RENDER_SYSTEM": "gles",
            "APP_RENDER_SYSTEM": "gles",
            "ENABLE_PULSEAUDIO": "ON",
            "ENABLE_ALSA": "ON",
            "ENABLE_CEC": "ON",
            "ENABLE_BLUETOOTH": "ON",
            "ENABLE_AVAHI": "ON",
            "ENABLE_AIRTUNES": "ON",
            "ENABLE_OPTICAL": "ON",
            "ENABLE_DVDCSS": "ON"
        }
        
        # Build dependencies
        self.build_deps = [
            "autoconf", "automake", "autopoint", "gettext", "autotools-dev",
            "cmake", "curl", "default-jre", "gawk", "gcc", "g++", "cpp", "pkg-config",
            "flatbuffers-compiler", "gdc", "gperf", "libasound2-dev",
            "libass-dev", "libavahi-client-dev", "libavahi-common-dev",
            "libbluetooth-dev", "libbluray-dev", "libbz2-dev", "libcdio-dev", "libcdio++-dev",
            "libcec-dev", "libp8-platform-dev", "libcrossguid-dev",
            "libcurl4-openssl-dev", "libcwiid-dev", "libdbus-1-dev",
            "libegl1-mesa-dev", "libenca-dev", "libflac-dev", "libfontconfig-dev",
            "libfmt-dev", "libfreetype6-dev", "libfribidi-dev", "libfstrcmp-dev",
            "libgbm-dev", "libgcrypt20-dev", "libgif-dev", "libgles2-mesa-dev",
            "libgl1-mesa-dev", "libglu1-mesa-dev", "libgnutls28-dev",
            "libgpg-error-dev", "libgtest-dev", "libinput-dev", "libiso9660-dev",
            "libjpeg-dev", "liblcms2-dev", "liblirc-dev", "libltdl-dev",
            "liblzo2-dev", "libmicrohttpd-dev", "libmariadb-dev",
            "libnfs-dev", "libogg-dev", "libomxil-bellagio-dev", "libpcre3-dev",
            "libplist-dev", "libpng-dev", "libpulse-dev", "libshairplay-dev",
            "libsmbclient-dev", "libspdlog-dev", "libsqlite3-dev", "libssl-dev",
            "libtag1-dev", "libtiff5-dev", "libtinyxml-dev", "libtinyxml2-dev", "libudev-dev",
            "libunistring-dev", "libva-dev", "libvorbis-dev", "libxkbcommon-dev",
            "libxmu-dev", "libxrandr-dev", "libxslt1-dev", "libxt-dev",
            "lsb-release", "meson", "nasm", "ninja-build", "python3-dev",
            "python3-pil", "python3-pip", "rapidjson-dev", "swig", "unzip",
            "uuid-dev", "vainfo", "wayland-protocols", "waylandpp-dev", "zip", "zlib1g-dev",
            "libdisplay-info-dev"
        ]
    
    def prepare_build_environment(self) -> bool:
        """Install all build dependencies"""
        logger.info("Installing Kodi build dependencies...")
        
        # Update package list
        ret, _, _ = run_command(["apt-get", "update"])
        if ret != 0:
            logger.error("Failed to update package list")
            return False
        
        # Install dependencies in chunks to avoid command line length issues
        chunk_size = 20
        failed_packages = []
        
        for i in range(0, len(self.build_deps), chunk_size):
            chunk = self.build_deps[i:i + chunk_size]
            logger.info(f"Installing dependencies chunk {i//chunk_size + 1}...")
            
            ret, _, err = run_command(["apt-get", "install", "-y"] + chunk, timeout=600)
            if ret != 0:
                logger.warning(f"Some packages failed to install: {err}")
                # Try to install packages one by one to identify failures
                for package in chunk:
                    ret, _, _ = run_command(["apt-get", "install", "-y", package], timeout=120)
                    if ret != 0:
                        failed_packages.append(package)
                        logger.warning(f"Failed to install: {package}")
        
        # Install Python dependencies
        python_deps = ["mako", "requests", "setuptools"]
        ret, _, _ = run_command(["pip3", "install"] + python_deps)
        
        if failed_packages:
            logger.warning(f"The following packages failed to install: {', '.join(failed_packages)}")
            logger.warning("Build may still succeed if these were optional dependencies")
        
        return True
    
    def get_latest_release_tag(self) -> Optional[str]:
        """Get the latest stable release tag from GitHub"""
        logger.info("Fetching latest Kodi release tag...")
        
        # Use git ls-remote to get tags
        ret, stdout, err = run_command([
            "git", "ls-remote", "--tags", "--refs", self.kodi_repo
        ], timeout=30)
        
        if ret != 0:
            logger.error(f"Failed to fetch tags: {err}")
            return None
        
        # Parse tags and find latest stable release
        # Kodi uses tags like "21.0-Omega", "20.5-Nexus", etc.
        import re
        version_pattern = re.compile(r'refs/tags/(\d+\.\d+)-\w+$')
        versions = []
        
        for line in stdout.strip().split('\n'):
            match = version_pattern.search(line)
            if match:
                tag = match.group(0).replace('refs/tags/', '')
                version = match.group(1)
                versions.append((version, tag))
        
        if not versions:
            logger.warning("No stable release tags found, using master")
            return None
        
        # Sort by version number and get the latest
        versions.sort(key=lambda x: tuple(map(int, x[0].split('.'))), reverse=True)
        latest_tag = versions[0][1]
        logger.info(f"Latest stable release: {latest_tag}")
        
        return latest_tag
    
    def clone_or_update_source(self, branch: Optional[str] = None) -> bool:
        """Clone or update Kodi source code"""
        ensure_directory(self.build_dir)
        
        # If no branch specified, get latest release
        if branch is None:
            branch = self.get_latest_release_tag()
            if branch is None:
                branch = "master"
                logger.warning("Using master branch as fallback")
        
        if self.source_dir.exists():
            logger.info("Updating existing Kodi source...")
            # Fetch all tags first
            ret, _, _ = run_command(["git", "fetch", "--tags"], cwd=self.source_dir)
            
            # Checkout the desired branch/tag
            ret, _, err = run_command(["git", "checkout", branch], cwd=self.source_dir)
            if ret != 0:
                logger.error(f"Failed to checkout {branch}: {err}")
                return False
            
            # Pull if it's a branch (not a tag)
            if not branch.startswith(tuple(str(i) for i in range(10))):  # Not a version tag
                ret, _, _ = run_command(["git", "pull"], cwd=self.source_dir)
        else:
            logger.info(f"Cloning Kodi source (branch/tag: {branch})...")
            ret, _, err = run_command([
                "git", "clone", "-b", branch, "--depth", "1",
                self.kodi_repo, str(self.source_dir)
            ], timeout=600)
            
            if ret != 0:
                logger.error(f"Failed to clone source: {err}")
                return False
        
        return True
    
    def check_libdisplay_info(self) -> bool:
        """Check if libdisplay-info is available"""
        # First check if the package exists
        ret, _, _ = run_command(["apt-cache", "show", "libdisplay-info-dev"], timeout=10)
        if ret == 0:
            # Try to install it
            ret, _, _ = run_command(["apt-get", "install", "-y", "libdisplay-info-dev"], timeout=120)
            if ret == 0:
                logger.info("libdisplay-info-dev installed successfully")
                return True
        
        # Check if library is already installed
        ret, _, _ = run_command(["pkg-config", "--exists", "libdisplay-info"], timeout=5)
        if ret == 0:
            return True
            
        logger.warning("libdisplay-info not available, will build without it")
        return False
    
    def configure_build(self) -> bool:
        """Configure Kodi build with CMake"""
        build_path = self.source_dir / "build"
        ensure_directory(build_path)
        
        # Check for optional dependencies
        if not self.check_libdisplay_info():
            self.cmake_flags["ENABLE_LIBDISPLAYINFO"] = "OFF"
        
        # Prepare CMake arguments
        cmake_args = ["cmake"]
        for key, value in self.cmake_flags.items():
            cmake_args.append(f"-D{key}={value}")
        cmake_args.append("..")
        
        logger.info("Configuring Kodi build...")
        logger.debug(f"CMake arguments: {' '.join(cmake_args)}")
        
        ret, stdout, err = run_command(cmake_args, cwd=build_path, timeout=300)
        
        if ret != 0:
            logger.error(f"CMake configuration failed: {err}")
            return False
        
        logger.info("Build configuration complete")
        return True
    
    def build_kodi(self) -> bool:
        """Build Kodi with maximum optimization"""
        build_path = self.source_dir / "build"
        
        if not build_path.exists():
            logger.error("Build directory not found. Run configure first.")
            return False
        
        logger.info(f"Building Kodi with {self.cpu_count} parallel jobs...")
        logger.info("This will take 30-60 minutes on Pi 5...")
        
        # Create build timestamp
        start_time = datetime.now()
        
        # Build with make
        ret, _, err = run_command(
            ["make", f"-j{self.cpu_count}"],
            cwd=build_path,
            timeout=7200  # 2 hours timeout
        )
        
        if ret != 0:
            logger.error(f"Build failed: {err}")
            return False
        
        build_time = (datetime.now() - start_time).total_seconds() / 60
        logger.info(f"Build completed in {build_time:.1f} minutes")
        
        return True
    
    def install_kodi(self) -> bool:
        """Install Kodi to prefix directory"""
        build_path = self.source_dir / "build"
        
        logger.info(f"Installing Kodi to {self.install_prefix}")
        
        ret, _, err = run_command(
            ["make", "install"],
            cwd=build_path,
            timeout=300
        )
        
        if ret != 0:
            logger.error(f"Installation failed: {err}")
            return False
        
        # Create symlinks in /usr/local/bin
        self._create_symlinks()
        
        return True
    
    def _create_symlinks(self):
        """Create symlinks for easy access"""
        symlinks = {
            "/usr/local/bin/kodi": self.install_prefix / "bin/kodi",
            "/usr/local/bin/kodi-standalone": self.install_prefix / "bin/kodi-standalone"
        }
        
        for link, target in symlinks.items():
            try:
                if Path(link).exists():
                    Path(link).unlink()
                Path(link).symlink_to(target)
                logger.info(f"Created symlink: {link} -> {target}")
            except Exception as e:
                logger.warning(f"Failed to create symlink {link}: {e}")
    
    def create_systemd_service(self) -> bool:
        """Create systemd service for Kodi"""
        service_content = """[Unit]
Description=OVERKILL Kodi Media Center
After=multi-user.target network.target sound.target

[Service]
Type=simple
User=overkill
Group=overkill
# GPU access groups
SupplementaryGroups=audio,video,input,render
Environment="HOME=/home/overkill"
Environment="KODI_HOME=/opt/overkill/kodi/share/kodi"
# Use GBM windowing for direct GPU access without X11
Environment="WINDOWING=gbm"
Environment="KODI_AE_SINK=ALSA"
ExecStart=/opt/overkill/kodi/bin/kodi-standalone --windowing=gbm
Restart=on-failure
RestartSec=5
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
"""
        
        service_path = Path("/etc/systemd/system/kodi.service")
        
        try:
            with open(service_path, 'w') as f:
                f.write(service_content)
            
            # Reload systemd and enable service
            run_command(["systemctl", "daemon-reload"])
            run_command(["systemctl", "enable", "kodi.service"])
            
            logger.info("Created and enabled Kodi systemd service")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create systemd service: {e}")
            return False
    
    def optimize_for_pi5(self) -> bool:
        """Apply Pi 5 specific optimizations"""
        # Create performance tweaks script
        tweaks_script = self.install_prefix / "bin/kodi-performance.sh"
        
        script_content = """#!/bin/bash
# OVERKILL Kodi Performance Tweaks

# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Increase GPU memory split (requires reboot)
# This is handled by overclock module

# Disable HDMI audio if not needed (reduces load)
# amixer cset numid=3 0

# Launch Kodi with optimizations
KODI_HOME=/opt/overkill/kodi/share/kodi \\
    exec /opt/overkill/kodi/bin/kodi-standalone "$@"
"""
        
        try:
            with open(tweaks_script, 'w') as f:
                f.write(script_content)
            tweaks_script.chmod(0o755)
            
            logger.info("Created performance optimization script")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create optimization script: {e}")
            return False
    
    def full_build(self, branch: Optional[str] = None) -> bool:
        """Perform complete Kodi build from source
        
        Args:
            branch: Specific branch/tag to build. If None, uses latest stable release.
        """
        logger.info("Starting OVERKILL Kodi build from source...")
        
        # Prepare environment
        if not self.prepare_build_environment():
            return False
        
        # Get source (will auto-detect latest release if branch is None)
        if not self.clone_or_update_source(branch):
            return False
        
        # Configure
        if not self.configure_build():
            return False
        
        # Build
        if not self.build_kodi():
            return False
        
        # Install
        if not self.install_kodi():
            return False
        
        # Create service
        if not self.create_systemd_service():
            return False
        
        # Optimize
        if not self.optimize_for_pi5():
            return False
        
        logger.info("KODI BUILD COMPLETE - MAXIMUM OPTIMIZATION ACHIEVED!")
        logger.info(f"Kodi installed to: {self.install_prefix}")
        logger.info("Start with: systemctl start kodi")
        
        return True