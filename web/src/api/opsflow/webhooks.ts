/**
 * OpsFlow Webhook 管理 API
 */

import { request } from '/@/utils/service'

const prefix = '/api/opsflow/'

/** 获取模板下的 webhooks */
export function GetWebhooks(templateId: number) {
  return request({ url: prefix + `templates/${templateId}/webhooks/`, method: 'get' })
}

/** 创建 webhook */
export function CreateWebhook(templateId: number, data: {
  name: string; url: string; trigger_events: string[];
  secret?: string; retry_count?: number; retry_interval?: number
}) {
  return request({ url: prefix + `templates/${templateId}/webhooks/`, method: 'post', data })
}

/** 更新 webhook */
export function UpdateWebhook(templateId: number, webhookId: number, data: any) {
  return request({
    url: prefix + `templates/${templateId}/webhooks/${webhookId}/`,
    method: 'patch', data,
  })
}

/** 删除 webhook */
export function DeleteWebhook(templateId: number, webhookId: number) {
  return request({
    url: prefix + `templates/${templateId}/webhooks/${webhookId}/`,
    method: 'delete',
  })
}

/** 获取 webhook 投递日志 */
export function GetWebhookLogs(templateId: number, webhookId: number) {
  return request({
    url: prefix + `templates/${templateId}/webhooks/${webhookId}/logs/`,
    method: 'get',
  })
}
