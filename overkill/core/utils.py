"""Utility functions for OVERKILL"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Union
from datetime import datetime
from .logger import logger


def run_command(
    cmd: Union[str, List[str]], 
    shell: bool = False,
    capture: bool = True,
    timeout: Optional[int] = 30
) -> Tuple[int, str, str]:
    """
    Run a shell command and return result
    
    Args:
        cmd: Command to run (string or list)
        shell: Run through shell
        capture: Capture output
        timeout: Command timeout in seconds
    
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    
    logger.debug(f"Running command: {cmd}")
    
    try:
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=capture,
            text=True,
            timeout=timeout
        )
        
        return result.returncode, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {cmd}")
        return -1, "", "Command timed out"
    
    except Exception as e:
        logger.error(f"Command failed: {cmd} - {e}")
        return -1, "", str(e)


def backup_file(file_path: Union[str, Path], backup_dir: Optional[Path] = None) -> Optional[Path]:
    """
    Create a backup of a file
    
    Args:
        file_path: File to backup
        backup_dir: Directory to store backup (default: same directory)
    
    Returns:
        Path to backup file or None if failed
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"File does not exist: {file_path}")
        return None
    
    if backup_dir is None:
        backup_dir = file_path.parent
    else:
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{file_path.stem}.{timestamp}.bak{file_path.suffix}"
    backup_path = backup_dir / backup_name
    
    try:
        shutil.copy2(file_path, backup_path)
        logger.info(f"Backed up {file_path} to {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to backup {file_path}: {e}")
        return None


def atomic_write(file_path: Union[str, Path], content: str, mode: str = "w") -> bool:
    """
    Write to file atomically (write to temp, then move)
    
    Args:
        file_path: Target file path
        content: Content to write
        mode: Write mode
    
    Returns:
        True if successful
    """
    file_path = Path(file_path)
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")
    
    try:
        # Write to temporary file
        with open(temp_path, mode) as f:
            f.write(content)
        
        # Sync to disk
        os.sync()
        
        # Move to final location
        temp_path.replace(file_path)
        
        logger.debug(f"Successfully wrote to {file_path}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to write to {file_path}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False


def is_service_running(service_name: str) -> bool:
    """Check if a systemd service is running"""
    ret, stdout, _ = run_command(f"systemctl is-active {service_name}")
    return ret == 0 and stdout.strip() == "active"


def restart_service(service_name: str) -> bool:
    """Restart a systemd service"""
    ret, _, _ = run_command(f"systemctl restart {service_name}")
    return ret == 0


def enable_service(service_name: str) -> bool:
    """Enable a systemd service"""
    ret, _, _ = run_command(f"systemctl enable {service_name}")
    return ret == 0


def create_systemd_service(
    name: str,
    description: str,
    exec_start: str,
    user: Optional[str] = None,
    working_dir: Optional[str] = None,
    restart: str = "on-failure",
    environment: Optional[dict] = None
) -> bool:
    """
    Create a systemd service file
    
    Args:
        name: Service name
        description: Service description
        exec_start: Command to execute
        user: User to run as
        working_dir: Working directory
        restart: Restart policy
        environment: Environment variables
    
    Returns:
        True if successful
    """
    service_content = f"""[Unit]
Description={description}
After=multi-user.target

[Service]
Type=simple
ExecStart={exec_start}
Restart={restart}
RestartSec=5
"""
    
    if user:
        service_content += f"User={user}\n"
    
    if working_dir:
        service_content += f"WorkingDirectory={working_dir}\n"
    
    if environment:
        for key, value in environment.items():
            service_content += f'Environment="{key}={value}"\n'
    
    service_content += """
[Install]
WantedBy=multi-user.target
"""
    
    service_path = Path(f"/etc/systemd/system/{name}.service")
    
    if atomic_write(service_path, service_content):
        run_command("systemctl daemon-reload")
        return True
    
    return False


def get_mount_points() -> List[dict]:
    """Get all mount points with usage info"""
    mount_points = []
    
    try:
        import psutil
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                mount_points.append({
                    "device": partition.device,
                    "mountpoint": partition.mountpoint,
                    "fstype": partition.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent
                })
            except:
                continue
    except ImportError:
        logger.warning("psutil not available, using basic mount info")
        ret, stdout, _ = run_command("mount")
        if ret == 0:
            for line in stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 3:
                    mount_points.append({
                        "device": parts[0],
                        "mountpoint": parts[2],
                        "fstype": parts[4].strip('()') if len(parts) > 4 else "unknown"
                    })
    
    return mount_points


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human readable string"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def ensure_directory(path: Union[str, Path], mode: int = 0o755) -> bool:
    """Ensure directory exists with proper permissions"""
    path = Path(path)
    
    try:
        path.mkdir(parents=True, exist_ok=True, mode=mode)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        return False


def is_root() -> bool:
    """Check if running as root"""
    return os.geteuid() == 0


def require_root() -> None:
    """Exit if not running as root"""
    if not is_root():
        logger.error("This operation requires root privileges")
        raise PermissionError("Root privileges required")


def safe_int(value: Union[str, int, float], default: int = 0) -> int:
    """Safely convert value to integer"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Union[str, int, float], default: float = 0.0) -> float:
    """Safely convert value to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default