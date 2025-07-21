"""Kodi addon installer with dependency resolution"""

import os
import shutil
import zipfile
import sqlite3
import tempfile
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from ..core.logger import logger
from ..core.utils import ensure_directory


@dataclass
class AddonInfo:
    """Information about a Kodi addon"""
    addon_id: str
    name: str
    version: str
    author: str
    summary: str
    description: str
    dependencies: List[Dict[str, str]]
    
    @classmethod
    def from_xml(cls, xml_content: str):
        """Parse addon info from addon.xml"""
        try:
            root = ET.fromstring(xml_content)
            
            # Get basic info
            addon_id = root.get('id', '')
            name = root.get('name', addon_id)
            version = root.get('version', '0.0.0')
            author = root.get('provider-name', 'Unknown')
            
            # Get metadata
            metadata = root.find('.//extension[@point="xbmc.addon.metadata"]')
            summary = ''
            description = ''
            
            if metadata:
                summary_elem = metadata.find('summary')
                if summary_elem is not None and summary_elem.text:
                    summary = summary_elem.text
                    
                desc_elem = metadata.find('description')
                if desc_elem is not None and desc_elem.text:
                    description = desc_elem.text
            
            # Get dependencies
            dependencies = []
            requires = root.find('requires')
            if requires:
                for imp in requires.findall('import'):
                    dep = {
                        'addon': imp.get('addon', ''),
                        'version': imp.get('version', '0.0.0'),
                        'optional': imp.get('optional', 'false') == 'true'
                    }
                    dependencies.append(dep)
            
            return cls(
                addon_id=addon_id,
                name=name,
                version=version,
                author=author,
                summary=summary,
                description=description,
                dependencies=dependencies
            )
            
        except Exception as e:
            logger.error(f"Failed to parse addon.xml: {e}")
            raise


class AddonInstaller:
    """Install Kodi addons with proper dependency handling"""
    
    # Known repository URLs
    KNOWN_REPOS = {
        'repository.xbmc.org': 'https://mirrors.kodi.tv/addons/nexus',
        'repository.umbrella': 'https://umbrella-dev.github.io/repository.umbrella/',
        'repository.cumination': 'https://kinkin-dev.github.io/repository.kinkin/',
        'repository.fenlight': 'https://tikipeter.github.io/',
        'repository.fenomscrapers': 'https://tikipeter.github.io/',
        'repository.ezra': 'https://ezra-hubbard.github.io/repository.ezra/',
        'repository.seren': 'https://nixgates.github.io/packages/',
        'repository.thecrew': 'https://team-crew.github.io/',
        'repository.numbers': 'https://lookingglass.rocks/addons/',
        'repository.shadow': 'https://kodi.shadowcrew.info/',
        'repository.risingtides': 'https://rising-tides.github.io/repo/',
    }
    
    # Direct download URLs for repository ZIP files
    REPO_ZIP_URLS = {
        'repository.umbrella': 'https://umbrella-dev.github.io/repository.umbrella/repository.umbrella-1.0.0.zip',
        'repository.cumination': 'https://kinkin-dev.github.io/repository.kinkin/repository.cumination-1.1.22.zip',
    }
    
    # Core Kodi modules to skip
    CORE_MODULES = {
        'xbmc.python', 'xbmc.gui', 'xbmc.json', 'xbmc.metadata',
        'xbmc.addon', 'kodi.resource'
    }
    
    def __init__(self, kodi_home: Path):
        self.kodi_home = Path(kodi_home)
        self.addons_dir = self.kodi_home / 'addons'
        self.temp_dir = self.kodi_home / 'temp'
        self.addon_data_dir = self.kodi_home / 'userdata' / 'addon_data'
        
        # Ensure directories exist
        ensure_directory(self.addons_dir)
        ensure_directory(self.temp_dir)
        ensure_directory(self.addon_data_dir)
        
        # Cache for downloaded files
        self.cache_dir = self.kodi_home / 'cache' / 'addons'
        ensure_directory(self.cache_dir)
    
    def is_addon_installed(self, addon_id: str) -> bool:
        """Check if addon is already installed"""
        addon_path = self.addons_dir / addon_id
        return addon_path.exists() and (addon_path / 'addon.xml').exists()
    
    def install_addon(self, addon_id: str, repo_url: Optional[str] = None) -> bool:
        """Install addon with all dependencies"""
        logger.info(f"Starting installation of {addon_id}")
        
        # Track what we've installed to avoid loops
        installed = set()
        to_install = [(addon_id, repo_url)]
        
        while to_install:
            current_id, current_repo = to_install.pop(0)
            
            if current_id in installed or current_id in self.CORE_MODULES:
                continue
            
            if self.is_addon_installed(current_id):
                logger.info(f"{current_id} already installed")
                installed.add(current_id)
                continue
            
            # Download and install
            logger.info(f"Installing {current_id}")
            addon_info = self._install_single_addon(current_id, current_repo)
            
            if addon_info:
                installed.add(current_id)
                
                # Add dependencies to install queue
                for dep in addon_info.dependencies:
                    if not dep['optional'] and dep['addon'] not in installed:
                        to_install.append((dep['addon'], current_repo))
            else:
                logger.error(f"Failed to install {current_id}")
                return False
        
        # Enable all installed addons in database
        for addon_id in installed:
            self._enable_addon_in_db(addon_id)
        
        logger.info(f"Successfully installed {len(installed)} addon(s)")
        return True
    
    def _install_single_addon(self, addon_id: str, repo_url: Optional[str] = None) -> Optional[AddonInfo]:
        """Install a single addon"""
        # Try to download
        zip_path = self._download_addon(addon_id, repo_url)
        if not zip_path:
            return None
        
        # Extract to temp
        temp_extract = self.temp_dir / addon_id
        if temp_extract.exists():
            shutil.rmtree(temp_extract)
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract)
            
            # Find addon directory (might be nested)
            addon_dir = self._find_addon_dir(temp_extract, addon_id)
            if not addon_dir:
                logger.error(f"Invalid addon structure for {addon_id}")
                return None
            
            # Parse addon.xml
            addon_xml_path = addon_dir / 'addon.xml'
            if not addon_xml_path.exists():
                logger.error(f"No addon.xml found for {addon_id}")
                return None
            
            addon_info = AddonInfo.from_xml(addon_xml_path.read_text())
            
            # Move to addons directory
            target_dir = self.addons_dir / addon_id
            if target_dir.exists():
                shutil.rmtree(target_dir)
            
            shutil.move(str(addon_dir), str(target_dir))
            
            # Create addon data directory
            addon_data_path = self.addon_data_dir / addon_id
            ensure_directory(addon_data_path)
            
            logger.info(f"Installed {addon_id} version {addon_info.version}")
            return addon_info
            
        except Exception as e:
            logger.error(f"Installation failed for {addon_id}: {e}")
            return None
        finally:
            # Cleanup
            if temp_extract.exists():
                shutil.rmtree(temp_extract)
    
    def _download_addon(self, addon_id: str, repo_url: Optional[str] = None) -> Optional[Path]:
        """Download addon zip file"""
        # Check cache first
        cached_files = list(self.cache_dir.glob(f"{addon_id}-*.zip"))
        if cached_files:
            logger.info(f"Using cached file for {addon_id}")
            return cached_files[0]
        
        # Check if we have a direct ZIP URL for this addon
        if addon_id in self.REPO_ZIP_URLS:
            zip_path = self._download_direct_zip(addon_id, self.REPO_ZIP_URLS[addon_id])
            if zip_path:
                return zip_path
        
        # Try different sources
        if repo_url:
            zip_path = self._download_from_url(addon_id, repo_url)
            if zip_path:
                return zip_path
        
        # Try known repositories
        for repo_name, repo_base in self.KNOWN_REPOS.items():
            zip_path = self._download_from_url(addon_id, repo_base)
            if zip_path:
                return zip_path
        
        logger.error(f"Could not find {addon_id} in any repository")
        return None
    
    def _download_from_url(self, addon_id: str, repo_base: str) -> Optional[Path]:
        """Download from specific repository URL"""
        # Ensure repo_base ends with /
        if not repo_base.endswith('/'):
            repo_base += '/'
            
        # First, try to get addon.xml to determine version
        addon_xml_url = f"{repo_base}{addon_id}/addon.xml"
        
        try:
            logger.debug(f"Fetching addon.xml from {addon_xml_url}")
            response = requests.get(addon_xml_url, timeout=10)
            
            if response.status_code == 200:
                # Parse to get version
                addon_info = AddonInfo.from_xml(response.text)
                version = addon_info.version
                
                # Download zip file
                zip_filename = f"{addon_id}-{version}.zip"
                zip_url = f"{repo_base}/{addon_id}/{zip_filename}"
                
                logger.info(f"Downloading {zip_filename}")
                zip_response = requests.get(zip_url, timeout=30, stream=True)
                
                if zip_response.status_code == 200:
                    # Save to cache
                    zip_path = self.cache_dir / zip_filename
                    
                    with open(zip_path, 'wb') as f:
                        for chunk in zip_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    logger.info(f"Downloaded {zip_filename} ({zip_path.stat().st_size} bytes)")
                    return zip_path
                    
        except requests.RequestException as e:
            logger.debug(f"Failed to download from {repo_base}: {e}")
        except Exception as e:
            logger.error(f"Download error: {e}")
        
        return None
    
    def _download_direct_zip(self, addon_id: str, zip_url: str) -> Optional[Path]:
        """Download ZIP file directly from URL"""
        try:
            logger.info(f"Downloading {addon_id} from {zip_url}")
            response = requests.get(zip_url, timeout=30, stream=True)
            
            if response.status_code == 200:
                # Extract filename from URL or use default
                filename = zip_url.split('/')[-1]
                if not filename.endswith('.zip'):
                    filename = f"{addon_id}.zip"
                
                zip_path = self.cache_dir / filename
                
                with open(zip_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Downloaded {filename} ({zip_path.stat().st_size} bytes)")
                return zip_path
            else:
                logger.error(f"Failed to download {zip_url}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.error(f"Direct download failed for {addon_id}: {e}")
        
        return None
    
    def _find_addon_dir(self, extract_path: Path, addon_id: str) -> Optional[Path]:
        """Find the actual addon directory in extracted files"""
        # Check if directly in extract path
        if (extract_path / 'addon.xml').exists():
            return extract_path
        
        # Check for addon_id directory
        addon_dir = extract_path / addon_id
        if addon_dir.exists() and (addon_dir / 'addon.xml').exists():
            return addon_dir
        
        # Search one level deep
        for item in extract_path.iterdir():
            if item.is_dir() and (item / 'addon.xml').exists():
                # Verify it's the right addon
                try:
                    xml_content = (item / 'addon.xml').read_text()
                    if f'id="{addon_id}"' in xml_content:
                        return item
                except:
                    pass
        
        return None
    
    def _enable_addon_in_db(self, addon_id: str):
        """Enable addon in Kodi database"""
        # Find the latest Addons database
        db_pattern = 'Addons*.db'
        db_files = list((self.kodi_home / 'userdata' / 'Database').glob(db_pattern))
        
        if not db_files:
            logger.warning("No Kodi addon database found")
            return
        
        # Use the latest version
        db_path = max(db_files, key=lambda p: p.name)
        
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # Check if addon exists in installed table
            cursor.execute(
                "SELECT * FROM installed WHERE addonID = ?",
                (addon_id,)
            )
            
            if not cursor.fetchone():
                # Insert as enabled
                cursor.execute(
                    "INSERT INTO installed (addonID, enabled) VALUES (?, 1)",
                    (addon_id,)
                )
                logger.info(f"Enabled {addon_id} in database")
            else:
                # Update to enabled
                cursor.execute(
                    "UPDATE installed SET enabled = 1 WHERE addonID = ?",
                    (addon_id,)
                )
                logger.info(f"Updated {addon_id} to enabled in database")
            
            conn.commit()
            conn.close()
            
        except sqlite3.Error as e:
            logger.error(f"Database error enabling {addon_id}: {e}")
            # Create marker file as fallback
            self._create_enabled_marker(addon_id)
    
    def _create_enabled_marker(self, addon_id: str):
        """Create enabled marker file as fallback"""
        addon_data_path = self.addon_data_dir / addon_id
        ensure_directory(addon_data_path)
        
        # Create empty enabled marker
        enabled_marker = addon_data_path / 'enabled'
        enabled_marker.touch()
    
    def get_addon_info(self, addon_id: str) -> Optional[AddonInfo]:
        """Get information about an installed addon"""
        addon_path = self.addons_dir / addon_id / 'addon.xml'
        
        if addon_path.exists():
            try:
                return AddonInfo.from_xml(addon_path.read_text())
            except:
                pass
        
        return None