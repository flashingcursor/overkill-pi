"""Kodi configuration management for OVERKILL"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from ..core.logger import logger
from ..core.utils import backup_file, atomic_write, ensure_directory


class KodiConfigurator:
    """Manage Kodi installation and configuration"""
    
    def __init__(self, kodi_home: Optional[Path] = None):
        self.kodi_home = kodi_home or Path("/home/overkill/.kodi")
        self.userdata = self.kodi_home / "userdata"
        self.addons = self.kodi_home / "addons"
        
    def is_installed(self) -> bool:
        """Check if Kodi is installed"""
        return self.kodi_home.exists() and (self.userdata / "guisettings.xml").exists()
    
    def create_directory_structure(self) -> bool:
        """Create Kodi directory structure"""
        directories = [
            self.kodi_home,
            self.userdata,
            self.userdata / "addon_data",
            self.userdata / "Database",
            self.userdata / "playlists",
            self.userdata / "playlists" / "video",
            self.userdata / "playlists" / "music",
            self.userdata / "Thumbnails",
            self.addons,
            self.kodi_home / "media",
            self.kodi_home / "system",
            self.kodi_home / "temp"
        ]
        
        try:
            for directory in directories:
                ensure_directory(directory)
            return True
        except Exception as e:
            logger.error(f"Failed to create Kodi directories: {e}")
            return False
    
    def configure_advanced_settings(self, cache_size_mb: int = 500) -> bool:
        """Create optimized advancedsettings.xml for Pi 5"""
        
        # Convert MB to bytes
        cache_size = cache_size_mb * 1024 * 1024
        
        settings = f"""<?xml version="1.0" encoding="UTF-8"?>
<advancedsettings>
  <!-- OVERKILL Optimized Settings for Pi 5 -->
  
  <!-- Cache Settings -->
  <cache>
    <buffermode>1</buffermode>
    <memorysize>{cache_size}</memorysize>
    <readfactor>20</readfactor>
  </cache>
  
  <!-- Network Settings -->
  <network>
    <bandwidth>0</bandwidth>
    <readbuffersize>0</readbuffersize>
    <httptimeout>30</httptimeout>
  </network>
  
  <!-- Video Settings -->
  <video>
    <busydialogdelayms>500</busydialogdelayms>
    <percentseekbackward>-2</percentseekbackward>
    <percentseekbackwardbig>-4</percentseekbackwardbig>
    <percentseekforward>2</percentseekforward>
    <percentseekforwardbig>4</percentseekforwardbig>
    <blackbarcolour>1</blackbarcolour>
    <fullscreenonexit>false</fullscreenonexit>
    <adjustrefreshrate>1</adjustrefreshrate>
    <stereoscopicregex3d>[-. _]3d[-. _]</stereoscopicregex3d>
    <stereoscopicregexsbs>[-. _]h?sbs[-. _]</stereoscopicregexsbs>
    <stereoscopicregextab>[-. _]h?tab[-. _]</stereoscopicregextab>
  </video>
  
  <!-- Audio Settings -->
  <audio>
    <ac3passthrough>true</ac3passthrough>
    <dtspassthrough>true</dtspassthrough>
    <multichannellpcm>false</multichannellpcm>
    <truehdpassthrough>true</truehdpassthrough>
    <dtshdpassthrough>true</dtshdpassthrough>
  </audio>
  
  <!-- GUI Settings -->
  <gui>
    <algorithmdirtyregions>3</algorithmdirtyregions>
    <visualizedirtyregions>false</visualizedirtyregions>
  </gui>
  
  <!-- Database Settings -->
  <videodatabase>
    <multiplecommits>5000</multiplecommits>
  </videodatabase>
  
  <musicdatabase>
    <multiplecommits>5000</multiplecommits>
  </musicdatabase>
  
</advancedsettings>
"""
        
        try:
            # Backup existing file if present
            advanced_settings_path = self.userdata / "advancedsettings.xml"
            if advanced_settings_path.exists():
                backup_file(advanced_settings_path)
            
            # Write new settings
            return atomic_write(advanced_settings_path, settings)
        
        except Exception as e:
            logger.error(f"Failed to write advanced settings: {e}")
            return False
    
    def configure_sources(self, sources: Dict[str, List[str]]) -> bool:
        """Configure media sources"""
        
        sources_xml = """<?xml version="1.0" encoding="UTF-8"?>
<sources>
"""
        
        for source_type, paths in sources.items():
            sources_xml += f"    <{source_type}>\n"
            sources_xml += "        <default pathversion=\"1\"></default>\n"
            
            for i, path in enumerate(paths):
                sources_xml += f"""        <source>
            <name>{Path(path).name}</name>
            <path pathversion="1">{path}</path>
            <allowsharing>true</allowsharing>
        </source>
"""
            
            sources_xml += f"    </{source_type}>\n"
        
        sources_xml += "</sources>"
        
        try:
            sources_path = self.userdata / "sources.xml"
            if sources_path.exists():
                backup_file(sources_path)
            
            return atomic_write(sources_path, sources_xml)
        
        except Exception as e:
            logger.error(f"Failed to write sources: {e}")
            return False
    
    def enable_services(self) -> bool:
        """Enable useful Kodi services"""
        
        services = {
            "webserver": {
                "enabled": "true",
                "port": "8080",
                "username": "kodi",
                "password": "overkill"
            },
            "airplay": {
                "enabled": "true"
            },
            "upnp": {
                "enabled": "true",
                "renderer": "true",
                "server": "true"
            },
            "zeroconf": {
                "enabled": "true"
            }
        }
        
        # This would modify guisettings.xml
        # For now, return True as placeholder
        logger.info("Kodi services configuration not fully implemented")
        return True
    
    def install_addon(self, addon_id: str, repo_url: Optional[str] = None) -> bool:
        """Install a Kodi addon"""
        from .addon_installer import AddonInstaller
        
        installer = AddonInstaller(self.kodi_home)
        
        try:
            logger.info(f"Installing addon: {addon_id}")
            
            # Check if already installed
            if installer.is_addon_installed(addon_id):
                logger.info(f"Addon {addon_id} is already installed")
                return True
            
            # Install the addon
            result = installer.install_addon(addon_id, repo_url)
            
            if result:
                logger.info(f"Successfully installed addon: {addon_id}")
            else:
                logger.error(f"Failed to install addon: {addon_id}")
                
            return result
            
        except Exception as e:
            logger.error(f"Addon installation error: {e}")
            return False
    
    def get_installed_addons(self) -> List[str]:
        """Get list of installed addons"""
        
        addon_list = []
        
        if self.addons.exists():
            for addon_dir in self.addons.iterdir():
                if addon_dir.is_dir() and (addon_dir / "addon.xml").exists():
                    addon_list.append(addon_dir.name)
        
        return addon_list
    
    def optimize_for_pi5(self) -> bool:
        """Apply Pi 5 specific optimizations"""
        
        try:
            # Create advanced settings
            self.configure_advanced_settings(cache_size_mb=500)
            
            # Create default sources
            default_sources = {
                "video": [
                    "/media/Videos",
                    "/home/overkill/Videos",
                    "nfs://192.168.1.1/media/videos/"
                ],
                "music": [
                    "/media/Music",
                    "/home/overkill/Music"
                ],
                "pictures": [
                    "/media/Pictures",
                    "/home/overkill/Pictures"
                ]
            }
            
            self.configure_sources(default_sources)
            
            # Enable services
            self.enable_services()
            
            logger.info("Applied Pi 5 optimizations to Kodi")
            return True
            
        except Exception as e:
            logger.error(f"Failed to optimize Kodi for Pi 5: {e}")
            return False
    
    def create_autostart_script(self) -> bool:
        """Create Kodi autostart script"""
        
        autostart_script = """#!/bin/bash
# OVERKILL Kodi Autostart Script

# Wait for network
sleep 10

# Set display environment
export DISPLAY=:0.0

# Launch Kodi
/usr/bin/kodi-standalone

# Restart on crash
while true; do
    if ! pgrep -x "kodi" > /dev/null; then
        /usr/bin/kodi-standalone
    fi
    sleep 5
done
"""
        
        try:
            script_path = Path("/home/overkill/.config/autostart/kodi.sh")
            ensure_directory(script_path.parent)
            
            if atomic_write(script_path, autostart_script):
                os.chmod(script_path, 0o755)
                return True
            
        except Exception as e:
            logger.error(f"Failed to create autostart script: {e}")
        
        return False


class KodiAddonBuilder:
    """Build custom Kodi addons"""
    
    @staticmethod
    def create_addon_xml(addon_id: str, name: str, version: str, 
                        provider: str = "OVERKILL") -> str:
        """Generate addon.xml content"""
        
        return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<addon id="{addon_id}" name="{name}" version="{version}" provider-name="{provider}">
    <requires>
        <import addon="xbmc.python" version="3.0.0"/>
    </requires>
    <extension point="xbmc.service" library="default.py">
        <provides>service</provides>
    </extension>
    <extension point="xbmc.addon.metadata">
        <summary lang="en_GB">OVERKILL Configuration Service</summary>
        <description lang="en_GB">Configure OVERKILL settings from within Kodi</description>
        <platform>linux</platform>
        <license>MIT</license>
    </extension>
</addon>
"""
    
    @staticmethod
    def create_settings_xml() -> str:
        """Generate settings.xml for addon"""
        
        return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<settings>
    <category label="Overclock">
        <setting id="overclock_profile" type="select" label="Profile" 
                 values="safe|balanced|performance|extreme" default="balanced"/>
        <setting id="show_temp" type="bool" label="Show Temperature" default="true"/>
    </category>
    
    <category label="Thermal">
        <setting id="fan_mode" type="select" label="Fan Mode" 
                 values="auto|manual|aggressive|silent" default="auto"/>
        <setting id="target_temp" type="slider" label="Target Temp (°C)" 
                 range="50,5,80" default="65"/>
    </category>
    
    <category label="Advanced">
        <setting id="debug_mode" type="bool" label="Debug Mode" default="false"/>
        <setting type="action" label="Open OVERKILL Config" 
                 action="RunPlugin(plugin://service.overkill/config)"/>
    </category>
</settings>
"""