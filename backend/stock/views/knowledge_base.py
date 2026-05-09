"""
知识库视图集 - 提供 Markdown 文件的目录结构和内容读取
"""
import os
from pathlib import Path
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings

# md/ 目录位于项目根目录（backend/ 的上级）
MD_ROOT = os.path.abspath(os.path.join(settings.BASE_DIR, '..', 'md'))


class KnowledgeBaseTreeView(viewsets.ViewSet):
    """知识库目录树"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        if not os.path.exists(MD_ROOT):
            return Response({'code': 2000, 'msg': 'success', 'data': []})

        tree = self._build_tree(MD_ROOT, MD_ROOT)
        return Response({'code': 2000, 'msg': 'success', 'data': tree})

    def _build_tree(self, current_dir, root_dir):
        entries = []
        try:
            items = sorted(os.listdir(current_dir))
        except PermissionError:
            return entries

        for item in items:
            full_path = os.path.join(current_dir, item)
            rel_path = os.path.relpath(full_path, root_dir).replace('\\', '/')
            is_dir = os.path.isdir(full_path)

            if item.startswith('.'):
                continue

            label = item
            if item.endswith('.md'):
                label = item[:-3]

            entry = {
                'label': label,
                'path': rel_path,
                'is_dir': is_dir,
            }

            if is_dir:
                children = self._build_tree(full_path, root_dir)
                if children:
                    entry['children'] = children
                else:
                    continue
            elif not item.endswith('.md'):
                continue

            entries.append(entry)

        return entries


class KnowledgeBaseContentView(viewsets.ViewSet):
    """知识库 Markdown 文件内容"""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        file_path = request.query_params.get('path', '')

        if not file_path:
            return Response({
                'code': 4000,
                'msg': '缺少 path 参数',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

        # 防止路径穿越
        md_root = os.path.abspath(MD_ROOT)
        full_path = os.path.abspath(os.path.join(md_root, file_path))

        if not full_path.startswith(md_root):
            return Response({
                'code': 4000,
                'msg': '无效的文件路径',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

        if not os.path.exists(full_path) or not full_path.endswith('.md'):
            return Response({
                'code': 4000,
                'msg': '文件不存在',
                'data': None
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return Response({
                'code': 5000,
                'msg': f'读取文件失败: {str(e)}',
                'data': None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            'code': 2000,
            'msg': 'success',
            'data': {
                'path': file_path,
                'content': content,
                'filename': os.path.basename(file_path),
            }
        })
