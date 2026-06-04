import { request } from '/@/utils/service';

export interface QueryParams {
  page?: number;
  limit?: number;
  [key: string]: any;
}

export interface PasswordPayload {
  oldPassword: string;
  newPassword: string;
  newPassword2: string;
}

/** 获取用户个人信息 */
export function GetUserInfo(params?: QueryParams) {
  return request({
    url: '/api/system/user/user_info/',
    method: 'get',
    params,
  });
}

/** 更新用户信息 */
export function updateUserInfo(data: Record<string, any>) {
  return request({
    url: '/api/system/user/update_user_info/',
    method: 'put',
    data,
  });
}

/** 获取自己接收的消息（最新几条） */
export function GetSelfReceive(params?: QueryParams) {
  return request({
    url: '/api/system/message_center/get_self_receive/',
    method: 'get',
    params,
  });
}

/** 修改密码 */
export function UpdatePassword(data: PasswordPayload) {
  return request({
    url: '/api/system/user/change_password/',
    method: 'put',
    data,
  });
}

/** 上传头像 */
export function uploadAvatar(data: FormData) {
  return request({
    url: '/api/system/file/',
    method: 'post',
    data,
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}
