"""Seed Template Presets — 10 个常见 IT 运维场景预设提示词 (中英双语)"""
from django.core.management.base import BaseCommand
from opsflow.models.template import TemplatePreset

PRESETS = [
    # ── 串行 serial ──
    {
        "name": "数据备份+校验", "name_en": "Backup & Verify",
        "icon": "💾", "category": "serial", "sort_order": 1,
        "prompt": "对服务器执行以下操作：1. 备份数据目录到 /backup 2. 校验备份完整性 3. 上传备份到远程存储 4. 发送备份完成通知",
        "prompt_en": "Execute the following on the server: 1. Backup data directory to /backup 2. Verify backup integrity 3. Upload backup to remote storage 4. Send completion notification",
    },
    {
        "name": "安全基线巡检", "name_en": "Security Baseline Check",
        "icon": "🛡", "category": "serial", "sort_order": 2,
        "prompt": "对服务器执行安全巡检：1. 检查 SSH 配置是否禁用了 root 登录 2. 检查防火墙规则是否完整 3. 检查关键端口是否按预期开放 4. 检查系统安全补丁状态。全部检查后生成安全巡检报告。",
        "prompt_en": "Run security baseline check on servers: 1. Verify SSH root login is disabled 2. Check firewall rules completeness 3. Verify critical port exposure 4. Check security patch status. Generate a security report when done.",
    },
    # ── 排他网关 exclusive_gateway ──
    {
        "name": "磁盘空间告警", "name_en": "Disk Space Alert",
        "icon": "💿", "category": "gateway", "sort_order": 3,
        "prompt": "检查服务器磁盘空间使用率，如果超过 80% 就发送告警通知并清理临时文件，如果未超过就发送正常报告。",
        "prompt_en": "Check server disk usage. If usage exceeds 80%, send an alert and clean temp files. Otherwise send a normal status report.",
    },
    {
        "name": "服务健康+自愈", "name_en": "Health Check & Auto-Heal",
        "icon": "🏥", "category": "gateway", "sort_order": 4,
        "prompt": "检查 Web 服务健康状态 /health 端点，如果服务挂了就重启服务。重启后再做一次健康检查，如果恢复了就发通知说已恢复，如果还是失败就发告警通知。",
        "prompt_en": "Check web service health at /health endpoint. If down, restart the service. Re-check after restart: if recovered, notify success; if still down, send alert.",
    },
    # ── 并行+汇聚 parallel ──
    {
        "name": "多机房并行部署", "name_en": "Multi-DC Parallel Deploy",
        "icon": "🌐", "category": "parallel", "sort_order": 5,
        "prompt": "并行部署应用到上海、北京、深圳三个机房的服务器上，所有机房部署完成后汇总结果并发送报告。",
        "prompt_en": "Deploy application in parallel to servers in Shanghai, Beijing, and Shenzhen data centers. After all deployments complete, summarize results and send report.",
    },
    {
        "name": "并行重启+验证", "name_en": "Parallel Restart & Verify",
        "icon": "⏯", "category": "parallel", "sort_order": 6,
        "prompt": "并行重启 Web 服务器、数据库服务器和缓存服务器，所有服务重启完成后统一做健康检查验证，最后发送操作报告。",
        "prompt_en": "Restart web server, database server, and cache server in parallel. Once all services are back, run a unified health check and send the operation report.",
    },
    # ── 循环A (节点级) loop_a ──
    {
        "name": "ECS 批量创建", "name_en": "Batch ECS Creation",
        "icon": "⚡", "category": "loop_a", "sort_order": 7,
        "prompt": "在阿里云 cn-hangzhou 地域，依次创建 3 台 ECS 实例，名称分别为 web-01、web-02、web-03，规格为 ecs.t5-lc1m1.small，创建后初始化配置并发送完成报告。",
        "prompt_en": "In Alibaba Cloud cn-hangzhou region, sequentially create 3 ECS instances named web-01, web-02, web-03 (type ecs.t5-lc1m1.small). After creation, initialize configuration and send completion report.",
    },
    {
        "name": "批量磁盘巡检", "name_en": "Batch Disk Inspection",
        "icon": "🔍", "category": "loop_a", "sort_order": 8,
        "prompt": "对 5 台服务器依次检查磁盘空间使用率，如果超过 80% 就发送告警，全部检查完后发送巡检汇总报告。",
        "prompt_en": "Check disk usage on 5 servers sequentially. If any exceeds 80%, send an alert. After all checks complete, send a summary inspection report.",
    },
    # ── 循环B (排他网关回环) loop_b ──
    {
        "name": "补丁滚动部署", "name_en": "Rolling Patch Deploy",
        "icon": "🔧", "category": "loop_b", "sort_order": 9,
        "prompt": "在阿里云 cn-shanghai 地域，循环执行以下操作直到成功：1. 备份系统盘 2. 执行 shell 打补丁命令 3. 重启实例 4. 检查实例状态。如果实例状态不是 Running，回到第1步重新来。如果状态是 Running，发送成功报告。",
        "prompt_en": "In Alibaba Cloud cn-shanghai region, loop the following until success: 1. Backup system disk 2. Run shell patch command 3. Reboot instance 4. Check instance status. If status is not Running, go back to step 1. If Running, send success report.",
    },
    {
        "name": "ECS 创建+等待就绪", "name_en": "ECS Create & Wait Ready",
        "icon": "⏳", "category": "loop_b", "sort_order": 10,
        "prompt": "在阿里云 cn-hangzhou 创建一台 ECS 实例，创建后反复检查实例状态，直到状态变为 Running 才继续往下走。确认 Running 后，初始化系统配置并发送成功报告。",
        "prompt_en": "Create one ECS instance in Alibaba Cloud cn-hangzhou. After creation, repeatedly check instance status until it becomes Running. Then initialize system configuration and send success report.",
    },
]


class Command(BaseCommand):
    help = "Seed 10 bilingual template presets for AI quick-start"

    def handle(self, *args, **options):
        created = 0
        for p in PRESETS:
            _, is_new = TemplatePreset.objects.get_or_create(
                name=p["name"],
                defaults={k: v for k, v in p.items() if k != "name"},
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Done. Created {created} new presets."))
