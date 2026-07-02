# 图片分类器 (Image Classifier)

一个基于 PyQt5 的桌面图片分类工具，支持重复图片检测、相似图片分组和快捷键快速分类。

## 功能特性

- 🖼️ **图片扫描**：支持扫描文件夹中的所有图片文件
- 🔍 **重复图片检测**：基于 MD5 哈希值识别完全相同的图片
- 📊 **相似图片分组**：基于 dHash 算法自动将相似图片分组
- ⌨️ **快捷键分类**：自定义快捷键快速将图片移动到指定文件夹
- 📁 **分类存储**：自动管理分类目标文件夹
- 💾 **会话保存**：支持中断后继续上次未完成的分类任务
- 🧹 **存储清理**：分类管理配置文件和缓存数据的清理功能

## 技术栈

- Python 3.x
- PyQt5 (GUI 框架)
- Pillow (图片处理)
- imagehash (图片哈希计算)

## 安装与运行

### 环境要求

- Python 3.8+
- pip 包管理工具

### 安装依赖

```bash
pip install -r requirements.txt
```

### 启动应用

**方式一：直接运行**

```bash
python app.py
```

**方式二：使用启动脚本 (Windows)**

```bash
双击运行 启动图片分类器.bat
```

## 使用说明

### 基本分类流程

1. **选择图片文件夹**：点击「选择图片文件夹」按钮，选择包含待分类图片的文件夹
2. **等待扫描完成**：系统会自动扫描文件夹中的所有图片
3. **后台分析**：扫描完成后，系统会在后台进行重复图片检测和相似图片分组
4. **开始分类**：使用方向键浏览图片，使用自定义快捷键将图片分类到指定文件夹

### 快捷键操作

| 按键 | 功能 |
|------|------|
| ← | 上一张图片 |
| → | 下一张图片 |
| ↑ | 上一组图片 |
| ↓ | 下一组图片 |
| 自定义字母/数字键 | 将当前组图片分类到对应文件夹 |

### 管理快捷键

1. 在左侧面板点击「添加快捷键」按钮
2. 输入单个字母或数字作为快捷键
3. 选择目标分类文件夹
4. 点击「删除快捷键」可移除已绑定的快捷键

### 处理重复图片

1. 扫描完成后，重复图片会显示在左侧「重复图片」面板中
2. 点击「查看详情」可查看所有重复图片的缩略图和详细信息
3. 可选择性保留或删除重复图片

### 清除存储占用

点击「清除存储占用」按钮可分类清理以下数据：
- 快捷键配置
- 重复图片处理记忆
- 最近文件夹记录
- 未完成分类会话

## 支持的图片格式

- JPG / JPEG
- PNG
- GIF
- BMP
- TIFF
- WebP

## 项目结构

```
.
├── app.py              # 应用入口
├── main_window.py      # 主窗口界面
├── classification_manager.py  # 分类管理逻辑
├── image_scanner.py    # 图片扫描与哈希计算
├── simple_hash.py      # 图片哈希算法实现
├── requirements.txt    # Python 依赖列表
├── 启动图片分类器.bat   # Windows 启动脚本
└── classifier_configs/ # 配置文件目录
    ├── recent_folders.json      # 最近文件夹记录
    ├── unfinished_session.json  # 未完成会话数据
    └── *.json                   # 各文件夹的快捷键配置
```

## Demo 体验

### 本地安装运行

由于本项目是基于 PyQt5 的桌面应用，需在本地环境安装运行：

**环境要求**

- Python 3.8+
- pip 包管理工具

**安装步骤**

```bash
# 克隆项目
git clone https://github.com/suisei-asteia/Image-classifier.git
cd Image-classifier

# 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

**Windows 用户便捷启动**

双击运行 `启动图片分类器.bat` 脚本即可启动应用。

### 演示视频

[演示视频链接]()

*请上传演示视频到第三方平台（如 Bilibili、YouTube）后替换上方链接*

## GitHub 仓库

[https://github.com/suisei-asteia/Image-classifier](https://github.com/suisei-asteia/Image-classifier)

## 许可证

MIT License