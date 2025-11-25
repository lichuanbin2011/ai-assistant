/**
 * ============================================================================
 * API 客户端封装 (lib/api-client.js)
 * ============================================================================
 *
 * 文件作用：
 *   统一封装所有 HTTP 请求，提供一致的错误处理和请求配置
 *
 * 主要功能：
 *   1. ApiClient 类 - 通用 HTTP 请求封装
 *   2. conversationsApi - 会话相关 API
 *   3. messagesApi - 消息相关 API
 *   4. pdfApi - PDF 文件相关 API（新增）
 *
 * 调用位置：
 *   - lib/hooks/useConversations.js
 *   - lib/hooks/useMessages.js
 *   - components/chat/ChatArea.js
 *   - app/chatpdf/page.js（新增）
 *
 * 修改记录：
 *   - 2025-11-15：添加 messagesApi.get() 方法（获取单条消息）
 *   - 2025-11-16：修复文件上传问题，添加 postFormData 方法和 pdfApi
 *
 * ============================================================================
 */

/**
 * API客户端封装
 * 统一处理请求和错误
 */
class ApiClient {
  constructor(baseURL = '') {
    this.baseURL = baseURL; // API 基础路径
  }

  /**
   * 通用请求方法
   *
   * ✅ 修改点 1：支持跳过 Content-Type 设置（用于文件上传）
   *
   * 修改说明：
   *   - 添加 skipContentType 选项判断
   *   - 当 body 是 FormData 时自动跳过 Content-Type
   *   - 其他情况保持原有的 JSON Content-Type
   */
  async request(url, options = {}) {
    const config = {
      ...options,
      headers: {
        // ✅ 修改：只在非 FormData 且未设置 skipContentType 时添加 Content-Type
        ...(options.skipContentType || options.body instanceof FormData
          ? {} // 跳过 Content-Type，让浏览器自动设置
          : { 'Content-Type': 'application/json' }), // 默认 JSON
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${this.baseURL}${url}`, config);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `HTTP ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API请求失败:', error);
      throw error;
    }
  }

  // GET请求
  get(url, options = {}) {
    return this.request(url, { ...options, method: 'GET' });
  }

  // POST请求（JSON）
  post(url, data, options = {}) {
    return this.request(url, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * ✅ 修改点 2：新增 postFormData 方法
   *
   * 作用：
   *   专门用于文件上传，不设置 Content-Type
   *   让浏览器自动设置为 multipart/form-data
   *
   * 参数：
   *   @param {string} url - 请求路径
   *   @param {FormData} formData - FormData 对象
   *   @param {Object} options - 额外配置
   *
   * 返回值：
   *   @returns {Promise<Object>} API 响应数据
   *
   * 使用示例：
   *   const formData = new FormData()
   *   formData.append('file', file)
   *   await apiClient.postFormData('/pdf/upload', formData)
   */
  postFormData(url, formData, options = {}) {
    return this.request(url, {
      ...options,
      method: 'POST',
      body: formData,
      skipContentType: true, // ✅ 跳过 Content-Type 设置
    });
  }

  // PATCH请求
  patch(url, data, options = {}) {
    return this.request(url, {
      ...options,
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // DELETE请求
  delete(url, options = {}) {
    return this.request(url, { ...options, method: 'DELETE' });
  }
}

// 导出单例
export const apiClient = new ApiClient('/api');

// 具体业务API封装
export const conversationsApi = {
  // 获取会话列表
  list: (params) => apiClient.get('/conversations', { params }),

  // 创建会话
  create: (data) => apiClient.post('/conversations', data),

  // 更新会话
  update: (id, data) => apiClient.patch(`/conversations/${id}`, data),

  // 删除会话
  delete: (id) => apiClient.delete(`/conversations/${id}`),

  // 生成标题
  generateTitle: (id) => apiClient.post(`/conversations/${id}/title`),

  // 获取消息列表
  getMessages: (id, params) =>
    apiClient.get(`/conversations/${id}/messages`, { params }),

  // 发送消息
  sendMessage: (id, data) =>
    apiClient.post(`/conversations/${id}/messages`, data),
};

/**
 * ============================================================================
 * 消息相关 API
 * ============================================================================
 */
export const messagesApi = {
  /**
   * 获取单条消息
   *
   * 作用：
   *   从数据库获取单条消息的完整信息（包含 citations）
   *
   * 参数：
   *   @param {string} messageId - 消息 ID
   *
   * 返回值：
   *   @returns {Promise<Object>} {
   *     success: true,
   *     data: {
   *       id: string,
   *       role: string,
   *       content: string,
   *       citations: Array,      // 引用来源
   *       isWebSearch: boolean,  // 是否为联网搜索
   *       createdAt: string,
   *       ...
   *     }
   *   }
   *
   * 调用位置：
   *   - lib/hooks/useMessages.js 的 refreshMessage()
   *
   * 使用示例：
   *   const response = await messagesApi.get('msg_123')
   *   log.debug(response.data.citations)
   */
  get: (messageId) => apiClient.get(`/messages/${messageId}`),

  /**
   * 删除消息
   *
   * 作用：
   *   从数据库删除指定消息
   *
   * 参数：
   *   @param {string} messageId - 消息 ID
   *
   * 返回值：
   *   @returns {Promise<Object>} { success: true }
   *
   * 调用位置：
   *   - lib/hooks/useMessages.js 的 deleteMessage()
   *   - components/chat/MessageItem.js 的删除按钮
   */
  delete: (id) => apiClient.delete(`/messages/${id}`),
};

/**
 * ============================================================================
 * ✅ 修改点 3：新增 PDF 相关 API
 * ============================================================================
 *
 * 作用：
 *   封装所有 PDF 文件相关的 API 操作
 *
 * 调用位置：
 *   - app/chatpdf/page.js（上传页面）
 *   - 未来可能的 PDF 管理页面
 *
 * ============================================================================
 */
export const pdfApi = {
  /**
   * 上传 PDF 文件
   *
   * 作用：
   *   上传 PDF 文件到服务器，保存到数据库
   *
   * 参数：
   *   @param {File} file - PDF 文件对象（从 input[type=file] 获取）
   *
   * 返回值：
   *   @returns {Promise<Object>} {
   *     success: true,
   *     message: '上传成功',
   *     data: {
   *       id: string,           // PDF 记录 ID
   *       name: string,         // 原始文件名
   *       fileName: string,     // 服务器保存的文件名
   *       filePath: string,     // 访问路径
   *       size: number,         // 文件大小（字节）
   *       userId: string,       // 上传用户 ID
   *       createdAt: string,    // 上传时间
   *     }
   *   }
   *
   * 错误处理：
   *   - 401: 未登录
   *   - 400: 文件类型错误或文件过大
   *   - 500: 服务器错误
   *
   * 使用示例：
   *   const file = event.target.files[0]
   *   try {
   *     const result = await pdfApi.upload(file)
   *     log.debug('上传成功:', result.data)
   *   } catch (error) {
   *     console.error('上传失败:', error.message)
   *   }
   */
  upload: (file) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.postFormData('/pdf/upload', formData); // ✅ 使用新的 postFormData 方法
  },

  /**
   * 获取 PDF 列表
   *
   * 作用：
   *   获取当前用户上传的所有 PDF 文件列表
   *
   * 返回值：
   *   @returns {Promise<Object>} {
   *     success: true,
   *     data: [
   *       {
   *         id: string,
   *         name: string,
   *         fileName: string,
   *         filePath: string,
   *         size: number,
   *         createdAt: string,
   *       },
   *       ...
   *     ]
   *   }
   *
   * 使用示例：
   *   const result = await pdfApi.list()
   *   log.debug('PDF 列表:', result.data)
   */
  list: () => apiClient.get('/pdf/list'),

  /**
   * 删除 PDF 文件
   *
   * 作用：
   *   删除指定的 PDF 文件（数据库记录和物理文件）
   *
   * 参数：
   *   @param {string} id - PDF 文件 ID
   *
   * 返回值：
   *   @returns {Promise<Object>} {
   *     success: true,
   *     message: '删除成功'
   *   }
   *
   * 使用示例：
   *   await pdfApi.delete('pdf_123')
   *   log.debug('删除成功')
   */
  delete: (id) => apiClient.delete(`/pdf/${id}`),

  /**
   * 获取 PDF 详情
   *
   * 作用：
   *   获取指定 PDF 文件的详细信息
   *
   * 参数：
   *   @param {string} id - PDF 文件 ID
   *
   * 返回值：
   *   @returns {Promise<Object>} {
   *     success: true,
   *     data: {
   *       id: string,
   *       name: string,
   *       fileName: string,
   *       filePath: string,
   *       size: number,
   *       userId: string,
   *       createdAt: string,
   *       updatedAt: string,
   *     }
   *   }
   *
   * 使用示例：
   *   const result = await pdfApi.get('pdf_123')
   *   log.debug('PDF 详情:', result.data)
   */
  get: (id) => apiClient.get(`/pdf/${id}`),
};
