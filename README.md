# AlphaLabs Signer

<div align="center">

**专业的 Lighter 协议签名服务管理器**

[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)](#支持平台)
[![Version](https://img.shields.io/github/v/release/AlphaAILabs/signer-manager)](https://github.com/AlphaAILabs/signer-manager/releases)

[下载](#下载安装) · [快速开始](#快速开始) · [功能特性](#功能特性) · [策略介绍](#策略介绍)

</div>

---

## 📖 简介

AlphaLabs Signer 是一款专为 Lighter 协议设计的本地签名服务管理器，提供安全、高性能的订单签名能力。通过直观的图形界面，轻松管理多个交易策略的签名服务。

### 核心优势

- 🔐 **安全可靠**: 私钥本地存储，签名操作完全离线
- ⚡ **高性能**: 支持高并发签名请求，签名速度 2,000+ ops/s
- 🎯 **多策略支持**: 集成 EdgeX、Based、Backpack 三大核心策略
- 💻 **跨平台**: 支持 macOS 和 Windows 系统
- 🎨 **现代化界面**: 简洁直观的用户界面，支持深色/浅色主题

---

## 📥 下载安装

### 支持平台

| 操作系统 | 架构 | 下载链接 |
|---------|------|---------|
| **macOS** | Apple Silicon (M1/M2/M3) & Intel | [下载 DMG](https://github.com/AlphaAILabs/signer-manager/releases/latest) |
| **Windows** | x64 | [下载安装包](https://github.com/AlphaAILabs/signer-manager/releases/latest) |

### 安装说明

#### macOS 安装

1. 下载 `AlphaLabsSigner-*-macOS.dmg`
2. 双击 DMG 文件打开
3. 拖动 `AlphaLabs Signer.app` 到 Applications 文件夹
4. 首次运行时，右键点击应用选择"打开"（需要允许未签名应用）

#### Windows 安装

1. 下载 `AlphaLabsSigner-*-Windows-Setup.exe`
2. 双击运行安装程序
3. 按照安装向导完成安装
4. 从开始菜单或桌面快捷方式启动应用

---

## 🚀 快速开始

### 1. 启动服务

1. 打开 AlphaLabs Signer 应用
2. 点击 **"启动服务"** 按钮
3. 等待服务启动完成（首次启动可能需要几秒钟加载依赖）
4. 看到 **"服务运行中"** 绿色指示灯即表示服务已就绪

### 2. 服务端口

默认服务运行在 `http://localhost:10000`

您的交易策略程序可以通过此地址调用签名服务。

### 3. API 使用

签名服务提供标准的 HTTP API 接口，支持以下功能：

- 创建客户端账户
- 订单签名（Create Order）
- 订单取消签名（Cancel Order）
- 批量订单签名
- 账户切换

详细的 API 文档请参考服务启动后的日志输出。

---

## ✨ 功能特性

### 🎯 三大核心策略

#### Lighter-EdgeX [002]
- **磨损率**: 0.023% - 0.025%
- **特点**: 结合两大核心插件优势，提供超低磨损率
- **适用**: 追求稳定高收益的最佳选择
- **支持**: 大部分 token

#### Lighter-Based [003]
- **磨损率**: 0.02% - 0.023%
- **特点**: 基于 Based 协议的策略，平衡收益与风险
- **适用**: 稳健型交易者
- **支持**: 大部分 token

#### Lighter-Backpack [005]
- **磨损率**: 0.014% - 0.035%
- **特点**: 集成 Backpack 生态，灵活的磨损率范围
- **适用**: 适应不同市场环境
- **支持**: 大部分 token

### 🛠️ 管理功能

- ✅ 一键启动/停止服务
- ✅ 实时日志查看
- ✅ 服务状态监控
- ✅ 深色/浅色主题切换
- ✅ 端口配置（默认 10000）

---

## 📄 许可证

本软件为闭源专有软件，版权归 AlphaAI Labs 所有。

**注意事项：**
- ⚠️ 未经授权不得修改、反编译或分发本软件
- ⚠️ 请妥善保管您的私钥，AlphaLabs Signer 不会上传任何私钥信息
- ⚠️ 本软件仅供合法合规使用，使用者需自行承担交易风险

---

## 🤝 技术支持

如遇到问题或需要技术支持，请通过以下方式联系我们：

- 📧 提交 [Issue](https://github.com/AlphaAILabs/signer-manager/issues)
- 💬 加入 [Telegram 社区](https://t.me/+DYoJd7HuN1kyNGE1)
- 🌐 访问 [官方网站](https://alphalabs.app)

---

<div align="center">

**Made with ❤️ by AlphaAI Labs**

© 2024 AlphaAI Labs. All rights reserved.

</div>