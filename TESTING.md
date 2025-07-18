# OVERKILL Testing Guide

## Development Setup

### 1. Create Virtual Environment

```bash
cd overkill
python3 -m venv venv
source venv/bin/activate
pip install -e .[dev]
```

### 2. Install Development Dependencies

```bash
pip install pytest pytest-cov black flake8 mypy
```

## Running Tests

### Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=overkill --cov-report=html

# Run specific test file
pytest tests/test_config.py

# Run with verbose output
pytest -v
```

### Integration Tests

```bash
# Test on actual Pi hardware
sudo python -m pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code
black overkill/

# Lint code
flake8 overkill/

# Type checking
mypy overkill/
```

## Manual Testing Checklist

### Core Functionality

- [ ] Bootstrap script runs without errors
- [ ] Python environment created successfully
- [ ] Configurator launches with correct UI
- [ ] Navigation works (arrow keys, enter, escape)
- [ ] All menu items accessible

### System Detection

- [ ] Pi 5 correctly detected
- [ ] Memory size accurate
- [ ] NVMe devices listed
- [ ] Temperature reading works
- [ ] CPU/GPU frequencies displayed

### Overclock Features

- [ ] Profile list displays correctly
- [ ] Current profile highlighted
- [ ] Silicon quality test runs (~20 minutes)
- [ ] Silicon grade saved and displayed
- [ ] Custom profile creator validates input
- [ ] Profile application creates backup
- [ ] Config.txt modified correctly
- [ ] Reboot prompt appears

### Thermal Management

- [ ] Real-time thermal status displays
- [ ] CPU/GPU temperatures shown
- [ ] Fan speed reading (PWM/RPM)
- [ ] Throttle detection works
- [ ] Power estimation displayed
- [ ] Temperature trend shown
- [ ] Fan mode selection works
- [ ] Service installation successful
- [ ] Service starts and runs

### Kodi Integration

- [ ] Kodi builds from source (~1 hour)
- [ ] Repository installation works
- [ ] Addon installer downloads correctly
- [ ] Dependencies resolved automatically
- [ ] Addons enabled in database
- [ ] Real-Debrid configuration saves
- [ ] Service starts automatically
- [ ] Plugin accessible from Programs
- [ ] System info displays in Kodi
- [ ] Temperature warnings work
- [ ] Settings are saved

## Testing Silicon Quality Feature

### Full Test Procedure

1. **Pre-test Setup**:
   - Ensure active cooling is running
   - Close all other applications
   - Monitor initial temperature (should be < 50°C)

2. **Run Silicon Test**:
   ```bash
   sudo overkill
   # Select: Overclock Configuration → Test Silicon Quality
   # Confirm to start ~20 minute test
   ```

3. **Expected Behavior**:
   - Progress bar shows current test profile
   - Temperature displayed in real-time
   - Each profile tested for 5 minutes
   - Automatic abort if temp > 90°C
   - Results show grade (S/A/B/C/D)

4. **Verify Results**:
   ```bash
   # Check saved grade
   cat /etc/overkill/silicon_grade.json
   ```

## Testing Overclock Profiles

### Safety Protocol

1. **Before Testing**:
   - Run silicon quality test first
   - Ensure adequate cooling installed
   - Have recovery method ready
   - Backup important data

2. **Progressive Testing**:
   ```bash
   # Apply profile based on silicon grade
   sudo overkill
   # Select: Overclock Configuration → Apply Profile
   # Choose recommended profile
   # Reboot when prompted
   
   # Run stress test
   stress-ng --cpu 0 --timeout 300s
   
   # Monitor temperature
   watch -n 1 vcgencmd measure_temp
   ```

3. **Stability Verification**:
   - System boots successfully
   - No kernel panics under load
   - Temperature stays below 85°C
   - No throttling occurs
   - Check throttle status:
     ```bash
     vcgencmd get_throttled
     # Should return: throttled=0x0
     ```

## Performance Benchmarks

### CPU Performance

```bash
# Install sysbench
sudo apt install sysbench

# Run CPU benchmark
sysbench cpu --cpu-max-prime=20000 run

# Record results for each profile
```

### Storage Performance

```bash
# Test NVMe speed
sudo hdparm -tT /dev/nvme0n1

# Write speed test
dd if=/dev/zero of=~/test.tmp bs=1G count=1 oflag=dsync
```

### Media Performance

```bash
# Test Kodi video playback
# Play 4K HEVC content
# Monitor for dropped frames
```

## Debugging

### Enable Debug Logging

```python
# In Python code
from overkill.core.logger import setup_logging
setup_logging(debug=True)
```

### Check Logs

```bash
# OVERKILL logs
tail -f /var/log/overkill/overkill_*.log

# System logs
journalctl -u overkill-thermal -f

# Kodi logs
tail -f ~/.kodi/temp/kodi.log
```

### Common Issues

1. **Import Errors**:
   - Check virtual environment activated
   - Verify all dependencies installed

2. **Permission Errors**:
   - Ensure running with sudo
   - Check file ownership

3. **UI Rendering Issues**:
   - Check terminal size (minimum 80x24)
   - Try different terminal emulators

## Test Coverage Goals

- Core modules: > 80% coverage
- Hardware modules: > 60% coverage (hardware dependent)
- UI modules: > 70% coverage
- Overall: > 75% coverage

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - run: |
        pip install -e .[dev]
        pytest --cov=overkill
        black --check overkill/
        flake8 overkill/
```

## Release Testing

Before each release:

1. [ ] Full installation test on fresh Pi 5
2. [ ] Upgrade test from previous version
3. [ ] All overclock profiles tested
4. [ ] Kodi addon functionality verified
5. [ ] Documentation reviewed and updated
6. [ ] Changelog updated
7. [ ] Version numbers consistent