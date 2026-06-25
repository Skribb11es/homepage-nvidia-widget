import subprocess
import os
import re
from flask import Flask, jsonify, request, abort

app = Flask(__name__)

API_TOKEN = os.environ.get("NVIDIA_SMI_TOKEN", "").strip()

def run_cmd(cmd):
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    except Exception as e:
        return ""


def _parse_gpu_block(block: str):
    lines = [l for l in block.splitlines() if l.strip()]
    if not lines:
        return None

    # Extract GPU index
    idx_match = re.match(r'^\s*(\d+)', lines[0] or "")
    if not idx_match:
        return None
    gpu_index = int(idx_match.group(1))

    # Extract GPU name from the GPU info line
    # Pattern: "  0  Tesla P100-PCIE-16GB           Off | ..."
    name_match = re.search(r'\|\s*\d+\s+(?:MIG\s+)?(?P<name>.+?)\s+Off\s*\|', lines[0] or "")
    if not name_match:
        return None
    gpu_name = name_match.group("name").strip()

    # Parse the metrics line:
    # " N/A   45C    P0             32W /  250W |   15987MiB /  16384MiB |      0%      Default |"
    m = re.search(
        r'(N/A|\d+\.?\d*)\s+'           # Fan (N/A or numeric)
        r'(N/A|(\d+\.?\d*)C)\s+'         # Temp
        r'(\w+)\s+'                       # Perf state
        r'(\d+\.?\d*)\s*W\s*/\s*(\d+\.?\d*)\s*W\s*'  # Power:Usage/Cap
        r'\|\s*'
        r'(\d+\.?\d*)\s*MiB\s*/\s*(\d+\.?\d*)\s*MiB\s*'  # Memory-Usage
        r'\|\s*'
        r'(\d+\.?\d*)\s*%',              # GPU-Util
        lines[0] or ""
    )
    if m:
        temp = float(m.group(3)) if m.group(2) != 'N/A' else None
        return {
            "index": gpu_index,
            "name": gpu_name,
            "temperature": temp,
            "power_usage_watts": float(m.group(5)),
            "power_cap_watts": float(m.group(6)),
            "memory_used_mi": float(m.group(7)),
            "memory_total_mi": float(m.group(8)),
            "gpu_utilization": float(m.group(10)),
        }

    return None


def parse_gpu_info(raw: str):
    gpus = []
    # Split on the separator lines like "+-------------------------+------------------------+----------------------+"
    blocks = re.split(r'^\+-[\+\-]+-+$', raw, flags=re.MULTILINE)

    for block in blocks:
        gpu = _parse_gpu_block(block.strip())
        if gpu:
            gpus.append(gpu)

    return gpus


def get_gpus():
    # First try the CSV format query for reliable parsing
    raw = run_cmd(["nvidia-smi",
        "--query-gpu=name,temperature.gpu,power.draw,power.limit,"
        "memory.used,memory.total,utilization.gpu,utilization.memory",
        "--format=csv,noheader,nounits"])

    if raw:
        gpus = []
        for line in raw.splitlines():
            line = line.strip()
            if not line or 'No running processes found' in line:
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 8:
                continue
            try:
                gpus.append({
                    "index": len(gpus),
                    "name": parts[0] if parts[0] != 'N/A' else None,
                    "temperature": float(parts[1]) if parts[1] != 'N/A' else None,
                    "power_usage_watts": float(parts[2]) if parts[2] != 'N/A' else None,
                    "power_cap_watts": float(parts[3]) if parts[3] != 'N/A' else None,
                    "memory_used_mi": float(parts[4]) if parts[4] != 'N/A' else None,
                    "memory_total_mi": float(parts[5]) if parts[5] != 'N/A' else None,
                    "gpu_utilization": float(parts[6]) if parts[6] != 'N/A' else None,
                    "memory_utilization": float(parts[7]) if parts[7] != 'N/A' else None,
                })
            except (ValueError, IndexError):
                continue
        if gpus:
            return gpus

    # Fallback: parse full nvidia-smi text table
    raw_full = run_cmd(["nvidia-smi"])
    return parse_gpu_info(raw_full) if raw_full else []


def check_auth():
    if not API_TOKEN:
        return True

    header = request.headers.get("Authorization", "")
    token_qs = request.args.get("token", "")

    if header.startswith("Bearer "):
        tok = header.replace("Bearer ", "", 1).strip()
        return tok == API_TOKEN

    return token_qs.strip() == API_TOKEN


@app.route("/gpus", methods=["GET"])
def list_gpus():
    if not check_auth():
        abort(401)

    gpus = get_gpus()
    return jsonify({
        "gpus": gpus,
        "count": len(gpus),
    })


@app.route("/gpu/<int:index>", methods=["GET"])
def get_gpu(index):
    if not check_auth():
        abort(401)

    gpus = get_gpus()

    if not gpus:
        abort(500, description="Failed to retrieve GPU information. Is nvidia-smi available?")

    if index < 0 or index >= len(gpus):
        abort(404, description=f"GPU with index {index} not found. Available GPUs: {list(range(len(gpus)))}")

    gpu = gpus[index]
    return jsonify({
        "index": gpu["index"],
        "name": gpu["name"],
        "temperature": {
            "value": gpu.get("temperature"),
            "unit": "C",
        },
        "power": {
            "usage_watts": gpu.get("power_usage_watts"),
            "cap_watts": gpu.get("power_cap_watts"),
            "unit": "W",
        },
        "utilization": {
            "gpu_percent": gpu.get("gpu_utilization"),
            "memory_percent": gpu.get("memory_utilization"),
            "unit": "%",
        },
        "memory": {
            "used_mi": gpu.get("memory_used_mi"),
            "total_mi": gpu.get("memory_total_mi"),
            "used_gb": round(gpu.get("memory_used_mi", 0) / 1024, 2) if gpu.get("memory_used_mi") is not None else None,
            "total_gb": round(gpu.get("memory_total_mi", 0) / 1024, 2) if gpu.get("memory_total_mi") is not None else None,
            "unit": "MiB",
        },
    })


@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "service": "nvidia-smi-status-server",
        "endpoints": [
            "/gpus - List all GPUs",
            "/gpu/<index> - Get detailed info for a specific GPU",
            "/gpu/0 - Example: GPU index 0",
        ],
    })


if __name__ == "__main__":
    bind_ip = os.environ.get("BIND_ADDRESS", "0.0.0.0")
    port = int(os.environ.get("BIND_PORT", "8787"))
    app.run(host=bind_ip, port=port)
