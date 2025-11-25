// ============================================================================
// OpenRouter Embeddings API 测试（多模型）
// ============================================================================

import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const envPath = join(__dirname, '.env.local');

console.log('加载环境变量:', envPath);
dotenv.config({ path: envPath });

const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENAI_BASE_URL = process.env.OPENAI_BASE_URL || 'https://openrouter.ai/api/v1';

console.log('\n环境变量检查:');
console.log('  - OPENAI_API_KEY:', OPENAI_API_KEY ? ` ${OPENAI_API_KEY.slice(0, 15)}...` : '❌ 未配置');
console.log('  - OPENAI_BASE_URL:', OPENAI_BASE_URL);
console.log('');

// ============================================================================
// 测试函数
// ============================================================================
async function testModel(modelName, description) {
  console.log(` 测试: ${description}`);
  console.log(`   模型: ${modelName}`);
  console.log('─────────────────────────────────────────────────────────');
  
  try {
    const response = await fetch(`${OPENAI_BASE_URL}/embeddings`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:3000',
        'X-Title': 'Test App',
      },
      body: JSON.stringify({
        model: modelName,
        input: 'Hello World',
      }),
    });

    const data = await response.json();
    
    if (data.error) {
      console.log('   错误:', data.error.message);
      console.log('  - 错误代码:', data.error.code);
      return false;
    } else if (data.data && data.data[0]?.embedding) {
      console.log('  成功！');
      console.log('  - 维度:', data.data[0].embedding.length);
      console.log('  - 前 3 个值:', data.data[0].embedding.slice(0, 3).map(v => v.toFixed(4)));
      if (data.usage) {
        console.log('  - Token 使用:', data.usage.prompt_tokens);
        console.log('  - 成本:', data.usage.cost ? `$${data.usage.cost}` : '未知');
      }
      return true;
    } else {
      console.log('  响应格式异常');
      return false;
    }
  } catch (error) {
    console.error(' 请求失败:', error.message);
    return false;
  } finally {
    console.log('');
  }
}

async function test() {
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║       OpenRouter Embeddings 可用模型测试                   ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');

  const models = [
    { name: 'openai/text-embedding-3-small', desc: 'openai/text-embedding-3-small' },
    { name: 'openai/text-embedding-3-large', desc: 'OpenAI Large' },
    { name: 'baai/bge-m3', desc: 'baai/bge-m3' },
    { name: 'qwen/qwen3-embedding-8b', desc: 'qwen/qwen3-embedding-8b' },
    { name: 'qwen/qwen3-embedding-4b', desc: 'qwen/qwen3-embedding-4b' },
    
    { name: 'voyage/voyage-2', desc: 'Voyage AI v2 (推荐)' },
    { name: 'voyage/voyage-large-2', desc: 'Voyage AI Large v2' },
    { name: 'qwen/qwen3-embedding-0.6b', desc: 'Qwen 0.6B (免费)' },
  ];

  const results = [];
  
  for (const model of models) {
    const success = await testModel(model.name, model.desc);
    results.push({ model: model.name, success });
    
    // 避免频繁请求
    await new Promise(resolve => setTimeout(resolve, 1000));
  }

  // 总结
  console.log('╔════════════════════════════════════════════════════════════╗');
  console.log('║          测试总结                                          ║');
  console.log('╚════════════════════════════════════════════════════════════╝\n');
  
  const successModels = results.filter(r => r.success);
  const failedModels = results.filter(r => !r.success);
  
  if (successModels.length > 0) {
    console.log('可用模型:');
    successModels.forEach(r => console.log(`   - ${r.model}`));
    console.log('');
    console.log('建议配置 .env.local:');
    console.log(`   OPENAI_EMBEDDING_MODEL=${successModels[0].model}`);
  } else {
    console.log('所有模型均不可用');
    console.log('');
    console.log('可能原因:');
    console.log('   1. API Key 无效或余额不足');
    console.log('   2. OpenRouter 账号未启用 embedding 功能');
    console.log('   3. 需要使用 OpenAI 官方 API 而非 OpenRouter');
  }
  
  if (failedModels.length > 0) {
    console.log('');
    console.log('不可用模型:');
    failedModels.forEach(r => console.log(`   - ${r.model}`));
  }
}

test().catch(error => {
  console.error('\n 测试失败:', error);
  process.exit(1);
});
