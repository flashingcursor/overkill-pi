"""User management for OVERKILL"""

import pwd
import grp
import crypt
import subprocess
from typing import List, Optional
from ..core.logger import logger
from ..core.utils import run_command


class UserManager:
    """Manage OVERKILL user creation and permissions"""
    
    def __init__(self):
        self.username = "overkill"
        self.groups = [
            "sudo", "audio", "video", "input", "dialout", 
            "plugdev", "netdev", "render", "gpio", "spi", 
            "i2c", "kmem", "disk", "adm"
        ]
        self.home_dirs = [
            ".kodi", ".overkill", "Pictures", "Videos", 
            "Music", "Downloads", "Games"
        ]
    
    def user_exists(self, username: str) -> bool:
        """Check if user exists"""
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False
    
    def create_overkill_user(self, password: str) -> bool:
        """Create the overkill user with all necessary permissions"""
        try:
            if self.user_exists(self.username):
                logger.info(f"User {self.username} already exists")
                return True
            
            # Create user
            logger.info(f"Creating user {self.username}")
            ret, _, err = run_command([
                "useradd",
                "-m",  # Create home directory
                "-s", "/bin/bash",  # Shell
                "-c", "Overkill Media Center",  # Comment
                self.username
            ])
            
            if ret != 0:
                logger.error(f"Failed to create user: {err}")
                return False
            
            # Set password
            encrypted_pass = crypt.crypt(password, crypt.mksalt(crypt.METHOD_SHA512))
            ret, _, err = run_command([
                "usermod",
                "-p", encrypted_pass,
                self.username
            ])
            
            if ret != 0:
                logger.error(f"Failed to set password: {err}")
                return False
            
            # Add to groups
            existing_groups = []
            for group in self.groups:
                try:
                    grp.getgrnam(group)
                    existing_groups.append(group)
                except KeyError:
                    logger.debug(f"Group {group} does not exist, skipping")
            
            if existing_groups:
                groups_str = ",".join(existing_groups)
                ret, _, err = run_command([
                    "usermod",
                    "-a", "-G", groups_str,
                    self.username
                ])
                
                if ret != 0:
                    logger.warning(f"Failed to add some groups: {err}")
            
            # Create home directory structure
            self._create_home_directories()
            
            # Set ownership
            home_path = f"/home/{self.username}"
            run_command(["chown", "-R", f"{self.username}:{self.username}", home_path])
            
            logger.info(f"User {self.username} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return False
    
    def _create_home_directories(self) -> None:
        """Create directory structure in user's home"""
        home_path = f"/home/{self.username}"
        
        for dirname in self.home_dirs:
            dir_path = f"{home_path}/{dirname}"
            run_command(["sudo", "-u", self.username, "mkdir", "-p", dir_path])
    
    def grant_sudo_nopasswd(self) -> bool:
        """Grant passwordless sudo access (optional, for convenience)"""
        try:
            sudoers_content = f"{self.username} ALL=(ALL) NOPASSWD: ALL\n"
            sudoers_file = f"/etc/sudoers.d/{self.username}"
            
            with open(sudoers_file, 'w') as f:
                f.write(sudoers_content)
            
            # Set proper permissions
            run_command(["chmod", "0440", sudoers_file])
            
            logger.info(f"Granted passwordless sudo to {self.username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant sudo access: {e}")
            return False
    
    def configure_autologin(self) -> bool:
        """Configure automatic login for kiosk mode"""
        try:
            # For systemd-based systems
            getty_override_dir = "/etc/systemd/system/getty@tty1.service.d"
            run_command(["mkdir", "-p", getty_override_dir])
            
            override_content = f"""[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin {self.username} --noclear %I $TERM
"""
            
            override_file = f"{getty_override_dir}/autologin.conf"
            with open(override_file, 'w') as f:
                f.write(override_content)
            
            # Reload systemd
            run_command(["systemctl", "daemon-reload"])
            
            logger.info("Configured automatic login")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure autologin: {e}")
            return False