# 发布前检查清单

## 📋 代码检查

- [x] main.py - GUI 主程序
- [x] service/ - 服务代码完整
- [x] service/main.py - 服务入口存在
- [x] service/signers/ - 签名库文件完整
  - [x] signer-arm64.dylib (macOS ARM64)
  - [x] signer-amd64.so (Linux x64)
  - [x] signer-amd64.dll (Windows x64)
- [x] requirements.txt - GUI 依赖
- [x] service/requirements.txt - 服务依赖
- [x] build.spec - PyInstaller 配置

## 🔧 配置检查

- [x] .github/workflows/build.yml - GitHub Actions 工作流
- [x] .gitignore - 排除构建产物
- [x] LICENSE - 许可证文件

## 📝 文档检查

- [x] README.md - 项目说明
- [x] BUILD_GUIDE.md - 构建指南
- [x] CHANGELOG.md - 更新日志
- [x] TESTING.md - 测试指南
- [x] SUMMARY.md - 项目总结

## ✨ 功能检查

- [x] GUI 启动正常
- [x] 服务启动功能
- [x] 服务停止功能
- [x] 重复启动/停止无错误
- [x] 主题切换功能
- [x] 日志清除功能
- [x] 彩色日志显示
- [x] Ubuntu Mono 字体显示数字
- [x] 窗口关闭正常

## 🎨 UI 检查

- [x] 标题: "专业交易 插件套件"
- [x] 紫色主题色: #818CF8
- [x] 服务卡片: "Lighter - EdgeX[002]"
- [x] 状态徽章动态显示
- [x] 按钮中文化
- [x] 卡片圆角 15px
- [x] 按钮圆角 10px
- [x] Light/Dark 主题切换

## 🔨 构建检查

- [x] build.spec 包含所有 service 文件
- [x] build.spec 包含所有隐藏导入
- [x] GitHub Actions 工作流配置正确
- [x] macOS 构建任务配置
- [x] Windows 构建任务配置
- [x] DMG 创建脚本
- [x] Inno Setup 配置

## 🚀 发布流程

### 准备发布

1. [ ] 更新版本号
   - [ ] build.spec 中的 CFBundleVersion
   - [ ] build.spec 中的 CFBundleShortVersionString
   - [ ] CHANGELOG.md 添加新版本

2. [ ] 本地测试
   - [ ] 运行 `python main.py`
   - [ ] 测试启动服务
   - [ ] 测试停止服务
   - [ ] 测试主题切换
   - [ ] 测试日志清除

3. [ ] 提交代码
   ```bash
   git add .
   git commit -m "Release v1.1.0"
   git push
   ```

4. [ ] 创建标签
   ```bash
   git tag v1.1.0
   git push origin v1.1.0
   ```

### 构建验证

5. [ ] 检查 GitHub Actions
   - [ ] 访问 Actions 页面
   - [ ] 确认构建开始
   - [ ] 等待构建完成

6. [ ] 验证构建产物
   - [ ] macOS DMG 创建成功
   - [ ] Windows Setup.exe 创建成功
   - [ ] 文件大小合理（50-80 MB）

7. [ ] 测试安装包
   - [ ] 下载 macOS DMG
   - [ ] 测试安装和运行
   - [ ] 下载 Windows Setup.exe
   - [ ] 测试安装和运行（如有 Windows 环境）

### 发布确认

8. [ ] 检查 Release
   - [ ] Release 自动创建
   - [ ] DMG 文件已上传
   - [ ] Setup.exe 文件已上传
   - [ ] Release Notes 正确

9. [ ] 更新文档
   - [ ] README.md 链接正确
   - [ ] 版本号一致

10. [ ] 通知用户
    - [ ] 发布公告
    - [ ] 更新说明

## ⚠️ 常见问题

### 构建失败

- 检查 Actions 日志
- 确认 service/ 目录完整
- 确认 requirements.txt 正确
- 确认 build.spec 配置正确

### 服务无法启动

- 检查端口 8000 是否被占用
- 查看日志错误信息
- 确认服务文件完整

### DMG 无法打开

- 右键点击选择"打开"
- 系统偏好设置 > 安全性与隐私

### Windows 安装失败

- 以管理员身份运行
- 关闭杀毒软件
- 检查磁盘空间

## 📊 质量标准

- [ ] 代码无明显 bug
- [ ] UI 美观流畅
- [ ] 功能完整可用
- [ ] 文档清晰完善
- [ ] 构建成功无错误
- [ ] 安装包可正常使用

## ✅ 最终确认

- [ ] 所有功能测试通过
- [ ] 所有文档更新完成
- [ ] GitHub Actions 构建成功
- [ ] Release 创建成功
- [ ] 安装包测试通过
- [ ] 准备好发布

---

**检查人**: _____________
**日期**: _____________
**版本**: v1.1.0

