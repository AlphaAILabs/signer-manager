# 构建指南

本项目使用 GitHub Actions 自动构建，无需本地构建。

## 🚀 自动构建流程

### 1. 创建新版本

```bash
# 更新版本号
# 编辑 build.spec 中的 CFBundleVersion
# 编辑 CHANGELOG.md 添加更新日志

# 提交更改
git add .
git commit -m "Release v1.1.0"
git push

# 创建标签触发构建
git tag v1.1.0
git push origin v1.1.0
```

### 2. GitHub Actions 自动执行

推送标签后，GitHub Actions 会自动：

1. **构建 macOS 版本**
   - 在 macOS 虚拟机上运行
   - 使用 PyInstaller 打包应用
   - 创建 DMG 安装包
   - 上传到 Artifacts

2. **构建 Windows 版本**
   - 在 Windows 虚拟机上运行
   - 使用 PyInstaller 打包应用
   - 使用 Inno Setup 创建安装程序
   - 上传到 Artifacts

3. **创建 GitHub Release**
   - 自动创建新的 Release
   - 上传 DMG 和安装程序
   - 生成 Release Notes

### 3. 下载构建产物

- 访问 [Actions](../../actions) 页面查看构建进度
- 访问 [Releases](../../releases) 页面下载安装包

## 🔧 手动触发构建

如果不想创建标签，可以手动触发构建：

1. 进入 GitHub 仓库的 **Actions** 标签
2. 选择 **Build and Release** 工作流
3. 点击 **Run workflow** 按钮
4. 选择分支（通常是 main）
5. 点击 **Run workflow** 确认

构建完成后，可以在 Actions 页面下载 Artifacts。

## 📦 构建产物

### macOS
- **文件名**: `LighterSigningService-{version}-macOS.dmg`
- **大小**: 约 50-80 MB
- **支持**: macOS 10.13+
- **架构**: Universal (Intel + Apple Silicon)

### Windows
- **文件名**: `LighterSigningService-{version}-Windows-Setup.exe`
- **大小**: 约 40-60 MB
- **支持**: Windows 10/11
- **架构**: x64

## 🛠️ 本地开发测试

如果需要本地测试（不构建发布版）：

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py
```

## 📋 构建配置文件

- `.github/workflows/build.yml` - GitHub Actions 工作流配置
- `build.spec` - PyInstaller 打包配置
- `requirements.txt` - Python 依赖列表

## ⚙️ 构建要求

GitHub Actions 会自动处理所有依赖：

- Python 3.11
- PyInstaller
- CustomTkinter
- FastAPI + Uvicorn
- eth-account
- 所有 service 依赖

## 🐛 故障排除

### 构建失败

1. 检查 Actions 日志查看错误信息
2. 确保 `service/` 目录包含所有必要文件
3. 确保 `requirements.txt` 包含所有依赖
4. 确保 `build.spec` 配置正确

### 服务文件缺失

确保以下文件存在：
- `service/main.py`
- `service/requirements.txt`
- `service/signers/signer-arm64.dylib`
- `service/signers/signer-amd64.so`
- `service/signers/signer-amd64.dll`

### 依赖问题

如果构建时出现依赖错误：
1. 更新 `requirements.txt`
2. 更新 `build.spec` 中的 `hiddenimports`
3. 重新触发构建

## 📝 版本号管理

版本号需要在以下位置更新：

1. Git 标签: `v1.1.0`
2. `build.spec`: `CFBundleVersion` 和 `CFBundleShortVersionString`
3. `CHANGELOG.md`: 添加新版本的更新日志

## 🎯 发布检查清单

发布新版本前检查：

- [ ] 更新 `CHANGELOG.md`
- [ ] 更新 `build.spec` 中的版本号
- [ ] 测试本地运行正常
- [ ] 提交所有更改
- [ ] 创建并推送标签
- [ ] 等待 GitHub Actions 构建完成
- [ ] 测试下载的安装包
- [ ] 确认 Release 页面信息正确

---

**维护者**: AlphaAI Labs
**最后更新**: 2025-10-01

