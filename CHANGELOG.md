# Changelog

All notable changes to OVERKILL-PI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Silicon quality testing with progressive stress tests
- Silicon grading system (S/A/B/C/D) based on stability
- Custom overclock profile creator with validation
- Real-time thermal monitoring with hardware fan speed reading
- Kodi addon installer with dependency resolution
- Support for popular addon repositories (Umbrella, FEN, Seren, etc.)
- Real-Debrid integration for Kodi addons
- Comprehensive Kodi settings management
- Temperature trend analysis in thermal status
- Power consumption estimation
- Throttle detection and reporting
- Armbian compatibility for all features
- CLAUDE.md for AI-assisted development
- Extensive documentation updates

### Changed
- Replaced placeholder implementations with working code
- Enhanced thermal monitoring with multiple detection methods
- Improved overclock profile recommendations based on silicon testing
- Updated bootstrap script for better error handling

### Fixed
- Fan speed detection on various Pi 5 configurations
- Boot config path detection for Armbian
- Network configuration for NetworkManager systems

## [3.0.0] - 2024-01-15

### Added
- Complete Python rewrite of OVERKILL
- Professional TUI using curses
- Modular architecture with plugin support
- Comprehensive hardware detection
- Safe overclock profiles
- Thermal management system
- Kodi integration framework

### Changed
- Migrated from bash to Python
- New configuration format (JSON/YAML)
- Improved error handling
- Better logging system

### Removed
- Legacy bash scripts
- Manual configuration editing

## [2.0.0] - 2023-12-01

### Added
- Initial Raspberry Pi 5 support
- NVMe optimization
- Basic overclock profiles

## [1.0.0] - 2023-06-15

### Added
- Initial release for Raspberry Pi 4
- Basic overclocking features
- Simple bash-based menu system