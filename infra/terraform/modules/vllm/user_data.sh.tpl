#!/bin/bash
# AXON vLLM Bootstrap — EC2 g5.2xlarge user_data
# Installs vLLM, downloads model, starts serving
set -euo pipefail

exec > /var/log/vllm-bootstrap.log 2>&1
echo "=== AXON vLLM Bootstrap $(date) ==="

# ─── System setup ──────────────────────────────────────────────────────────────
apt-get update -qq
apt-get install -y -qq python3-pip nvidia-cuda-toolkit

# ─── Install vLLM ─────────────────────────────────────────────────────────────
pip3 install --upgrade pip
pip3 install vllm==0.6.* huggingface-hub[cli]

# ─── Download model weights ───────────────────────────────────────────────────
echo "Downloading model: ${model_id}"
huggingface-cli download "${model_id}" --local-dir /opt/models/qwen25-20b-awq

# ─── Create systemd service ───────────────────────────────────────────────────
cat > /etc/systemd/system/vllm.service << 'SYSTEMD'
[Unit]
Description=AXON vLLM Inference Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/models
ExecStart=/usr/local/bin/vllm serve /opt/models/qwen25-20b-awq \
  --host 0.0.0.0 \
  --port ${vllm_port} \
  --api-key ${api_key} \
  --max-model-len 8192 \
  --gpu-memory-utilization 0.90 \
  --quantization awq \
  --dtype half \
  --enforce-eager \
  --served-model-name Qwen/Qwen2.5-20B-Instruct-AWQ
Restart=always
RestartSec=10
Environment=CUDA_VISIBLE_DEVICES=0
Environment=HF_HOME=/opt/models/.cache

[Install]
WantedBy=multi-user.target
SYSTEMD

# ─── Start service ────────────────────────────────────────────────────────────
systemctl daemon-reload
systemctl enable vllm.service
systemctl start vllm.service

echo "=== vLLM Bootstrap COMPLETE $(date) ==="
echo "Model: ${model_id}"
echo "Port: ${vllm_port}"
echo "Endpoint: http://$(hostname -I | awk '{print $1}'):${vllm_port}/v1"
