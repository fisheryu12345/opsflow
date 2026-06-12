# Plugin View 精简重构

> 提交: TBD | 日期: 2026-06-12
> 涉及 App: opsflow
> 类型: 重构

---

## 动机

`plugin_views.py` 经历了多轮 i18n 改造，先后引入了 `_resolve_lang` / `_snake_to_title` / `_ABBR_MAP` / `_fmt` 等辅助函数，代码膨胀到 357 行，逻辑复杂且 unnecessary。

最终意识到：**后端不需要替前端选语言**。API 永远返回 `name` + `name_en`，前端根据 `locale` 自己选择显示哪个。所有语言转换逻辑、缩写映射、标题生成都可以删掉。

## 变更要点

| 文件 | 变更前 | 变更后 |
|------|--------|--------|
| `backend/opsflow/views/plugin_views.py` | 357 行，含 `_ABBR_MAP`(30行) + `_snake_to_title`(20行) + `_resolve_lang`(20行) + `_fmt`/`_fmt_detail`/`_fmt_form_schema` 三个 helper | 248 行，每个端点直接从 PluginMeta 读 name+name_en 返回 |
| `composables/usePluginName.ts` | 存在，额外包装一层 `useI18n()` | 删除，各组件内联 |
| `api/plugins.ts` | 含 `withLang()` 函数，给 API 加 `?lang=en` 参数 | 删除 `withLang`，不再传语言参数 |

### 重构前后对比

**重构前** — 每个端点需经过 `_resolve_lang` 后处理：
```python
def _resolve_lang(request, data):
    if request.query_params.get('lang') != 'en':
        return data
    name_en = data.pop('name_en', '') or ''
    if name_en: data['name'] = name_en
    return data

def list(self, request):
    # ... 构建 version_map ...
    data = [_resolve_lang(request, item) for item in version_map.values()]
    return DetailResponse(data=data)
```

**重构后** — 直接返回 DB 值：
```python
def list(self, request):
    version_map = {}
    for p in qs:
        if p.code not in version_map:
            version_map[p.code] = {
                "code": p.code,
                "name": p.name,
                "name_en": p.name_en or "",
                # ...
            }
    return DetailResponse(data=list(version_map.values()))
```

### 前端变化

前端 4 个组件统一改为：
```ts
const { t, locale } = useI18n()
const isEn = computed(() => String(locale.value).startsWith('en'))
```
模板中用 `{{ isEn && item.name_en ? item.name_en : item.name }}` 替代之前的 `{{ pn(item) }}`。

## 迁移说明

无需迁移。API 响应格式不变（始终返回 `name` + `name_en`），只是去掉了 `?lang=en` 参数的支持 —— 参数仍然可以传但无影响。

### 关联文档

- 相关功能文档: [plugin-hotload-i18n](features/2026-06-12-plugin-hotload-i18n.md)
