/**
 * ============================================================================
 * 消息内容渲染组件 (app/components/chat/MessageContent.js)
 * ============================================================================
 *
 * 文件作用：
 *   渲染聊天消息内容，支持富文本格式
 *
 * 主要功能：
 *   1. Markdown 渲染（标题、列表、表格、引用等）
 *   2. 代码语法高亮（支持多种编程语言）
 *   3. 数学公式渲染（LaTeX 格式）
 *   4. 代码块复制功能
 *   5. 链接在新标签页打开
 *
 * 组件结构：
 *   MessageContent
 *   └── ReactMarkdown
 *       ├── 普通文本
 *       ├── 代码块 → CodeBlock 组件
 *       │   ├── 语言标签
 *       │   ├── 复制按钮
 *       │   └── 语法高亮代码
 *       ├── 数学公式 → KaTeX 渲染
 *       └── 链接 → 新标签页打开
 *
 * 技术栈：
 *   - react-markdown：Markdown 解析和渲染
 *   - remark-gfm：GitHub Flavored Markdown（表格、删除线等）
 *   - remark-math：数学公式解析
 *   - rehype-katex：数学公式渲染
 *   - react-syntax-highlighter：代码语法高亮
 *   - KaTeX：数学公式样式
 *
 * 支持的 Markdown 语法：
 *   - 标题：# ## ###
 *   - 列表：- * 1.
 *   - 表格：| --- |
 *   - 代码块：```language
 *   - 行内代码：`code`
 *   - 链接：[text](url)
 *   - 图片：![alt](url)
 *   - 引用：>
 *   - 删除线：~~text~~
 *   - 任务列表：- [ ] - [x]
 *   - 数学公式：$ $$ （LaTeX）
 *
 * ============================================================================
 */

'use client';

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import 'katex/dist/katex.min.css';

/**
 * 消息内容渲染组件
 *
 * 功能：
 *   - 将 Markdown 文本渲染为 HTML
 *   - 支持代码语法高亮
 *   - 支持数学公式渲染
 *   - 自定义代码块和链接的渲染方式
 *
 * Props 说明：
 *
 * @param {Object} props - 组件属性
 * @param {string} props.content - 消息内容（Markdown 格式）
 *   示例：
 *     "# 标题\n\n这是一段文本\n\n```javascript\nconsole.log('Hello')\n```"
 *
 * 返回值：
 *   React 组件（渲染后的 HTML）
 *
 * 使用示例：
 *   <MessageContent content="# Hello\n\nThis is **bold** text." />
 */
export default function MessageContent({ content }) {
  return (
    // ======================================================================
    // 外层容器：Markdown 样式容器
    // ======================================================================
    //  markdown-content：自定义类名（可在 globals.css 中定义样式）
    //  prose：Tailwind Typography 插件的基础类
    //    - 提供默认的排版样式（标题、段落、列表等）
    //  prose-sm：小号排版（字体更小，行距更紧凑）
    //  max-w-none：取消最大宽度限制（默认 prose 有最大宽度）
    <div className="markdown-content prose prose-sm max-w-none">
      {/* ==================================================================
          ReactMarkdown 组件：Markdown 解析和渲染
          ================================================================== */}
      {/* 
         ReactMarkdown：
           - 将 Markdown 文本解析为 AST（抽象语法树）
           - 将 AST 渲染为 React 组件
        
         remarkPlugins：Markdown 解析插件（处理 Markdown 语法）
           - remarkGfm：GitHub Flavored Markdown
             - 支持表格：| --- |
             - 支持删除线：~~text~~
             - 支持任务列表：- [ ] - [x]
             - 支持自动链接：https://example.com
           - remarkMath：数学公式解析
             - 支持行内公式：$E=mc^2$
             - 支持块级公式：$$\int_0^1 x^2 dx$$
        
         rehypePlugins：HTML 处理插件（处理渲染后的 HTML）
           - rehypeKatex：数学公式渲染
             - 将 LaTeX 公式渲染为 HTML + CSS
             - 使用 KaTeX 库（比 MathJax 更快）
        
         components：自定义组件渲染
           - code：自定义代码块渲染
           - a：自定义链接渲染
      */}
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={{
          // 代码块渲染
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const codeString = String(children).replace(/\n$/, '');

            return !inline && match ? (
              <CodeBlock language={match[1]} code={codeString} {...props} />
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            );
          },
          // 链接在新标签页打开
          a({ node, children, href, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}

/**
 * 代码块组件 - 带复制功能
 */
function CodeBlock({ language, code }) {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  return (
    <div className="relative group my-4">
      {/* 语言标签和复制按钮 */}
      <div className="flex items-center justify-between bg-gray-800 text-gray-300 px-4 py-2 rounded-t-lg text-xs">
        <span className="font-mono">{language}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-6 px-2 text-gray-300 hover:text-white hover:bg-gray-700"
        >
          {isCopied ? (
            <>
              <Check className="h-3 w-3 mr-1" />
              已复制
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 mr-1" />
              复制代码
            </>
          )}
        </Button>
      </div>

      {/* 代码内容 */}
      <SyntaxHighlighter
        language={language}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0,
          borderBottomLeftRadius: '0.5rem',
          borderBottomRightRadius: '0.5rem',
        }}
        showLineNumbers
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
