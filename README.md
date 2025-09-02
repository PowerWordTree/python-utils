# Python Utils

内部使用的 Python 工具库，收集常用的辅助代码，方便在多个项目中复用。

## 安装与使用

### 方式一：直接复制文件
将需要的工具文件从本仓库复制到目标项目的合适位置，并在代码中正常导入使用。

### 方式二：Git Subtree 引入
1. 添加远程仓库：
   git remote add python-utils <仓库地址>
2. 引入指定目录：
   git subtree add --prefix=utils python-utils main --squash
3. 后续更新：
   git subtree pull --prefix=utils python-utils main --squash

### 方式三：Git Submodule 引入
1. 添加子模块：
   git submodule add <仓库地址> utils
2. 初始化并更新：
   git submodule update --init --recursive
3. 更新子模块：
   git submodule update --remote utils

### 方式四：通过包管理器（如 pip）安装
如果本仓库已发布到 PyPI 或内部私有源，可直接：
   pip install python-utils

## 许可证
[MIT License](LICENSE)
