# AXON AI Infrastructure — vLLM on EC2 g5.2xlarge
#
# Deploys:
#   - EC2 g5.2xlarge (NVIDIA A10G 24GB VRAM)
#   - vLLM serving Qwen2.5-20B-Instruct-AWQ
#   - Security group (API port 8000, SSH)
#   - EBS gp3 100GB for model weights
#
# Usage:
#   cd infra/terraform
#   terraform init
#   terraform plan -var="key_name=your-key"
#   terraform apply -var="key_name=your-key"

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "terra-os-tfstate"
    key    = "vllm/terraform.tfstate"
    region = "eu-central-1"
  }
}

provider "aws" {
  region = var.aws_region
}

# ─── Variables ─────────────────────────────────────────────────────────────────

variable "aws_region" {
  default = "eu-central-1"
}

variable "instance_type" {
  default     = "g5.2xlarge"
  description = "EC2 instance type — g5.2xlarge = 1x A10G 24GB, 8 vCPU, 32GB RAM"
}

variable "key_name" {
  description = "SSH key pair name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID (use existing terra-os VPC)"
  type        = string
  default     = ""
}

variable "subnet_id" {
  description = "Subnet ID for the instance"
  type        = string
  default     = ""
}

variable "model_id" {
  default     = "Qwen/Qwen2.5-20B-Instruct-AWQ"
  description = "HuggingFace model ID to serve"
}

variable "vllm_port" {
  default = 8000
  type    = number
}

variable "api_key" {
  default     = "token-terra"
  description = "API key for vLLM server auth"
  sensitive   = true
}

variable "allowed_cidr" {
  default     = ["10.0.0.0/16"]
  description = "CIDRs allowed to access vLLM API (internal VPC only)"
  type        = list(string)
}

# ─── Data ──────────────────────────────────────────────────────────────────────

# Deep Learning AMI (Ubuntu 22.04) with NVIDIA drivers pre-installed
data "aws_ami" "deep_learning" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning AMI GPU PyTorch 2.* (Ubuntu 22.04) *"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# ─── Security Group ───────────────────────────────────────────────────────────

resource "aws_security_group" "vllm" {
  name_prefix = "axon-vllm-"
  description = "AXON vLLM inference server"
  vpc_id      = var.vpc_id != "" ? var.vpc_id : null

  # vLLM API — internal only
  ingress {
    from_port   = var.vllm_port
    to_port     = var.vllm_port
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr
    description = "vLLM OpenAI-compatible API"
  }

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidr
    description = "SSH access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = {
    Name    = "axon-vllm-sg"
    Project = "terra-os"
    Service = "ai-inference"
  }
}

# ─── EC2 Instance ─────────────────────────────────────────────────────────────

resource "aws_instance" "vllm" {
  ami                    = data.aws_ami.deep_learning.id
  instance_type          = var.instance_type
  key_name               = var.key_name
  vpc_security_group_ids = [aws_security_group.vllm.id]
  subnet_id              = var.subnet_id != "" ? var.subnet_id : null

  root_block_device {
    volume_size = 100
    volume_type = "gp3"
    iops        = 3000
    throughput  = 250
    encrypted   = true
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tpl", {
    model_id  = var.model_id
    vllm_port = var.vllm_port
    api_key   = var.api_key
  }))

  metadata_options {
    http_tokens                 = "required" # IMDSv2
    http_put_response_hop_limit = 1
  }

  tags = {
    Name    = "axon-vllm-inference"
    Project = "terra-os"
    Service = "ai-inference"
    Model   = var.model_id
  }
}

# ─── Outputs ──────────────────────────────────────────────────────────────────

output "vllm_private_ip" {
  value       = aws_instance.vllm.private_ip
  description = "Private IP of vLLM inference server"
}

output "vllm_instance_id" {
  value = aws_instance.vllm.id
}

output "vllm_endpoint" {
  value       = "http://${aws_instance.vllm.private_ip}:${var.vllm_port}/v1"
  description = "Internal vLLM API endpoint (set as VLLM_BASE_URL)"
}

output "ami_id" {
  value = data.aws_ami.deep_learning.id
}
