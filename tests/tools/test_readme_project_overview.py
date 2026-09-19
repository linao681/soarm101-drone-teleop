from pathlib import Path


ROOT = Path(__file__).parents[2]
README = ROOT / "README.md"


def test_readme_describes_current_control_modes_and_hardware():
    text = README.read_text()

    required = [
        "双无线主从遥操作",
        "无线主臂",
        "无线从臂",
        "无人机",
        "空中抓取",
        "firmware/xiao_soarm/",
        "firmware/xiao_soarm_leader/",
        "./start_soarm_demo.sh --leader wireless",
        "./start_soarm_demo.sh --leader wired",
        "./start_soarm_demo.sh --leader wireless --check",
        "NetworkManager 连接名称",
        "SOARM_WIFI_SSID",
        'export SOARM_WIFI_SSID="your-network-name"',
    ]
    for phrase in required:
        assert phrase in text


def test_readme_records_safety_calibration_and_validation_limits():
    text = README.read_text()

    required = [
        "保持最后位置",
        "移除舵机电源",
        "本地校准结构和范围验证",
        "舵机 EEPROM/固件快照检查",
        "重新校准后同步更新校准文件和固件",
        "短时间双无线实机遥操验证",
        "十分钟无线耐久测试尚未执行",
        "wifi_config.h",
        "不能提交",
    ]
    for phrase in required:
        assert phrase in text

    assert "校准文件与具体机械臂绑定" not in text
    assert "145 秒" not in text
    assert "19.7 Hz" not in text
    assert "67 ms" not in text
    assert "-46 dBm" not in text


def test_readme_keeps_firmware_commands_in_isolated_project_directories():
    text = README.read_text()

    assert '(cd firmware/xiao_soarm && \\' in text
    assert '(cd firmware/xiao_soarm_leader && \\' in text
    assert "cd firmware/xiao_soarm\n" not in text
    assert "cd firmware/xiao_soarm_leader\n" not in text


def test_readme_is_project_focused_but_preserves_upstream_attribution():
    text = README.read_text()

    assert "Hugging Face LeRobot" in text
    assert "https://github.com/huggingface/lerobot" in text
    assert "主臂通过 LeRobot 连接 Ubuntu 电脑" not in text
    assert "## LeRobot Dataset" not in text
    assert "## SoTA Models" not in text
    assert "## Inference & Evaluation" not in text
