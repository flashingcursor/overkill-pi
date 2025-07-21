"""Kodi addon installer with dependency resolution"""

import os
import re
import shutil
import zipfile
import sqlite3
import tempfile
import requests
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from packaging.version import parse as parse_version
from bs4 import BeautifulSoup
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
    
    def _discover_repository_zip_url(self, base_url: str) -> Optional[str]:
        """Discover the latest repository ZIP URL from the base URL"""
        logger.info(f"Discovering repository ZIP from {base_url}")
        
        try:
            # Ensure base URL ends with /
            if not base_url.endswith('/'):
                base_url += '/'
            
            # Fetch the base URL content
            response = requests.get(base_url, timeout=10)
            response.raise_for_status()
            
            # Parse HTML to find repository ZIP links
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all links that match repository.*.zip pattern
            repo_zips = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                # Match repository.*.zip files
                if re.match(r'^repository\.[^/]+\.zip$', href):
                    repo_zips.append(href)
            
            # Also search in raw text for any missed links
            text_matches = re.findall(r'repository\.[^/]+?-[\d.]+\.zip', response.text)
            repo_zips.extend(text_matches)
            
            # Remove duplicates and filter valid versions
            versioned_zips = {}
            for zip_name in set(repo_zips):
                # Extract version from filename (e.g., repository.umbrella-2.0.10.zip)
                version_match = re.search(r'-([\d.]+)\.zip$', zip_name)
                if version_match:
                    version_str = version_match.group(1)
                    try:
                        version = parse_version(version_str)
                        versioned_zips[version] = zip_name
                    except:
                        logger.debug(f"Could not parse version from {zip_name}")
            
            if not versioned_zips:
                logger.warning("No versioned repository ZIPs found")
                return None
            
            # Select the latest version
            latest_version = max(versioned_zips.keys())
            latest_zip = versioned_zips[latest_version]
            
            # Construct full URL
            if latest_zip.startswith('http'):
                full_url = latest_zip
            else:
                full_url = base_url + latest_zip
            
            logger.info(f"Found latest repository ZIP: {latest_zip} (version {latest_version})")
            return full_url
            
        except Exception as e:
            logger.error(f"Failed to discover repository ZIP: {e}")
            return None
    
    def install_addon_from_repo_url(self, addon_id: str, repo_base_url: str) -> bool:
        """Install addon from repository base URL (with discovery)"""
        logger.info(f"Installing {addon_id} from repository at {repo_base_url}")
        
        # Step 0: Discover the repository ZIP URL
        repo_zip_url = self._discover_repository_zip_url(repo_base_url)
        if not repo_zip_url:
            logger.error("Could not discover repository ZIP URL")
            return False
        
        # Step 1: Install the repository
        repo_addon_id = self._install_repository_from_zip(repo_zip_url)
        if not repo_addon_id:
            logger.error("Failed to install repository")
            return False
        
        # Step 2: Load repository data
        self._load_repository_data(repo_addon_id)
        
        # Step 3: Install the addon using the repository
        return self.install_addon(addon_id, repo_base_url)
    
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
        
        # Notify Kodi to scan for updates instead of direct DB manipulation
        self._notify_kodi_scan()
        
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
    
    def _install_repository_from_zip(self, repo_zip_url: str) -> Optional[str]:
        """Install a repository from its ZIP URL"""
        logger.info(f"Installing repository from {repo_zip_url}")
        
        temp_zip = self.temp_dir / "temp_repo.zip"
        
        try:
            # Download the repository ZIP
            response = requests.get(repo_zip_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save to temp file
            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Extract to addons directory
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                zip_ref.extractall(self.addons_dir)
            
            # Find the repository addon ID from the extracted files
            for item in self.addons_dir.iterdir():
                if item.is_dir() and item.name.startswith('repository.'):
                    addon_xml = item / 'addon.xml'
                    if addon_xml.exists():
                        # Verify this is a repository addon
                        tree = ET.parse(addon_xml)
                        root = tree.getroot()
                        if root.find('.//extension[@point="xbmc.addon.repository"]') is not None:
                            repo_id = root.get('id')
                            logger.info(f"Installed repository: {repo_id}")
                            return repo_id
            
            logger.error("No valid repository found in ZIP")
            return None
            
        except Exception as e:
            logger.error(f"Failed to install repository: {e}")
            return None
        finally:
            # Cleanup
            if temp_zip.exists():
                temp_zip.unlink()
    
    def _load_repository_data(self, repo_addon_id: str):
        """Load repository metadata to find available addons"""
        repo_path = self.addons_dir / repo_addon_id
        if not repo_path.exists():
            logger.error(f"Repository {repo_addon_id} not found")
            return
        
        # Parse repository addon.xml to get the datadir URL
        addon_xml = repo_path / 'addon.xml'
        if not addon_xml.exists():
            return
        
        try:
            tree = ET.parse(addon_xml)
            root = tree.getroot()
            
            # Find repository extension
            repo_ext = root.find('.//extension[@point="xbmc.addon.repository"]')
            if repo_ext is not None:
                datadir = repo_ext.find('datadir')
                if datadir is not None and datadir.text:
                    # Store this repository's base URL for later use
                    self.KNOWN_REPOS[repo_addon_id] = datadir.text.rstrip('/')
                    logger.info(f"Loaded repository {repo_addon_id} with datadir: {datadir.text}")
        except Exception as e:
            logger.error(f"Failed to load repository data: {e}")
    
    def _notify_kodi_scan(self):
        """Notify Kodi to scan for addon updates via JSON-RPC"""
        logger.info("Notifying Kodi to scan for addon updates...")
        
        try:
            # Try common Kodi JSON-RPC endpoints
            kodi_hosts = [
                "http://localhost:8080/jsonrpc",
                "http://127.0.0.1:8080/jsonrpc",
                "http://localhost:8090/jsonrpc"
            ]
            
            payload = {
                "jsonrpc": "2.0",
                "method": "Addons.ScanForUpdates",
                "id": 1
            }
            
            for host in kodi_hosts:
                try:
                    response = requests.post(host, json=payload, timeout=5)
                    if response.status_code == 200:
                        logger.info(f"Successfully triggered Kodi addon scan at {host}")
                        return
                except:
                    continue
            
            logger.info("Could not connect to Kodi JSON-RPC - addons will be detected on next Kodi start")
            
        except Exception as e:
            logger.debug(f"Failed to notify Kodi: {e}")
    
    def _enable_addon_in_db(self, addon_id: str):
        """[DEPRECATED] Direct database manipulation is unsafe and should not be used"""
        logger.warning(f"Skipping direct database manipulation for {addon_id}")
        # The addon will be enabled automatically when Kodi scans for it
    
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