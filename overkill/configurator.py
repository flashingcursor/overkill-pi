#!/usr/bin/env python3
"""Main OVERKILL configurator application"""

import sys
import os
from typing import Optional
import click
from .ui.tui import OverkillTUI
from .core.config import Config
from .core.system import get_system_detector, get_system_info
from .core.logger import logger, setup_logging
from .core.utils import is_root, format_bytes
from .media.addon_manager import AddonManager


class OverkillConfigurator:
    """Main configuration application"""
    
    def __init__(self):
        self.config = Config()
        self.system = get_system_detector()
        self.tui = OverkillTUI()
        self.addon_manager = AddonManager()
        self.running = True
        
    def main_menu(self):
        """Main menu options"""
        return [
            "System Information",
            "Overclock Settings",
            "Thermal Management", 
            "Media Services",
            "Network Settings",
            "Display Settings",
            "Advanced Options",
            "About OVERKILL",
            "Exit"
        ]
    
    def show_system_info(self):
        """Display detailed system information"""
        info = get_system_info()
        
        # Format system information
        lines = [
            f"Model: {info.model}",
            f"CPU: {info.cpu}",
            f"Memory: {info.memory_gb:.1f} GB",
            f"Kernel: {info.kernel}",
            f"OS: {info.os_name} {info.os_version[:50]}...",
            "",
            "Storage Devices:"
        ]
        
        # Add storage info
        for device in info.storage_devices[:3]:  # Limit to 3 devices
            lines.append(f"  {device['device']}: {device['total_gb']:.1f}GB "
                        f"({device['percent']:.1f}% used)")
        
        # Add NVMe info
        if info.nvme_devices:
            lines.append("")
            lines.append("NVMe Devices:")
            for nvme in info.nvme_devices:
                lines.append(f"  {nvme}")
        
        # Add temperature
        if info.temperature:
            lines.append("")
            lines.append(f"Temperature: {info.temperature:.1f}°C")
        
        # Add frequency info
        if info.cpu_freq:
            lines.append(f"CPU Frequency: {info.cpu_freq['current']:.0f} MHz")
        if info.gpu_freq:
            lines.append(f"GPU Frequency: {info.gpu_freq} MHz")
        
        # Check overclock status
        current_profile = self.config.get("overclock.current_profile", "none")
        lines.append("")
        lines.append(f"Overclock Profile: {current_profile}")
        
        # Silicon grade
        silicon_grade = self.config.get("hardware.silicon_grade", "unknown")
        lines.append(f"Silicon Grade: {silicon_grade}")
        
        message = "\n".join(lines)
        self.tui.show_info("System Information", message)
    
    def configure_overclock(self):
        """Overclock configuration menu"""
        profiles = self.config.get_all_profiles()
        current = self.config.get("overclock.current_profile", "safe")
        
        menu_items = []
        for name, profile in profiles.items():
            indicator = " (current)" if name == current else ""
            menu_items.append(
                f"{profile.name}: {profile.arm_freq}MHz/{profile.gpu_freq}MHz"
                f"{indicator}"
            )
        
        menu_items.extend([
            "Test Silicon Quality",
            "Create Custom Profile",
            "Back"
        ])
        
        while True:
            choice = self.tui.menu("Overclock Settings", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                break
            elif choice < len(profiles):
                # Select a profile
                profile_name = list(profiles.keys())[choice]
                if self.apply_overclock_profile(profile_name):
                    self.tui.show_success("Success", 
                        f"Applied {profile_name} overclock profile\n"
                        "Reboot required to take effect")
                    break
            elif choice == len(profiles):
                # Test silicon quality
                self.test_silicon_quality()
            elif choice == len(profiles) + 1:
                # Create custom profile
                self.create_custom_profile()
    
    def apply_overclock_profile(self, profile_name: str) -> bool:
        """Apply an overclock profile"""
        profile = self.config.get_profile(profile_name)
        if not profile:
            self.tui.show_error("Error", f"Profile {profile_name} not found")
            return False
        
        # Here we would apply the actual overclock settings
        # For now, just update the config
        self.config.set("overclock.enabled", True)
        self.config.set("overclock.current_profile", profile_name)
        
        logger.info(f"Applied overclock profile: {profile_name}")
        return True
    
    def test_silicon_quality(self):
        """Test silicon quality through progressive stress testing"""
        if not self.tui.confirm(
            "Silicon Quality Test",
            "This will test your Pi 5's silicon quality by:\n\n"
            "• Running progressive overclock tests\n"
            "• Each test takes ~5 minutes\n"
            "• Monitoring temperature and stability\n"
            "• Finding maximum stable overclock\n\n"
            "WARNING: This will stress your system!\n"
            "Ensure adequate cooling is installed.\n\n"
            "Continue with silicon quality test?"
        ):
            return
        
        from .hardware.silicon_tester import SiliconTester
        tester = SiliconTester()
        
        # Create progress dialog
        self.tui.show_message(
            "Testing Silicon Quality",
            "Starting silicon quality test...\n"
            "This will take 15-25 minutes.\n\n"
            "DO NOT power off during testing!",
            msg_type="info"
        )
        
        try:
            # Run tests with progress callback
            def progress_callback(current, total, message):
                # Update UI with progress
                progress_pct = int((current / total) * 100)
                self.tui.draw_header()
                self.tui.stdscr.addstr(
                    10, 10, 
                    f"Progress: {progress_pct}% - {message}"
                )
                self.tui.stdscr.refresh()
            
            # Run the test
            grade = tester.test_silicon_quality(progress_callback)
            
            # Show results
            result_text = (
                f"Silicon Grade: {grade.grade}\n"
                f"{grade.description}\n\n"
                f"Maximum Stable: {grade.max_stable_profile}\n"
                f"Recommended: {grade.recommended_profile}\n\n"
                f"Test Results:\n"
            )
            
            for result in grade.test_results:
                status = "✓ PASS" if result.stable else "✗ FAIL"
                result_text += (
                    f"\n{result.profile_name}: {status}\n"
                    f"  Max Temp: {result.max_temp:.1f}°C\n"
                    f"  Throttled: {'Yes' if result.throttled else 'No'}\n"
                )
                if result.errors:
                    result_text += f"  Errors: {', '.join(result.errors)}\n"
            
            self.tui.show_info("Silicon Quality Results", result_text)
            
            # Offer to apply recommended profile
            if grade.recommended_profile != "stock":
                if self.tui.confirm(
                    "Apply Recommended Profile?",
                    f"Would you like to apply the {grade.recommended_profile} profile?\n\n"
                    "This is a safe overclock for your silicon."
                ):
                    self.apply_overclock_profile(grade.recommended_profile)
                    
        except Exception as e:
            logger.error(f"Silicon testing failed: {e}")
            self.tui.show_error(
                "Test Failed",
                f"Silicon quality test failed:\n{str(e)}\n\n"
                "Please check system logs for details."
            )
    
    def create_custom_profile(self):
        """Create custom overclock profile"""
        from .hardware.profile_creator import CustomProfileCreator
        
        creator = CustomProfileCreator(self.config, self.tui)
        profile = creator.create_profile()
        
        if profile:
            self.tui.show_success(
                "Profile Created",
                f"Custom profile '{profile.name}' has been created.\n\n"
                "You can apply it from the overclock menu."
            )
            
            # Offer to apply now
            if self.tui.confirm("Apply Profile?", "Would you like to apply this profile now?"):
                self.apply_overclock_profile(profile.name)
    
    def configure_thermal(self):
        """Thermal management configuration"""
        menu_items = [
            "Fan Control Mode",
            "Temperature Targets",
            "Fan Curve Editor",
            "View Current Status",
            "Back"
        ]
        
        while True:
            choice = self.tui.menu("Thermal Management", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                break
            elif choice == 0:
                self.configure_fan_mode()
            elif choice == 1:
                self.configure_temp_targets()
            elif choice == 2:
                self.edit_fan_curve()
            elif choice == 3:
                self.show_thermal_status()
    
    def configure_fan_mode(self):
        """Configure fan control mode"""
        modes = ["Auto", "Manual", "Aggressive", "Silent"]
        current = self.config.get("thermal.fan_mode", "auto")
        
        # Find current mode index
        current_idx = 0
        for i, mode in enumerate(modes):
            if mode.lower() == current.lower():
                current_idx = i
                break
        
        choice = self.tui.menu("Select Fan Mode", modes, selected=current_idx)
        if choice is not None:
            self.config.set("thermal.fan_mode", modes[choice].lower())
            self.tui.show_success("Success", f"Fan mode set to {modes[choice]}")
    
    def configure_temp_targets(self):
        """Configure temperature targets (placeholder)"""
        current_target = self.config.get("thermal.target_temp", 65)
        current_max = self.config.get("thermal.max_temp", 80)
        
        self.tui.show_info("Temperature Targets",
            f"Current Settings:\n"
            f"Target Temperature: {current_target}°C\n"
            f"Maximum Temperature: {current_max}°C\n\n"
            "Temperature adjustment not yet implemented")
    
    def edit_fan_curve(self):
        """Edit fan curve (placeholder)"""
        self.tui.show_info("Fan Curve Editor",
            "Fan curve editing allows precise control\n"
            "over fan speed at different temperatures.\n\n"
            "This feature is not yet implemented")
    
    def show_thermal_status(self):
        """Show current thermal status with real fan speed"""
        from .hardware.thermal_monitor import ThermalMonitor
        monitor = ThermalMonitor()
        
        # Get current thermal data
        thermal_data = monitor.get_thermal_status()
        
        # Format display
        status_text = f"CPU Temperature: {thermal_data['cpu_temp']:.1f}°C\n"
        
        if thermal_data['gpu_temp']:
            status_text += f"GPU Temperature: {thermal_data['gpu_temp']:.1f}°C\n"
        
        status_text += f"\nFan Speed: "
        if thermal_data['fan_speed_rpm']:
            status_text += f"{thermal_data['fan_speed_rpm']} RPM ({thermal_data['fan_speed_pct']:.0f}%)\n"
        elif thermal_data['fan_speed_pct'] is not None:
            status_text += f"{thermal_data['fan_speed_pct']:.0f}%\n"
        else:
            status_text += "Unknown\n"
        
        status_text += f"Fan Mode: {thermal_data['fan_mode']}\n"
        
        if thermal_data['pwm_freq']:
            status_text += f"PWM Frequency: {thermal_data['pwm_freq']} Hz\n"
        
        status_text += f"\nThermal State: {thermal_data['thermal_state']}\n"
        
        if thermal_data['throttle_status']['throttled']:
            status_text += "\n⚠️  THROTTLING ACTIVE:\n"
            if thermal_data['throttle_status']['under_voltage']:
                status_text += "  • Under-voltage detected\n"
            if thermal_data['throttle_status']['freq_capped']:
                status_text += "  • Frequency capped\n"
            if thermal_data['throttle_status']['soft_temp_limit']:
                status_text += "  • Soft temperature limit reached\n"
        
        if thermal_data['power_draw']:
            status_text += f"\nEstimated Power: {thermal_data['power_draw']:.1f}W\n"
        
        # Show temperature trend
        history = monitor.get_temperature_history(60)  # Last minute
        if len(history) > 2:
            temps = [h[1] for h in history]
            trend = temps[-1] - temps[0]
            if trend > 2:
                status_text += f"\nTrend: Rising (+{trend:.1f}°C/min)"
            elif trend < -2:
                status_text += f"\nTrend: Falling ({trend:.1f}°C/min)"
            else:
                status_text += "\nTrend: Stable"
        
        self.tui.show_info("Thermal Status", status_text)
    
    def configure_media_services(self):
        """Media services configuration"""
        menu_items = [
            "Kodi Settings",
            "Addon Repositories",
            "Network Shares (Samba)",
            "DLNA Server",
            "AirPlay Support",
            "Bluetooth Audio",
            "Back"
        ]
        
        while True:
            choice = self.tui.menu("Media Services", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                break
            elif choice == 0:
                self.configure_kodi_settings()
            elif choice == 1:
                self.manage_addon_repositories()
            else:
                self.tui.show_info("Coming Soon",
                    f"{menu_items[choice]} configuration\n"
                    "is not yet implemented")
    
    def configure_kodi_settings(self):
        """Configure Kodi-specific settings"""
        self.tui.show_info("Kodi Settings",
            "Kodi configuration includes:\n"
            "- Performance settings\n"
            "- Cache optimization\n"
            "- Audio/Video settings\n"
            "- Library management\n\n"
            "Not yet implemented")
    
    def manage_addon_repositories(self):
        """Manage Kodi addon repositories"""
        # Check if Kodi is installed
        if not self.addon_manager.check_kodi_installed():
            self.tui.show_warning("Kodi Not Found",
                "Kodi installation not detected.\n"
                "Please install Kodi first.")
            return
        
        while True:
            # Get repository status
            installed_repos = self.addon_manager.get_installed_repositories()
            
            menu_items = []
            
            # Premium repositories (what was --umbrella and --fap)
            menu_items.append("═══ PREMIUM REPOSITORIES ═══")
            
            # Umbrella
            umbrella_status = " [INSTALLED]" if "umbrella" in installed_repos else ""
            menu_items.append(f"Umbrella Repository{umbrella_status}")
            
            # FEN/Seren pack
            fap_status = " [INSTALLED]" if "fap" in installed_repos else ""
            menu_items.append(f"FEN/Seren Addon Pack{fap_status}")
            
            menu_items.append("═══ OTHER REPOSITORIES ═══")
            
            # Other repos
            for repo_name in ["crew", "numbers", "shadow", "rising_tides", "cumination"]:
                repo_info = self.addon_manager.get_repository_info(repo_name)
                if repo_info:
                    status = " [INSTALLED]" if repo_info["installed"] else ""
                    menu_items.append(f"{repo_info['name']}{status}")
            
            menu_items.extend([
                "═══ MANAGEMENT ═══",
                "Install Essential Addons",
                "Configure Real-Debrid",
                "Update All Repositories",
                "Back"
            ])
            
            choice = self.tui.menu("Addon Repository Management", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                break
            elif choice == 1:  # Umbrella
                self.install_repository("umbrella")
            elif choice == 2:  # FEN/Seren
                self.install_repository("fap")
            elif choice == 4:  # Crew
                self.install_repository("crew")
            elif choice == 5:  # Numbers
                self.install_repository("numbers")
            elif choice == 6:  # Shadow
                self.install_repository("shadow")
            elif choice == 7:  # Rising Tides
                self.install_repository("rising_tides")
            elif choice == 8:  # Cumination
                self.install_repository("cumination")
            elif choice == 10:  # Essential addons
                self.install_essential_addons()
            elif choice == 11:  # Real-Debrid
                self.configure_real_debrid()
            elif choice == 12:  # Update all
                self.update_all_repositories()
    
    def install_repository(self, repo_name: str):
        """Install a specific repository"""
        repo_info = self.addon_manager.get_repository_info(repo_name)
        if not repo_info:
            self.tui.show_error("Error", f"Unknown repository: {repo_name}")
            return
        
        if repo_info["installed"]:
            self.tui.show_info("Already Installed",
                f"{repo_info['name']} is already installed.")
            return
        
        # Show repository details
        details = f"{repo_info['name']}\n\n{repo_info['description']}\n\n"
        details += "This will install:\n"
        for addon in repo_info['addons']:
            details += f"- {addon}\n"
        details += "\nProceed with installation?"
        
        if self.tui.confirm("Install Repository", details):
            self.tui.show_info("Installing", f"Installing {repo_info['name']}...")
            
            success, message = self.addon_manager.install_repository(repo_name)
            
            if success:
                self.tui.show_success("Success", message)
            else:
                self.tui.show_error("Installation Failed", message)
    
    def install_essential_addons(self):
        """Install essential/recommended addons"""
        if self.tui.confirm("Install Essential Addons",
            "This will install:\n"
            "- YouTube\n"
            "- Netflix (requires account)\n"
            "- Spotify Connect\n"
            "- Twitch\n\n"
            "Continue?"):
            
            self.tui.show_info("Installing", "Installing essential addons...")
            results = self.addon_manager.install_essential_addons()
            
            # Show results
            success_count = sum(1 for r in results.values() if r)
            total_count = len(results)
            
            if success_count == total_count:
                self.tui.show_success("Success", 
                    f"All {total_count} addons installed successfully!")
            else:
                self.tui.show_warning("Partial Success",
                    f"Installed {success_count} of {total_count} addons.\n"
                    "Check logs for details.")
    
    def configure_real_debrid(self):
        """Configure Real-Debrid integration"""
        self.tui.show_info("Real-Debrid Configuration",
            "Real-Debrid provides premium links for streaming.\n\n"
            "To configure:\n"
            "1. Get your API key from real-debrid.com\n"
            "2. Enter it in the next screen\n\n"
            "This feature is not yet fully implemented.")
    
    def update_all_repositories(self):
        """Update all installed repositories"""
        installed = self.addon_manager.get_installed_repositories()
        
        if not installed:
            self.tui.show_info("No Repositories",
                "No repositories are currently installed.")
            return
        
        if self.tui.confirm("Update Repositories",
            f"Update {len(installed)} installed repositories?"):
            
            self.tui.show_info("Updating", "Updating repositories...")
            results = self.addon_manager.update_all_repositories()
            
            success_count = sum(1 for r in results.values() if r)
            self.tui.show_success("Update Complete",
                f"Updated {success_count} of {len(results)} repositories.")
    
    def configure_network(self):
        """Network configuration"""
        self.tui.show_info("Network Settings",
            "Network configuration includes:\n"
            "- WiFi settings\n"
            "- Performance optimization\n"
            "- Wake-on-LAN\n"
            "- Static IP configuration\n\n"
            "Not yet implemented")
    
    def configure_display(self):
        """Display configuration"""
        self.tui.show_info("Display Settings",
            "Display configuration includes:\n"
            "- Resolution settings\n"
            "- Refresh rate\n"
            "- HDR configuration\n"
            "- Overscan adjustment\n\n"
            "Not yet implemented")
    
    def advanced_options(self):
        """Advanced options menu"""
        menu_items = [
            "Backup Configuration",
            "Restore Configuration",
            "Reset to Defaults",
            "View Logs",
            "Developer Options",
            "Back"
        ]
        
        while True:
            choice = self.tui.menu("Advanced Options", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                break
            elif choice == 2:
                # Reset to defaults
                if self.tui.confirm("Reset Configuration",
                    "This will reset all settings to defaults"):
                    self.config.reset_to_defaults()
                    self.tui.show_success("Success", 
                        "Configuration reset to defaults")
            else:
                self.tui.show_info("Coming Soon",
                    f"{menu_items[choice]} is not yet implemented")
    
    def show_about(self):
        """Show about information"""
        self.tui.show_info("About OVERKILL",
            "OVERKILL v3.0.0\n"
            "Professional Media Center for Raspberry Pi 5\n\n"
            "Features:\n"
            "- Extreme overclocking\n"
            "- Intelligent thermal management\n"
            "- Custom Kodi builds\n"
            "- Advanced media services\n\n"
            "UNLIMITED POWER. ZERO RESTRICTIONS.\n\n"
            "Use at your own risk!")
    
    def run(self, tui: OverkillTUI):
        """Main run loop"""
        # Check requirements
        meets_requirements, issues = self.system.check_requirements()
        
        if not meets_requirements:
            message = "System does not meet all requirements:\n\n"
            for issue in issues:
                message += f"- {issue}\n"
            message += "\nContinue anyway?"
            
            if not tui.confirm("Requirements Check", message):
                return
        
        # Main menu loop
        while self.running:
            menu_items = self.main_menu()
            choice = tui.menu("OVERKILL Configuration", menu_items)
            
            if choice is None or choice == len(menu_items) - 1:
                # Exit
                if tui.confirm("Exit", "Are you sure you want to exit?"):
                    self.running = False
            elif choice == 0:
                self.show_system_info()
            elif choice == 1:
                self.configure_overclock()
            elif choice == 2:
                self.configure_thermal()
            elif choice == 3:
                self.configure_media_services()
            elif choice == 4:
                self.configure_network()
            elif choice == 5:
                self.configure_display()
            elif choice == 6:
                self.advanced_options()
            elif choice == 7:
                self.show_about()
    
    def start(self):
        """Start the configurator"""
        try:
            self.tui.run(self.run)
        except Exception as e:
            logger.error(f"Configurator error: {e}")
            raise


@click.command()
@click.option('--debug', is_flag=True, help='Enable debug output')
def main(debug: bool):
    """OVERKILL Media Center Configurator"""
    # Check for root
    if not is_root():
        print("This program must be run as root (use sudo)")
        sys.exit(1)
    
    # Setup logging
    setup_logging(debug)
    
    # Create and run configurator
    configurator = OverkillConfigurator()
    configurator.start()


if __name__ == "__main__":
    main()