/**
 * ============================================================================
 * 简单日志包装器 (lib/log.js)
 * ============================================================================
 */

const IS_PRODUCTION = process.env.NODE_ENV === 'production';
const LOG_LEVEL = process.env.LOG_LEVEL || 'info';

// 简单的日志级别映射
const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

const currentLevel = LOG_LEVELS[LOG_LEVEL] || 1;

// 创建日志函数
const log = {
  debug: (...args) => {
    if (currentLevel <= LOG_LEVELS.debug && !IS_PRODUCTION) {
      console.log('🔍 [DEBUG]', ...args);
    }
  },
  info: (...args) => {
    if (currentLevel <= LOG_LEVELS.info) {
      console.log('ℹ️ [INFO]', ...args);
    }
  },
  warn: (...args) => {
    if (currentLevel <= LOG_LEVELS.warn) {
      console.warn('⚠️ [WARN]', ...args);
    }
  },
  error: (...args) => {
    console.error('❌ [ERROR]', ...args);
  },
  // 保持原有的 console.log 行为（用于快速替换）
  log: (...args) => {
    if (!IS_PRODUCTION) {
      console.log(...args);
    }
  },
};

export default log;
