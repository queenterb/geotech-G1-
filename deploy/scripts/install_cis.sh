#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CIS_SRC="${REPO_ROOT}/cis"
SYSTEMD_SRC="${REPO_ROOT}/deploy/systemd"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root"
  exit 1
fi

echo "Installing CIS dependencies"
apt-get update
apt-get install -y \
  clang llvm libbpf-dev libelf-dev zlib1g-dev \
  bpftool gcc make \
  python3 python3-pip python3-venv

id -u cis > /dev/null 2>&1 || useradd -r -m -s /usr/sbin/nologin cis
mkdir -p /opt/cis /var/log/cis
cp -r "${CIS_SRC}"/* /opt/cis/
chown -R cis:cis /opt/cis /var/log/cis

python3 -m pip install --upgrade pip
python3 -m pip install -r /opt/cis/requirements.txt

install -m 0755 "${REPO_ROOT}/deploy/scripts/cis-health.sh" /usr/local/bin/cis-health
install -m 0755 "${REPO_ROOT}/deploy/scripts/smoke_test.sh" /usr/local/bin/cis-smoke-test

cp "${SYSTEMD_SRC}"/cis-*.service /etc/systemd/system/
cp "${SYSTEMD_SRC}"/cis-health.timer /etc/systemd/system/

systemctl daemon-reload
systemctl enable cis-ebpf-loader.service cis-sidechannel.service cis-digital-twin.service cis-main.service cis-health.timer

echo "CIS files installed. Build/load eBPF loader separately on Linux host before starting services."
