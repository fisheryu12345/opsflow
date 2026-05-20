# 微信公众号文章 HTML 模板参考

本文档是生成公众号文章的 HTML 模式参考。所有样式必须使用内联 style。

## 整体结构

```html
<div style="max-width:680px;margin:0 auto;padding:20px 16px 30px;font-family:-apple-system,'PingFang SC','Microsoft YaHei','Helvetica Neue',sans-serif;font-size:16px;line-height:1.8;color:#333;background:#fff;">

  <!-- 头部 -->
  <div style="margin-bottom:24px;">
    <div style="font-size:1.5em;font-weight:700;line-height:1.4;margin-bottom:10px;color:#1a1a1a;">标题</div>
    <div style="font-size:0.8em;color:#999;display:flex;justify-content:space-between;padding-bottom:14px;border-bottom:1px solid #eee;">
      <span>FT 量化期货交易系统</span>
      <span>2026-05-20</span>
    </div>
  </div>
</div>
```

## 分隔线

```html
<div style="text-align:center;margin:28px 0 20px;color:#ddd;font-size:1.2em;letter-spacing:6px;">◆ ◆ ◆</div>
```

## 章节标题 h2

```html
<h2 style="font-size:1.15em;font-weight:700;color:#1a1a1a;margin-bottom:14px;padding-left:12px;border-left:4px solid #2563eb;line-height:1.4;">一、章节标题</h2>
```

## 子标题 h3

```html
<h3 style="font-size:1.02em;font-weight:600;color:#333;margin:18px 0 10px;">子标题</h3>
```

## 段落

```html
<p style="margin-bottom:12px;font-size:0.95em;color:#444;">正文内容</p>
```

## 高亮文字

蓝色高亮：
```html
<span style="background:linear-gradient(to top,transparent 40%,#dbeafe 40%);font-weight:600;">高亮文字</span>
```

绿色高亮：
```html
<span style="background:linear-gradient(to top,transparent 40%,#d1fae5 40%);font-weight:600;">高亮文字</span>
```

## 表格

```html
<table style="width:100%;border-collapse:collapse;font-size:0.85em;margin:12px 0;border:1px solid #e8e8ee;">
  <tr><th style="background:#f8fafc;padding:8px 10px;font-weight:600;text-align:left;border-bottom:2px solid #e8e8ee;">列1</th><th style="background:#f8fafc;padding:8px 10px;font-weight:600;text-align:left;border-bottom:2px solid #e8e8ee;">列2</th></tr>
  <tr><td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">数据</td><td style="padding:7px 10px;border-bottom:1px solid #f0f0f0;">数据</td></tr>
  <tr><td style="padding:7px 10px;border-bottom:none;">最后一行</td><td style="padding:7px 10px;border-bottom:none;">数据</td></tr>
</table>
```

## 统计面板（用单行表格代替 CSS Grid）

```html
<table style="width:100%;border-collapse:collapse;font-size:0.85em;margin:12px 0;border:1px solid #e8e8ee;">
  <tr>
    <td style="padding:12px;text-align:center;border-right:1px solid #eee;background:#f8fafc;">
      <div style="font-size:1.3em;font-weight:700;color:#dc2626;">数值</div>
      <div style="font-size:0.72em;color:#999;margin-top:4px;">标签</div>
    </td>
    <td style="padding:12px;text-align:center;background:#f8fafc;">
      <div style="font-size:1.3em;font-weight:700;color:#059669;">数值</div>
      <div style="font-size:0.72em;color:#999;margin-top:4px;">标签</div>
    </td>
  </tr>
</table>
```

## 提示框 Callout

5种颜色，用于不同用途：

```html
<!-- 蓝色 - 定义/说明 -->
<div style="padding:14px 16px;margin:14px 0;font-size:0.9em;line-height:1.6;background:#eef3ff;border-left:4px solid #2563eb;border-radius:4px;">
  <b>标题：</b>内容
</div>

<!-- 绿色 - 案例/正面 -->
<div style="padding:14px 16px;margin:14px 0;font-size:0.9em;line-height:1.6;background:#ecfdf5;border-left:4px solid #059669;border-radius:4px;">

</div>

<!-- 橙色 - 提示/重要 -->
<div style="padding:14px 16px;margin:14px 0;font-size:0.9em;line-height:1.6;background:#fff7ed;border-left:4px solid #d97706;border-radius:4px;">

</div>

<!-- 紫色 - 分析/深度 -->
<div style="padding:14px 16px;margin:14px 0;font-size:0.9em;line-height:1.6;background:#f5f3ff;border-left:4px solid #7c3aed;border-radius:4px;">

</div>

<!-- 红色 - 风险提示 -->
<div style="padding:14px 16px;margin:14px 0;font-size:0.9em;line-height:1.6;background:#fef2f2;border-left:4px solid #dc2626;border-radius:4px;">

</div>
```

## 公式块（等宽字体 + 左边框）

```html
<div style="background:#f8fafc;border-left:3px solid #2563eb;padding:14px 16px;margin:14px 0;font-family:'Courier New',monospace;font-size:0.85em;line-height:1.7;color:#333;border-radius:0 4px 4px 0;">
  公式行1<br>
  公式行2<br>
  结果：<b>结论</b>
</div>
```

## SVG 柱状图（权益曲线）

固定 viewBox 340×190，自适应宽度：

```html
<div style="background:#fafafa;border:1px solid #e8e8ee;border-radius:8px;padding:16px;margin:14px 0;text-align:center;">
  <div style="font-size:0.82em;color:#666;margin-bottom:10px;">权益走势（日期范围）</div>
  <svg viewBox="0 0 340 190" style="width:100%;max-width:340px;">
    <!-- 网格参考线 -->
    <text x="12" y="22" font-size="10" fill="#999">1,030k</text><line x1="0" y1="24" x2="330" y2="24" stroke="#f0f0f0" stroke-width="1"/>
    <text x="12" y="62" font-size="10" fill="#999">990k</text><line x1="0" y1="64" x2="330" y2="64" stroke="#f0f0f0" stroke-width="1"/>
    <text x="12" y="102" font-size="10" fill="#999">950k</text><line x1="0" y1="104" x2="330" y2="104" stroke="#f0f0f0" stroke-width="1"/>
    <text x="12" y="142" font-size="10" fill="#999">910k</text><line x1="0" y1="144" x2="330" y2="144" stroke="#f0f0f0" stroke-width="1"/>
    <!-- 柱子：rect + 数值文本 + 日期文本 -->
    <rect x="20" y="68" width="18" height="76" fill="#059669" rx="2"/>
    <text x="22" y="62" font-size="9" fill="#999">998k</text>
    <text x="20" y="154" font-size="8" fill="#999">04-30</text>
    <!-- 绿色柱 = 正收益日，红色柱 = 负收益日 -->
    <rect x="92" y="76" width="18" height="68" fill="#dc2626" rx="2"/>
    <!-- 图例 -->
    <rect x="30" y="170" width="8" height="8" fill="#059669" rx="1"/><text x="42" y="179" font-size="8" fill="#999">正收益日</text>
    <rect x="110" y="170" width="8" height="8" fill="#dc2626" rx="1"/><text x="122" y="179" font-size="8" fill="#999">负收益日</text>
  </svg>
  <div style="margin-top:6px;font-size:0.75em;color:#999;">峰值: +X% ｜ 谷值: -Y%</div>
</div>
```

SVG 柱状图计算：
- viewBox height=190，图表区域 y=0~160，底部 y=160
- 每根柱子根据 equity 值映射高度：`height = (equity - minEquity) / (maxEquity - minEquity) * 120 + 10`
- y 位置：`y = 160 - height`
- 柱子宽度18，间距24（每根间隔 x += 24）
- 参考线取 max、min 和两个中间值

## 品种列表

```html
<div style="margin:10px 0;font-size:0.85em;line-height:1.8;">
  【空】品种1 3U ｜ 【多】品种2 2U<br>
  【多】品种3 1U
</div>
```

## 方向标记

- 【多】表示多头
- 【空】表示空头

颜色规则：
- 正收益数据：`color:#059669`
- 负收益数据：`color:#dc2626`
- 普通强调：`color:#2563eb`

## 文件保存规范

1. 文件名格式：`策略简称-核心卖点-公众号文章.html`（如 `海龟V2策略深度解析-公众号文章.html`）
2. 保存到项目根目录的 `wechat/` 文件夹
3. 同步更新 `wechat/README.md`，在文章列表追加新条目
