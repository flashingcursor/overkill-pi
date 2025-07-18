"""TTY configuration for TV viewing optimization"""

import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from ..core.logger import logger
from ..core.utils import run_command, atomic_write


class TTYConfigurator:
    """Configure TTY for optimal TV viewing"""
    
    def __init__(self):
        self.console_setup_file = Path("/etc/default/console-setup")
        self.font_faces = {
            "standard": "Fixed",
            "terminus": "TerminusBold",
            "large": "VGA"
        }
        
        # Font sizes for different resolutions
        self.font_sizes = {
            "4k": {"face": "terminus", "size": "32x16"},
            "1080p": {"face": "terminus", "size": "28x14"}, 
            "720p": {"face": "terminus", "size": "20x10"},
            "default": {"face": "standard", "size": "16x8"}
        }
    
    def is_physical_console(self) -> bool:
        """Check if running on physical console (not SSH)"""
        try:
            tty = os.ttyname(0)
            return tty.startswith("/dev/tty") and not tty.startswith("/dev/pts")
        except:
            return False
    
    def get_framebuffer_resolution(self) -> Optional[Tuple[int, int]]:
        """Get framebuffer resolution"""
        try:
            # Install fbset if not available
            if not Path("/usr/bin/fbset").exists():
                logger.info("Installing fbset for resolution detection...")
                run_command(["apt-get", "install", "-y", "fbset"])
            
            # Get resolution from fbset
            ret, stdout, _ = run_command(["fbset", "-s"])
            if ret == 0:
                for line in stdout.split('\n'):
                    if 'mode' in line and '"' in line:
                        # Extract resolution from mode line
                        mode = line.split('"')[1]
                        if 'x' in mode:
                            width, height = mode.split('x')[:2]
                            return int(width), int(height.split('-')[0])
            
        except Exception as e:
            logger.debug(f"Failed to get framebuffer resolution: {e}")
        
        return None
    
    def determine_font_config(self) -> dict:
        """Determine optimal font configuration based on resolution"""
        resolution = self.get_framebuffer_resolution()
        
        if not resolution:
            logger.warning("Could not detect resolution, using default font")
            return self.font_sizes["default"]
        
        width, height = resolution
        logger.info(f"Detected resolution: {width}x{height}")
        
        if width >= 3840:
            return self.font_sizes["4k"]
        elif width >= 1920:
            return self.font_sizes["1080p"]
        elif width >= 1280:
            return self.font_sizes["720p"]
        else:
            return self.font_sizes["default"]
    
    def install_fonts(self) -> bool:
        """Install console fonts if needed"""
        packages = ["console-setup", "console-data", "kbd"]
        
        missing = []
        for pkg in packages:
            ret, _, _ = run_command(["dpkg", "-l", pkg])
            if ret != 0:
                missing.append(pkg)
        
        if missing:
            logger.info(f"Installing console font packages: {', '.join(missing)}")
            ret, _, err = run_command(["apt-get", "install", "-y"] + missing)
            if ret != 0:
                logger.error(f"Failed to install font packages: {err}")
                return False
        
        return True
    
    def configure_console_setup(self, font_config: dict) -> bool:
        """Configure console-setup with optimal settings"""
        try:
            # Read existing configuration
            config_lines = []
            if self.console_setup_file.exists():
                with open(self.console_setup_file, 'r') as f:
                    config_lines = f.readlines()
            
            # Update or add font settings
            face = self.font_faces[font_config["face"]]
            size = font_config["size"]
            
            updated = False
            new_lines = []
            
            for line in config_lines:
                if line.startswith("FONTFACE="):
                    new_lines.append(f'FONTFACE="{face}"\n')
                    updated = True
                elif line.startswith("FONTSIZE="):
                    new_lines.append(f'FONTSIZE="{size}"\n')
                    updated = True
                else:
                    new_lines.append(line)
            
            # Add settings if not found
            if not updated:
                new_lines.extend([
                    f'FONTFACE="{face}"\n',
                    f'FONTSIZE="{size}"\n'
                ])
            
            # Write configuration
            if atomic_write(self.console_setup_file, ''.join(new_lines)):
                logger.info(f"Configured console font: {face} {size}")
                return True
            
        except Exception as e:
            logger.error(f"Failed to configure console setup: {e}")
        
        return False
    
    def apply_font_settings(self) -> bool:
        """Apply font settings to current console"""
        try:
            # Apply settings using setupcon
            ret, _, err = run_command(["setupcon", "--save-only"])
            if ret != 0:
                logger.warning(f"setupcon save failed: {err}")
            
            # Force immediate application on console
            if self.is_physical_console():
                ret, _, err = run_command(["setupcon", "--force"])
                if ret == 0:
                    logger.info("Applied new console font settings")
                    return True
                else:
                    logger.warning(f"Failed to apply font: {err}")
            
        except Exception as e:
            logger.error(f"Failed to apply font settings: {e}")
        
        return False
    
    def configure_for_tv(self) -> bool:
        """Main method to configure TTY for TV viewing"""
        if not self.is_physical_console():
            logger.info("Not on physical console, skipping TTY configuration")
            return True
        
        # Install required packages
        if not self.install_fonts():
            return False
        
        # Determine optimal font
        font_config = self.determine_font_config()
        
        # Configure console-setup
        if not self.configure_console_setup(font_config):
            return False
        
        # Apply settings
        self.apply_font_settings()
        
        # Additional TV optimizations
        self.apply_tv_optimizations()
        
        return True
    
    def apply_tv_optimizations(self):
        """Apply additional optimizations for TV viewing"""
        try:
            # Disable console blanking
            run_command(["setterm", "-blank", "0", "-powerdown", "0"])
            
            # Set console to not clear on boot
            if Path("/etc/systemd/system/getty@tty1.service.d").exists():
                override = """[Service]
TTYVTDisallocate=no
"""
                override_file = Path("/etc/systemd/system/getty@tty1.service.d/noclear.conf")
                atomic_write(override_file, override)
            
            logger.info("Applied TV viewing optimizations")
            
        except Exception as e:
            logger.warning(f"Some TV optimizations failed: {e}")