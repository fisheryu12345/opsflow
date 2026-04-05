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