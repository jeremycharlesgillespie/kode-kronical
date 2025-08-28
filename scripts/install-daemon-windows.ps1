# kode-kronical-daemon installation script for Windows
# Requires PowerShell 5.0+ and Administrator privileges

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("install", "uninstall", "start", "stop", "status")]
    [string]$Action = "install",
    
    [Parameter(Mandatory=$false)]
    [string]$InstallPath = "C:\Program Files\kode-kronical",
    
    [Parameter(Mandatory=$false)]
    [string]$DataPath = "C:\ProgramData\kode-kronical",
    
    [Parameter(Mandatory=$false)]
    [string]$ServiceName = "kode-kronical-daemon"
)

# Ensure we're running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator. Please run PowerShell as Administrator and try again."
    exit 1
}

# Configuration
$ErrorActionPreference = "Stop"
$ConfigPath = Join-Path $DataPath "config"
$LogPath = Join-Path $DataPath "logs"
$ServiceDisplayName = "KodeKronical System Monitoring Daemon"
$ServiceDescription = "Continuous system monitoring daemon for kode-kronical performance tracking"

# Helper functions
function Write-ColorMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { Write-ColorMessage $args[0] "Green" }
function Write-Info { Write-ColorMessage $args[0] "Cyan" }
function Write-Warning { Write-ColorMessage $args[0] "Yellow" }
function Write-Error { Write-ColorMessage $args[0] "Red" }

function Test-PythonInstallation {
    Write-Info "Checking Python installation..."
    
    try {
        $pythonVersion = python --version 2>&1
        if ($pythonVersion -match "Python (\d+)\.(\d+)") {
            $major = [int]$matches[1]
            $minor = [int]$matches[2]
            if ($major -ge 3 -and $minor -ge 8) {
                Write-Success "Found Python $pythonVersion"
                return $true
            } else {
                Write-Warning "Python version $pythonVersion found, but Python 3.8+ is required"
            }
        }
    } catch {
        Write-Warning "Python not found in PATH"
    }
    
    return $false
}

function Install-Python {
    Write-Info "Installing Python..."
    
    # Check if Chocolatey is available
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Using Chocolatey to install Python..."
        choco install python -y
    } else {
        Write-Info "Chocolatey not found. Please install Python 3.8+ manually from https://python.org"
        Write-Info "Make sure to check 'Add Python to PATH' during installation"
        Write-Warning "After installing Python, please run this script again"
        exit 1
    }
    
    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    
    if (-not (Test-PythonInstallation)) {
        Write-Error "Python installation failed or Python is not in PATH"
        exit 1
    }
}

function Install-Requirements {
    Write-Info "Installing Python requirements..."
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Install core requirements
    if (Test-Path "requirements.txt") {
        python -m pip install -r requirements.txt
    } else {
        Write-Warning "requirements.txt not found, installing basic dependencies"
        python -m pip install omegaconf
    }
    
    # Install psutil for system monitoring
    Write-Info "Installing psutil..."
    python -m pip install psutil
    
    # Install additional dependencies
    python -m pip install pyyaml pywin32
    
    Write-Success "Python requirements installed"
}

function Create-Directories {
    Write-Info "Creating directories..."
    
    @($InstallPath, $DataPath, $ConfigPath, $LogPath) | ForEach-Object {
        if (-not (Test-Path $_)) {
            New-Item -ItemType Directory -Path $_ -Force | Out-Null
            Write-Info "Created directory: $_"
        }
    }
    
    Write-Success "Directories created"
}

function Install-DaemonFiles {
    Write-Info "Installing daemon files..."
    
    # Get script directory and project root
    $scriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $projectRoot = Split-Path -Parent $scriptDir
    $daemonPath = Join-Path $projectRoot "kode-kronical-daemon"
    
    # Copy daemon executable
    if (-not (Test-Path $daemonPath)) {
        Write-Error "kode-kronical-daemon executable not found at: $daemonPath"
        Write-Error "Please ensure kode-kronical-daemon exists in the project root"
        exit 1
    }
    
    $targetDaemonPath = Join-Path $InstallPath "kode-kronical-daemon"
    Copy-Item $daemonPath $targetDaemonPath -Force
    
    # Copy source files if they exist
    $srcPath = Join-Path $projectRoot "src"
    if (Test-Path $srcPath) {
        $targetSrcPath = Join-Path $InstallPath "src"
        Copy-Item $srcPath $targetSrcPath -Recurse -Force
        Write-Info "Copied source files to: $targetSrcPath"
    }
    
    Write-Success "Daemon files installed to: $InstallPath"
}

function Install-Configuration {
    Write-Info "Installing configuration..."
    
    $configFile = Join-Path $ConfigPath "daemon.yaml"
    
    # Get script directory and project root
    $scriptDir = Split-Path -Parent $MyInvocation.PSCommandPath
    $projectRoot = Split-Path -Parent $scriptDir
    $exampleConfig = Join-Path $projectRoot "config\daemon.yaml.example"
    
    if (Test-Path $exampleConfig) {
        Copy-Item $exampleConfig $configFile -Force
    } else {
        # Create basic configuration
        $configContent = @"
daemon:
  pid_file: $DataPath\daemon.pid
  log_file: $LogPath\daemon.log
  data_dir: $DataPath\data
  sample_interval: 1.0
  data_retention_hours: 168
  enable_network_monitoring: true

monitoring:
  auto_track_python: true
  cpu_alert_threshold: 90
  memory_alert_threshold: 85

export:
  format: json
  compress: true
  batch_size: 1000
"@
        $configContent | Out-File -FilePath $configFile -Encoding UTF8
    }
    
    # Update paths in config file for Windows
    $config = Get-Content $configFile -Raw
    $config = $config -replace "~/.local/share/kode-kronical", ($DataPath -replace "\\", "\\")
    $config = $config -replace "/var/log/kode-kronical", ($LogPath -replace "\\", "\\")
    $config = $config -replace "/var/run/kode-kronical-daemon.pid", (Join-Path $DataPath "daemon.pid" -replace "\\", "\\")
    $config | Out-File -FilePath $configFile -Encoding UTF8 -NoNewline
    
    Write-Success "Configuration installed to: $configFile"
}

function Create-WindowsService {
    Write-Info "Creating Windows service..."
    
    # Create wrapper script for Windows service
    $wrapperScript = Join-Path $InstallPath "service-wrapper.py"
    $wrapperContent = @"
import os
import sys
import time
import subprocess
import win32serviceutil
import win32service
import win32event
import servicemanager

class KodeKronicalDaemonService(win32serviceutil.ServiceFramework):
    _svc_name_ = "$ServiceName"
    _svc_display_name_ = "$ServiceDisplayName"
    _svc_description_ = "$ServiceDescription"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.daemon_process = None
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        if self.daemon_process:
            self.daemon_process.terminate()
        win32event.SetEvent(self.hWaitStop)
        
    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                            servicemanager.PYS_SERVICE_STARTED,
                            (self._svc_name_, ''))
        
        # Change to installation directory
        os.chdir(r"$InstallPath")
        
        # Start daemon process
        daemon_path = os.path.join(r"$InstallPath", "kode-kronical-daemon")
        config_path = os.path.join(r"$ConfigPath", "daemon.yaml")
        
        cmd = [sys.executable, daemon_path, "-c", config_path, "start"]
        
        try:
            self.daemon_process = subprocess.Popen(cmd)
            
            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service failed: {e}")

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(KodeKronicalDaemonService)
"@
    
    $wrapperContent | Out-File -FilePath $wrapperScript -Encoding UTF8
    
    # Install the service
    python $wrapperScript install
    
    Write-Success "Windows service created: $ServiceName"
}

function Start-DaemonService {
    Write-Info "Starting kode-kronical-daemon service..."
    
    try {
        Start-Service -Name $ServiceName
        Start-Sleep -Seconds 3
        
        $service = Get-Service -Name $ServiceName
        if ($service.Status -eq "Running") {
            Write-Success "Service started successfully"
        } else {
            Write-Error "Service failed to start. Status: $($service.Status)"
        }
    } catch {
        Write-Error "Failed to start service: $($_.Exception.Message)"
    }
}

function Stop-DaemonService {
    Write-Info "Stopping kode-kronical-daemon service..."
    
    try {
        Stop-Service -Name $ServiceName -Force
        Write-Success "Service stopped"
    } catch {
        Write-Warning "Service may not be running: $($_.Exception.Message)"
    }
}

function Get-DaemonStatus {
    Write-Info "Checking daemon status..."
    
    try {
        $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
        if ($service) {
            Write-Info "Service Status: $($service.Status)"
            
            # Check for data files
            $dataDir = Join-Path $DataPath "data"
            if (Test-Path $dataDir) {
                $dataFiles = Get-ChildItem -Path $dataDir -Filter "metrics_*.json" | Where-Object { $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) }
                if ($dataFiles.Count -gt 0) {
                    Write-Success "✓ Recent data files found ($($dataFiles.Count) files)"
                } else {
                    Write-Warning "✗ No recent data files found"
                }
            }
        } else {
            Write-Warning "Service not installed"
        }
    } catch {
        Write-Error "Failed to check status: $($_.Exception.Message)"
    }
}

function Remove-Installation {
    Write-Info "Uninstalling kode-kronical-daemon..."
    
    # Stop and remove service
    try {
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        $wrapperScript = Join-Path $InstallPath "service-wrapper.py"
        if (Test-Path $wrapperScript) {
            python $wrapperScript remove
        }
    } catch {
        Write-Warning "Failed to remove service: $($_.Exception.Message)"
    }
    
    # Remove files
    if (Test-Path $InstallPath) {
        Remove-Item $InstallPath -Recurse -Force
        Write-Info "Removed: $InstallPath"
    }
    
    if (Test-Path $DataPath) {
        Remove-Item $DataPath -Recurse -Force
        Write-Info "Removed: $DataPath"
    }
    
    Write-Success "Uninstallation complete"
}

function Show-Usage {
    Write-Success "Installation complete!"
    Write-Info ""
    Write-Info "Usage:"
    Write-Info "  Get-Service $ServiceName                    # Check service status"
    Write-Info "  Start-Service $ServiceName                  # Start service"
    Write-Info "  Stop-Service $ServiceName                   # Stop service"
    Write-Info "  Restart-Service $ServiceName                # Restart service"
    Write-Info "  Get-EventLog -LogName Application -Source '$ServiceName' -Newest 10  # View logs"
    Write-Info ""
    Write-Info "Configuration:"
    Write-Info "  Config file: $(Join-Path $ConfigPath 'daemon.yaml')"
    Write-Info "  Data directory: $(Join-Path $DataPath 'data')"
    Write-Info "  Log directory: $LogPath"
    Write-Info ""
    Write-Info "KodeKronical Integration:"
    Write-Info "  The daemon is now running and collecting system metrics."
    Write-Info "  Your KodeKronical applications will automatically detect and use it."
}

# Main execution
try {
    switch ($Action) {
        "install" {
            Write-Success "Starting kode-kronical-daemon installation for Windows..."
            
            if (-not (Test-PythonInstallation)) {
                Install-Python
            }
            
            Install-Requirements
            Create-Directories
            Install-DaemonFiles
            Install-Configuration
            Create-WindowsService
            Start-DaemonService
            Get-DaemonStatus
            Show-Usage
            
            Write-Success "Installation completed successfully!"
        }
        
        "uninstall" {
            Remove-Installation
        }
        
        "start" {
            Start-DaemonService
        }
        
        "stop" {
            Stop-DaemonService
        }
        
        "status" {
            Get-DaemonStatus
        }
        
        default {
            Write-Error "Invalid action: $Action. Use: install, uninstall, start, stop, or status"
            exit 1
        }
    }
} catch {
    Write-Error "Installation failed: $($_.Exception.Message)"
    Write-Error $_.ScriptStackTrace
    exit 1
}