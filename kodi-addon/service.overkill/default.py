#!/usr/bin/env python3
"""OVERKILL Plugin for Kodi - User interface for configuration"""

import sys
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from urllib.parse import parse_qsl
from resources.lib.overkill_client import OverkillClient


class OverkillPlugin:
    """Main plugin class"""
    
    def __init__(self, base_url, addon_handle):
        self.base_url = base_url
        self.addon_handle = addon_handle
        self.addon = xbmcaddon.Addon()
        self.client = OverkillClient()
        
    def run(self, paramstring):
        """Route to appropriate function"""
        params = dict(parse_qsl(paramstring))
        
        if not params:
            self.main_menu()
        else:
            action = params.get('action')
            
            if action == 'system_info':
                self.show_system_info()
            elif action == 'overclock':
                self.overclock_menu()
            elif action == 'thermal':
                self.thermal_menu()
            elif action == 'set_profile':
                self.set_overclock_profile(params.get('profile'))
            elif action == 'set_fan_mode':
                self.set_fan_mode(params.get('mode'))
            elif action == 'open_configurator':
                self.open_configurator()
            else:
                self.main_menu()
    
    def main_menu(self):
        """Display main menu"""
        xbmcplugin.setPluginCategory(self.addon_handle, 'OVERKILL Configuration')
        xbmcplugin.setContent(self.addon_handle, 'files')
        
        # Get current status
        status = self.client.get_status()
        
        # System Info
        self._add_menu_item(
            'System Information',
            'View detailed system information',
            'action=system_info',
            icon='DefaultProgram.png'
        )
        
        # Overclock
        profile = status.get('profile', 'unknown') if status else 'unknown'
        self._add_menu_item(
            f'Overclock Settings (Current: {profile})',
            'Manage overclock profiles',
            'action=overclock',
            icon='DefaultSettings.png'
        )
        
        # Thermal
        temp = status.get('temperature', 0) if status else 0
        self._add_menu_item(
            f'Thermal Management ({temp:.1f}°C)',
            'Configure fan control and thermal settings',
            'action=thermal',
            icon='DefaultAddonService.png'
        )
        
        # Open full configurator
        self._add_menu_item(
            'Open OVERKILL Configurator',
            'Launch the full configuration interface',
            'action=open_configurator',
            icon='DefaultProgram.png'
        )
        
        xbmcplugin.endOfDirectory(self.addon_handle)
    
    def show_system_info(self):
        """Display system information"""
        info = self.client.get_system_info()
        
        if not info:
            xbmcgui.Dialog().notification(
                'OVERKILL',
                'Failed to get system information',
                xbmcgui.NOTIFICATION_ERROR
            )
            return
        
        # Format info for display
        text = f"""[B]System Information[/B]
        
Model: {info.get('model', 'Unknown')}
CPU: {info.get('cpu', 'Unknown')}
Memory: {info.get('memory_gb', 0):.1f} GB
Kernel: {info.get('kernel', 'Unknown')}

[B]Storage:[/B]"""
        
        # Add storage devices
        for device in info.get('storage_devices', [])[:3]:
            text += f"\n{device.get('device', 'Unknown')}: {device.get('total_gb', 0):.1f}GB ({device.get('percent', 0):.1f}% used)"
        
        # Add NVMe devices
        nvme_devices = info.get('nvme_devices', [])
        if nvme_devices:
            text += "\n\n[B]NVMe Devices:[/B]"
            for nvme in nvme_devices:
                text += f"\n{nvme}"
        
        # Add thermal info
        text += f"\n\n[B]Thermal:[/B]"
        text += f"\nTemperature: {info.get('temperature', 0):.1f}°C"
        text += f"\nCPU Frequency: {info.get('cpu_freq', {}).get('current', 0):.0f} MHz"
        
        if info.get('gpu_freq'):
            text += f"\nGPU Frequency: {info.get('gpu_freq', 0)} MHz"
        
        # Show in text viewer
        xbmcgui.Dialog().textviewer('OVERKILL System Information', text)
    
    def overclock_menu(self):
        """Display overclock menu"""
        profiles = self.client.get_overclock_profiles()
        current = self.client.get_current_profile()
        
        if not profiles:
            xbmcgui.Dialog().notification(
                'OVERKILL',
                'Failed to get overclock profiles',
                xbmcgui.NOTIFICATION_ERROR
            )
            return
        
        # Build menu
        items = []
        for name, profile in profiles.items():
            label = f"{profile['name']}: {profile['arm_freq']}MHz / {profile['gpu_freq']}MHz"
            if name == current:
                label += " [COLOR green](Current)[/COLOR]"
            
            list_item = xbmcgui.ListItem(label)
            list_item.setInfo('video', {
                'plot': profile.get('description', '')
            })
            
            url = f"{self.base_url}?action=set_profile&profile={name}"
            items.append((url, list_item, False))
        
        xbmcplugin.addDirectoryItems(self.addon_handle, items)
        xbmcplugin.endOfDirectory(self.addon_handle)
    
    def thermal_menu(self):
        """Display thermal management menu"""
        xbmcplugin.setPluginCategory(self.addon_handle, 'Thermal Management')
        
        # Fan modes
        modes = ['auto', 'manual', 'aggressive', 'silent']
        current_mode = self.addon.getSetting('fan_mode') or 'auto'
        
        for mode in modes:
            label = mode.capitalize()
            if mode == current_mode:
                label += " [COLOR green](Current)[/COLOR]"
            
            self._add_menu_item(
                label,
                f'Set fan control to {mode} mode',
                f'action=set_fan_mode&mode={mode}',
                icon='DefaultAddonService.png'
            )
        
        xbmcplugin.endOfDirectory(self.addon_handle)
    
    def set_overclock_profile(self, profile):
        """Set overclock profile"""
        if not profile:
            return
        
        dialog = xbmcgui.Dialog()
        if dialog.yesno(
            'OVERKILL',
            f'Apply {profile} overclock profile?',
            'This will require a system reboot.'
        ):
            result = self.client.set_overclock_profile(profile)
            
            if result and result.get('success'):
                dialog.notification(
                    'OVERKILL',
                    f'Applied {profile} profile',
                    xbmcgui.NOTIFICATION_INFO
                )
                
                if dialog.yesno('OVERKILL', 'Reboot now to apply changes?'):
                    xbmc.executebuiltin('Reboot')
            else:
                dialog.notification(
                    'OVERKILL',
                    'Failed to apply profile',
                    xbmcgui.NOTIFICATION_ERROR
                )
    
    def set_fan_mode(self, mode):
        """Set fan control mode"""
        if not mode:
            return
        
        self.addon.setSetting('fan_mode', mode)
        result = self.client.set_fan_mode(mode)
        
        if result and result.get('success'):
            xbmcgui.Dialog().notification(
                'OVERKILL',
                f'Fan mode set to {mode}',
                xbmcgui.NOTIFICATION_INFO
            )
        else:
            xbmcgui.Dialog().notification(
                'OVERKILL',
                'Failed to set fan mode',
                xbmcgui.NOTIFICATION_ERROR
            )
    
    def open_configurator(self):
        """Open full OVERKILL configurator"""
        xbmc.executebuiltin('System.Exec(sudo overkill)')
        xbmcgui.Dialog().notification(
            'OVERKILL',
            'Launching configurator...',
            xbmcgui.NOTIFICATION_INFO
        )
    
    def _add_menu_item(self, label, description, params, icon=None):
        """Add a menu item"""
        list_item = xbmcgui.ListItem(label)
        list_item.setInfo('video', {'plot': description})
        
        if icon:
            list_item.setArt({'icon': icon})
        
        url = f"{self.base_url}?{params}"
        xbmcplugin.addDirectoryItem(
            self.addon_handle,
            url,
            list_item,
            isFolder=('action=' in params and 'set_' not in params)
        )


def main():
    """Main entry point"""
    base_url = sys.argv[0]
    addon_handle = int(sys.argv[1])
    paramstring = sys.argv[2][1:]  # Remove leading '?'
    
    plugin = OverkillPlugin(base_url, addon_handle)
    plugin.run(paramstring)


if __name__ == '__main__':
    main()