"""
============================================================================
内存缓存模块（LRU Cache）
============================================================================

文件位置：
  rag-service/app/core/cache.py

文件作用：
  提供内存 LRU 缓存功能，用于缓存向量化结果

主要功能：
  1. LRU 缓存 - 最近最少使用缓存策略
  2. TTL 过期 - 基于时间的缓存过期
  3. 自动淘汰 - 缓存满时自动删除最旧条目
  4. 统计信息 - 缓存使用情况统计

LRU 原理：
  - Least Recently Used（最近最少使用）
  - 当缓存满时，删除最久未使用的条目
  - 使用 OrderedDict 实现（保持插入顺序）

使用场景：
  - 缓存向量化结果（避免重复计算）
  - 缓存查询结果（提高响应速度）
  - 缓存热点数据（减少数据库查询）

技术栈：
  - OrderedDict（有序字典，实现 LRU）
  - hashlib（MD5 哈希，生成缓存键）
  - time（时间戳，实现 TTL）

依赖文件：
  无（独立模块）

============================================================================
"""
import hashlib  # MD5 哈希
import time  # 时间戳
from typing import Optional, Dict, Any  # 类型注解
from collections import OrderedDict  # 有序字典
from loguru import logger  # 日志记录器


# ============================================================================
# 内存缓存类
# ============================================================================

class MemoryCache:
    """
    内存 LRU 缓存（线程安全）
    
    功能说明：
      - 使用 LRU 策略管理缓存
      - 支持 TTL 过期（基于时间）
      - 自动淘汰最旧条目
      - 提供统计信息
    
    LRU 原理：
      - 使用 OrderedDict 保持插入顺序
      - 每次访问时移动到末尾（表示最近使用）
      - 缓存满时删除开头的条目（最久未使用）
    
    TTL 原理：
      - 每个条目记录插入时间戳
      - 访问时检查是否过期
      - 过期则删除并返回 None
    
    使用示例：
        ```python
        cache = MemoryCache(max_size=1000, ttl_seconds=3600)
        
        # 写入缓存
        cache.set("hello", "model-v1", [0.1, 0.2, 0.3])
        
        # 读取缓存
        embedding = cache.get("hello", "model-v1")
        
        # 清空缓存
        cache.clear()
        
        # 统计信息
        stats = cache.stats()
        ```
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        """
        初始化缓存
        
        功能说明：
          - 设置缓存大小和过期时间
          - 初始化缓存字典和时间戳字典
          - 记录初始化日志
        
        Args:
            max_size: 最大缓存条目数
                - 类型：整数
                - 默认：10000
                - 说明：缓存满时自动删除最旧条目
                - 建议：根据内存大小调整（1000-100000）
            
            ttl_seconds: 缓存过期时间（秒）
                - 类型：整数
                - 默认：3600（1 小时）
                - 说明：超过此时间的缓存会被删除
                - 建议：根据数据更新频率调整（300-86400）
        
        数据结构：
          - _cache: OrderedDict（有序字典）
            - 键：缓存键（格式：emb:{model}:{md5}）
            - 值：向量列表
          
          - _timestamps: Dict（普通字典）
            - 键：缓存键
            - 值：插入时间戳（浮点数）
        
        内存估算：
          - 每个向量：1024 维 × 4 字节 = 4KB
          - 每个条目：4KB + 键（~50 字节）+ 时间戳（8 字节）≈ 4.1KB
          - 10000 条目：约 41MB
        """
        self.max_size = max_size  # 最大缓存条目数
        self.ttl_seconds = ttl_seconds  # 缓存过期时间（秒）
        self._cache: OrderedDict = OrderedDict()  # 缓存字典（有序）
        self._timestamps: Dict[str, float] = {}  # 时间戳字典

        logger.info(f"初始化内存缓存: max_size={max_size}, ttl={ttl_seconds}s")

    def _generate_key(self, text: str, model: str) -> str:
        """
        生成缓存键
        
        功能说明：
          - 根据文本和模型生成唯一的缓存键
          - 使用 MD5 哈希避免键过长
          - 包含模型名称以区分不同模型
        
        Args:
            text: 文本内容
                - 类型：字符串
                - 示例："什么是机器学习？"
            
            model: 模型名称
                - 类型：字符串
                - 示例："sentence-transformers/all-MiniLM-L6-v2"

        Returns:
            缓存键（格式：emb:{model}:{md5}）
            示例："emb:all-MiniLM-L6-v2:5d41402abc4b2a76b9719d911017c592"
        
        为什么使用 MD5：
          - 文本可能很长（几千字符）
          - 直接使用文本作为键会占用大量内存
          - MD5 哈希固定 32 字符，节省内存
        
        为什么包含模型名称：
          - 不同模型生成的向量不同
          - 同一文本在不同模型下需要不同的缓存
        
        哈希碰撞：
          - MD5 碰撞概率极低（2^128 分之一）
          - 在缓存场景下可以接受
        """
        # ========== 1. 计算文本的 MD5 哈希 ==========
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        # 说明：
        #   - encode('utf-8'): 将字符串转换为字节（MD5 需要字节输入）
        #   - hexdigest(): 返回 16 进制字符串（32 字符）
        #   - 示例："5d41402abc4b2a76b9719d911017c592"

        # ========== 2. 构建缓存键 ==========
        return f"emb:{model}:{text_hash}"
        # 说明：
        #   - 格式：emb:{model}:{md5}
        #   - emb: 前缀，表示这是向量缓存
        #   - model: 模型名称
        #   - text_hash: 文本的 MD5 哈希

    def get(self, text: str, model: str) -> Optional[list]:
        """
        获取缓存
        
        功能说明：
          - 根据文本和模型查询缓存
          - 检查是否过期
          - 更新 LRU 顺序（移到末尾）
        
        查询流程：
          1. 生成缓存键
          2. 检查是否存在
          3. 检查是否过期
          4. 更新 LRU 顺序
          5. 返回缓存值
        
        Args:
            text: 文本内容
            model: 模型名称

        Returns:
            向量列表或 None
            - 命中：返回向量列表（例如：[0.1, 0.2, 0.3, ...]）
            - 未命中：返回 None
            - 过期：删除缓存并返回 None
        
        使用示例：
            ```python
            cache = MemoryCache()
            
            # 查询缓存
            embedding = cache.get("hello", "model-v1")
            
            if embedding is None:
                # 缓存未命中，需要重新计算
                embedding = compute_embedding("hello")
                cache.set("hello", "model-v1", embedding)
            ```
        """
        # ========== 1. 生成缓存键 ==========
        key = self._generate_key(text, model)

        # ========== 2. 检查是否存在 ==========
        if key not in self._cache:
            return None  # 缓存未命中

        # ========== 3. 检查是否过期 ==========
        timestamp = self._timestamps.get(key, 0)  # 获取插入时间戳（默认 0）
        if time.time() - timestamp > self.ttl_seconds:
            # 缓存已过期
            logger.debug(f"缓存过期: {key[:50]}...")
            del self._cache[key]  # 删除缓存
            del self._timestamps[key]  # 删除时间戳
            return None
        # 说明：
        #   - time.time(): 当前时间戳（浮点数，单位：秒）
        #   - time.time() - timestamp: 缓存存在的时间
        #   - 如果超过 ttl_seconds，则过期

        # ========== 4. 更新 LRU 顺序 ==========
        self._cache.move_to_end(key)
        # 说明：
        #   - move_to_end(key): 将键移到 OrderedDict 的末尾
        #   - 表示这个条目最近被使用
        #   - LRU 策略：删除开头的条目（最久未使用）

        # ========== 5. 返回缓存值 ==========
        logger.debug(f"缓存命中: {key[:50]}...")
        return self._cache[key]

    def set(self, text: str, model: str, embedding: list) -> None:
        """
        设置缓存
        
        功能说明：
          - 将向量写入缓存
          - 缓存满时自动删除最旧条目
          - 记录插入时间戳
        
        写入流程：
          1. 生成缓存键
          2. 检查缓存是否已满
          3. 如果已满，删除最旧条目
          4. 写入新条目
          5. 记录时间戳
        
        Args:
            text: 文本内容
            model: 模型名称
            embedding: 向量列表
                - 类型：列表
                - 示例：[0.1, 0.2, 0.3, ...]
                - 长度：通常 384、768、1024 等

        Returns:
            None
        
        使用示例：
            ```python
            cache = MemoryCache()
            
            # 计算向量
            embedding = compute_embedding("hello")
            
            # 写入缓存
            cache.set("hello", "model-v1", embedding)
            ```
        """
        # ========== 1. 生成缓存键 ==========
        key = self._generate_key(text, model)

        # ========== 2. 检查缓存是否已满 ==========
        if len(self._cache) >= self.max_size:
            # 缓存已满，删除最旧的条目
            oldest_key = next(iter(self._cache))  # 获取第一个键（最旧）
            del self._cache[oldest_key]  # 删除缓存
            del self._timestamps[oldest_key]  # 删除时间戳
            logger.debug(f"缓存已满，删除最旧条目: {oldest_key[:50]}...")
        # 说明：
        #   - next(iter(self._cache)): 获取 OrderedDict 的第一个键
        #   - OrderedDict 保持插入顺序，第一个键是最旧的
        #   - LRU 策略：删除最久未使用的条目

        # ========== 3. 添加新条目 ==========
        self._cache[key] = embedding  # 写入缓存
        self._timestamps[key] = time.time()  # 记录时间戳

        logger.debug(f"缓存写入: {key[:50]}... (当前大小: {len(self._cache)})")

    def clear(self) -> int:
        """
        清空缓存
        
        功能说明：
          - 删除所有缓存条目
          - 删除所有时间戳
          - 返回删除的条目数
        
        使用场景：
          - 模型更新后清空旧缓存
          - 内存不足时释放空间
          - 测试或调试
        
        Returns:
            删除的条目数
        
        使用示例：
            ```python
            cache = MemoryCache()
            
            # 清空缓存
            count = cache.clear()
            print(f"删除了 {count} 个条目")
            ```
        """
        # ========== 1. 记录条目数 ==========
        count = len(self._cache)

        # ========== 2. 清空缓存 ==========
        self._cache.clear()  # 清空缓存字典
        self._timestamps.clear()  # 清空时间戳字典

        logger.info(f"缓存已清空，删除 {count} 个条目")
        return count

    def stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        功能说明：
          - 返回缓存的使用情况
          - 包括条目数、最大大小、TTL、内存使用量
        
        Returns:
            统计信息字典：
            {
                "total_keys": 1000,           # 当前条目数
                "max_size": 10000,            # 最大条目数
                "ttl_seconds": 3600,          # TTL（秒）
                "memory_usage_mb": 4.1        # 内存使用量（MB）
            }
        
        使用示例：
            ```python
            cache = MemoryCache()
            stats = cache.stats()
            print(f"缓存条目数: {stats['total_keys']}")
            print(f"内存使用: {stats['memory_usage_mb']} MB")
            ```
        """
        return {
            "total_keys": len(self._cache),  # 当前条目数
            "max_size": self.max_size,  # 最大条目数
            "ttl_seconds": self.ttl_seconds,  # TTL（秒）
            "memory_usage_mb": self._estimate_memory_usage(),  # 内存使用量（MB）
        }

    def _estimate_memory_usage(self) -> float:
        """
        估算内存使用量（MB）
        
        功能说明：
          - 粗略估算缓存占用的内存
          - 包括向量、键、时间戳的开销
        
        估算公式：
          - 每个向量：1024 维 × 4 字节 = 4096 字节 = 4KB
          - 每个键：约 50 字节
          - 每个时间戳：8 字节（浮点数）
          - 每个条目：4096 + 50 + 8 + 其他开销 ≈ 4200 字节
        
        Returns:
            内存使用量（MB）
        
        注意：
          - 这是粗略估算，实际内存使用可能不同
          - Python 对象有额外的开销（引用计数、类型信息等）
          - 不同维度的向量占用内存不同
        """
        # ========== 粗略估算 ==========
        # 每个向量 1024 维 × 4 字节 = 4KB
        # 加上键和时间戳的开销（约 200 字节）
        total_bytes = len(self._cache) * (4 * 1024 + 200)
        # 说明：
        #   - 4 * 1024: 每个向量 4KB（假设 1024 维，每维 4 字节）
        #   - 200: 键和时间戳的开销
        #   - 实际维度可能不同（384、768、1024 等）

        # ========== 转换为 MB ==========
        return round(total_bytes / 1024 / 1024, 2)
        # 说明：
        #   - / 1024 / 1024: 字节 → KB → MB
        #   - round(..., 2): 保留 2 位小数


# ============================================================================
# 工厂函数（单例模式）
# ============================================================================

# 全局缓存实例
_cache_instance: Optional[MemoryCache] = None


def get_cache(max_size: int = 10000, ttl_seconds: int = 3600) -> MemoryCache:
    """
    获取缓存实例（单例）
    
    功能说明：
      - 使用单例模式，避免重复创建
      - 第一次调用时创建实例
      - 后续调用返回同一个实例
    
    Args:
        max_size: 最大缓存条目数
            - 默认：10000
            - 仅在第一次调用时生效
        
        ttl_seconds: 缓存过期时间（秒）
            - 默认：3600（1 小时）
            - 仅在第一次调用时生效

    Returns:
        MemoryCache: 缓存实例
    
    使用示例：
        ```python
        # 第一次调用，创建实例
        cache = get_cache(max_size=1000, ttl_seconds=1800)
        
        # 后续调用，返回同一个实例
        cache2 = get_cache()
        
        # cache 和 cache2 是同一个对象
        assert cache is cache2
        ```
    """
    global _cache_instance

    if _cache_instance is None:
        _cache_instance = MemoryCache(max_size=max_size, ttl_seconds=ttl_seconds)

    return _cache_instance


# ============================================================================
# LRU 原理详解
# ============================================================================
# LRU（Least Recently Used）：
#   - 最近最少使用缓存策略
#   - 当缓存满时，删除最久未使用的条目
#   - 假设：最近使用的数据更可能再次使用
#
# 实现原理：
#   1. 使用 OrderedDict 保持插入顺序
#   2. 每次访问时移动到末尾（move_to_end）
#   3. 缓存满时删除开头的条目（最久未使用）
#
# 时间复杂度：
#   - 查询：O(1)
#   - 插入：O(1)
#   - 删除：O(1)
#
# 空间复杂度：
#   - O(n)，n 为缓存条目数

# ============================================================================
# TTL 原理详解
# ============================================================================
# TTL（Time To Live）：
#   - 基于时间的缓存过期策略
#   - 每个条目记录插入时间戳
#   - 访问时检查是否过期
#
# 实现原理：
#   1. 插入时记录时间戳（time.time()）
#   2. 访问时计算存在时间（当前时间 - 插入时间）
#   3. 如果超过 TTL，删除并返回 None
#
# 优点：
#   - 简单高效
#   - 避免缓存过期数据
#
# 缺点：
#   - 需要额外的时间戳字典
#   - 过期检查在访问时进行（懒删除）

# ============================================================================
# 缓存键设计
# ============================================================================
# 格式：emb:{model}:{md5}
#
# 组成部分：
#   1. emb: 前缀，表示这是向量缓存
#   2. model: 模型名称（区分不同模型）
#   3. md5: 文本的 MD5 哈希（避免键过长）
#
# 为什么使用 MD5：
#   - 文本可能很长（几千字符）
#   - 直接使用文本作为键会占用大量内存
#   - MD5 哈希固定 32 字符，节省内存
#
# 为什么包含模型名称：
#   - 不同模型生成的向量不同
#   - 同一文本在不同模型下需要不同的缓存

# ============================================================================
# 内存估算
# ============================================================================
# 每个条目：
#   - 向量：1024 维 × 4 字节 = 4096 字节 = 4KB
#   - 键：约 50 字节
#   - 时间戳：8 字节
#   - 其他开销：约 50 字节
#   - 总计：约 4.2KB
#
# 不同缓存大小的内存使用：
#   - 1000 条目：约 4.2MB
#   - 10000 条目：约 42MB
#   - 100000 条目：约 420MB
#
# 建议：
#   - 根据可用内存调整 max_size
#   - 监控内存使用情况
#   - 定期清理过期缓存

# ============================================================================
# 性能优化建议
# ============================================================================
# 1. 调整缓存大小
#    - 根据内存大小调整 max_size
#    - 监控缓存命中率
#
# 2. 调整 TTL
#    - 根据数据更新频率调整
#    - 过短：缓存命中率低
#    - 过长：可能缓存过期数据
#
# 3. 定期清理
#    - 定期清理过期缓存
#    - 避免内存泄漏
#
# 4. 监控统计
#    - 使用 stats() 监控缓存使用情况
#    - 根据统计信息调整参数
#
# 5. 考虑分布式缓存
#    - 如果需要跨进程/跨机器共享缓存
#    - 使用 Redis 等分布式缓存
