#!/usr/bin/env python3
"""OVERKILL System Installer - Full system setup with MAXIMUM POWER"""

import os
import sys
import time
import getpass
from pathlib import Path
from typing import Optional, List, Tuple
import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from .core.logger import logger
from .core.utils import run_command, is_root, ensure_directory, atomic_write
from .core.system import get_system_detector
from .ui.tui import OverkillTUI
from .hardware.overclock import OverclockManager
from .hardware.thermal import ThermalManager
from .media.kodi_builder import KodiBuilder
from .system.user_manager import UserManager
from .system.package_manager import PackageManager
from .system.kernel_optimizer import KernelOptimizer
from .system.infrastructure import InfrastructureManager
from .system.tty_config import TTYConfigurator


console = Console()


class OverkillInstaller:
    """Complete OVERKILL system installer"""
    
    def __init__(self):
        self.system = get_system_detector()
        self.tui = OverkillTUI()
        self.user_manager = UserManager()
        self.package_manager = PackageManager()
        self.kernel_optimizer = KernelOptimizer()
        self.infrastructure = InfrastructureManager()
        self.tty_config = TTYConfigurator()
        self.overclock = OverclockManager()
        self.thermal = ThermalManager()
        
    def show_banner(self):
        """Show OVERKILL banner with MAXIMUM ENTHUSIASM"""
        banner = """[red]
        ....            _                                       ..         .          ..       .. 
    .x~X88888Hx.       u                                  < .z@8"`        @88>  x .d88"  x .d88"  
   H8X 888888888h.    88Nu.   u.                .u    .    !@88E          %8P    5888R    5888R   
  8888:`*888888888:  '88888.o888c      .u     .d88B :@8c   '888E   u       .     '888R    '888R   
  88888:        `%8   ^8888  8888   ud8888.  ="8888f8888r   888E u@8NL   .@88u    888R     888R   
. `88888          ?>   8888  8888 :888'8888.   4888>'88"    888E`"88*"  ''888E`   888R     888R   
`. ?888%           X   8888  8888 d888 '88%"   4888> '      888E .dN.     888E    888R     888R   
  ~*??.            >   8888  8888 8888.+"      4888>        888E~8888     888E    888R     888R   
 .x88888h.        <   .8888b.888P 8888L       .d888L .+     888E '888&    888E    888R     888R   
:"""8888888x..  .x     ^Y8888*""  '8888c. .+  ^"8888*"      888E  9888.   888&   .888B .  .888B . 
`    `*888888888"        `Y"       "88888%       "Y"      '"888*" 4888"   R888"  ^*888%   ^*888%  
        ""***""                      "YP'                    ""    ""      ""      "%       "%    
[/red]"""
        
        console.print(Panel(banner, style="red", border_style="red"))
        console.print("[cyan]    Version 3.0.0 - Raspberry Pi 5 Media Center DOMINATION[/cyan]")
        console.print("[yellow]    Because a Pi 5 deserves more than basic media playback[/yellow]\n")
    
    def show_disclaimer(self) -> bool:
        """Show full disclaimer and require agreement"""
        console.clear()
        self.show_banner()
        
        disclaimer = """
[red]╔══════════════════════════════════════════════════════════════════════════════╗
║                    [yellow]!!! IMPORTANT - PLEASE READ CAREFULLY !!!                     [red]║
╚══════════════════════════════════════════════════════════════════════════════╝[/red]

[yellow]Welcome to the OVERKILL installation script. Before you proceed, you must understand and agree to the following:[/yellow]

  1. [white]Risk of Data Loss:[/white] This script will modify system files, install packages, and reconfigure your system.
     [red]BACKUP ANY IMPORTANT DATA BEFORE CONTINUING. We are not responsible for any data loss.[/red]

  2. [white]Extreme Overclocking:[/white] This script applies aggressive overclock settings that push your Raspberry Pi 5
     beyond official specifications. This [yellow]requires adequate cooling (e.g., an active cooler)[/yellow].
     [red]Improper cooling can lead to system instability or permanent hardware damage.[/red]

  3. [white]System Stability:[/white] These settings are designed for maximum performance, not guaranteed stability.
     The 'silicon lottery' means not all chips will handle these settings equally well.

  4. [white]No Warranty:[/white] You are using this script at your own risk. Use of this script may void your
     device's warranty. The authors provide this script 'as-is' without any warranty of any kind.

[cyan]By proceeding, you acknowledge these risks and agree that you are solely responsible for any outcome.[/cyan]

To confirm you have read, understood, and agree to these terms, please type [white]I AGREE[/white] and press Enter.
To cancel the installation, press CTRL+C at any time.
"""
        
        console.print(disclaimer)
        
        while True:
            agreement = console.input("\n> ")
            if agreement == "I AGREE":
                return True
            elif agreement.upper() == "I AGREE":
                console.print("[yellow]Please type exactly 'I AGREE' (case sensitive)[/yellow]")
            else:
                console.print("[red]Agreement not provided. Installation cancelled.[/red]")
                return False
    
    def check_system(self) -> bool:
        """Validate system with EXTREME PREJUDICE"""
        console.print("\n[red]▶▶▶ SYSTEM VALIDATION - PI 5 + NVME REQUIRED ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        # Check for Pi 5
        if not self.system.is_pi5:
            console.print(f"[yellow]OVERKILL is designed exclusively for Raspberry Pi 5.[/yellow]")
            console.print(f"[yellow]Detected Model: {self.system.model}[/yellow]")
            console.print("[yellow]Proceeding may cause instability or failure. You proceed at your own risk.[/yellow]")
            
            if not click.confirm("Are you sure you want to continue?"):
                console.print("[red]Installation aborted by user.[/red]")
                return False
        else:
            console.print("[green]Pi 5 detected - MAXIMUM POWER AVAILABLE[/green]")
        
        # Check for NVMe
        nvme_devices = self.system.get_nvme_devices()
        if not nvme_devices:
            console.print("[red]NO NVMe DETECTED - OVERKILL REQUIRES NVMe[/red]")
            console.print("[red]This setup is optimized for NVMe storage. Please install one.[/red]")
            return False
        else:
            console.print(f"[green]NVMe storage detected: {nvme_devices[0]} - MAXIMUM SPEED ENABLED[/green]")
        
        # Check RAM
        memory_gb = self.system.get_memory_info()
        if memory_gb >= 8:
            console.print("[green]8GB RAM detected - ABSOLUTELY MENTAL MODE[/green]")
        else:
            console.print(f"[yellow]Only {memory_gb:.0f}GB RAM - Overkill will still dominate[/yellow]")
        
        # Check cooling
        if Path("/sys/class/thermal/cooling_device0/type").exists():
            console.print("[green]Active cooling detected - READY FOR MAXIMUM OVERCLOCK[/green]")
        else:
            console.print("[yellow]No active cooling detected - GET A FAN FOR FULL POWER[/yellow]")
        
        return True
    
    def set_tty_font(self):
        """Configure TTY for TV viewing"""
        console.print("\n[red]▶▶▶ CONFIGURING TTY FOR TV VIEWING ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        if self.tty_config.is_physical_console():
            self.tty_config.configure_for_tv()
            console.print("[green]TTY font optimized for TV viewing[/green]")
        else:
            console.print("[cyan]SSH session detected. Skipping TTY font adjustment.[/cyan]")
    
    def create_user(self):
        """Create OVERKILL user with FULL SYSTEM ACCESS"""
        console.print("\n[red]▶▶▶ CREATING OVERKILL USER ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        if self.user_manager.user_exists("overkill"):
            console.print("[green]Overkill user already exists - GOOD[/green]")
        else:
            console.print("[green]Creating overkill user with full system access[/green]")
            
            # Get password
            while True:
                password = getpass.getpass("Enter a strong password for the 'overkill' user: ")
                confirm = getpass.getpass("Confirm the password: ")
                
                if password == confirm and password:
                    break
                else:
                    console.print("[yellow]Passwords do not match or are empty. Please try again.[/yellow]")
            
            if self.user_manager.create_overkill_user(password):
                console.print("[green]Overkill user created with full permissions[/green]")
            else:
                console.print("[red]Failed to create user[/red]")
                return False
        
        return True
    
    def setup_infrastructure(self):
        """Create OVERKILL INFRASTRUCTURE - BEYOND LIBREELEC"""
        console.print("\n[red]▶▶▶ OVERKILL INFRASTRUCTURE - BEYOND LIBREELEC ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        console.print("[green]Creating advanced directory structure...[/green]")
        self.infrastructure.create_all_directories()
        self.infrastructure.create_version_file()
        console.print("[green]Advanced infrastructure established[/green]")
    
    def install_packages(self):
        """Install ALL PACKAGES FOR COMPLETE DOMINATION"""
        console.print("\n[red]▶▶▶ INSTALLING COMPLETE DEPENDENCIES ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Installing packages...", total=None)
            
            if self.package_manager.install_all_packages():
                console.print("[green]All dependencies installed[/green]")
            else:
                console.print("[red]Failed to install some packages[/red]")
    
    def optimize_kernel(self):
        """KERNEL OPTIMIZATION - MAXIMUM PERFORMANCE"""
        console.print("\n[red]▶▶▶ KERNEL OPTIMIZATION - MAXIMUM PERFORMANCE ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        console.print("[green]Applying EXTREME kernel optimizations...[/green]")
        self.kernel_optimizer.apply_all_optimizations()
        console.print("[green]Kernel optimizations applied - MAXIMUM PERFORMANCE ACHIEVED[/green]")
    
    def configure_hardware(self):
        """PI 5 HARDWARE DOMINATION - NO RESTRICTIONS"""
        console.print("\n[red]▶▶▶ PI 5 HARDWARE DOMINATION - NO RESTRICTIONS ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        # Apply balanced overclock by default
        from .core.config import OverclockProfile
        balanced = OverclockProfile(
            name="balanced",
            arm_freq=2600,
            gpu_freq=950,
            over_voltage=3,
            description="Initial OVERKILL configuration"
        )
        
        result = self.overclock.apply_profile(balanced)
        if result.success:
            console.print("[green]Applied initial overclock settings[/green]")
        
        console.print("[yellow]Applied EXTREME overclocking - monitor your temps![/yellow]")
    
    def setup_thermal(self):
        """INTELLIGENT THERMAL MANAGEMENT"""
        console.print("\n[red]▶▶▶ INTELLIGENT THERMAL MANAGEMENT ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        console.print("[green]Installing advanced fan control system...[/green]")
        if self.thermal.install_fan_control():
            console.print("[green]Advanced thermal management configured[/green]")
        else:
            console.print("[yellow]Thermal management setup failed - manual configuration needed[/yellow]")
    
    def build_kodi(self):
        """BUILD KODI FROM SOURCE - OPTIMIZED FOR PI 5"""
        console.print("\n[red]▶▶▶ BUILDING KODI FROM SOURCE ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        console.print("[yellow]Building Kodi from source provides:[/yellow]")
        console.print("  • Latest stable release from GitHub")
        console.print("  • Pi 5 specific CPU optimizations (Cortex-A76)")
        console.print("  • Hardware-accelerated video decoding")
        console.print("  • Optimized for 8GB RAM configurations")
        console.print("  • Latest features and bug fixes")
        console.print("\n[cyan]Build time: 45-80 minutes on Pi 5[/cyan]")
        
        if click.confirm("\nBuild Kodi from source?"):
            builder = KodiBuilder()
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                # Prepare environment
                task = progress.add_task("Installing build dependencies...", total=None)
                if not builder.prepare_build_environment():
                    console.print("[red]Failed to install build dependencies[/red]")
                    return
                
                # Clone source
                progress.update(task, description="Fetching latest Kodi release...")
                if not builder.clone_or_update_source():
                    console.print("[red]Failed to clone source code[/red]")
                    return
                
                # Configure build
                progress.update(task, description="Configuring build with Pi 5 optimizations...")
                if not builder.configure_build():
                    console.print("[red]Failed to configure build[/red]")
                    return
                
                # Build Kodi
                progress.update(task, description="Building Kodi (this will take 30-60 minutes)...")
                if not builder.build_kodi():
                    console.print("[red]Build failed - check logs for details[/red]")
                    return
                
                # Install
                progress.update(task, description="Installing Kodi...")
                if not builder.install_kodi():
                    console.print("[red]Installation failed[/red]")
                    return
                
                # Create service
                progress.update(task, description="Creating systemd service...")
                builder.create_systemd_service()
                
                # Apply optimizations
                progress.update(task, description="Applying Pi 5 optimizations...")
                builder.optimize_for_pi5()
            
            console.print("[green]✓ Kodi built and installed successfully![/green]")
            console.print("[cyan]Kodi installed to: /opt/overkill/kodi[/cyan]")
            console.print("[cyan]Start with: sudo systemctl start kodi[/cyan]")
        else:
            console.print("[yellow]Skipping Kodi build - you can build it later from the configurator[/yellow]")
    
    def show_addon_info(self):
        """Show information about addon repositories"""
        console.print("\n[cyan]Addon repositories can be installed from the configurator:[/cyan]")
        console.print("- Umbrella Repository (premium all-in-one addon)")
        console.print("- FEN/Seren Pack (popular streaming addons)")
        console.print("- And many more!")
        console.print("\n[yellow]Access via: Media Services → Addon Repositories[/yellow]")
    
    def finalize(self):
        """FINALIZE OVERKILL INSTALLATION"""
        console.print("\n[red]▶▶▶ FINALIZING OVERKILL INSTALLATION ◀◀◀[/red]")
        console.print("[cyan]" + "═" * 60 + "[/cyan]")
        
        console.print("[green]Setting final permissions...[/green]")
        run_command(["chown", "-R", "overkill:overkill", "/home/overkill"])
        
        console.print("\n[red]🔥 OVERKILL INSTALLATION COMPLETE 🔥[/red]")
        console.print("\n[cyan]Run 'sudo overkill' to access the configuration interface[/cyan]")
        
        console.print("\n[white]Ready to experience UNLIMITED POWER?[/white]")
        if click.confirm("Reboot now to apply all changes?"):
            console.print("[red]ACTIVATING OVERKILL MODE...[/red]")
            time.sleep(3)
            run_command(["reboot"])
        else:
            console.print("[yellow]Manual activation required: sudo reboot[/yellow]")
    
    def run(self):
        """Main installation flow"""
        if not is_root():
            console.print("[red]OVERKILL requires root for UNLIMITED POWER[/red]")
            sys.exit(1)
        
        # Show disclaimer
        if not self.show_disclaimer():
            sys.exit(1)
        
        console.clear()
        self.show_banner()
        self.set_tty_font()
        
        console.print("\n[yellow]User agreement accepted. Preparing for ABSOLUTE DOMINATION...[/yellow]\n")
        time.sleep(2)
        
        # Run installation steps
        if not self.check_system():
            sys.exit(1)
        
        if not self.create_user():
            sys.exit(1)
        
        self.setup_infrastructure()
        self.install_packages()
        self.optimize_kernel()
        self.configure_hardware()
        self.setup_thermal()
        self.build_kodi()
        self.show_addon_info()
        self.finalize()


@click.command()
def main():
    """OVERKILL Complete System Installer"""
    installer = OverkillInstaller()
    installer.run()


if __name__ == "__main__":
    main()