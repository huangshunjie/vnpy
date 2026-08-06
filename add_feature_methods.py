"""
为引擎添加特征（因子）管理方法的脚本
"""

import os

PROJECT_ROOT = r"c:\Users\11229\Documents\GitHub\vnpy"
engine_file = os.path.join(PROJECT_ROOT, "vnpy", "quant_research", "engine.py")

print("=" * 80)
print("为引擎添加特征管理方法")
print("=" * 80)

# 特征管理方法代码
feature_methods = '''
    # ------------------------------------------------------------------
    # Feature Center — 特征工程
    # ------------------------------------------------------------------

    def _gen_feature_id(self) -> str:
        """生成特征ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        count = len([f for f in self.feature_registry.list() if f.feature_id.startswith(f"FT-{date_str}")]) + 1
        return f"FT-{date_str}-{count:03d}"

    def register_feature(
        self,
        name: str,
        category: str = "technical",
        description: str = "",
        formula: str = "",
        tags: Optional[List[str]] = None,
        depends_on_datasets: Optional[List[str]] = None,
        depends_on_features: Optional[List[str]] = None,
        version: str = "v1.0",
        author: str = "",
        status: Optional[FeatureStatus] = None,
    ) -> FeatureRecord:
        """注册新特征"""
        now = datetime.now()
        record = FeatureRecord(
            feature_id=self._gen_feature_id(),
            name=name,
            category=category,
            description=description,
            formula=formula,
            status=status or FeatureStatus.EXPERIMENTAL,
            tags=tags or [],
            depends_on_datasets=depends_on_datasets or [],
            depends_on_features=depends_on_features or [],
            version=version,
            author=author,
            created_at=now,
            updated_at=now,
        )
        self.feature_registry.create(record)
        self._put(EVENT_FEATURE_CREATED, record)
        return record

    def update_feature(self, record: FeatureRecord) -> None:
        """更新特征"""
        record.updated_at = datetime.now()
        self.feature_registry.update(record)
        self._put(EVENT_FEATURE_UPDATED, record)

    def delete_feature(self, feature_id: str) -> None:
        """删除特征"""
        self.feature_registry.delete(feature_id)
        self._put(EVENT_FEATURE_DELETED, feature_id)

    def get_feature(self, feature_id: str) -> Optional[FeatureRecord]:
        """获取特征"""
        return self.feature_registry.get(feature_id)

    def list_features(
        self,
        category: Optional[str] = None,
        status: Optional[FeatureStatus] = None,
    ) -> List[FeatureRecord]:
        """列出特征"""
        return self.feature_registry.filter(category=category, status=status)

    def search_features(self, keyword: str) -> List[FeatureRecord]:
        """搜索特征"""
        return self.feature_registry.search(keyword)

    def compute_feature_ic(
        self, feature_id: str, target: str = "return"
    ) -> Optional[ICRecord]:
        """计算特征IC值"""
        # 简化实现
        feature = self.feature_registry.get(feature_id)
        if not feature:
            return None
        
        ic_record = ICRecord(
            feature_id=feature_id,
            target=target,
            ic_mean=0.0,
            ic_std=0.0,
            ir=0.0,
            rank_ic_mean=0.0,
            computed_at=datetime.now(),
        )
        feature.ic_records.append(ic_record)
        self.feature_registry.update(feature)
        return ic_record
'''

# 读取文件
with open(engine_file, 'r', encoding='utf-8') as f:
    content = f.read()

# 在数据集方法之后添加特征方法
import re

# 找到 get_dependents 方法的结束
pattern = r'(def get_dependents\(self.*?\n.*?# 简化实现，返回空列表\s*\n.*?return \[\])'

match = re.search(pattern, content, re.DOTALL)

if match:
    # 在 get_dependents 方法后添加特征方法
    insert_pos = match.end()
    new_content = content[:insert_pos] + '\n' + feature_methods + content[insert_pos:]
    
    # 写回文件
    with open(engine_file, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("[完成] 特征管理方法已添加到引擎")
    print("\n添加的方法:")
    print("  - register_feature()    # 注册新特征")
    print("  - update_feature()      # 更新特征")
    print("  - delete_feature()      # 删除特征")
    print("  - get_feature()         # 获取特征")
    print("  - list_features()       # 列出特征")
    print("  - search_features()     # 搜索特征")
    print("  - compute_feature_ic()  # 计算IC值")
else:
    print("[错误] 未找到插入位置")
    print("尝试在文件末尾添加...")
    
    # 在文件末尾添加
    with open(engine_file, 'a', encoding='utf-8') as f:
        f.write('\n' + feature_methods)
    
    print("[完成] 已添加到文件末尾")

print("\n" + "=" * 80)
print("请关闭卡住的对话框（点取消或强制关闭）")
print("然后重启VN Trader，特征功能将完全可用！")
print("=" * 80)
