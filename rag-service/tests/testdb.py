"""
测试数据库连接和方法
"""
import sys
from pathlib import Path

# ✅ 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid
from datetime import datetime
from app.core.database import get_database
from app.core.config import get_settings

async def test_database():
    """测试数据库方法"""
    print("=" * 80)
    print("开始测试数据库方法")
    print("=" * 80)

    db = get_database()

    # 连接数据库
    print("\n📡 连接数据库...")
    await db.connect()
    print("✅ 数据库连接成功")

    try:
        # ====================================================================
        # 测试 1：fetchval（查询单个值）
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 1：fetchval（查询单个值）")
        print("=" * 80)

        result = await db.fetchval("SELECT 1")
        print(f"✅ fetchval 结果: {result}")
        assert result == 1, "fetchval 测试失败"

        # ====================================================================
        # 测试 2：fetch（查询多行）
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 2：fetch（查询多行）")
        print("=" * 80)

        rows = await db.fetch("SELECT 1 as num, 'test' as text")
        print(f"✅ fetch 结果: {rows}")
        assert len(rows) == 1, "fetch 测试失败"
        assert rows[0]['num'] == 1, "fetch 数据错误"

        # ====================================================================
        # 测试 3：fetchrow（查询单行）
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 3：fetchrow（查询单行）")
        print("=" * 80)

        row = await db.fetchrow("SELECT 1 as num, 'test' as text")
        print(f"✅ fetchrow 结果: {row}")
        assert row['num'] == 1, "fetchrow 测试失败"

        # ====================================================================
        # 测试 4：execute（带位置参数）
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 4：execute（带位置参数）")
        print("=" * 80)

        # 创建临时测试表
        print("创建临时测试表...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS test_users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        print("✅ 测试表创建成功")

        # 插入测试数据（使用位置参数）
        test_id = str(uuid.uuid4())
        test_name = "测试用户"
        test_age = 25

        print(f"\n插入测试数据: id={test_id}, name={test_name}, age={test_age}")
        result = await db.execute(
            """
            INSERT INTO test_users (id, name, age)
            VALUES ($1, $2, $3)
            """,
            test_id,
            test_name,
            test_age
        )
        print(f"✅ 插入结果: {result}")

        # ====================================================================
        # 测试 5：查询刚插入的数据
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 5：查询刚插入的数据")
        print("=" * 80)

        user = await db.fetchrow(
            "SELECT * FROM test_users WHERE id = $1",
            test_id
        )
        print(f"✅ 查询结果: {user}")
        assert user['id'] == test_id, "查询数据不匹配"
        assert user['name'] == test_name, "查询数据不匹配"
        assert user['age'] == test_age, "查询数据不匹配"

        # ====================================================================
        # 测试 6：更新数据
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 6：更新数据")
        print("=" * 80)

        new_age = 30
        result = await db.execute(
            "UPDATE test_users SET age = $1 WHERE id = $2",
            new_age,
            test_id
        )
        print(f"✅ 更新结果: {result}")

        # 验证更新
        user = await db.fetchrow(
            "SELECT age FROM test_users WHERE id = $1",
            test_id
        )
        print(f"✅ 更新后的年龄: {user['age']}")
        assert user['age'] == new_age, "更新失败"

        # ====================================================================
        # 测试 7：模拟 PDF 插入（完整测试）
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 7：模拟 PDF 插入（完整测试）")
        print("=" * 80)

        # 检查 pdfs 表是否存在
        table_exists = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'pdfs'
            )
        """)

        if table_exists:
            print("✅ pdfs 表存在")

            # 模拟 PDF 上传的数据库插入
            pdf_id = str(uuid.uuid4())
            pdf_name = "测试文档.pdf"
            pdf_file_path = f"uploads/{pdf_id}.pdf"
            pdf_size = 1024 * 1024  # 1MB
            pdf_status = "processing"
            user_id = "test_user_123"

            print(f"\n插入 PDF 记录:")
            print(f"  - id: {pdf_id}")
            print(f"  - name: {pdf_name}")
            print(f"  - filePath: {pdf_file_path}")
            print(f"  - size: {pdf_size}")
            print(f"  - status: {pdf_status}")
            print(f"  - userId: {user_id}")

            result = await db.execute(
                """
                INSERT INTO pdfs (
                    id, name, "fileName", "filePath", size, status, "userId", "createdAt", "updatedAt"
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                """,
                pdf_id,
                pdf_name,
                pdf_name,
                pdf_file_path,
                pdf_size,
                pdf_status,
                user_id
            )
            print(f"✅ PDF 插入结果: {result}")

            # 查询验证
            pdf = await db.fetchrow(
                'SELECT * FROM pdfs WHERE id = $1',
                pdf_id
            )
            print(f"✅ 查询到的 PDF: {dict(pdf)}")

            # 清理测试数据
            await db.execute("DELETE FROM pdfs WHERE id = $1", pdf_id)
            print("✅ 测试数据已清理")
        else:
            print("⚠️ pdfs 表不存在，跳过 PDF 插入测试")

        # ====================================================================
        # 测试 8：批量插入
        # ====================================================================
        print("\n" + "=" * 80)
        print("测试 8：批量插入")
        print("=" * 80)

        users_data = [
            (str(uuid.uuid4()), f"用户{i}", 20 + i)
            for i in range(5)
        ]

        print(f"批量插入 {len(users_data)} 条数据...")
        await db.executemany(
            "INSERT INTO test_users (id, name, age) VALUES ($1, $2, $3)",
            users_data
        )
        print("✅ 批量插入成功")

        # 验证
        count = await db.fetchval("SELECT COUNT(*) FROM test_users")
        print(f"✅ 表中共有 {count} 条记录")

        # ====================================================================
        # 清理测试数据
        # ====================================================================
        print("\n" + "=" * 80)
        print("清理测试数据")
        print("=" * 80)

        await db.execute("DROP TABLE IF EXISTS test_users")
        print("✅ 测试表已删除")

        # ====================================================================
        # 测试总结
        # ====================================================================
        print("\n" + "=" * 80)
        print("✅ 所有测试通过！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        # 断开数据库连接
        await db.disconnect()
        print("\n✅ 数据库连接已关闭")


if __name__ == "__main__":
    asyncio.run(test_database())
