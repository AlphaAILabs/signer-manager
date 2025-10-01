# 测试指南

## 功能测试清单

### 1. 启动测试 ✅

**步骤:**
1. 运行 `./run.sh` 或 `python main.py`
2. 检查 GUI 是否正常显示
3. 检查日志显示 "Service found and ready"

**预期结果:**
- GUI 正常打开
- 显示深色主题
- 日志区域显示初始化信息

---

### 2. 服务启动测试 ✅

**步骤:**
1. 点击 "▶ 启动服务" 按钮
2. 观察日志输出
3. 检查状态指示器变化

**预期结果:**
- 按钮变为禁用状态
- 状态指示器变为绿色 ●
- 状态文本显示 "服务运行中"
- 状态徽章显示 "运行中"（绿色）
- 日志显示服务启动信息
- 服务日志以紫色显示

**验证服务运行:**
```bash
curl http://localhost:8000/health
# 应返回: {"status":"healthy"}
```

---

### 3. 服务停止测试 ✅

**步骤:**
1. 在服务运行时，点击 "■ 停止服务" 按钮
2. 观察日志输出
3. 检查状态指示器变化

**预期结果:**
- 按钮变为禁用状态
- 状态指示器变为红色 ●
- 状态文本恢复为 "超低磨损率 0.018%"
- 状态徽章显示 "已上线"（紫色）
- 日志显示 "Service stopped successfully"（绿色）
- **不应出现任何错误**

---

### 4. 重复启动/停止测试 ✅

**步骤:**
1. 启动服务
2. 停止服务
3. 再次启动服务
4. 再次停止服务
5. 重复 3-5 次

**预期结果:**
- 每次启动/停止都正常工作
- 没有 `'NoneType' object has no attribute 'poll'` 错误
- 日志正常显示
- UI 状态正确更新

---

### 5. 主题切换测试 ✅

**步骤:**
1. 点击右上角 "☀️ Light" 按钮
2. 观察界面变化
3. 再次点击按钮（现在显示 "🌙 Dark"）
4. 观察界面恢复深色主题

**预期结果:**
- 浅色主题：
  - 背景变为浅色
  - 文字变为深色
  - 按钮文字显示 "🌙 Dark"
  - 日志显示 "Switched to light theme"
- 深色主题：
  - 背景变为深色
  - 文字变为浅色
  - 按钮文字显示 "☀️ Light"
  - 日志显示 "Switched to dark theme"

---

### 6. 日志清除测试 ✅

**步骤:**
1. 启动并停止服务几次，生成一些日志
2. 点击 "清除日志" 按钮
3. 观察日志区域

**预期结果:**
- 所有日志被清除
- 显示 "Log cleared" 消息

---

### 7. 日志颜色测试 ✅

**步骤:**
1. 执行各种操作生成不同类型的日志
2. 检查日志颜色

**预期结果:**
- INFO 日志：灰色
- SUCCESS 日志：绿色 (#52C41A)
- WARNING 日志：橙色 (#FAAD14)
- ERROR 日志：红色 (#FF4D4F)
- SERVICE 日志：紫色 (#818CF8)

---

### 8. 窗口关闭测试 ✅

**步骤:**
1. 启动服务
2. 关闭 GUI 窗口
3. 检查服务是否停止

**预期结果:**
- 日志显示 "Stopping service before exit..."
- 服务正常停止
- 窗口关闭
- 进程完全退出

---

### 9. UI 元素测试 ✅

**检查项:**
- [x] 标题显示 "专业交易 插件套件"
- [x] "插件套件" 为紫色 (#818CF8)
- [x] 副标题显示正确
- [x] 服务卡片标题 "Lighter - EdgeX[002]"
- [x] 状态徽章圆角正确
- [x] 按钮圆角为 10px
- [x] 卡片圆角为 15px
- [x] 主题切换按钮有边框

---

### 10. 长时间运行测试 ✅

**步骤:**
1. 启动服务
2. 让服务运行 5-10 分钟
3. 观察日志和性能

**预期结果:**
- 服务持续运行
- 日志正常输出
- 内存使用稳定
- 日志自动限制在 1000 行

---

### 11. 错误处理测试 ✅

**测试场景:**

#### 场景 A: 端口被占用
```bash
# 在另一个终端启动服务占用端口
cd service
python main.py
```
然后在 GUI 中启动服务

**预期结果:**
- 显示错误日志（红色）
- 服务启动失败
- UI 状态正确

#### 场景 B: 服务文件不存在
1. 临时重命名 `service/main.py`
2. 尝试启动服务

**预期结果:**
- 显示错误消息
- 启动按钮可能被禁用

---

### 12. 性能测试 ✅

**指标:**
- 启动时间: < 2 秒
- 内存占用: ~100MB
- CPU 占用: 空闲时 < 5%
- 日志响应: 实时（< 100ms）

---

## 自动化测试脚本

```bash
#!/bin/bash

echo "🧪 Running automated tests..."

# Test 1: Check if GUI starts
echo "Test 1: GUI startup"
timeout 5 python main.py &
PID=$!
sleep 2
if ps -p $PID > /dev/null; then
    echo "✅ GUI started successfully"
    kill $PID
else
    echo "❌ GUI failed to start"
fi

# Test 2: Check service files
echo "Test 2: Service files"
if [ -f "service/main.py" ]; then
    echo "✅ Service files found"
else
    echo "❌ Service files missing"
fi

# Test 3: Check dependencies
echo "Test 3: Dependencies"
python -c "import customtkinter; import fastapi; import uvicorn" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ All dependencies installed"
else
    echo "❌ Missing dependencies"
fi

echo "🎉 Tests completed!"
```

---

## Bug 报告模板

如果发现问题，请使用以下模板报告：

```markdown
### Bug 描述
[简短描述问题]

### 重现步骤
1. 
2. 
3. 

### 预期行为
[描述应该发生什么]

### 实际行为
[描述实际发生了什么]

### 日志输出
```
[粘贴相关日志]
```

### 环境信息
- OS: [macOS/Windows/Linux]
- Python 版本: 
- GUI 版本: 

### 截图
[如果适用，添加截图]
```

---

## 测试通过标准

所有以下测试必须通过：

- [x] GUI 正常启动
- [x] 服务可以启动
- [x] 服务可以停止
- [x] 重复启动/停止无错误
- [x] 主题切换正常
- [x] 日志清除功能正常
- [x] 日志颜色正确
- [x] 窗口关闭正常
- [x] UI 元素显示正确
- [x] 长时间运行稳定
- [x] 错误处理正确

---

**测试负责人**: AlphaAI Labs QA Team
**最后更新**: 2025-10-01

