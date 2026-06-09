# -*- coding: utf-8 -*-

"""
@author: 猿小天
@contact: QQ:1638245306
@Created on: 2021/8/12 012 10:25
@Remark: drf-spectacular 配置 — 自定义 AutoSchema

重写 drf-spectacular 的 AutoSchema 以支持自定义 tags 分组逻辑。
"""

from drf_spectacular.openapi import AutoSchema


def get_summary(string):
    """从操作描述中提取第一行作为 summary"""
    if string is not None:
        result = string.strip().replace(" ", "").split("\n")
        return result[0]
    return string


class CustomAutoSchema(AutoSchema):
    """自定义 AutoSchema，根据 URL 层级自动设置 tags"""

    def get_tags(self):
        tags = super().get_tags()
        if tags and hasattr(self.view, 'request') and self.view.request:
            # 保留默认 tags 逻辑，drf-spectacular 已按路径自动分组
            return tags
        return tags
