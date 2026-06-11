# SO-ARM101 Pro 新电脑部署指南

> Ubuntu 22.04 x86 + NVIDIA GPU ｜ 仓库：[github.com/linao681/soarm-101](https://github.com/linao681/soarm-101)

---

## 1. 系统更新

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget
```

## 2. NVIDIA 驱动

```bash
ubuntu-drivers devices
sudo apt install -y nvidia-driver-550
sudo reboot
```

重启后验证：

```bash
nvidia-smi
```

## 3. Miniforge + Conda 环境

```bash
cd ~
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
chmod +x Miniforge3-Linux-x86_64.sh
./Miniforge3-Linux-x86_64.sh
# 一路回车 + yes

source ~/.bashrc
conda create -y -n lerobot python=3.10
conda activate lerobot
```

## 4. SSH Key（免密 GitHub）

```bash
ssh-keygen -t ed25519 -C "2796645002@qq.com"
cat ~/.ssh/id_ed25519.pub
```

复制公钥 → [github.com/settings/keys](https://github.com/settings/keys) → New SSH Key → 粘贴保存。

```bash
ssh -T git@github.com
# Hi linao681! ✓
```

> 不想配 SSH 就用 HTTPS：`git clone https://github.com/linao681/soarm-101.git`

## 5. 克隆 & 安装

```bash
cd ~
git clone git@github.com:linao681/soarm-101.git lerobot
cd ~/lerobot

conda install -y ffmpeg -c conda-forge
pip install -e ".[feetech]"
```

验证：

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python -c "import lerobot; print('OK')"
```

## 6. 硬件接线

| | 电源 | 电机 |
|---|---|---|
| Leader | **5V** | C001 / C044 / C046 |
| Follower | **12V** | C018 / C047 |

> Follower 必须 12V！

电机 1→2→3→4→5→6 用 3-pin 线级联 → 控制板 → USB-C 电脑 → **最后接电源**。

## 7. 电机校准

```bash
# 先只连 Follower，找端口
lerobot-find-port   # 记录 /dev/ttyACM0

# 再只连 Leader，找端口
lerobot-find-port   # 记录 /dev/ttyACM1

# 权限
sudo chmod 666 /dev/ttyACM0 /dev/ttyACM1
```

校准 Follower：

```bash
python -m lerobot.scripts.lerobot_calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=white \
    --robot.calibration_dir=./cali/
```

校准 Leader：

```bash
python -m lerobot.scripts.lerobot_calibrate \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=blue \
    --teleop.calibration_dir=./cali/
```

## 8. 摄像头

```bash
lerobot-find-cameras
# 记录外景和腕部摄像头 index
```

## 9. 遥操作测试

```bash
lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=white \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=blue \
    --robot.calibration_dir=./cali/ \
    --teleop.calibration_dir=./cali/
```

Leader 动 → Follower 跟 ✅

---

## 流程图

```
系统更新 → 驱动 → 重启 → Miniforge → conda 环境
→ SSH Key → git clone → pip install → 接线
→ 找端口 → 校准 Follower → 校准 Leader → 摄像头 → 遥操作
```

## 常见问题

| 现象 | 解决 |
|---|---|
| `nvidia-smi` 失败 | 驱动没装或没重启 |
| CUDA False | `pip install torch --force-reinstall` |
| 无 `/dev/ttyACM*` | USB 没插或没供电 |
| 权限拒绝 | `sudo chmod 666 /dev/ttyACM*` |
| 舵机不动 | 检查电源，Follower 必须 12V |
| 电机缺失 | 3-pin 线松了，检查级联 |
| 机械臂抖动 | 重新校准 |
