"""
LLM Service 完整测试脚本
端口: 8002
"""
import requests
import json
import time
from typing import Dict, Any

# ==================== 配置 ====================
BASE_URL = "http://localhost:8002"
API_V1 = f"{BASE_URL}/api/v1"
TIMEOUT = 30

# ==================== 颜色输出 ====================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_success(msg):
    print(f"{Colors.GREEN} {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED} {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}  {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}  {msg}{Colors.END}")

def print_header(msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{msg}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")

# ==================== 测试函数 ====================

def test_root():
    """测试根路径"""
    print_header("0. 根路径测试")

    try:
        response = requests.get(BASE_URL, timeout=5)
        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("根路径访问成功")
            print_info(f"服务名称: {data.get('service')}")
            print_info(f"版本: {data.get('version')}")
            print_info(f"环境: {data.get('environment')}")
            print_info(f"状态: {data.get('status')}")
            print_info(f"文档地址: {BASE_URL}{data.get('docs')}")
            return True
        else:
            print_error("根路径访问失败")
            return False
    except requests.exceptions.ConnectionError:
        print_error("无法连接到服务")
        print_warning(f"请确保服务运行在 {BASE_URL}")
        print_info("启动命令: python -m app.main")
        return False
    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_health():
    """测试健康检查"""
    print_header("1. 健康检查")

    try:
        response = requests.get(f"{API_V1}/health", timeout=5)
        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("健康检查通过")
            print_info(f"状态: {data.get('status')}")
            print_info(f"版本: {data.get('version')}")
            print_info(f"环境: {data.get('environment')}")

            providers = data.get('providers', {})
            print_info("可用的提供商:")
            for provider, available in providers.items():
                status = "" if available else ""
                print(f"  {status} {provider}")

            return True
        else:
            print_error("健康检查失败")
            print_error(f"响应: {response.text}")
            return False
    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_liveness():
    """测试存活探针"""
    print_header("2. 存活探针测试")

    try:
        response = requests.get(f"{API_V1}/health/live", timeout=5)
        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("存活探针正常")
            print_info(f"状态: {data.get('status')}")
            return True
        else:
            print_error("存活探针失败")
            return False
    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_readiness():
    """测试就绪探针"""
    print_header("3. 就绪探针测试")

    try:
        response = requests.get(f"{API_V1}/health/ready", timeout=5)
        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print_success("就绪探针正常")
            print_info(f"状态: {data.get('status')}")
            print_info(f"运行时间: {data.get('uptime', 0):.2f}s")
            return True
        else:
            print_error("就绪探针失败")
            return False
    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_simple_generate():
    """测试简单生成（非流式）"""
    print_header("4. 简单生成测试（非流式）")

    data = {
        "messages": [
            {"role": "user", "content": "用一句话介绍自己"}
        ],
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "temperature": 0.7,
        "stream": False
    }

    try:
        print_info("发送请求...")
        start_time = time.time()

        response = requests.post(
            f"{API_V1}/generate",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        duration = time.time() - start_time
        print_info(f"状态码: {response.status_code}")
        print_info(f"响应时间: {duration:.2f}s")

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                print_success("生成成功")

                data_obj = result.get('data', {})
                print_info(f"提供商: {data_obj.get('provider')}")
                print_info(f"模型: {data_obj.get('model')}")

                response_text = data_obj.get('response', '')
                print(f"\n{Colors.CYAN}响应内容:{Colors.END}")
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")
                print(response_text)
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")

                usage = data_obj.get('usage')
                if usage:
                    print_info(f"Token 使用:")
                    print(f"  输入: {usage.get('prompt_tokens')}")
                    print(f"  输出: {usage.get('completion_tokens')}")
                    print(f"  总计: {usage.get('total_tokens')}")

                return True
            else:
                print_error(f"生成失败: {result.get('message')}")
                return False
        else:
            print_error("请求失败")
            print_error(f"响应: {response.text}")
            return False

    except requests.exceptions.Timeout:
        print_error("请求超时")
        return False
    except Exception as e:
        print_error(f"异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_stream_generate():
    """测试流式生成"""
    print_header("5. 流式生成测试")

    data = {
        "messages": [
            {"role": "user", "content": "数到10"}
        ],
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "temperature": 0.7,
        "stream": True
    }

    try:
        print_info("发送流式请求...")
        start_time = time.time()

        response = requests.post(
            f"{API_V1}/generate/stream",
            json=data,
            headers={"Content-Type": "application/json"},
            stream=True,
            timeout=TIMEOUT
        )

        print_info(f"状态码: {response.status_code}")

        if response.status_code != 200:
            print_error("流式请求失败")
            print_error(f"响应: {response.text}")
            return False

        print(f"\n{Colors.CYAN}流式响应:{Colors.END}")
        print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")

        full_response = ""
        chunk_count = 0

        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')

                if line.startswith('data: '):
                    data_str = line[6:]

                    try:
                        chunk_data = json.loads(data_str)

                        if chunk_data['type'] == 'content':
                            content = chunk_data['content']
                            print(content, end='', flush=True)
                            full_response += content
                            chunk_count += 1

                        elif chunk_data['type'] == 'done':
                            duration = time.time() - start_time
                            print(f"\n{Colors.CYAN}{'-' * 70}{Colors.END}")
                            print_success("流式生成完成")
                            print_info(f"响应时间: {duration:.2f}s")
                            print_info(f"总字符数: {len(full_response)}")
                            print_info(f"总块数: {chunk_count}")
                            return True

                        elif chunk_data['type'] == 'error':
                            print_error(f"\n错误: {chunk_data['error']}")
                            return False

                    except json.JSONDecodeError:
                        print_warning(f"\n无法解析: {data_str}")
                        continue

        print_error("流式响应未正常结束")
        return False

    except requests.exceptions.Timeout:
        print_error("请求超时")
        return False
    except Exception as e:
        print_error(f"异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_with_history():
    """测试带历史记录的对话"""
    print_header("6. 多轮对话测试（上下文记忆）")

    data = {
        "messages": [
            {"role": "user", "content": "我叫张三"},
            {"role": "assistant", "content": "你好，张三！很高兴认识你。"},
            {"role": "user", "content": "我叫什么名字？"}
        ],
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "temperature": 0.7,
        "stream": False
    }

    try:
        print_info("发送多轮对话请求...")

        response = requests.post(
            f"{API_V1}/generate",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                print_success("多轮对话成功")

                response_text = result['data']['response']
                print(f"\n{Colors.CYAN}响应内容:{Colors.END}")
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")
                print(response_text)
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")

                # 检查是否记住了名字
                if "张三" in response_text:
                    print_success(" 上下文记忆正常（AI 记住了名字）")
                    return True
                else:
                    print_warning(" 上下文记忆可能有问题（AI 没有提到名字）")
                    return False
            else:
                print_error(f"对话失败: {result.get('message')}")
                return False
        else:
            print_error("请求失败")
            print_error(f"响应: {response.text}")
            return False

    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_different_temperatures():
    """测试不同温度参数"""
    print_header("7. 温度参数测试")

    temperatures = [0.0, 0.5, 1.0]
    results = []

    for temp in temperatures:
        print_info(f"\n测试温度: {temp}")

        data = {
            "messages": [
                {"role": "user", "content": "说一个数字"}
            ],
            "provider": "openrouter",
            "model": "openai/gpt-4o",
            "temperature": temp,
            "stream": False
        }

        try:
            response = requests.post(
                f"{API_V1}/generate",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    response_text = result['data']['response']
                    print_success(f"温度 {temp} 测试通过")
                    print_info(f"响应: {response_text[:50]}...")
                    results.append(True)
                else:
                    print_error(f"温度 {temp} 测试失败")
                    results.append(False)
            else:
                print_error(f"温度 {temp} 请求失败")
                results.append(False)

            time.sleep(1)  # 避免请求过快

        except Exception as e:
            print_error(f"温度 {temp} 异常: {e}")
            results.append(False)

    return all(results)


def test_system_prompt():
    """测试系统提示词"""
    print_header("8. 系统提示词测试")

    data = {
        "messages": [
            {"role": "system", "content": "你是一个只会说'喵'的猫咪助手"},
            {"role": "user", "content": "你好"}
        ],
        "provider": "openrouter",
        "model": "openai/gpt-4o",
        "stream": False
    }

    try:
        print_info("发送带系统提示词的请求...")

        response = requests.post(
            f"{API_V1}/generate",
            json=data,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )

        print_info(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                print_success("系统提示词测试成功")

                response_text = result['data']['response']
                print(f"\n{Colors.CYAN}响应内容:{Colors.END}")
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")
                print(response_text)
                print(f"{Colors.CYAN}{'-' * 70}{Colors.END}")

                return True
            else:
                print_error(f"测试失败: {result.get('message')}")
                return False
        else:
            print_error("请求失败")
            return False

    except Exception as e:
        print_error(f"异常: {e}")
        return False


def test_error_handling():
    """测试错误处理"""
    print_header("9. 错误处理测试")

    test_cases = [
        {
            "name": "空消息列表",
            "data": {
                "messages": [],
                "provider": "openrouter",
                "stream": False
            },
            "expected_status": 422
        },
        {
            "name": "无效角色",
            "data": {
                "messages": [
                    {"role": "invalid_role", "content": "test"}
                ],
                "provider": "openrouter",
                "stream": False
            },
            "expected_status": 422
        },
        {
            "name": "最后消息非用户消息",
            "data": {
                "messages": [
                    {"role": "user", "content": "你好"},
                    {"role": "assistant", "content": "你好！"}
                ],
                "provider": "openrouter",
                "stream": False
            },
            "expected_status": 422
        },
        {
            "name": "无效温度参数",
            "data": {
                "messages": [
                    {"role": "user", "content": "test"}
                ],
                "provider": "openrouter",
                "temperature": 3.0,  # 超出范围
                "stream": False
            },
            "expected_status": 422
        }
    ]

    results = []

    for test_case in test_cases:
        print_info(f"\n测试: {test_case['name']}")

        try:
            response = requests.post(
                f"{API_V1}/generate",
                json=test_case['data'],
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == test_case['expected_status']:
                print_success(f" {test_case['name']} - 错误处理正确")
                results.append(True)
            else:
                print_error(f" {test_case['name']} - 预期状态码 {test_case['expected_status']}，实际 {response.status_code}")
                results.append(False)

        except Exception as e:
            print_error(f" {test_case['name']} - 异常: {e}")
            results.append(False)

    return all(results)


def test_concurrent_requests():
    """测试并发请求"""
    print_header("10. 并发请求测试")

    import concurrent.futures

    def make_request(index):
        data = {
            "messages": [
                {"role": "user", "content": f"说一个字（请求 {index}）"}
            ],
            "provider": "openrouter",
            "model": "openai/gpt-4o",
            "stream": False
        }

        try:
            response = requests.post(
                f"{API_V1}/generate",
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=TIMEOUT
            )
            return response.status_code == 200
        except:
            return False

    print_info("发送 5 个并发请求...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_request, i) for i in range(1, 6)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    success_count = sum(results)
    print_info(f"成功: {success_count}/5")

    if success_count == 5:
        print_success("并发请求测试通过")
        return True
    else:
        print_warning(f"部分请求失败 ({5 - success_count} 个)")
        return False


# ==================== 主函数 ====================

def main():
    """主函数"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}🧪 LLM Service 完整测试套件{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.END}")
    print_info(f"测试地址: {BASE_URL}")
    print_info(f"API 版本: v1")
    print_info(f"超时时间: {TIMEOUT}s")

    # 测试结果字典
    results: Dict[str, bool] = {}

    # 运行所有测试
    tests = [
        ("根路径", test_root),
        ("健康检查", test_health),
        ("存活探针", test_liveness),
        ("就绪探针", test_readiness),
        ("简单生成", test_simple_generate),
        ("流式生成", test_stream_generate),
        ("多轮对话", test_conversation_with_history),
        ("温度参数", test_different_temperatures),
        ("系统提示词", test_system_prompt),
        ("错误处理", test_error_handling),
        ("并发请求", test_concurrent_requests),
    ]

    # 首先检查服务是否运行
    if not test_root():
        print_error("\n 服务未运行或无法访问")
        print_info("请先启动服务:")
        print_info("  cd services/llm-service")
        print_info("  python -m app.main")
        return

    # 运行其他测试
    for test_name, test_func in tests[1:]:
        try:
            results[test_name] = test_func()
            time.sleep(1)  # 测试间隔
        except KeyboardInterrupt:
            print_warning("\n\n 测试被用户中断")
            break
        except Exception as e:
            print_error(f"\n测试 '{test_name}' 发生未预期的错误: {e}")
            results[test_name] = False

    # 显示测试总结
    print_header("📊 测试结果汇总")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        if result:
            print_success(f" {test_name}")
        else:
            print_error(f" {test_name}")

    print(f"\n{Colors.CYAN}{'-' * 70}{Colors.END}")
    print_info(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")

    if passed == total:
        print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 所有测试通过！{Colors.END}\n")
    else:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}  {total - passed} 个测试失败{Colors.END}\n")

    print(f"{Colors.CYAN}{'=' * 70}{Colors.END}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_warning("\n\n 测试被用户中断")
    except Exception as e:
        print_error(f"\n 发生错误: {e}")
        import traceback
        traceback.print_exc()
