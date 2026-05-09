方案二：更改本地计算机的执行策略（需管理员）
如果你希望所有用户都能运行脚本，或者方案一无效，可以使用此方法。
右键点击“开始”菜单，选择 “Windows PowerShell (管理员)” 或 “终端 (管理员)”。
输入以下命令并回车：
powershell

暗色
复制
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned

Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process
& C:\Users\dell\Desktop\Vue\.venv\Scripts\Activate.ps1 


PIP 下载加速
pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

npm 
npm config set registry https://registry.npmmirror.com

🚀 方案一：切换至国内镜像源（首选）
这是最常见的原因。npm 默认的官方源服务器在国外，国内访问速度慢且不稳定，很容易导致安装过程“卡住”。
执行命令：在终端中运行以下命令，将 npm 源切换到国内高速镜像。

npm config set registry https://registry.npmmirror.com

npm config get registry
# 确认返回的是 https://registry.npmmirror.com/ 后
npm install --verbose



参考了9篇结果
npm 安装慢主要是因为默认的官方源服务器在国外，国内访问网络延迟高且不稳定。要解决这个问题，最直接有效的方法是切换到国内镜像源。
以下是为你整理的几种加速方案，按推荐程度排序：
1. 🚀 核心方案：切换国内镜像源（最推荐）
这是最简单、提升最明显的方法。目前最稳定、速度最快的源是淘宝镜像（npmmirror）。
永久切换（推荐）
只需执行一次，以后所有 npm install 都会自动走加速通道。
bash

暗色
复制
npm config set registry https://registry.npmmirror.com
验证是否生效
bash

暗色
复制
npm config get registry
# 输出应为: https://registry.npmmirror.com/
临时使用（单次有效）
如果你不想永久修改配置，可以在安装命令后加上源地址：
bash

暗色
复制
npm install <包名> --registry=https://registry.npmmirror.com
恢复官方源
如果以后需要发布包或连接海外私有库，可以切回官方：

npm config set registry https://registry.npmjs.org
2. 🛠️ 进阶方案：使用包管理工具或管理器
如果你觉得手动敲命令麻烦，或者追求极致的安装速度，可以尝试以下工具：
使用 nrm 管理镜像源
nrm (npm registry manager) 可以帮你快速测试各个源的速度并一键切换。
安装： npm install -g nrm
测速： nrm test (它会列出淘宝、腾讯云、华为云等源的速度)
切换： nrm use taobao (自动切换到最快的源)
换用更快的包管理器
npm 本身在安装机制上相对较慢，可以考虑替代方案：
pnpm（强烈推荐）： 它是目前速度最快的包管理器之一。它通过硬链接机制复用磁盘上的包，安装速度通常比 npm 快 2-3 倍，且极度节省磁盘空间。
安装：npm install -g pnpm
使用：pnpm install
cnpm： 淘宝官方维护的客户端，基于 npm 修改，默认走淘宝源。
安装：npm install -g cnpm --registry=https://registry.npmmirror.com
使用：cnpm install <包名>