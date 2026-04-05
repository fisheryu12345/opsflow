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