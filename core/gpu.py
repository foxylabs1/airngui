"""
GPU detection and PRIME offload support.
Detects NVIDIA/AMD GPUs, checks driver status, provides
environment variables for PRIME offload on hybrid GPU systems.
"""

import subprocess
import re
import os


class GPUInfo:
    """Represents a detected GPU."""
    def __init__(self, index, name, driver, vram_mb=0, gpu_type="unknown"):
        self.index = index
        self.name = name
        self.driver = driver
        self.vram_mb = vram_mb
        self.gpu_type = gpu_type  # "nvidia", "amd", "intel"

    def __str__(self):
        vram = f" ({self.vram_mb} MB)" if self.vram_mb else ""
        return f"[{self.index}] {self.name}{vram} ({self.driver})"


def detect_gpus():
    """
    Detect all GPUs on the system.
    Returns list of GPUInfo objects.
    """
    gpus = []

    # Try nvidia-smi first (most reliable for NVIDIA)
    nvidia_gpus = _detect_nvidia_smi()
    if nvidia_gpus:
        gpus.extend(nvidia_gpus)

    # Fallback / supplement with lspci
    lspci_gpus = _detect_lspci()
    for lg in lspci_gpus:
        # Don't duplicate NVIDIA GPUs already found via nvidia-smi
        if lg.gpu_type == "nvidia" and any(g.gpu_type == "nvidia" for g in gpus):
            continue
        gpus.append(lg)

    return gpus


def _detect_nvidia_smi():
    """Detect NVIDIA GPUs via nvidia-smi."""
    gpus = []
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total,driver_version",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return gpus

        for line in result.stdout.strip().splitlines():
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                gpus.append(GPUInfo(
                    index=int(parts[0]),
                    name=parts[1],
                    driver=f"nvidia {parts[3]}",
                    vram_mb=int(float(parts[2])),
                    gpu_type="nvidia",
                ))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return gpus


def _detect_lspci():
    """Detect GPUs via lspci (catches Intel/AMD iGPUs too)."""
    gpus = []
    try:
        result = subprocess.run(
            ["lspci", "-nn"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return gpus

        idx = 0
        for line in result.stdout.splitlines():
            # VGA compatible controller or 3D controller
            if "VGA compatible" in line or "3D controller" in line:
                name = line.split(":", 2)[-1].strip() if ":" in line else line

                if "NVIDIA" in line.upper():
                    gpu_type = "nvidia"
                    driver = "nvidia"
                elif "AMD" in line.upper() or "ATI" in line.upper():
                    gpu_type = "amd"
                    driver = "amdgpu"
                elif "INTEL" in line.upper():
                    gpu_type = "intel"
                    driver = "i915"
                else:
                    gpu_type = "unknown"
                    driver = "unknown"

                gpus.append(GPUInfo(
                    index=idx,
                    name=name,
                    driver=driver,
                    gpu_type=gpu_type,
                ))
                idx += 1
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return gpus


def has_discrete_gpu():
    """Check if system has a discrete NVIDIA or AMD GPU."""
    gpus = detect_gpus()
    return any(g.gpu_type in ("nvidia", "amd") for g in gpus)


def get_prime_env():
    """
    Return environment variables dict for NVIDIA PRIME offload.
    This makes a process run on the dGPU instead of iGPU.
    """
    return {
        "__NV_PRIME_RENDER_OFFLOAD": "1",
        "__VK_LAYER_NV_optimus": "NVIDIA_only",
        "__GLX_VENDOR_LIBRARY_NAME": "nvidia",
    }


def has_prime_offload():
    """Check if NVIDIA PRIME offload is available."""
    try:
        result = subprocess.run(
            ["prime-run", "true"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check if the env var approach works
    env = os.environ.copy()
    env.update(get_prime_env())
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, env=env, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_hashcat():
    """Check if hashcat is installed and return version info."""
    try:
        result = subprocess.run(
            ["hashcat", "--version"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def check_hcxtools():
    """Check if hcxpcapngtool is available (converts .cap to .hc22000)."""
    try:
        result = subprocess.run(
            ["which", "hcxpcapngtool"],
            capture_output=True, timeout=5,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def build_gpu_launch_env():
    """
    Build the full environment dict for launching GPU-accelerated tools.
    Merges current env with PRIME offload vars if on a hybrid system.
    """
    env = os.environ.copy()
    gpus = detect_gpus()

    has_igpu = any(g.gpu_type == "intel" for g in gpus)
    has_dgpu = any(g.gpu_type == "nvidia" for g in gpus)

    # Only apply PRIME offload on hybrid systems (iGPU + dGPU)
    if has_igpu and has_dgpu:
        env.update(get_prime_env())

    return env
