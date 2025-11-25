// ============================================================================
// 通用工具函数库
// ============================================================================
// 文件作用：
//   提供项目中常用的工具函数，如 CSS 类名合并、日期格式化等
// ============================================================================

import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

// ----------------------------------------------------------------------------
// cn() - CSS 类名合并工具
// ----------------------------------------------------------------------------
// 作用：
//   智能合并 Tailwind CSS 类名，避免冲突
//
// 使用场景：
//   组件需要接收外部传入的 className，同时保持内部默认样式
//
// 示例：
//   cn("px-4 py-2", "px-6") → "px-6 py-2" (后面的 px-6 覆盖 px-4)
//   cn("text-red-500", condition && "text-blue-500") → 根据条件动态切换颜色
//
// 技术细节：
//   1. clsx: 处理条件类名（如 condition && "class"）
//   2. twMerge: 合并 Tailwind 类名，自动处理冲突（后者覆盖前者）
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// ============================================================================
// 使用示例
// ============================================================================
//
// 【在组件中使用】
// import { cn } from '@/lib/utils'
//
// function Button({ className, variant = 'primary', ...props }) {
//   return (
//     <button
//       className={cn(
//         "px-4 py-2 rounded",              // 基础样式
//         variant === 'primary' && "bg-blue-500 text-white",  // 条件样式
//         variant === 'secondary' && "bg-gray-500 text-white",
//         className                         // 外部传入的样式（优先级最高）
//       )}
//       {...props}
//     />
//   )
// }
//
// 【调用示例】
// <Button className="px-6">提交</Button>
// 最终类名: "px-6 py-2 rounded bg-blue-500 text-white"
// (px-6 覆盖了默认的 px-4)
//
// ============================================================================

// ----------------------------------------------------------------------------
// 未来可扩展的工具函数（示例）
// ----------------------------------------------------------------------------

/**
 * 格式化日期
 * @param {Date|string} date - 日期对象或 ISO 字符串
 * @returns {string} 格式化后的日期字符串
 *
 * 示例:
 *   formatDate(new Date()) → "2025年11月13日"
 */
// export function formatDate(date) {
//   const d = new Date(date)
//   return d.toLocaleDateString('zh-CN', {
//     year: 'numeric',
//     month: 'long',
//     day: 'numeric'
//   })
// }

/**
 * 截断文本
 * @param {string} text - 原始文本
 * @param {number} maxLength - 最大长度
 * @returns {string} 截断后的文本
 *
 * 示例:
 *   truncate("Hello World", 5) → "Hello..."
 */
// export function truncate(text, maxLength) {
//   if (text.length <= maxLength) return text
//   return text.slice(0, maxLength) + '...'
// }

// ============================================================================
