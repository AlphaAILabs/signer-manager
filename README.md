# Lighter Signing Service - GUI Client

一个美观、现代化的 GUI 应用程序，用于管理 Lighter Signing Service。

## ✨ 特性

- 🎨 现代化美观的 UI 设计，支持深色/浅色主题
- 🚀 一键启动/停止服务
- 📊 实时彩色日志显示
- 📦 内置服务代码 - 无需外部依赖
- 🖥️ 跨平台支持（macOS, Windows）
- 🎯 专业交易插件套件风格

## 📥 下载安装

### 用户使用

从 [Releases](../../releases) 页面下载最新版本：

- **macOS**: 下载 `.dmg` 文件
  - 打开 DMG 文件
  - 将应用拖到 Applications 文件夹
  - 首次运行需要右键点击选择"打开"
  
- **Windows**: 下载 `-Setup.exe` 安装程序
  - 运行安装程序
  - 按照向导完成安装
  - 从开始菜单或桌面启动

### 使用方法

1. 启动应用程序
2. 点击 "▶ 启动服务" 按钮
3. 服务将在 `http://localhost:8000` 运行
4. 查看日志了解服务状态
5. 点击 "■ 停止服务" 停止服务

## 🛠️ 开发者指南

### 前置要求

- Python 3.11+
- Git

### 本地开发

1. **克隆仓库**:
```bash
git clone https://github.com/AlphaAILabs/lighter-signing-service-gui.git
cd lighter-signing-service-gui
```

2. **创建虚拟环境**:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **安装依赖**:
```bash
pip install -r requirements.txt
```

4. **运行应用**:
```bash
python main.py
```

### 构建发布版本

本项目使用 **GitHub Actions** 自动构建，详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)。

**快速发布**:
```bash
git tag v1.1.0
git push origin v1.1.0
```

GitHub Actions 会自动构建并发布 DMG 和 Windows 安装程序。

## 📁 项目结构

```
alphalabs-lighter-signer-client/
├── .github/
│   └── workflows/
│       └── build.yml          # GitHub Actions 构建配置
├── main.py                    # 主 GUI 应用
├── service/                   # 内置签名服务
│   ├── main.py               # 服务入口
│   ├── requirements.txt      # 服务依赖
│   └── signers/              # 原生签名库
│       ├── signer-arm64.dylib   # macOS ARM64
│       ├── signer-amd64.so      # Linux x64
│       └── signer-amd64.dll     # Windows x64
├── requirements.txt          # GUI 依赖
├── build.spec               # PyInstaller 配置
├── CHANGELOG.md             # 更新日志
├── TESTING.md               # 测试指南
└── README.md
```

## 🔧 配置说明

- **端口**: 默认 8000（在代码中配置）
- **主题**: 支持 Light/Dark 切换
- **日志**: 自动限制 1000 行
- **服务目录**: 内置在应用中

## 🌐 服务端点

服务运行后可访问：

- 健康检查: `GET http://localhost:8000/health`
- API 文档: `http://localhost:8000/docs`
- 交互式文档: `http://localhost:8000/redoc`

## 🐛 故障排除

### 服务无法启动

1. 检查端口 8000 是否被占用
2. 查看 GUI 日志中的错误信息
3. 确保服务文件完整

### GUI 无法启动

1. 确认 Python 3.11+ 已安装
2. 重新安装依赖: `pip install -r requirements.txt`
3. 尝试直接运行: `python main.py`

### macOS 安全提示

首次运行时：
1. 右键点击应用
2. 选择"打开"
3. 点击"打开"确认

或者：
1. 系统偏好设置 > 安全性与隐私
2. 点击"仍要打开"

## 🚀 发布流程

详见 [BUILD_GUIDE.md](BUILD_GUIDE.md)。

## 📝 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细更新历史。

## 🧪 测试

查看 [TESTING.md](TESTING.md) 了解测试指南。

## 📄 许可证

Copyright © 2025 AlphaAI Labs. All rights reserved.

## 💬 支持

如有问题或建议，请在 GitHub 上提交 Issue。

