import requests
import json

BASE_URL = "http://localhost:8002/api/v1"


def test_search():
    """测试联网搜索"""
    response = requests.post(
        f"{BASE_URL}/search",
        json={
            "query": "2024年诺贝尔物理学奖",
            "model": "openai/gpt-4o-mini",
            "max_results": 5
        }
    )

    print("=== 联网搜索测试 ===")
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"回答: {data['answer'][:200]}...")
    print(f"来源数量: {len(data['sources'])}")
    print(f"Token 使用: {data['tokens_used']}")
    print(f"延迟: {data['latency_ms']}ms")
    print()


def test_search_stream():
    """测试流式搜索"""
    response = requests.post(
        f"{BASE_URL}/search/stream",
        json={
            "query": "什么是深度学习？",
            "model": "openai/gpt-4o-mini",
            "stream": True
        },
        stream=True
    )

    print("=== 流式搜索测试 ===")
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]
                if data != "[DONE]":
                    event = json.loads(data)
                    if event['type'] == 'content':
                        print(event['content'], end='', flush=True)
                    elif event['type'] == 'status':
                        print(f"\n[{event['message']}]")
                    elif event['type'] == 'search_results':
                        print(f"\n[找到 {event['total']} 条搜索结果]")
    print("\n")


if __name__ == "__main__":
    test_search()
    test_search_stream()
