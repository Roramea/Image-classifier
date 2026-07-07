# 图片分类器

一个基于 PyQt5 的图片分类工具，支持按快捷键快速分类图片、检测重复图片、相似度分组等功能。

## 功能特性

### 核心功能
- **图片扫描**：自动扫描文件夹中的图片，支持 JPG、PNG、GIF、BMP、TIFF、WebP 等格式
- **快捷键分类**：自定义快捷键绑定目标文件夹，一键分类图片
- **重复图片检测**：通过 MD5 哈希检测完全相同的图片，支持选择性保留
- **相似度分组**：基于感知哈希（dHash）将相似图片自动分组，可调整阈值
- **哈希分析**：独立窗口进行哈希计算，显示进度和预估剩余时间

### 高级特性
- **会话恢复**：意外关闭后自动保存进度，重启时提示恢复未完成的分类
- **文件夹隔离**：快捷键配置按文件夹独立存储，互不影响
- **增量更新**：切换文件夹或重新扫描时智能增量更新哈希缓存，仅处理新增或修改的图片
- **循环导航**：支持图片组和图片的循环浏览（使用取模运算实现首尾相连）
- **存储清理**：提供分类存储清理选项，支持选择性清除各类配置数据
- **图片旋转**：支持顺时针/逆时针旋转当前图片

## 技术栈

- **Python** 3.x
- **PyQt5** >= 5.15.9 - GUI 框架
- **Pillow** >= 10.0.0 - 图像处理

## 架构设计

项目采用 **MVP（Model-View-Presenter）** 模式，职责清晰分离：

- **View（视图层）**：`views/` 和 `dialogs/`，负责界面展示和用户交互，不包含业务逻辑
- **Presenter（控制器层）**：`presenters/`，协调 View 和 Model，处理用户操作和状态更新
- **Model（模型层）**：`core/` 和 `services/`，包含核心业务逻辑、数据管理和算法实现

## 开发者特性

### 调试服务器

应用启动时会自动在端口 `8765` 启动调试 HTTP 服务器，用于查看实时日志和调试信息。

## 项目结构

```
文件分类器/
├── app.py                    # 应用入口
├── requirements.txt          # 依赖列表
├── 启动图片分类器.bat         # Windows 启动脚本
├── classifier_configs/       # 配置文件目录（自动生成）
│   ├── {md5}.json            # 文件夹特定快捷键配置
│   ├── {md5}_hash_cache.json # 哈希缓存
│   ├── recent_folders.json   # 最近文件夹记录
│   ├── unfinished_session.json # 未完成会话
│   └── debug_logs.json       # 调试日志
├── core/                     # 核心模块
│   ├── classification_manager.py # 分类管理器（配置、状态）
│   ├── image_scanner.py      # 图片扫描器
│   ├── simple_hash.py        # 哈希算法实现
│   ├── scan_thread.py        # 后台扫描线程
│   ├── debug_manager.py      # 调试管理器（日志、HTTP服务器）
│   ├── observer.py           # 观察者模式基类
│   └── utils.py              # 工具函数
├── services/                 # 业务服务
│   ├── classification_service.py # 分类服务
│   ├── duplicate_service.py  # 重复图片服务
│   └── hash_analysis_service.py # 哈希分析服务
├── views/                    # 视图层
│   └── main_window.py        # 主窗口
├── presenters/               # 控制器层（MVP）
│   └── main_presenter.py     # 主控制器
├── dialogs/                  # 对话框组件
│   ├── folder_select_dialog.py    # 文件夹选择
│   ├── hash_analysis_dialog.py    # 哈希分析
│   ├── duplicate_detail_dialog.py # 重复详情
│   ├── shortcut_input_dialog.py   # 快捷键输入
│   └── storage_clean_dialog.py    # 存储清理
└── widgets/                  # 自定义组件
    └── scrolling_label.py    # 滚动标签
```

## 安装与运行

### 环境要求

- Python 3.x
- pip 包管理器

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动方式

**方式一：双击启动脚本**

```
启动图片分类器.bat
```

**方式二：命令行运行**

```bash
python app.py
```

## 使用指南

### 基本流程

1. **选择文件夹**：点击"选择文件夹"按钮或从最近文件夹列表中选择
2. **等待扫描**：程序自动扫描文件夹中的图片
3. **开始分类**：使用自定义快捷键将当前图片移动到对应文件夹

### 快捷键操作

- 添加快捷键：点击快捷键列表旁的"添加"按钮，按下目标按键后按 Enter 确认
- 删除快捷键：选中快捷键后点击"删除"按钮
- 使用快捷键：在主界面按下绑定的按键，当前图片将被分类到对应文件夹

### 重复图片处理

1. 点击"分析哈希"按钮进行哈希分析
2. 分析完成后，重复图片会出现在右侧列表中
3. 点击重复组可查看详情，选择保留哪张图片

### 相似度阈值调整

- 使用顶部的 +/- 按钮或直接输入数值调整相似度阈值
- 阈值越低，分组越严格（只有非常相似的图片才会分到一组）
- 阈值越高，分组越宽松

## 配置说明

配置文件存储在 `classifier_configs/` 目录下：

- **文件夹特定配置**：以文件夹路径的 MD5 哈希命名的 `.json` 文件，存储该文件夹的快捷键配置
- **哈希缓存**：以文件夹路径的 MD5 哈希命名的 `_hash_cache.json` 文件，存储已计算的哈希值
- **最近文件夹**：`recent_folders.json` 记录最近访问的文件夹
- **未完成会话**：`unfinished_session.json` 保存未完成的分类进度

## 注意事项

- 文件夹名称不能包含 Windows 非法字符（`<>`:`/|\?*`）
- 不能使用 Windows 保留名称（CON、PRN、AUX、NUL 等）
- 分类过程中关闭程序会自动保存进度
- 重复图片处理记忆会在当前分类完成后自动清除