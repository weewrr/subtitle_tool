/**
 * 后端统一响应结构解壳工具
 *
 * 后端所有 /api/* JSON 均返回 { success, data, error_code, message }。
 * 走 ApiService 的调用由 axios 拦截器自动解壳;
 * 直连后端的场景(el-upload、裸 axios 轮询等)需手动调用本工具。
 */

/**
 * 解开统一响应壳,返回业务 data;非统一结构原样返回
 * @param {*} data - HTTP 响应体
 * @returns {*} 业务数据
 */
export function unwrapApiResponse(data) {
  if (data && typeof data === 'object' && 'success' in data && 'error_code' in data && 'data' in data) {
    return data.data
  }
  return data
}
