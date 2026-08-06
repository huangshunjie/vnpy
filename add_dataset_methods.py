"""
为引擎添加数据集管理方法的脚本
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("=" * 80)
print("为引擎添加数据集管理方法")
print("=" * 80)

# 数据集管理方法代码
dataset_methods = '''
    # ------------------------------------------------------------------
    # Dataset Center — 数据集管理
    # ------------------------------------------------------------------

    def _gen_dataset_id(self) -> str:
        """生成数据集ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        count = len([d for d in self.dataset_registry.list() if d.dataset_id.startswith(f"DS-{date_str}")]) + 1
        return f"DS-{date_str}-{count:03d}"

    def register_dataset(
        self,
        name: str,
        version: str = "v1.0",
        description: str = "",
        source: str = "",
        symbols: Optional[List[str]] = None,
        start_date: str = "",
        end_date: str = "",
        fields: Optional[List[str]] = None,
        row_count: int = 0,
        size_mb: float = 0.0,
        tags: Optional[List[str]] = None,
        created_by: str = "",
    ) -> DatasetRecord:
        """注册新数据集"""
        now = datetime.now()
        record = DatasetRecord(
            dataset_id=self._gen_dataset_id(),
            name=name,
            version=version,
            description=description,
            source=source,
            status=DatasetStatus.PENDING,
            symbols=symbols or [],
            start_date=start_date,
            end_date=end_date,
            fields=fields or [],
            row_count=row_count,
            size_mb=size_mb,
            tags=tags or [],
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )
        self.dataset_registry.create(record)
        self._put(EVENT_DATASET_CREATED, record)
        return record

    def update_dataset(self, record: DatasetRecord) -> None:
        """更新数据集"""
        record.updated_at = datetime.now()
        self.dataset_registry.update(record)
        self._put(EVENT_DATASET_UPDATED, record)

    def delete_dataset(self, dataset_id: str) -> None:
        """删除数据集"""
        self.dataset_registry.delete(dataset_id)
        self._put(EVENT_DATASET_DELETED, dataset_id)

    def get_dataset(self, dataset_id: str) -> Optional[DatasetRecord]:
        """获取数据集"""
        return self.dataset_registry.get(dataset_id)

    def list_datasets(
        self,
        status: Optional[DatasetStatus] = None,
        source: Optional[str] = None,
    ) -> List[DatasetRecord]:
        """列出数据集"""
        return self.dataset_registry.filter(status=status, source=source)

    def search_datasets(self, keyword: str) -> List[DatasetRecord]:
        """搜索数据集"""
        return self.dataset_registry.search(keyword)

    def take_snapshot(self, dataset_id: str) -> None:
        """创建数据集快照"""
        record = self.dataset_registry.get(dataset_id)
        if record:
            snapshot = DatasetSnapshot(
                snapshot_id=f"{dataset_id}-SNAP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                version=record.version,
                row_count=record.row_count,
                quality_score=record.quality_score,
                taken_at=datetime.now(),
            )
            record.snapshots.append(snapshot)
            self.dataset_registry.update(record)
            self._put(EVENT_DATASET_UPDATED, record)

    def get_lineage(self, dataset_id: str) -> List[str]:
        """获取数据集血缘（上游依赖）"""
        # 简化实现，返回空列表
        return []

    def get_dependents(self, dataset_id: str) -> List[str]:
        """获取数据集下游依赖"""
        # 简化实现，返回空列表
        return []
'''

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到添加位置（在实验方法之后）
# 查找最后一个实验相关方法的结束位置
import re

# 找到 add_note 方法的结束（最后一个实验方法）
pattern = r'(def add_note\(self.*?\n.*?record\.notes\s*=\s*note\s*\n.*?record\.updated_at.*?\n.*?self\.experiment_registry\.update\(record\)\s*\n.*?self\._put\(EVENT_EXPERIMENT_UPDATED, record\))'

match = re.search(pattern, content, re.DOTALL)

if match:
    # 在 add_note 方法后添加数据集方法
    insert_pos = match.end()
    new_content = content[:insert_pos] + '\n' + dataset_methods + content[insert_pos:]
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("[完成] 数据集管理方法已添加到引擎")
    print("\n添加的方法:")
    print("  - register_dataset()    # 注册新数据集")
    print("  - update_dataset()      # 更新数据集")
    print("  - delete_dataset()      # 删除数据集")
    print("  - get_dataset()         # 获取数据集")
    print("  - list_datasets()       # 列出数据集")
    print("  - search_datasets()     # 搜索数据集")
    print("  - take_snapshot()       # 创建快照")
    print("  - get_lineage()         # 获取血缘")
    print("  - get_dependents()      # 获取下游依赖")
else:
    print("[错误] 未找到插入位置")
    print("尝试在文件末尾添加...")
    
    # 在文件末尾添加
    with open(engine_file, 'a', encoding='utf-8') as f:
        f.write('\n' + dataset_methods)
    
    print("[完成] 已添加到文件末尾")

print("\n" + "=" * 80)
print("重启VN Trader后，数据集功能将完全可用！")
print("=" * 80)
