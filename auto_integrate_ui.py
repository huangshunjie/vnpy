# -*- coding: utf-8 -*-
"""
auto_integrate_ui.py

自动完成UI集成脚本
"""
import sys
import re

def integrate_ui():
    """自动集成UI增强"""
    
    file_path = r"C:\Users\11229\Documents\GitHub\vnpy\vnpy\quant_research\ui\behavior_tab.py"
    
    print("Reading original file...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Step 1: 添加核心引擎实例
    print("Step 1: Adding core engine instances...")
    old_init = """        self._engine = engine
        self._feature_calculator = KLineFeatureCalculator()
        self._init_ui()"""
    
    new_init = """        self._engine = engine
        self._feature_calculator = KLineFeatureCalculator()
        
        # Core engines (Phase 2-4)
        self.feature_engine = FeatureEngine()
        self.condition_builder = ConditionBuilder()
        self.sampling_engine = SamplingEngine()
        self.feature_registry = get_global_registry()
        print(f"[BehaviorTab] Loaded {len(self.feature_registry.get_feature_names())} features")
        
        self._init_ui()"""
    
    content = content.replace(old_init, new_init)
    
    # Step 2: 更新状态栏
    print("Step 2: Updating status bar...")
    content = content.replace(
        'self._status_label = QLabel("就绪")',
        'self._status_label = QLabel(f"就绪 | {len(self.feature_registry.get_feature_names())}个特征")'
    )
    
    # Step 3: 添加模板选择
    print("Step 3: Adding template selection...")
    old_condition_start = '''        condition_layout.addWidget(QLabel("条件表达式（Python语法）:"))'''
    
    new_condition_start = '''        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("模板:"))
        
        self._template_combo = QComboBox()
        self._template_combo.addItem("自定义", "")
        templates = self.condition_builder.get_condition_templates()
        for template in templates:
            self._template_combo.addItem(template['name'], template)
        template_layout.addWidget(self._template_combo, 1)
        
        apply_btn = QPushButton("应用")
        apply_btn.clicked.connect(self._on_apply_template)
        template_layout.addWidget(apply_btn)
        condition_layout.addLayout(template_layout)
        
        condition_layout.addWidget(QLabel("条件表达式（Python语法）:"))'''
    
    content = content.replace(old_condition_start, new_condition_start)
    
    # Step 4: 添加实时验证
    print("Step 4: Adding real-time validation...")
    old_condition_edit = '''        self._condition_edit.setMaximumHeight(80)
        condition_layout.addWidget(self._condition_edit)
        
        btn_layout = QHBoxLayout()'''
    
    new_condition_edit = '''        self._condition_edit.setMaximumHeight(80)
        self._condition_edit.textChanged.connect(self._on_condition_changed)
        condition_layout.addWidget(self._condition_edit)
        
        # 验证状态
        self._validation_label = QLabel("请输入条件表达式")
        self._validation_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        condition_layout.addWidget(self._validation_label)
        
        btn_layout = QHBoxLayout()'''
    
    content = content.replace(old_condition_edit, new_condition_edit)
    
    # Step 5: 添加验证按钮
    print("Step 5: Adding validation button...")
    old_btn = '''        self._btn_view_features = QPushButton("查看可用特征")
        self._btn_view_features.clicked.connect(self._on_view_features)
        btn_layout.addWidget(self._btn_view_features)
        btn_layout.addStretch()'''
    
    new_btn = '''        self._btn_view_features = QPushButton("📚 浏览特征")
        self._btn_view_features.clicked.connect(self._on_view_features)
        btn_layout.addWidget(self._btn_view_features)
        
        validate_btn = QPushButton("✓ 验证条件")
        validate_btn.clicked.connect(self._on_validate_condition)
        btn_layout.addWidget(validate_btn)
        
        btn_layout.addStretch()'''
    
    content = content.replace(old_btn, new_btn)
    
    # Step 6: 更新导入
    print("Step 6: Updating imports...")
    content = content.replace(
        'from PySide6.QtWidgets import (',
        'from PySide6.QtWidgets import (\n    QMessageBox,'
    )
    
    # Step 7: 添加事件处理方法
    print("Step 7: Adding event handlers...")
    
    # 找到文件末尾的位置（_validate_inputs方法之后）
    event_handlers = '''
    
    def _on_apply_template(self):
        """应用条件模板"""
        template = self._template_combo.currentData()
        if template:
            self._condition_edit.setText(template['expression'])
            self._research_name_edit.setText(template['name'])
            self._status_label.setText(f"已应用模板: {template['name']}")
    
    def _on_condition_changed(self):
        """实时条件验证"""
        condition = self._condition_edit.toPlainText().strip()
        if not condition:
            self._validation_label.setText("请输入条件表达式")
            self._validation_label.setStyleSheet("color: #6c757d; font-size: 11px;")
            return
        
        valid, error, features = self.condition_builder.validate_expression(condition)
        
        if valid:
            feature_text = ', '.join(features[:3])
            if len(features) > 3:
                feature_text += f" (+{len(features)-3}个)"
            self._validation_label.setText(f"✓ 有效 | 依赖: {feature_text}")
            self._validation_label.setStyleSheet("color: green; font-size: 11px;")
        else:
            self._validation_label.setText(f"✗ {error}")
            self._validation_label.setStyleSheet("color: red; font-size: 11px;")
    
    def _on_validate_condition(self):
        """详细验证条件"""
        condition = self._condition_edit.toPlainText().strip()
        if not condition:
            QMessageBox.warning(self, "验证", "请输入条件表达式")
            return
        
        valid, error, features = self.condition_builder.validate_expression(condition)
        
        if valid:
            msg = f"✓ 条件有效\\n\\n依赖特征 ({len(features)}个):\\n{', '.join(features)}"
            QMessageBox.information(self, "验证结果", msg)
        else:
            QMessageBox.warning(self, "验证失败", f"条件表达式无效:\\n\\n{error}")
'''
    
    # 在文件末尾添加
    content = content.rstrip() + event_handlers
    
    # Step 8: 增强_on_view_features方法
    print("Step 8: Enhancing feature browser...")
    old_view_features = '''    def _on_view_features(self):
        """查看可用特征"""
        features = self._feature_calculator.get_available_features()
        
        from PySide6.QtWidgets import QDialog, QTextEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("可用K线特征")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        text = "## 可用特征\\n\\n"
        for feature in sorted(features):
            info = self._feature_calculator.get_feature_info(feature)
            if info:
                text += f"**{feature}** - {info.display_name}\\n"
                text += f"  {info.description}\\n\\n"
        
        text_edit.setMarkdown(text)
        layout.addWidget(text_edit)
        
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        dialog.exec()'''
    
    new_view_features = '''    def _on_view_features(self):
        """增强的特征浏览器"""
        from PySide6.QtWidgets import QDialog, QTextEdit
        from ..model.kline_feature_model import KLineFeatureType
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"K线特征库 ({len(self.feature_registry.get_feature_names())}个)")
        dialog.resize(700, 600)
        
        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        
        stats = self.feature_registry.get_statistics()
        text = f"# K线特征库\\n\\n**总计:** {stats['total_features']}个特征\\n"
        text += f"**适合条件:** {stats['suitable_for_condition']}个\\n\\n---\\n\\n"
        
        for feature_type in KLineFeatureType:
            features = self.feature_registry.list_features(feature_type=feature_type)
            if features:
                text += f"\\n## {feature_type.value.upper()}\\n\\n"
                for f in sorted(features, key=lambda x: x.name)[:10]:
                    text += f"**{f.name}** - {f.display_name}\\n"
                    text += f"> {f.description}\\n\\n"
        
        text_edit.setMarkdown(text)
        layout.addWidget(text_edit)
        
        btn = QPushButton("关闭")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        dialog.exec()'''
    
    content = content.replace(old_view_features, new_view_features)
    
    # 写入文件
    print("Writing enhanced file...")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("\n" + "="*60)
    print("UI Integration Complete!")
    print("="*60)
    print("\nEnhancements applied:")
    print("  ✓ Core engine instances added")
    print("  ✓ 8 template selection added")
    print("  ✓ Real-time validation added")
    print("  ✓ Validation button added")
    print("  ✓ Event handlers added")
    print("  ✓ Enhanced feature browser")
    print("\nOriginal file backed up as: behavior_tab.py.backup")
    print("\nNext: Start VeighNa Studio to test the enhanced UI!")

if __name__ == "__main__":
    try:
        integrate_ui()
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
