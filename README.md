# OVERKILL-PI

Professional media center configuration tool for Raspberry Pi 5, featuring aggressive overclocking, thermal management, and Kodi integration with a terminal-based UI similar to raspi-config.

## Features

### Core Functionality
- **Interactive TUI**: Professional terminal interface for easy configuration
- **Hardware Detection**: Automatic Pi 5 detection and validation
- **Silicon Quality Testing**: Comprehensive stress testing to grade your chip (S/A/B/C/D)
- **Smart Overclocking**: Safe overclock profiles based on actual silicon capability
- **Custom Profile Creation**: Create and test your own overclock profiles
- **Thermal Management**: Real-time fan speed monitoring and intelligent control
- **Temperature Monitoring**: Live thermal status with throttle detection

### Media Center Features  
- **Kodi Integration**: Build Kodi from source with Pi 5 optimizations
- **Addon Management**: Automatic addon installation with dependency resolution
- **Repository Support**: Pre-configured popular repositories (Umbrella, FEN, Seren, etc.)
- **Real-Debrid Integration**: Configure premium streaming services
- **Settings Management**: Comprehensive Kodi configuration

### System Optimization
- **Kernel Tuning**: Performance optimizations for media playback
- **Network Configuration**: Ethernet and WiFi setup
- **Display Configuration**: HDMI/4K settings optimized for TVs
- **Armbian Support**: Full compatibility with Armbian for Raspberry Pi

## Quick Start

```bash
# Download and run bootstrap script
curl -sSL https://raw.githubusercontent.com/flashingcursor/overkill-pi/master/overkill-bootstrap.sh | sudo bash

# Or clone and install locally
git clone https://github.com/flashingcursor/overkill-pi
cd overkill-pi
sudo ./overkill-bootstrap.sh

# Launch configurator
sudo overkill
```

## Requirements

### Hardware
- Raspberry Pi 5 (8GB strongly recommended for best performance)
- NVMe SSD storage (required - SD cards not supported)
- Active cooling solution (official Pi 5 cooler minimum)
- Quality power supply (27W USB-C PD recommended)

### Software
- Armbian for Raspberry Pi 5 (recommended) or Raspberry Pi OS (64-bit)
- Python 3.9 or newer
- Internet connection for package downloads

## Installation

### Method 1: Quick Install (Recommended)
```bash
# Download and run the bootstrap script
curl -sSL https://raw.githubusercontent.com/flashingcursor/overkill-pi/master/overkill-bootstrap.sh | sudo bash
```

### Method 2: Manual Installation
```bash
# Clone the repository
git clone https://github.com/flashingcursor/overkill-pi.git
cd overkill-pi

# Run the bootstrap script
sudo ./overkill-bootstrap.sh
```

### Post-Installation
After installation, launch the configurator:
```bash
sudo overkill
```

On first run, the installer will:
1. Detect your hardware
2. Create the overkill user
3. Install dependencies
4. Apply initial optimizations
5. Optionally build Kodi from source

## Usage

### Main Menu Options

1. **System Information** - View detailed hardware info and current settings
2. **Overclock Configuration** - Apply and test overclock profiles
3. **Thermal Management** - Configure fan control and temperature targets
4. **Media Services** - Kodi installation and addon management
5. **Network Configuration** - Setup WiFi and ethernet
6. **Display Configuration** - HDMI and resolution settings
7. **Advanced Options** - Additional system tweaks

### Silicon Quality Testing

Test your Pi 5's overclocking capability:
```bash
sudo overkill
# Select: Overclock Configuration → Test Silicon Quality
```

The test will:
- Run progressive stress tests (15-25 minutes)
- Monitor temperature and stability
- Grade your chip (S/A/B/C/D)
- Recommend safe overclock settings

### Creating Custom Profiles

```bash
sudo overkill
# Select: Overclock Configuration → Create Custom Profile
```

Enter your desired frequencies and voltages with real-time validation.

## Architecture

```
overkill-pi/
├── overkill/              # Main Python package
│   ├── core/              # Core functionality (config, logging, utils)
│   ├── hardware/          # Hardware detection and control
│   │   ├── overclock.py   # Overclock profile management
│   │   ├── silicon_tester.py  # Silicon quality testing
│   │   ├── thermal.py     # Fan control
│   │   └── thermal_monitor.py # Real-time monitoring
│   ├── media/             # Kodi and media services
│   │   ├── kodi_builder.py    # Build from source
│   │   ├── addon_installer.py # Addon management
│   │   └── addon_manager.py   # Repository handling
│   ├── system/            # System configuration
│   ├── ui/                # Terminal UI components
│   └── plugins/           # Extension system
├── overkill-bootstrap.sh  # Installation script
├── requirements.txt       # Python dependencies
└── setup.py              # Package configuration
```

## Development

```bash
# Set up development environment
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]

# Run tests
pytest

# Format code
black overkill/

# Type checking
mypy overkill/
```

## Troubleshooting

### Common Issues

1. **"NVMe not detected"**
   - Ensure NVMe drive is properly seated in the M.2 HAT
   - Check power supply is adequate (27W recommended)
   - Update bootloader: `sudo rpi-eeprom-update -a`

2. **"Temperature too high" during testing**
   - Improve cooling solution
   - Check thermal paste application
   - Ensure proper airflow in case

3. **"Kodi build fails"**
   - Ensure at least 8GB RAM
   - Check internet connection
   - Free up disk space (need ~10GB for build)

4. **System instability after overclock**
   - Boot while holding SHIFT to disable overclock
   - Run `sudo overkill` and select a lower profile
   - Check power supply quality

### Logs and Support

Logs are stored in:
```
/home/overkill/.local/share/overkill/logs/
```

For issues, please include:
- Hardware details (RAM, cooling, power supply)
- Log files
- Screenshot of error

Report issues at: https://github.com/flashingcursor/overkill-pi/issues

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code passes linting (`black`, `flake8`)
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - See [LICENSE](LICENSE) file for details

## Disclaimer

**⚠️ WARNING: USE AT YOUR OWN RISK ⚠️**

This tool applies aggressive optimizations that may:
- **Void your warranty**
- **Cause permanent hardware damage**
- **Lead to data loss**
- **Result in system instability**

**Requirements for safe operation:**
- Adequate cooling (active cooler minimum)
- Quality power supply (27W USB-C PD)
- Proper ventilation
- Temperature monitoring

The authors are not responsible for any damage to your hardware. By using this software, you accept all risks.

## Acknowledgments

- Raspberry Pi Foundation for the excellent Pi 5
- Kodi team for the media center platform
- Armbian team for ARM Linux excellence
- Community testers and contributors

---

**OVERKILL-PI** - Because your Pi 5 deserves to run at MAXIMUM POWER! 🔥