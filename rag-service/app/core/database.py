"""
============================================================================
PostgreSQL 数据库连接模块（databases 版本）
============================================================================

文件位置：
  rag-service/app/core/database.py

文件作用：
  管理 PostgreSQL 数据库连接，提供异步数据库操作接口

主要功能：
  1. 连接管理 - 创建和关闭数据库连接池
  2. CRUD 操作 - 执行增删改查操作
  3. 事务管理 - 支持事务操作
  4. 批量操作 - 支持批量插入/更新
  5. 错误处理 - 统一的错误处理和日志记录

技术栈：
  - databases（异步数据库库）
  - PostgreSQL（数据库）
  - pgvector（向量扩展）

依赖文件：
  - app/core/config.py（配置管理）

数据库要求：
  - PostgreSQL 12+
  - pgvector 扩展（用于向量存储）

使用示例：
    ```python
    from app.core.database import get_database
    
    db = get_database()
    
    # 连接数据库
    await db.connect()
    
    # 查询数据
    rows = await db.fetch("SELECT * FROM users WHERE age > :age", age=18)
    
    # 插入数据
    await db.execute(
        "INSERT INTO users (name, age) VALUES (:name, :age)",
        name="Alice",
        age=25
    )
    
    # 关闭连接
    await db.disconnect()
    ```

============================================================================
"""
from databases import Database  # 异步数据库库
from typing import Optional, List, Dict, Any  # 类型注解
from loguru import logger  # 日志记录器

from app.core.config import get_settings  # 配置管理

# ========== 加载配置 ==========
settings = get_settings()


# ============================================================================
# 数据库管理器类
# ============================================================================

class DatabaseManager:
    """
    数据库连接管理器
    
    功能说明：
      - 管理数据库连接池
      - 提供异步数据库操作接口
      - 支持事务和批量操作
      - 统一的错误处理
    
    连接池原理：
      - 预先创建多个数据库连接
      - 请求时从池中获取连接
      - 使用完毕后归还连接
      - 避免频繁创建/关闭连接的开销
    
    使用示例：
        ```python
        db = DatabaseManager()
        
        # 连接数据库
        await db.connect()
        
        # 查询数据
        rows = await db.fetch("SELECT * FROM users")
        
        # 关闭连接
        await db.disconnect()
        ```
    """

    def __init__(self):
        """
        初始化数据库管理器
        
        功能说明：
          - 初始化数据库实例为 None
          - 初始化连接状态为 False
        
        属性说明：
          - database: Database 实例（databases 库）
          - _connected: 连接状态标志
        """
        self.database: Optional[Database] = None
        # 说明：
        #   - Database 实例（databases 库）
        #   - 初始化为 None，连接时创建
        
        self._connected = False
        # 说明：
        #   - 连接状态标志
        #   - False: 未连接
        #   - True: 已连接

    async def connect(self):
        """
        创建连接池
        
        功能说明：
          - 创建 Database 实例
          - 配置连接池参数
          - 连接数据库
          - 测试连接
          - 检查 pgvector 扩展
        
        连接池参数：
          - min_size: 最小连接数（5）
          - max_size: 最大连接数（从配置读取，默认 10）
        
        连接流程：
          1. 检查是否已连接（避免重复连接）
          2. 创建 Database 实例
          3. 连接数据库
          4. 测试连接（SELECT 1）
          5. 检查 pgvector 扩展
        
        错误处理：
          - 连接失败时记录错误日志
          - 抛出异常（由调用方处理）
        
        使用示例：
            ```python
            db = DatabaseManager()
            await db.connect()
            ```
        """
        # ========== 1. 检查是否已连接 ==========
        if self._connected:
            logger.warning("数据库已连接，跳过重复连接")
            return
        # 说明：
        #   - 避免重复连接
        #   - 如果已连接，直接返回

        try:
            # ========== 2. 记录连接信息 ==========
            logger.info(f"正在连接数据库: {settings.DATABASE_URL.split('@')[1]}")
            # 说明：
            #   - split('@')[1]: 只显示主机和数据库名（隐藏用户名和密码）
            #   - 示例：postgres:5432/ai_chat

            # ========== 3. 创建 Database 实例 ==========
            self.database = Database(
                settings.DATABASE_URL,
                min_size=5,
                max_size=settings.DATABASE_POOL_SIZE,
            )
            # 说明：
            #   - settings.DATABASE_URL: 数据库连接字符串
            #     格式：postgresql://用户名:密码@主机:端口/数据库名
            #   - min_size: 最小连接数（5）
            #     说明：连接池中始终保持的连接数
            #   - max_size: 最大连接数（从配置读取，默认 10）
            #     说明：连接池中最多创建的连接数

            # ========== 4. 连接数据库 ==========
            await self.database.connect()
            # 说明：
            #   - 异步连接数据库
            #   - 创建连接池
            #   - 如果连接失败，抛出异常

            logger.info("数据库连接池创建成功")

            # ========== 5. 测试连接 ==========
            result = await self.database.fetch_val("SELECT 1")
            # 说明：
            #   - 执行简单查询测试连接
            #   - SELECT 1: 返回常量 1
            #   - 如果查询失败，说明连接有问题
            
            logger.info(f"数据库连接测试成功: {result}")

            # ========== 6. 检查 pgvector 扩展 ==========
            has_vector = await self.database.fetch_val(
                "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            # 说明：
            #   - 查询 pg_extension 表
            #   - 检查是否安装了 vector 扩展
            #   - EXISTS: 返回 True/False
            
            if has_vector:
                logger.info(" pgvector 扩展已启用")
            else:
                logger.warning(" pgvector 扩展未启用，向量功能将不可用")
            # 说明：
            #   - pgvector: PostgreSQL 向量扩展
            #   - 用于存储和查询向量数据
            #   - 如果未启用，向量功能将不可用

            # ========== 7. 更新连接状态 ==========
            self._connected = True

        except Exception as e:
            # ========== 错误处理 ==========
            logger.error(f" 数据库连接失败: {e}")
            logger.error(f" 连接字符串: {settings.DATABASE_URL.split('@')[1]}")
            raise
            # 说明：
            #   - 记录错误日志
            #   - 抛出异常（由调用方处理）

    async def disconnect(self):
        """
        关闭连接池
        
        功能说明：
          - 关闭数据库连接池
          - 释放所有连接
          - 更新连接状态
        
        使用场景：
          - 应用关闭时
          - 测试结束时
        
        使用示例：
            ```python
            db = DatabaseManager()
            await db.connect()
            # ... 使用数据库 ...
            await db.disconnect()
            ```
        """
        # ========== 检查连接状态 ==========
        if self.database and self._connected:
            # ========== 关闭连接池 ==========
            await self.database.disconnect()
            # 说明：
            #   - 关闭所有数据库连接
            #   - 释放资源
            
            # ========== 更新连接状态 ==========
            self._connected = False
            
            logger.info(" 数据库连接池已关闭")

    async def execute(self, query: str, **values) -> Any:
        """
        执行 SQL（INSERT/UPDATE/DELETE）
        
        功能说明：
          - 执行写操作（INSERT、UPDATE、DELETE）
          - 支持命名参数
          - 返回影响的行数
        
        参数格式：
          - 使用命名参数：:param
          - 示例：INSERT INTO users (name) VALUES (:name)
        
        Args:
            query: SQL 查询（使用命名参数 :param）
                - 类型：字符串
                - 示例："INSERT INTO users (name, age) VALUES (:name, :age)"
            
            **values: 命名参数
                - 类型：关键字参数
                - 示例：name="Alice", age=25

        Returns:
            影响的行数
            - 类型：整数
            - 示例：1（插入/更新/删除了 1 行）

        Example:
            ```python
            # 插入数据
            await db.execute(
                "INSERT INTO users (name, age) VALUES (:name, :age)",
                name="Alice",
                age=25
            )
            
            # 更新数据
            await db.execute(
                "UPDATE users SET age = :age WHERE name = :name",
                name="Alice",
                age=26
            )
            
            # 删除数据
            await db.execute(
                "DELETE FROM users WHERE name = :name",
                name="Alice"
            )
            ```
        
        错误处理：
          - 记录错误日志（SQL 和参数）
          - 抛出异常（由调用方处理）
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")
        # 说明：
        #   - 如果未连接，抛出异常
        #   - 避免在未连接时执行 SQL

        try:
            # ========== 2. 执行 SQL ==========
            return await self.database.execute(query=query, values=values)
            # 说明：
            #   - query: SQL 查询字符串
            #   - values: 命名参数字典
            #   - 返回影响的行数

        except Exception as e:
            # ========== 3. 错误处理 ==========
            logger.error(f"SQL 执行失败: {e}")
            logger.error(f"SQL: {query}")
            logger.error(f"参数: {values}")
            raise
            # 说明：
            #   - 记录详细的错误信息
            #   - 包括 SQL 和参数
            #   - 抛出异常（由调用方处理）

    async def fetch(self, query: str, **values) -> List[Dict]:
        """
        查询多行
        
        功能说明：
          - 执行 SELECT 查询
          - 返回多行结果
          - 结果为字典列表
        
        Args:
            query: SQL 查询（使用命名参数 :param）
                - 类型：字符串
                - 示例："SELECT * FROM users WHERE age > :age"
            
            **values: 命名参数
                - 类型：关键字参数
                - 示例：age=18

        Returns:
            字典列表
            - 类型：List[Dict]
            - 示例：[{"id": 1, "name": "Alice", "age": 25}, ...]

        Example:
            ```python
            # 查询所有用户
            rows = await db.fetch("SELECT * FROM users")
            
            # 查询年龄大于 18 的用户
            rows = await db.fetch(
                "SELECT * FROM users WHERE age > :age",
                age=18
            )
            
            # 遍历结果
            for row in rows:
                print(row["name"], row["age"])
            ```
        
        错误处理：
          - 记录错误日志（SQL 和参数）
          - 抛出异常（由调用方处理）
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")

        try:
            # ========== 2. 执行查询 ==========
            rows = await self.database.fetch_all(query=query, values=values)
            # 说明：
            #   - fetch_all: 查询所有匹配的行
            #   - 返回 Row 对象列表
            
            # ========== 3. 转换为字典列表 ==========
            return [dict(row) for row in rows]
            # 说明：
            #   - dict(row): 将 Row 对象转换为字典
            #   - 列表推导式：转换所有行

        except Exception as e:
            # ========== 4. 错误处理 ==========
            logger.error(f"SQL 查询失败: {e}")
            logger.error(f"SQL: {query}")
            logger.error(f"参数: {values}")
            raise

    async def fetchrow(self, query: str, **values) -> Optional[Dict]:
        """
        查询单行
        
        功能说明：
          - 执行 SELECT 查询
          - 返回单行结果
          - 结果为字典或 None
        
        Args:
            query: SQL 查询（使用命名参数 :param）
                - 类型：字符串
                - 示例："SELECT * FROM users WHERE id = :id"
            
            **values: 命名参数
                - 类型：关键字参数
                - 示例：id=123

        Returns:
            字典或 None
            - 类型：Optional[Dict]
            - 示例：{"id": 1, "name": "Alice", "age": 25}
            - 如果没有结果，返回 None

        Example:
            ```python
            # 查询单个用户
            row = await db.fetchrow(
                "SELECT * FROM users WHERE id = :id",
                id=123
            )
            
            if row:
                print(row["name"], row["age"])
            else:
                print("用户不存在")
            ```
        
        错误处理：
          - 记录错误日志（SQL 和参数）
          - 抛出异常（由调用方处理）
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")

        try:
            # ========== 2. 执行查询 ==========
            row = await self.database.fetch_one(query=query, values=values)
            # 说明：
            #   - fetch_one: 查询单行
            #   - 如果没有结果，返回 None
            
            # ========== 3. 转换为字典 ==========
            return dict(row) if row else None
            # 说明：
            #   - 如果有结果，转换为字典
            #   - 如果没有结果，返回 None

        except Exception as e:
            # ========== 4. 错误处理 ==========
            logger.error(f"SQL 查询失败: {e}")
            logger.error(f"SQL: {query}")
            logger.error(f"参数: {values}")
            raise

    async def fetchval(self, query: str, **values) -> Any:
        """
        查询单个值
        
        功能说明：
          - 执行 SELECT 查询
          - 返回第一行第一列的值
          - 常用于 COUNT、SUM 等聚合查询
        
        Args:
            query: SQL 查询（使用命名参数 :param）
                - 类型：字符串
                - 示例："SELECT COUNT(*) FROM users WHERE age > :age"
            
            **values: 命名参数
                - 类型：关键字参数
                - 示例：age=18

        Returns:
            单个值
            - 类型：Any（整数、字符串、浮点数等）
            - 示例：42（COUNT 结果）

        Example:
            ```python
            # 统计用户数量
            count = await db.fetchval(
                "SELECT COUNT(*) FROM users WHERE age > :age",
                age=18
            )
            print(f"用户数量: {count}")
            
            # 获取最大年龄
            max_age = await db.fetchval("SELECT MAX(age) FROM users")
            print(f"最大年龄: {max_age}")
            ```
        
        错误处理：
          - 记录错误日志（SQL 和参数）
          - 抛出异常（由调用方处理）
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")

        try:
            # ========== 2. 执行查询 ==========
            return await self.database.fetch_val(query=query, values=values)
            # 说明：
            #   - fetch_val: 查询单个值
            #   - 返回第一行第一列的值

        except Exception as e:
            # ========== 3. 错误处理 ==========
            logger.error(f"SQL 查询失败: {e}")
            logger.error(f"SQL: {query}")
            logger.error(f"参数: {values}")
            raise

    async def transaction(self):
        """
        获取事务上下文
        
        功能说明：
          - 返回事务上下文管理器
          - 支持 async with 语法
          - 自动提交或回滚
        
        事务原理：
          - BEGIN: 开始事务
          - COMMIT: 提交事务（成功）
          - ROLLBACK: 回滚事务（失败）
        
        Returns:
            事务上下文管理器
        
        Usage:
            ```python
            # 使用事务
            async with db.transaction():
                await db.execute("INSERT INTO users ...", name="Alice")
                await db.execute("UPDATE accounts ...", balance=100)
            
            # 如果任何操作失败，所有操作都会回滚
            # 如果所有操作成功，自动提交
            ```
        
        使用场景：
          - 需要保证多个操作的原子性
          - 示例：转账（扣款 + 入账）
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")

        # ========== 2. 返回事务上下文 ==========
        return self.database.transaction()
        # 说明：
        #   - 返回事务上下文管理器
        #   - 支持 async with 语法
        #   - 自动提交或回滚

    async def execute_many(self, query: str, values: List[Dict]) -> None:
        """
        批量执行（用于批量插入）
        
        功能说明：
          - 批量执行 SQL（INSERT/UPDATE/DELETE）
          - 使用事务保证原子性
          - 提高批量操作性能
        
        Args:
            query: SQL 查询（使用命名参数）
                - 类型：字符串
                - 示例："INSERT INTO users (name, age) VALUES (:name, :age)"
            
            values: 参数列表
                - 类型：List[Dict]
                - 示例：[{"name": "Alice", "age": 25}, {"name": "Bob", "age": 30}]

        Returns:
            None

        Example:
            ```python
            # 批量插入用户
            await db.execute_many(
                "INSERT INTO users (name, age) VALUES (:name, :age)",
                [
                    {"name": "Alice", "age": 25},
                    {"name": "Bob", "age": 30},
                    {"name": "Charlie", "age": 35},
                ]
            )
            ```
        
        性能优化：
          - 使用事务（减少提交次数）
          - 批量执行（减少网络往返）
        
        错误处理：
          - 任何一条失败，所有操作都会回滚
          - 记录错误日志
          - 抛出异常
        """
        # ========== 1. 检查连接状态 ==========
        if not self._connected:
            raise RuntimeError("数据库未连接")

        try:
            # ========== 2. 使用事务批量执行 ==========
            async with self.database.transaction():
                # 说明：
                #   - 使用事务保证原子性
                #   - 如果任何一条失败，所有操作都会回滚
                
                for value_dict in values:
                    await self.database.execute(query=query, values=value_dict)
                # 说明：
                #   - 遍历参数列表
                #   - 逐条执行 SQL

            # ========== 3. 记录成功日志 ==========
            logger.debug(f"批量执行成功: {len(values)} 条记录")

        except Exception as e:
            # ========== 4. 错误处理 ==========
            logger.error(f"批量执行失败: {e}")
            raise
            # 说明：
            #   - 记录错误日志
            #   - 抛出异常（由调用方处理）


# ============================================================================
# 工厂函数（单例模式）
# ============================================================================

# 全局数据库实例
_db_instance: Optional[DatabaseManager] = None
# 说明：
#   - 全局变量，存储数据库实例
#   - 初始化为 None
#   - 第一次调用 get_database() 时创建


def get_database() -> DatabaseManager:
    """
    获取数据库实例（单例）
    
    功能说明：
      - 使用单例模式，避免重复创建
      - 第一次调用时创建实例
      - 后续调用返回同一个实例
    
    单例原理：
      - 使用全局变量存储实例
      - 检查是否为 None
      - 如果为 None，创建新实例
      - 如果不为 None，返回已有实例
    
    Returns:
        DatabaseManager: 数据库实例
    
    使用示例：
        ```python
        # 第一次调用，创建实例
        db = get_database()
        
        # 后续调用，返回同一个实例
        db2 = get_database()
        
        # db 和 db2 是同一个对象
        assert db is db2
        ```
    """
    global _db_instance

    if _db_instance is None:
        _db_instance = DatabaseManager()

    return _db_instance


# ============================================================================
# databases 库说明
# ============================================================================
# databases 是一个异步数据库库，支持多种数据库：
#   - PostgreSQL
#   - MySQL
#   - SQLite
#
# 主要特点：
#   1. 异步支持（async/await）
#   2. 连接池管理
#   3. 事务支持
#   4. 简洁的 API
#
# 安装：
#   pip install databases[postgresql]
#
# 文档：
#   https://www.encode.io/databases/

# ============================================================================
# 连接池原理
# ============================================================================
# 连接池是一种资源管理技术：
#
# 1. 预先创建连接
#    - 应用启动时创建多个数据库连接
#    - 避免频繁创建/关闭连接的开销
#
# 2. 连接复用
#    - 请求时从池中获取连接
#    - 使用完毕后归还连接
#    - 连接可以被多个请求复用
#
# 3. 连接数控制
#    - min_size: 最小连接数（始终保持）
#    - max_size: 最大连接数（按需创建）
#
# 4. 性能优势
#    - 减少连接创建/关闭的开销
#    - 提高并发处理能力
#    - 避免数据库连接数过多

# ============================================================================
# 命名参数说明
# ============================================================================
# databases 库使用命名参数（:param）：
#
# 1. 格式
#    - SQL: "SELECT * FROM users WHERE name = :name"
#    - 参数: {"name": "Alice"}
#
# 2. 优点
#    - 可读性好
#    - 避免 SQL 注入
#    - 支持参数复用
#
# 3. 示例
#    ```python
#    await db.execute(
#        "INSERT INTO users (name, age) VALUES (:name, :age)",
#        name="Alice",
#        age=25
#    )
#    ```

# ============================================================================
# 事务说明
# ============================================================================
# 事务（Transaction）是数据库的重要特性：
#
# 1. ACID 特性
#    - Atomicity（原子性）：全部成功或全部失败
#    - Consistency（一致性）：数据保持一致
#    - Isolation（隔离性）：事务之间互不干扰
#    - Durability（持久性）：提交后永久保存
#
# 2. 使用场景
#    - 批量操作（全部成功或全部失败）
#
# 3. 使用方式
#    ```python
#    async with db.transaction():
#        await db.execute("INSERT ...")
#        await db.execute("UPDATE ...")
#    ```

# ============================================================================
# pgvector 扩展说明
# ============================================================================
# pgvector 是 PostgreSQL 的向量扩展：
#
# 1. 功能
#    - 存储向量数据（VECTOR 类型）
#    - 向量相似度搜索
#    - 支持多种距离度量（欧氏距离、余弦相似度等）
#
# 2. 安装
#    ```sql
#    CREATE EXTENSION vector;
#    ```
#
# 3. 使用
#    ```sql
#    CREATE TABLE embeddings (
#        id SERIAL PRIMARY KEY,
#        text TEXT,
#        embedding VECTOR(1024)
#    );
#    
#    SELECT * FROM embeddings
#    ORDER BY embedding <=> '[0.1, 0.2, ...]'
#    LIMIT 5;
#    ```
#
# 4. 文档
#    https://github.com/pgvector/pgvector
