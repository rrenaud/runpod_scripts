#!/usr/bin/env python3
"""
Shared base class for launching RunPod GPU pods via GraphQL API.

Subclass and override class attributes (gpu_type_id, pod_name_prefix, etc.)
to create GPU-specific launchers.
"""

import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


class PodManager:
    # --- Override these in subclasses ---
    gpu_type_id: str = "NVIDIA A100 80GB PCIe"
    pod_name_prefix: str = "pod"
    network_volume_id: str = ""
    datacenter_id: str = ""
    min_vcpu: int = 8
    min_memory_gb: int = 100
    template_id: str = "runpod-torch-v240"
    container_disk_gb: int = 20
    docker_args: str = "bash -c 'bash /workspace/init/init.sh; exec /start.sh'"
    ssh_user: str = "rrenaud"
    vscode_start_dir: str = "/workspace"

    def __init__(self):
        self.home = Path.home()
        self.api_key_path = self.home / ".runpod_api_key.txt"
        self.ssh_key_path = self.home / ".ssh" / "id_rsa"
        self.ssh_config_path = self.home / ".ssh" / "config"
        self.known_hosts_path = self.home / ".ssh" / "known_hosts"

        # Read API key
        if not self.api_key_path.exists():
            print(f"Error: API key file not found at {self.api_key_path}")
            sys.exit(1)
        self.api_key = self.api_key_path.read_text().strip()

        # Read SSH public key
        ssh_pub_key_path = self.home / ".ssh" / "id_rsa.pub"
        if ssh_pub_key_path.exists():
            self.ssh_public_key = ssh_pub_key_path.read_text().strip()
        else:
            print(f"Warning: SSH public key not found at {ssh_pub_key_path}")
            self.ssh_public_key = ""

        # Generate pod name with timestamp
        self.gpu_count = 1
        self.pod_name = f"{self.pod_name_prefix}-{time.strftime('%Y%m%d-%H%M%S')}"
        self.volume_gb = 0  # No separate volume when using network volume
        self.ports = "22/tcp,8888/http"
        self.volume_mount_path = "/workspace"

    def graphql_request(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GraphQL request to RunPod API."""
        response = requests.post(
            "https://api.runpod.io/graphql",
            headers={"Content-Type": "application/json"},
            params={"api_key": self.api_key},
            json={"query": query, "variables": variables or {}},
        )

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        if "errors" in data:
            raise Exception(f"GraphQL errors: {data['errors']}")

        return data

    def create_pod(self) -> str:
        """Create the RunPod pod using GraphQL API and return its ID."""
        print(f"\nCreating {self.gpu_type_id} pod...")
        print(f"  GPU Type: {self.gpu_type_id}")
        print(f"  GPU Count: {self.gpu_count}")
        print(f"  Datacenter: {self.datacenter_id}")
        print(f"  Template: {self.template_id}")
        print(f"  Pod Name: {self.pod_name}")
        print(f"  Container Disk: {self.container_disk_gb} GB")
        print(f"  Network Volume: {self.network_volume_id}")
        print(f"  Public IP: Enabled")
        print(f"  Ports: {self.ports}")
        print(f"  SSH User: {self.ssh_user}")
        if self.ssh_public_key:
            key_preview = self.ssh_public_key[:50] + "..."
            print(f"  SSH Public Key: {key_preview}")

        mutation = """
        mutation PodFindAndDeployOnDemand($input: PodFindAndDeployOnDemandInput!) {
          podFindAndDeployOnDemand(input: $input) {
            id
            imageName
            machineId
            costPerHr
            machine {
              podHostId
            }
          }
        }
        """

        env_vars = []
        if self.ssh_public_key:
            env_vars.append({"key": "PUBLIC_KEY", "value": self.ssh_public_key})

        input_data = {
            "cloudType": "SECURE",
            "gpuCount": self.gpu_count,
            "volumeInGb": self.volume_gb,
            "containerDiskInGb": self.container_disk_gb,
            "minVcpuCount": self.min_vcpu,
            "minMemoryInGb": self.min_memory_gb,
            "gpuTypeId": self.gpu_type_id,
            "name": self.pod_name,
            "dataCenterId": self.datacenter_id,
            "templateId": self.template_id,
            "ports": self.ports,
            "volumeMountPath": self.volume_mount_path,
            "networkVolumeId": self.network_volume_id,
            "supportPublicIp": True,
            "env": env_vars,
        }

        if self.docker_args:
            input_data["dockerArgs"] = self.docker_args

        try:
            result = self.graphql_request(mutation, {"input": input_data})

            if "data" not in result or "podFindAndDeployOnDemand" not in result["data"]:
                raise Exception(f"Unexpected response: {result}")

            pod_data = result["data"]["podFindAndDeployOnDemand"]
            pod_id = pod_data["id"]
            cost_per_hr = pod_data.get("costPerHr")

            print(f"\n  Pod created successfully!")
            print(f"  Pod ID: {pod_id}")
            if cost_per_hr is None:
                raise ValueError("Hourly cost not found in API response")
            print(f"  Hourly Cost: ${cost_per_hr:.3f}/hr")

            return pod_id

        except Exception as e:
            print(f"\n  Failed to create pod: {e}")
            sys.exit(1)

    def get_pod_info(self, pod_id: str) -> Dict[str, Any]:
        """Get pod information using GraphQL API."""
        query = """
        query Pod($input: PodFilter!) {
          pod(input: $input) {
            id
            name
            desiredStatus
            runtime {
              uptimeInSeconds
              ports {
                ip
                isIpPublic
                privatePort
                publicPort
                type
              }
              gpus {
                id
                gpuUtilPercent
                memoryUtilPercent
              }
            }
          }
        }
        """

        result = self.graphql_request(query, {"input": {"podId": pod_id}})

        if "data" in result and "pod" in result["data"]:
            return result["data"]["pod"]
        else:
            raise Exception(f"Failed to get pod info: {result}")

    def wait_for_pod_running(self, pod_id: str, max_attempts: int = 60):
        """Wait for the pod to be in RUNNING state."""
        print("\nWaiting for pod to start...")

        for attempt in range(1, max_attempts + 1):
            try:
                pod_info = self.get_pod_info(pod_id)
                if pod_info.get("runtime"):
                    print("  Pod is now running!")
                    return
                print(f"  Attempt {attempt}/{max_attempts} - Pod not ready yet...")
                time.sleep(5)
            except Exception as e:
                print(f"  Attempt {attempt}/{max_attempts} - Error: {e}")
                time.sleep(5)

        print("  Error: Pod did not start within timeout period")
        sys.exit(1)

    def get_ssh_details(self, pod_id: str) -> Tuple[str, str]:
        """Get SSH host and port from pod information via GraphQL API."""
        print("\nGetting SSH connection details...")

        max_attempts = 40
        for attempt in range(1, max_attempts + 1):
            try:
                pod_info = self.get_pod_info(pod_id)

                if not pod_info.get("runtime") or not pod_info["runtime"].get("ports"):
                    print(f"  Attempt {attempt}/{max_attempts} - Waiting for SSH port to be exposed...")
                    time.sleep(5)
                    continue

                ports = pod_info["runtime"]["ports"]
                for port in ports:
                    if port.get("privatePort") == 22:
                        ssh_host = port.get("ip")
                        ssh_port = str(port.get("publicPort", 22))
                        if ssh_host and ssh_port:
                            print(f"  SSH connection details obtained")
                            print(f"  Host: {ssh_host}")
                            print(f"  Port: {ssh_port}")
                            print(f"  Public IP: {port.get('isIpPublic', False)}")
                            return ssh_host, ssh_port

                print(f"  Attempt {attempt}/{max_attempts} - SSH port not found yet...")
                time.sleep(5)

            except Exception as e:
                print(f"  Attempt {attempt}/{max_attempts} - Error: {e}")
                time.sleep(5)

        print("  Error: Could not get SSH connection details within timeout period")
        sys.exit(1)

    def add_to_known_hosts(self, ssh_host: str, ssh_port: str):
        """Add the pod to SSH known_hosts."""
        print("\nAdding pod to SSH known_hosts...")
        self.known_hosts_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            result = subprocess.run(
                ["ssh-keyscan", "-p", ssh_port, "-H", ssh_host],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0 and result.stdout:
                with open(self.known_hosts_path, "a") as f:
                    f.write(result.stdout)
                print("  Added to known_hosts successfully!")
            else:
                print("  ssh-keyscan may have failed, but continuing...")
        except Exception as e:
            print(f"  Could not add to known_hosts ({e}), but continuing...")

    def update_ssh_config(self, pod_id: str, ssh_host: str, ssh_port: str) -> str:
        """Add SSH config entry for the pod."""
        ssh_host_alias = f"runpod-{pod_id}"
        print(f"\nAdding SSH config entry as '{ssh_host_alias}'...")

        self.ssh_config_path.parent.mkdir(parents=True, exist_ok=True)

        config_entry = f"""
# RunPod Pod: {self.pod_name}
Host {ssh_host_alias}
    HostName {ssh_host}
    Port {ssh_port}
    User {self.ssh_user}
    IdentityFile {self.ssh_key_path}
    StrictHostKeyChecking no
"""

        with open(self.ssh_config_path, "a") as f:
            f.write(config_entry)

        print("  SSH config updated!")
        return ssh_host_alias

    def test_ssh_connection(self, ssh_host: str, ssh_port: str, max_attempts: int = 30) -> bool:
        """Poll SSH connection until it succeeds or we give up."""
        print("\nWaiting for SSH service to be ready...")

        cmd = [
            "ssh",
            "-o", "ConnectTimeout=5",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            "-i", str(self.ssh_key_path),
            "-p", ssh_port,
            f"{self.ssh_user}@{ssh_host}",
            "echo 'SSH connection successful!'",
        ]

        for attempt in range(1, max_attempts + 1):
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"  SSH ready after {attempt} attempt(s)!")
                    return True
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                pass
            print(f"  Attempt {attempt}/{max_attempts} - not ready yet...")
            time.sleep(5)

        print("  SSH did not become ready within timeout, continuing anyway...")
        return False

    def launch_vscode(self, ssh_host_alias: str):
        """Launch VSCode connected to the pod."""
        print("\nLaunching VSCode...")

        try:
            subprocess.Popen(
                ["code", "--remote", f"ssh-remote+{ssh_host_alias}", self.vscode_start_dir],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            print("  VSCode launched!")
        except Exception as e:
            print(f"  Failed to launch VSCode: {e}")
            print("  You can manually connect using the SSH details below")

    def print_summary(self, pod_id: str, ssh_host_alias: str, ssh_host: str, ssh_port: str):
        """Print connection summary."""
        print("\n" + "=" * 60)
        print("Pod is ready!")
        print("=" * 60)
        print(f"Pod ID: {pod_id}")
        print(f"Pod Name: {self.pod_name}")
        print(f"SSH Alias: {ssh_host_alias}")
        print()
        print("Manual SSH connection:")
        print(f"  ssh {ssh_host_alias}")
        print("  OR")
        print(f"  ssh {self.ssh_user}@{ssh_host} -p {ssh_port} -i {self.ssh_key_path}")
        print()
        print("To stop the pod:")
        print(f"  Visit https://runpod.io/console/pods")
        print("=" * 60)

    def run(self):
        """Main execution flow."""
        try:
            print("=" * 60)
            print(f"RunPod {self.gpu_type_id} Pod Launcher")
            print("=" * 60)

            pod_id = self.create_pod()
            self.wait_for_pod_running(pod_id)
            ssh_host, ssh_port = self.get_ssh_details(pod_id)
            self.add_to_known_hosts(ssh_host, ssh_port)
            ssh_host_alias = self.update_ssh_config(pod_id, ssh_host, ssh_port)
            self.test_ssh_connection(ssh_host, ssh_port)
            self.launch_vscode(ssh_host_alias)
            self.print_summary(pod_id, ssh_host_alias, ssh_host, ssh_port)

        except KeyboardInterrupt:
            print("\n\n  Operation cancelled by user")
            sys.exit(1)
        except Exception as e:
            print(f"\n\n  Error: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
