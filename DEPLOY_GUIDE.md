# SO-ARM101 Pro 新电脑完整部署指南

> Ubuntu 22.04 x86 + NVIDIA GPU ｜ 仓库：[github.com/linao681/soarm-101](https://github.com/linao681/soarm-101)

---

## 一、系统基础

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential git curl wget
```

---

## 二、NVIDIA 驱动

```bash
ubuntu-drivers devices
sudo apt install -y nvidia-driver-550
sudo reboot
```

重启后验证：

```bash
nvidia-smi
```

---

## 三、Miniforge + Conda 环境

```bash
cd ~
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
chmod +x Miniforge3-Linux-x86_64.sh
./Miniforge3-Linux-x86_64.sh
# 安装过程一路回车 + yes

source ~/.bashrc
conda create -y -n lerobot python=3.10
conda activate lerobot
```

---

## 四、SSH Key（免密连接 GitHub）

```bash
ssh-keygen -t ed25519 -C "2796645002@qq.com"
# 一路回车

cat ~/.ssh/id_ed25519.pub
```

复制输出的公钥 → 打开 [github.com/settings/keys](https://github.com/settings/keys) → **New SSH Key** → 粘贴保存。

验证：

```bash
ssh -T git@github.com
# 显示 "Hi linao681!" 即成功
```

> **跳过 SSH**：如果不想配置 SSH，克隆时用 HTTPS：
> ```bash
> git clone https://github.com/linao681/soarm-101.git lerobot
> ```

---

## 五、克隆项目 & 安装

```bash
cd ~
git clone git@github.com:linao681/soarm-101.git lerobot
cd ~/lerobot

# 安装 ffmpeg
conda install -y ffmpeg -c conda-forge

# 安装 LeRobot + feetech 电机驱动
pip install -e ".[feetech]"
```

验证：

```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
python -c "import lerobot; print('LeRobot OK')"
```

---

## 六、硬件接线

### 电源说明

| 臂 | 电源电压 | 电机型号 |
|---|---|---|
| **Leader** | **5V** | C001 / C044 / C046 |
| **Follower** | **12V** | C018 / C047 |

> ⚠️ **Follower 臂必须使用 12V 电源，接错会烧毁电机！**

### 接线顺序

1. 舵机通过 3-pin 线级联（电机 1 → 电机 2 → ... → 电机 6）
2. 第一个电机连接到控制板
3. 控制板通过 USB-C 连接电脑
4. **最后**接上电源

---

## 七、电机校准

### 7.1 查找 USB 端口

```bash
# 先只连接 Follower 臂的 USB
lerobot-find-port
# 按提示：拔掉 USB → 回车 → 插上 USB → 回车
# 记录端口，如 /dev/ttyACM0

# 再只连接 Leader 臂的 USB
lerobot-find-port
# 记录端口，如 /dev/ttyACM1
```

### 7.2 设置 USB 权限

```bash
sudo chmod 666 /dev/ttyACM0
sudo chmod 666 /dev/ttyACM1
```

> 每次重新插拔 USB 都需要重新执行。或者创建 udev 规则一劳永逸。

### 7.3 校准 Follower 臂

```bash
# 只连接 Follower 臂 USB
python -m lerobot.scripts.lerobot_calibrate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.id=white \
    --robot.calibration_dir=./cali/
```

按提示逐个连接电机，脚本自动分配 ID：

| 关节 | ID | 说明 |
|---|---|---|
| 夹爪 (gripper) | 6 | 末端夹持器 |
| 手腕旋转 (wrist_roll) | 5 | |
| 手腕俯仰 (wrist_pitch) | 4 | |
| 肘部 (elbow) | 3 | |
| 肩部 (shoulder) | 2 | |
| 底座旋转 (base_roll) | 1 | |

### 7.4 校准 Leader 臂

```bash
# 只连接 Leader 臂 USB
python -m lerobot.scripts.lerobot_calibrate \
    --teleop.type=so100_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=blue \
    --teleop.calibration_dir=./cali/
```

---

## 八、摄像头配置

```bash
# 查找可用摄像头
lerobot-find-cameras

# 记录输出中外景摄像头和腕部摄像头的 index
# 通常 外景=0, 腕部=2
```

---

## 九、遥操作测试

同时连接 Leader、Follower 和摄像头后：

```bash
python -m lerobot.scripts.lerobot_teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM0 \
    --robot.cameras="{ out: {type: opencv, index_or_path: 0, width: 640, height: 480, fps: 25}, wrist: {type: opencv, index_or_path: 2, width: 640, height: 480, fps: 25}}" \
    --robot.id=white \
    --teleop.type=so100_leader \
    --teleop.port=/dev/ttyACM1 \
    --teleop.id=blue \
    --display_data=true \
    --robot.calibration_dir=./cali/ \
    --teleop.calibration_dir=./cali/
```

**预期结果**：移动 Leader 臂 → Follower 臂同步跟随。

---

## 十、保存校准文件到 GitHub

做完校准后，把校准文件提交到仓库，以后换电脑无需重新校准：

```bash
git add cali/
git commit -m "Add calibration files"
git push
```

---

## 完整流程图

```
系统更新
  └→ NVIDIA 驱动安装 → 重启
      └→ Miniforge 安装 → 创建 lerobot 环境
          └→ SSH Key 配置 → git clone
              └→ pip install
                  └→ 硬件接线（电源！）
                      └→ 查找 USB 端口
                          └→ 校准 Follower
                              └→ 校准 Leader
                                  └→ 查找摄像头
                                      └→ 遥操作测试 ✅
                                          └→ push 校准文件
```

---

## 常见问题速查

| 现象 | 原因 | 解决 |
|---|---|---|
| `nvidia-smi` 找不到 | 驱动未安装或未重启 | `sudo apt install -y nvidia-driver-550 && sudo reboot` |
| `torch.cuda.is_available()` 返回 False | PyTorch 版本不匹配 | `pip install torch --force-reinstall` |
| 找不到 `/dev/ttyACM*` | USB 没插或没供电 | 检查 USB 连接和电源 |
| `Permission denied` 端口 | 权限不足 | `sudo chmod 666 /dev/ttyACM*` |
| `git clone` 失败 | SSH Key 未配置 | 配置 SSH Key 或改用 HTTPS 地址 |
| 舵机完全不转 | 电源电压不对 | Follower 必须 12V，检查电源 |
| 舵机抖动/异响 | 校准不准确 | 重新执行校准步骤 |
| 遥操作无同步 | 端口或 ID 不对 | 检查 `--robot.port` 和 `--teleop.port` 是否正确 |
| `conda` 命令不存在 | Miniforge 未初始化 | `source ~/.bashrc` 或重新打开终端 |

---

## 关键提醒

1. **Follower 臂必须 12V 供电**，Leader 臂 5V，不可混用
2. Python 版本必须是 **3.10**，3.12 有兼容性问题
3. 安装命令是 `pip install -e ".[feetech]"`，**不要漏掉引号和方括号**
4. 校准完记得 `git push`，换电脑直接 clone 就有校准数据
5. 官方参考文档：[wiki.seeedstudio.com/cn/lerobot_so100m_new](https://wiki.seeedstudio.com/cn/lerobot_so100m_new/)
