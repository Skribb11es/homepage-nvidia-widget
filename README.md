# homepage-nvidia-smi-widget

A small widget and server to expose NVIDIA GPU status for use with [Homepage](https://gethomepage.dev/).

## Quick install

Run the following command on the machine with NVIDIA GPUs to install the API:

```bash
curl -fsSL https://raw.githubusercontent.com/Skribb11es/homepage-nvidia-widget/main/install.sh | bash
```

If you want to use a custom token for authentication, set the `NVIDIA_SMI_TOKEN` environment variable in the `nvidia-status-server.env` file created in the installation process.

```bash
nano /etc/nvidia-status-server.env
```

## Config

There are three optional environment variables you can set in the `nvidia-status-server.env` file to configure the server:

### `NVIDIA_SMI_TOKEN` - Used to secure the API with a set token. If unspecified, the API does not require authentication to be utilized. Default value is `None` (no authentication).

```bash
NVIDIA_SMI_TOKEN=supersecretpasswordhere
```

### `BIND_ADDRESS` - The IP address the API server binds to. Default value is `0.0.0.0` (all interfaces).

```bash
BIND_ADDRESS=0.0.0.0
```

### `BIND_PORT` - The port the API server listens on. Default value is `8787`.

```bash
BIND_PORT=8787
```

## API Endpoints

### `GET /`

Returns service info and available endpoints.

### `GET /gpus`

List all available GPUs with basic info.

**Response:**
```json
{
  "count": 2,
  "gpus": [
    {
      "index": 0,
      "name": "Tesla P100-PCIE-16GB",
      "temperature": 45.0,
      "power_usage_watts": 32.0,
      "power_cap_watts": 250.0,
      "memory_used_mi": 15987.0,
      "memory_total_mi": 16384.0,
      "gpu_utilization": 0.0,
      "memory_utilization": 0.0
    },
    {
      "index": 1,
      "name": "Tesla P100-PCIE-16GB",
      "temperature": 43.0,
      "power_usage_watts": 32.0,
      "power_cap_watts": 250.0,
      "memory_used_mi": 16219.0,
      "memory_total_mi": 16384.0,
      "gpu_utilization": 0.0,
      "memory_utilization": 0.0
    }
  ]
}
```

### `GET /gpu/<index>`

Get detailed info for a specific GPU by index.

**Example:** `GET /gpu/0`

**Response:**
```json
{
  "index": 0,
  "name": "Tesla P100-PCIE-16GB",
  "temperature": { "value": 45.0, "unit": "C" },
  "power": { "usage_watts": 32.0, "cap_watts": 250.0, "unit": "W" },
  "utilization": { "gpu_percent": 0.0, "memory_percent": 0.0, "unit": "%" },
  "memory": {
    "used_mi": 15987.0,
    "total_mi": 16384.0,
    "used_gb": 15.61,
    "total_gb": 16.0,
    "unit": "MiB"
  }
}
```

## Homepage integration

Using the [Custom API](https://gethomepage.dev/widgets/services/customapi/) support of [Homepage](https://gethomepage.dev/) you can add GPU data to your homepage:

```yaml
- GPU:
    - GPU 0:
        icon: nvidia.png
        href: http://GPU_HOST_IP:8787/gpu/0
        description: Tesla P100-PCIE-16GB
        widget:
          type: customapi
          url: http://GPU_HOST_IP:8787/gpu/0?token=supersecretpasswordhere
          refreshInterval: 10
          method: GET
          mappings:
            - field: temperature.value
              label: Temp
            - field: power.usage_watts
              label: Power
            - field: utilization.gpu_percent
              label: Load
            - field: memory.used_gb
              label: VRAM Used
            - field: memory.total_gb
              label: VRAM Total
```