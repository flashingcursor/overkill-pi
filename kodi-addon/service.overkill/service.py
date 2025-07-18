#!/usr/bin/env python3
"""OVERKILL Service for Kodi - Background monitoring and control"""

import xbmc
import xbmcaddon
import xbmcgui
import time
import json
from resources.lib.overkill_client import OverkillClient


class OverkillMonitor(xbmc.Monitor):
    """Monitor class for OVERKILL service"""
    
    def __init__(self):
        super().__init__()
        self.addon = xbmcaddon.Addon()
        self.client = OverkillClient()
        self.update_interval = 30  # seconds
        self.show_notifications = self.addon.getSetting('show_notifications') == 'true'
        self.temp_warning_threshold = int(self.addon.getSetting('temp_warning') or '75')
        
    def onSettingsChanged(self):
        """Handle settings changes"""
        self.show_notifications = self.addon.getSetting('show_notifications') == 'true'
        self.temp_warning_threshold = int(self.addon.getSetting('temp_warning') or '75')
        xbmc.log("OVERKILL: Settings updated", xbmc.LOGINFO)
    
    def run(self):
        """Main service loop"""
        xbmc.log("OVERKILL Service: Started", xbmc.LOGINFO)
        
        last_warning_time = 0
        warning_interval = 300  # 5 minutes between warnings
        
        while not self.abortRequested():
            try:
                # Get system status
                status = self.client.get_status()
                
                if status:
                    # Update window properties for skin access
                    self._update_window_properties(status)
                    
                    # Check temperature warning
                    temp = status.get('temperature', 0)
                    if temp > self.temp_warning_threshold:
                        current_time = time.time()
                        if current_time - last_warning_time > warning_interval:
                            self._show_temp_warning(temp)
                            last_warning_time = current_time
                    
                    # Log status periodically
                    if int(time.time()) % 300 == 0:  # Every 5 minutes
                        xbmc.log(f"OVERKILL: Temp={temp}°C, Profile={status.get('profile', 'unknown')}", 
                                xbmc.LOGINFO)
                
            except Exception as e:
                xbmc.log(f"OVERKILL Service Error: {str(e)}", xbmc.LOGERROR)
            
            # Wait for next update or abort
            if self.waitForAbort(self.update_interval):
                break
        
        xbmc.log("OVERKILL Service: Stopped", xbmc.LOGINFO)
    
    def _update_window_properties(self, status):
        """Update window properties for skin access"""
        window = xbmcgui.Window(10000)  # Home window
        
        # Set properties
        window.setProperty('overkill.temperature', str(status.get('temperature', 0)))
        window.setProperty('overkill.profile', status.get('profile', 'unknown'))
        window.setProperty('overkill.fan_speed', str(status.get('fan_speed', 0)))
        
        # Throttle status
        throttle = status.get('throttle_status', {})
        window.setProperty('overkill.throttled', 
                          'true' if throttle.get('throttled') else 'false')
    
    def _show_temp_warning(self, temperature):
        """Show temperature warning notification"""
        if self.show_notifications:
            xbmcgui.Dialog().notification(
                'OVERKILL Warning',
                f'High temperature: {temperature:.1f}°C',
                xbmcgui.NOTIFICATION_WARNING,
                5000
            )


def main():
    """Main entry point for service"""
    monitor = OverkillMonitor()
    monitor.run()


if __name__ == '__main__':
    main()