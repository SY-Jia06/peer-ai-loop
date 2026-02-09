# 🔄 peer-ai-loop

> AI 同行审查循环：让不同 AI 互相审查代码，迭代改进，发挥各自优势

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 💡 核心理念

这个项目基于一个有趣的发现：**AI 最擅长的事情就是修对方的代码**。

- **Gemini 3 Pro** 擅长快速实现复杂功能
- **Claude** 擅长深度代码审查和发现边界问题
- **Codex** (预留) 擅长性能优化和算法实现

通过让它们互相审查，可以得到比单一 AI 更全面、更专业的代码质量保障。

## ✨ 特性

- 🚀 **并行审查** - 多个 AI 同时审查，节省时间
- 🎯 **专业报告** - 生成结构化 Markdown 审查报告
- 🔧 **可扩展** - 轻松添加新的 AI 模型
- ⚡ **高效** - 异步执行，充分利用 AI API
- 📊 **共识分析** - 自动识别多个 AI 都发现的关键问题

## 🎬 效果展示

### 示例：分布式限流器的同行审查循环

**实现者**: Gemini 3 Pro (89秒)
**审查者**: Claude

```bash
python main.py "实现一个分布式限流器，使用令牌桶算法，支持Redis存储" -o report.md
```

**Gemini 实现了**：
- ✅ 完整的令牌桶算法
- ✅ Lua 脚本保证原子性
- ✅ 支持高并发场景

**Claude 发现的问题**：
- 🔴 **严重**: 时间精度损失（浮点数秒 → 应用毫秒级整数）
- 🔴 **严重**: 脚本加载存在竞态条件
- 🟡 **中等**: 缺少参数校验、Key 注入风险
- 💡 **建议**: 添加失败模式控制、动态 TTL、批量检查接口

**评分**: 76/100 → 90/100 (改进后)

查看完整报告：[examples/01_distributed_rate_limiter.md](examples/01_distributed_rate_limiter.md)

---

---

**peer-ai-loop** = **peer review** + **AI** + **improvement loop**

---

## 🚀 快速开始

### 安装依赖

```bash
cd ai_review
pip install -r requirements.txt
```

### 配置 AI 工具

确保你已经安装了以下 CLI 工具：

- **Gemini**: `brew install gemini` (或按官方文档安装)
- **Claude Code**: `npm install -g @anthropic-ai/claude-code` (或按官方文档)

### 基础使用

```bash
# 基础用法（Gemini 实现 → Claude 审查）
python main.py "写一个快速排序函数"

# 指定实现者和审查者
python main.py "实现 LRU 缓存" -i gemini -r claude

# 保存报告到文件
python main.py "实现分布式锁" -o review_report.md

# 带上下文文件
python main.py "优化这个函数" -f mycode.py -o report.md
```

### 高级用法

```bash
# 使用最新的 Gemini 3 Pro 模型
python main.py "复杂任务" -i gemini -r claude

# 指定配置文件
python main.py "任务" -c custom_config.toml

# 查看帮助
python main.py --help
```

---

## 📁 项目结构

```
ai_review/
├── main.py              # CLI 主程序
├── ai_clients.py        # AI 客户端封装（Gemini, Claude, Codex）
├── reviewer.py          # 并行审查执行器
├── aggregator.py        # 审查结果聚合
├── reporter.py          # Markdown 报告生成
├── config.toml          # 配置文件
├── requirements.txt     # Python 依赖
└── examples/            # 示例审查报告
    ├── 01_distributed_rate_limiter.md  # 分布式限流器
    └── 02_async_task_scheduler.md      # 异步任务调度器
```

---

## ⚙️ 配置说明

编辑 `config.toml` 自定义 AI 模型和参数：

```toml
[ai.gemini]
enabled = true
command = "gemini"
model = "gemini-3-pro-preview"  # 最新 SOTA 模型

[ai.claude]
enabled = true
command = "claude"

[ai.codex]
enabled = false  # 需要有效的 OpenAI API key
command = "codex"
model = "gpt-5.2-codex"

[execution]
timeout_seconds = 300  # 审查超时时间

[output]
default_format = "markdown"
save_intermediate = false
```

---

## 📊 工作流程

```
用户输入编程任务
    ↓
AI #1 生成代码实现
    ↓
AI #2 和 AI #3 并行审查
    ↓
聚合审查结果
    ↓
生成 Markdown 报告
- 原始代码
- 各 AI 的审查意见
- 共识问题
- 独特见解
- 改进建议
```

---

## 🎯 使用场景

### 1. 代码质量提升
在提交 PR 前，让多个 AI 审查你的代码

### 2. 学习最佳实践
看不同 AI 如何看待同一段代码，学习多角度思考

### 3. 安全审计
利用多个 AI 的视角发现潜在的安全漏洞

### 4. 性能优化
获取多个 AI 的性能优化建议

### 5. 算法验证
验证算法实现的正确性和边界情况处理

---

## 🛠️ 技术栈

- **Python 3.8+** - 主要语言
- **asyncio** - 并行执行审查
- **click** - 命令行界面
- **rich** - 终端美化输出
- **toml** - 配置文件解析

---

## 📚 示例库

查看 [examples/](examples/) 文件夹获取更多实战示例：

- **分布式限流器** - 令牌桶算法 + Redis + Lua 原子性
- **异步任务调度器** - 优先级队列 + 延迟执行 + 重试机制
- **区块链实现** - PoW + Merkle 树 + 交易验证 (即将添加)

---

## 🔮 未来计划

- [ ] Web 界面可视化审查结果
- [ ] Git 集成 - 自动审查 Pull Request
- [ ] 审查历史记录和对比
- [ ] 自定义审查模板（安全、性能、可维护性）
- [ ] 迭代改进模式 - 根据审查自动改进代码

---

---

## 🚧 待完成功能

### 1. AI 权限选择接口
目前跳过权限的参数（`--yolo`, `--dangerously-skip-permissions`）是硬编码在配置文件中的。计划添加：
- CLI 参数：`--skip-permissions` / `--ask-permissions`
- 运行时动态选择是否跳过权限
- 为不同的 AI 设置不同的权限策略

### 2. 多轮迭代改进
当前版本只支持一轮改进（实现 → 审查 → 改进）。计划添加：
- `--iterations N` 参数，支持多轮迭代
- 每轮改进后重新审查
- 追踪代码质量的演进过程
- 生成迭代历史对比报告

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 License

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢
项目的代码100%由AI撰写

感谢以下 AI 助手的支持：
- **Gemini 3 Pro** - Google DeepMind
- **Claude** - Anthropic
- **Codex** - OpenAI

---

## 💬 联系方式

有问题或建议？欢迎提 Issue 或通过以下方式联系：

- GitHub Issues: [项目 Issues 页面]
- Email: a168995738@outlook.com (可选)

---

**⭐ 如果这个项目对你有帮助，请给个 Star！**
