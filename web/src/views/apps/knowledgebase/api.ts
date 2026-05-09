import { request } from '/@/utils/service'

const apiPrefix = '/api/stock/knowledge-base/'

export interface TreeNode {
  label: string
  path: string
  is_dir: boolean
  children?: TreeNode[]
}

export interface ContentData {
  path: string
  content: string
  filename: string
}

export function GetTree() {
  return request({
    url: apiPrefix + 'tree/',
    method: 'get',
  })
}

export function GetContent(path: string) {
  return request({
    url: apiPrefix + 'content/',
    method: 'get',
    params: { path },
  })
}
