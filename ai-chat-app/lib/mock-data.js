/**
 * ============================================================================
 * 模拟数据配置 (lib/mock-data.js)
 * ============================================================================
 *
 * 文件作用：
 *   定义应用中使用的模型列表和数据处理工具函数
 *
 * 主要内容：
 *   1. models - 可用的 AI 模型列表配置
 *   2. groupConversationsByTime - 会话时间分组函数
 *   3. 注释掉的示例数据（conversations、messages）
 *
 * 使用场景：
 *   - 模型选择器组件读取 models 数组
 *   - 会话列表按时间分组显示
 *   - 开发阶段参考示例数据结构
 * ============================================================================
 */

/**
 * 会话列表示例数据
 */

/**
 * ----------------------------------------------------------------------------
 * 可用模型列表
 * ----------------------------------------------------------------------------
 *
 * 作用：定义应用支持的所有 AI 模型配置
 *
 * 字段说明：
 * @property {string} id - 模型的唯一标识符（OpenRouter API 使用的模型名称）
 * @property {string} name - 模型的显示名称（用户界面显示）
 * @property {string} provider - 模型提供商（Anthropic/OpenAI/Google）
 * @property {boolean} supportsVision - 是否支持图像理解功能
 * @property {string} icon - 模型图标（Emoji）
 *
 * 调用位置：
 * - components/ModelSelector.js（模型选择下拉菜单）
 * - app/api/chat/route.js（验证模型是否支持图片）
 */
export const models = [
  {
    id: 'anthropic/claude-sonnet-4.5', // OpenRouter API 模型 ID
    name: 'Claude 4.5 Sonnet', // 用户界面显示名称
    provider: 'Anthropic', // 提供商：Anthropic
    supportsVision: true, // 支持图片理解
    icon: '🤖', // 显示图标
  },
  {
    id: 'anthropic/claude-opus-4', // Claude 4 Opus Thinking 模型
    name: 'Claude 4 Opus Thinking',
    provider: 'Anthropic',
    supportsVision: true, // 支持图片理解
    icon: '🧠', // 思考图标
  },
  {
    id: 'anthropic/claude-3.7-sonnet', // Claude 3.7 Sonnet 模型
    name: 'Claude 3.7 Sonnet',
    provider: 'Anthropic',
    supportsVision: true, // 支持图片理解
    icon: '🤖',
  },
  {
    id: 'gpt-4o', // OpenAI GPT-4o 模型
    name: 'GPT-4o',
    provider: 'OpenAI',
    supportsVision: true, // 支持图片理解
    icon: '✨',
  },
  {
    id: 'gpt-4.1-mini', // OpenAI GPT-4.1 mini 模型
    name: 'GPT-4.1 mini',
    provider: 'OpenAI',
    supportsVision: false, // 不支持图片理解
    icon: '⚡',
  },
  {
    id: 'google/gemini-2.5-flash', // Google Gemini 2.5 Flash 模型
    name: 'Gemini 2.5 Flash',
    provider: 'Google',
    supportsVision: true, // 支持图片理解
    icon: '💎',
  },
];

/**
 * ----------------------------------------------------------------------------
 * 按时间分组会话
 * ----------------------------------------------------------------------------
 *
 * 作用：将会话列表按时间分组（今天、昨天、7天内、更早）
 *
 * @param {Array} conversations - 会话列表数组
 * @returns {Object} 分组后的会话对象
 *
 * 返回对象结构：
 * {
 *   '今天': [...],    // 今天的会话
 *   '昨天': [...],    // 昨天的会话
 *   '7天内': [...],   // 7天内的会话
 *   '更早': [...]     // 更早的会话
 * }
 *
 * 使用场景：
 * - 会话列表侧边栏按时间分组显示
 * - 提升用户查找历史会话的效率
 *
 * 调用位置：
 * - components/ConversationList.js（会话列表组件）
 */
export function groupConversationsByTime(conversations) {
  // 初始化四个时间分组
  const groups = {
    今天: [], // 当天的会话
    昨天: [], // 昨天的会话
    '7天内': [], // 7天内的会话
    更早: [], // 更早的会话
  };

  // 遍历所有会话，根据 group 字段分配到对应分组
  conversations.forEach((conv) => {
    const group = conv.group || '更早'; // 默认分组为"更早"
    if (groups[group]) {
      // 如果分组存在
      groups[group].push(conv); // 添加到对应分组
    }
  });

  return groups; // 返回分组后的对象
}

// export const conversations = [
//   {
//     id: '1',
//     title: 'AI 聊天网站开发方案',
//     timestamp: '刚刚',
//     group: '今天',
//     model: 'claude-4.5-sonnet'
//   },
//   {
//     id: '2',
//     title: 'Monica 网站的简化聊天平台',
//     timestamp: '10:30',
//     group: '今天',
//     model: 'gpt-4o'
//   },
//   {
//     id: '3',
//     title: '精简版 Monica 聊天网站功能',
//     timestamp: '昨天',
//     group: '昨天',
//     model: 'claude-3.7-sonnet'
//   },
//   {
//     id: '4',
//     title: '网站聊天功能分析与设计',
//     timestamp: '3天前',
//     group: '7天内',
//     model: 'gpt-4o'
//   },
//   {
//     id: '5',
//     title: 'LangChain 集成 OpenRouter 教程',
//     timestamp: '5天前',
//     group: '7天内',
//     model: 'claude-4.5-sonnet'
//   },
//   {
//     id: '6',
//     title: 'Next.js 16 App Router 最佳实践',
//     timestamp: '10天前',
//     group: '更早',
//     model: 'gpt-4.1-mini'
//   },
//     {
//     id: '7',
//     title: 'AI 聊天网站开发方案',
//     timestamp: '刚刚',
//     group: '今天',
//     model: 'claude-4.5-sonnet'
//   },
//   {
//     id: '8',
//     title: 'Monica 网站的简化聊天平台',
//     timestamp: '10:30',
//     group: '今天',
//     model: 'gpt-4o'
//   },
//   {
//     id: '9',
//     title: '精简版 Monica 聊天网站功能',
//     timestamp: '昨天',
//     group: '昨天',
//     model: 'claude-3.7-sonnet'
//   },
//   {
//     id: '10',
//     title: '网站聊天功能分析与设计',
//     timestamp: '3天前',
//     group: '7天内',
//     model: 'gpt-4o'
//   },
//   {
//     id: '11',
//     title: 'LangChain 集成 OpenRouter 教程',
//     timestamp: '5天前',
//     group: '7天内',
//     model: 'claude-4.5-sonnet'
//   },
//   {
//     id: '12',
//     title: 'Next.js 16 App Router 最佳实践',
//     timestamp: '10天前',
//     group: '更早',
//     model: 'gpt-4.1-mini'
//   }
// ];

// /**
//  * 聊天消息示例数据
//  */
// export const messages = [
//   {
//     id: '1',
//     conversation_id: '1',
//     role: 'user',
//     content: '什么是 LangChain？它有哪些核心功能？',
//     timestamp: '10:30'
//   },
//   {
//     id: '2',
//     conversation_id: '2',
//     role: 'assistant',
//     content: `LangChain 是一个用于开发由语言模型驱动的应用程序的框架。它提供了以下核心功能：

// ## 核心功能

// 1. **链式调用（Chains）**：将多个组件连接起来，形成复杂的工作流
// 2. **记忆管理（Memory）**：保持对话上下文，实现多轮对话
// 3. **代理系统（Agents）**：让 AI 使用工具和执行动作
// 4. **提示模板（Prompt Templates）**：标准化和复用提示词

// ### 示例代码

// \`\`\`python
// from langchain import OpenAI
// from langchain.chains import LLMChain
// from langchain.prompts import PromptTemplate

// # 创建提示模板
// template = "请用简单的语言解释：{concept}"
// prompt = PromptTemplate(template=template, input_variables=["concept"])

// # 创建链
// llm = OpenAI(temperature=0.9)
// chain = LLMChain(llm=llm, prompt=prompt)

// # 执行
// result = chain.run("量子计算")
// print(result)
// \`\`\`

// ### 主要优势

// - ✅ 模块化设计，易于扩展
// - ✅ 支持多种 LLM 提供商
// - ✅ 丰富的工具生态系统
// - ✅ 活跃的社区支持`,
//     model: 'Claude 4.5 Sonnet',
//     timestamp: '10:30',
//     tokensUsed: 450
//   },
//   {
//     id: '3',
//     conversation_id: '3',
//     role: 'user',
//     content: '请分析这张聊天界面截图，说明它的设计特点',
//     images: ['/placeholder-chat.jpg'],
//     timestamp: '10:32'
//   },
//   {
//     id: '4',
//     conversation_id: '4',
//     role: 'assistant',
//     content: `这是一张 AI 聊天界面的截图，展示了现代聊天应用的典型设计特点：

// ## 布局特点

// 1. **两栏布局**
//    - 左侧：会话列表侧边栏（约 280px）
//    - 右侧：聊天消息区域

// 2. **顶部导航栏**
//    - Logo 和品牌标识
//    - 模型选择器（下拉菜单）
//    - 用户头像和设置

// 3. **会话管理**
//    - 按时间分组（今天、昨天、7天内等）
//    - 新建对话按钮突出显示
//    - 搜索功能便于查找历史对话

// ## 设计亮点

// | 特性 | 说明 |
// |------|------|
// | 消息气泡 | 用户消息右对齐（蓝色背景），AI 消息左对齐（白色背景） |
// | 流式输出 | 支持打字机效果，提升用户体验 |
// | 富文本渲染 | 支持 Markdown、代码高亮、数学公式 |
// | 图片上传 | 支持多模态交互 |

// 这种设计遵循了 **简洁、直观、高效** 的原则，参考了 ChatGPT、Claude 等主流 AI 聊天产品的设计语言。`,
//     model: 'GPT-4o',
//     timestamp: '10:32',
//     tokensUsed: 380
//   },
//   {
//     id: '5',
//     conversation_id: '5',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//   {
//     id: '6',
//     conversation_id: '6',
//     role: 'assistant',
//     content: `OpenRouter.ai 是一个统一的 API 网关，可以通过单一接口访问多个大模型提供商。以下是集成步骤：

// ## 1. 获取 API 密钥

// 访问 [OpenRouter.ai](https://openrouter.ai) 注册并获取 API Key。

// ## 2. 使用 LangChain 集成

// \`\`\`javascript
// import { ChatOpenAI } from "@langchain/openai";

// // 配置 OpenRouter
// const model = new ChatOpenAI({
//   modelName: "anthropic/claude-3.5-sonnet",
//   openAIApiKey: process.env.OPENROUTER_API_KEY,
//   configuration: {
//     baseURL: "https://openrouter.ai/api/v1",
//   },
//   temperature: 0.7,
// });

// // 发送消息
// const response = await model.invoke([
//   { role: "user", content: "你好，请介绍一下自己" }
// ]);

// log.debug(response.content);
// \`\`\`

// ## 3. 支持的模型

// - **OpenAI**: GPT-4o, GPT-4 Turbo, GPT-4.1 mini
// - **Anthropic**: Claude 4.5 Sonnet, Claude 4 Opus, Claude 3.7 Sonnet
// - **Google**: Gemini 2.5 Flash, Gemini Pro
// - **Meta**: Llama 3.3 70B

// ## 4. 成本优化

// OpenRouter 会自动选择最优价格的提供商，帮助降低 API 调用成本。

// > 💡 **提示**：建议在环境变量中存储 API 密钥，避免硬编码。`,
//     model: 'Claude 4.5 Sonnet',
//     timestamp: '10:35',
//     tokensUsed: 520
//   },
//     {
//     id: '7',
//     conversation_id: '7',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//     {
//     id: '8',
//     conversation_id: '8',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//     {
//     id: '9',
//     conversation_id: '9',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//     {
//     id: '10',
//     conversation_id: '10',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//     {
//     id: '11',
//     conversation_id: '11',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
//     {
//     id: '12',
//     conversation_id: '12',
//     role: 'user',
//     content: '如何使用 OpenRouter.ai 集成多个大模型？',
//     timestamp: '10:35'
//   },
// ];
