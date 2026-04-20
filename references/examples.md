# 示例集

本文档包含 booksmith 各关键 Phase 的 Input/Output 示例。查看示例时请同时阅读对应的 Phase 指令。

---

## Phase 0 示例：需求确认对话

### 示例 1：信息充分的快捷触发

**用户输入：**
```
帮我写一本关于 Docker 容器技术的技术书，O'Reilly 风格，12 章，有插图
```

**Skill 响应（跳过确认，直接开始）：**
```
收到！开始制作《Docker 容器技术》。
参数：O'Reilly 风格 / 目标读者：有基础 / 篇幅：12 章 / 有插图
正在初始化项目目录...
```

### 示例 2：信息不足，需要确认

**用户输入：**
```
我想把最近的 AI 学习笔记整理成一本书
```

**Skill 响应：**
```
收到，准备制作技术书。请确认：

1. 书名：「AI 学习笔记」，可以吗？
2. 目标读者：小白 / 有基础 / 专业人士？
3. 出版风格：O'Reilly（对话式技术书）/ Academic（学术报告）/ Handbook（操作手册）？
4. 篇幅偏好：精简（8-12 章）/ 详尽（15+ 章）？
5. 是否需要插图：是 / 否？
6. 末尾引导：需要加公众号/个人品牌引导吗？

直接回复修改项即可，没问题的我直接开始。
```

**用户回复：**
```
书名改成「AI 工程师成长指南」，目标读者是有基础，风格 Handbook，篇幅详尽，要插图
```

**Skill 响应：**
```
确认：
- 书名：AI 工程师成长指南
- 目标读者：有基础
- 出版风格：Handbook
- 篇幅：详尽（15+ 章）
- 插图：是

开始初始化项目...
```

---

## Phase 1 示例：调研 Agent 输出格式

### 调研文件示例：`research/01-core-concepts.md`

```markdown
# 调研报告：核心概念与定义

Agent：核心概念与定义
主题：Docker 容器技术
完成时间：2026-04-18

## S/A 级信源（高质量）

### 信源 1 [S]
- **标题**：What is a Container?
- **来源**：Docker Official Documentation
- **URL**：https://docs.docker.com/get-started/
- **一手程度**：S（一手：官方文档）
- **核心信息**：
  - 容器是打包了应用程序及其依赖的标准化单元
  - 容器与虚拟机的区别：共享 OS 内核，轻量级
  - 镜像层叠结构（Layered filesystem）

### 信源 2 [A]
- **标题**：Containerization vs Virtualization
- **来源**：Red Hat Blog, 2024
- **URL**：https://www.redhat.com/en/topics/containers/
- **一手程度**：A（权威：Red Hat 官方博客）
- **核心信息**：
  - 容器化提供一致的运行环境
  - 解决了"在我机器上能跑"的问题

## B/C 级信源（参考）

[省略...]

## 交叉验证

| 核心事实 | 验证信源 | 状态 |
|---------|---------|------|
| 容器是轻量级虚拟化 | [信源1], [信源2], [信源5] | ✅ 3个独立信源 |
| 镜像采用层叠结构 | [信源1], [信源3] | ✅ 2个独立信源 |
| Docker 是最流行的容器引擎 | [信源2], [信源8] | ⚠️ 仅有2个信源，待补充 |

## 信息缺口

- 容器安全的最新标准（2024-2025）信息不足
- ARM 架构下的容器兼容性数据较少
```

---

## Phase 2 示例：风格锚定

### O'Reilly 风格样板章结构

```
Chapter 01 — Running Your First Container

[场景引入：1-2段真实场景]
你有没有遇到过这种情况：本地跑得好好的代码，
交给同事却报了一堆环境依赖错误？
或者服务器上部署一个新服务，光是配环境就花了一整天？
...

[核心概念讲解]
## 什么是容器？

容器是一个打包了应用程序及其全部依赖的标准化单元...

[Tip 框]
提示：如果你在 Windows 或 macOS 上使用 Docker，
实际上是在运行一个轻量级 Linux 虚拟机（Docker Desktop）。

[Warning 框]
警告：不要把 production 服务跑在 docker run 的交互式终端里，
退出后容器会停止。应该使用后台模式（-d）。

[代码示例]
$ docker run -d -p 8080:80 nginx

[小结]
本章要点：
- 容器解决了环境一致性问题
- 镜像和容器的关系...
```

---

## Phase 3 示例：逐章写作

### `manuscript/glossary.md` 示例

```markdown
# 术语表

| 术语 | 英文 | 首次出现 | 简要定义 |
|------|------|---------|---------|
| 容器 | Container | ch01 | 打包应用及其依赖的标准化单元 |
| 镜像 | Image | ch01 | 容器的只读模板 |
| Dockerfile | Dockerfile | ch02 | 定义镜像构建步骤的配置文件 |
| 卷 | Volume | ch03 | 容器与宿主机共享的数据目录 |
| 网络模式 | Network Mode | ch04 | 容器间通信的隔离级别 |
```

### 章节手稿 `manuscript/ch03.md` 开头示例

```markdown
## Chapter 03 — 数据持久化与卷

> 上一章我们学会了如何用 Dockerfile 构建自定义镜像。
> 但容器里的数据命运如何？容器删除后数据还在吗？
> 本章解答这两个问题。

### 章节价值
学会使用卷（Volume）在容器和宿主机之间共享数据，
理解数据层和容器生命周期的关系。

### 核心概念
Dockerfile, Build Context, Multi-stage Build, .dockerignore

### 叙事递进
ch01 建立了"容器是什么"，ch02 学会了"如何构建镜像"，
ch03 要解决"数据如何持久化"——这是容器化实践的第三根支柱。
```

---

## Phase 4 示例：质量验证报告

### Phase 4 独立审查子 agent 输出格式

```json
{
  "reviewer": "独立质量审查 Agent",
  "target_reader": "有基础",
  "dimensions": [
    {
      "dimension": "可读性",
      "score": 8,
      "issues": [
        "ch07 的 7.2.1 节对新手过于跳跃，建议补充一个过渡段落"
      ]
    },
    {
      "dimension": "技术准确性",
      "score": 9,
      "issues": []
    },
    {
      "dimension": "叙事连贯性",
      "score": 7,
      "issues": [
        "ch05 和 ch06 的案例行业分布差异较大，建议统一使用电商场景"
      ]
    },
    {
      "dimension": "风格一致性",
      "score": 9,
      "issues": []
    },
    {
      "dimension": "引用质量",
      "score": 8,
      "issues": [
        "ch03 提到'Docker 官方推荐...'但没有引用，建议补充官方文档链接"
      ]
    }
  ],
  "verdict": "通过，有 2 处小问题建议迭代修复"
}
```

---

## Phase 7 示例：工作报告数据

```markdown
## 九、关键数据

| 指标 | 数值 |
|------|------|
| 章节数 | 12 |
| 总字数 | 48,320 |
| 信源数 | 43 |
| S/A 占比 | 65% |
| 插图数 | 7 |
| PDF 大小 | 12.4 MB |
| 质量验证 | 通过 ✅ |
```

---

## 断点续写示例

**场景**：用户说「继续写《Docker 容器技术》」

**Skill 读取 `project.json`**：

```json
{
  "title": "Docker 容器技术",
  "target_reader": "有基础",
  "style": "oreilly",
  "chapters_planned": 12,
  "current_phase": 3,
  "chapters_completed": ["ch01", "ch02", "ch03", "ch04", "ch05"]
}
```

**Skill 判断**：
- `current_phase: 3` → 处于 Phase 3 写作阶段
- `chapters_completed: ["ch01", "ch02", "ch03", "ch04", "ch05"]` → 下一章是 ch06

**Skill 响应**：
```
检测到未完成项目：Docker 容器技术
当前进度：Phase 3（第 6 章写作中）
已完成：ch01-ch05（共 5 章，约 18,000 字）

继续从 ch06 开始写作...
```
