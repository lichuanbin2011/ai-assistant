/**
 * ============================================================================
 * 用户注册 API (app/api/auth/register/route.js)
 * ============================================================================
 *
 * 文件作用：
 *   处理用户注册请求，创建新用户并初始化欢迎会话
 *
 * 主要功能：
 *   1. 验证邮箱和密码格式
 *   2. 检查邮箱是否已注册
 *   3. 加密密码并创建用户
 *   4. 自动创建欢迎会话和消息
 *
 * 路由：POST /api/auth/register
 *
 * 请求体：
 *   {
 *     email: string,      // 邮箱（必填）
 *     password: string,   // 密码（必填，至少6位）
 *     name?: string       // 用户名（可选）
 *   }
 *
 * 响应：
 *   成功：{ success: true, message: '注册成功', data: user }
 *   失败：{ success: false, error: '错误信息' }
 *
 * ============================================================================
 */

import { NextResponse } from 'next/server';
import { prisma } from '@/lib/prisma';
import bcrypt from 'bcryptjs';
import { WELCOME_CONVERSATION } from '@/lib/welcome-message';

/**
 * 用户注册接口
 * POST /api/auth/register
 */
export async function POST(req) {
  try {
    const { email, password, name } = await req.json();

    // 验证必填字段
    if (!email || !password) {
      return NextResponse.json(
        { success: false, error: '邮箱和密码不能为空' },
        { status: 400 }
      );
    }

    // 验证邮箱格式
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      return NextResponse.json(
        { success: false, error: '邮箱格式不正确' },
        { status: 400 }
      );
    }

    // 验证密码长度
    if (password.length < 6) {
      return NextResponse.json(
        { success: false, error: '密码长度至少6位' },
        { status: 400 }
      );
    }

    // 检查邮箱是否已存在
    const existingUser = await prisma.user.findUnique({
      where: { email },
    });

    if (existingUser) {
      return NextResponse.json(
        { success: false, error: '该邮箱已被注册' },
        { status: 409 }
      );
    }

    // 加密密码
    const passwordHash = await bcrypt.hash(password, 10);

    // 创建用户
    const user = await prisma.user.create({
      data: {
        email,
        passwordHash,
        name: name || email.split('@')[0], // 默认用户名为邮箱前缀
        role: 'user',
      },
      select: {
        id: true,
        email: true,
        name: true,
        role: true,
        createdAt: true,
      },
    });

    // 创建默认会话
    const conversation = await prisma.conversation.create({
      data: {
        userId: user.id,
        title: '欢迎使用 AI Chat',
        model: WELCOME_CONVERSATION.assistantMessage.model, // 从常量中获取模型
      },
    });

    // 插入欢迎消息
    await prisma.message.createMany({
      data: [
        {
          conversationId: conversation.id,
          role: WELCOME_CONVERSATION.userMessage.role,
          content: WELCOME_CONVERSATION.userMessage.content,
        },
        {
          conversationId: conversation.id,
          role: WELCOME_CONVERSATION.assistantMessage.role,
          content: WELCOME_CONVERSATION.assistantMessage.content,
        },
      ],
    });

    return NextResponse.json({
      success: true,
      message: '注册成功',
      data: user,
    });
  } catch (error) {
    console.error('注册失败:', error);
    return NextResponse.json(
      { success: false, error: '注册失败，请稍后重试' },
      { status: 500 }
    );
  }
}
