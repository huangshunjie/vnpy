"""
quant_research/ui/backtest_dialogs.py

BacktestSubmitDialog      — 提交回测对话框
BacktestCompleteDialog    — 填入回测结果对话框
"""
from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QDoubleSpinBox, QSpinBox,
    QComboBox,
)
from PySide6.QtCore import Qt

from ..model.backtest_model import BacktestRecord


class BacktestSubmitDialog(QDialog):
    """提交 / 编辑回测对话框。"""

    def __init__(self, parent=None, record: Optional[BacktestRecord] = None, engine=None):
        super().__init__(parent)
        self._record  = record
        self._editing = record is not None
        self._engine  = engine
        self.setWindowTitle("编辑回测" if self._editing else "提交回测")
        self.setMinimumWidth(540)
        self._init_ui()
        if self._editing:
            self._load_record()

    def _init_ui(self):
        root = QVBoxLayout(self)

        # ── 基本信息 ──────────────────────────────────────────────────
        info_grp = QGroupBox("基本信息")
        form = QFormLayout(info_grp)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("回测名称（必填）")
        form.addRow("名称 *", self._name_edit)

        self._strategy_combo = QComboBox()
        self._strategy_combo.setEditable(True)
        self._strategy_combo.addItem("（不关联策略）", "")
        # 从engine获取已注册策略列表
        if self._engine:
            try:
                strategies = self._engine.list_strategies()
                for s in strategies:
                    self._strategy_combo.addItem(
                        f"{s.strategy_id}  {s.name}", s.strategy_id)
            except Exception:
                pass
        self._strategy_combo.currentIndexChanged.connect(self._on_strategy_changed)
        form.addRow("策略 ID", self._strategy_combo)

        self._strategy_name_edit = QLineEdit()
        self._strategy_name_edit.setPlaceholderText("策略名称（选择策略后自动填充）")
        form.addRow("策略名称", self._strategy_name_edit)

        self._universe_edit = QLineEdit()
        self._universe_edit.setPlaceholderText("如 HS300 / 全A / 期货主力")
        form.addRow("标的池", self._universe_edit)

        self._author_edit = QLineEdit()
        self._author_edit.setPlaceholderText("提交人")
        form.addRow("提交人", self._author_edit)

        self._desc_edit = QPlainTextEdit()
        self._desc_edit.setPlaceholderText("回测说明")
        self._desc_edit.setFixedHeight(52)
        form.addRow("描述", self._desc_edit)

        root.addWidget(info_grp)

        # ── 回测参数 ──────────────────────────────────────────────────
        param_grp = QGroupBox("回测参数")
        pf = QFormLayout(param_grp)

        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText("YYYY-MM-DD")
        pf.addRow("开始日期", self._start_edit)

        self._end_edit = QLineEdit()
        self._end_edit.setPlaceholderText("YYYY-MM-DD")
        pf.addRow("结束日期", self._end_edit)

        self._capital_spin = QDoubleSpinBox()
        self._capital_spin.setRange(10000, 1e12)
        self._capital_spin.setValue(1_000_000)
        self._capital_spin.setDecimals(0)
        self._capital_spin.setSingleStep(100000)
        pf.addRow("初始资金", self._capital_spin)

        self._comm_spin = QDoubleSpinBox()
        self._comm_spin.setRange(0, 0.01)
        self._comm_spin.setDecimals(6)
        self._comm_spin.setValue(0.0003)
        self._comm_spin.setSingleStep(0.0001)
        pf.addRow("手续费率", self._comm_spin)

        self._slippage_spin = QDoubleSpinBox()
        self._slippage_spin.setRange(0, 0.01)
        self._slippage_spin.setDecimals(6)
        self._slippage_spin.setSingleStep(0.0001)
        pf.addRow("滑点", self._slippage_spin)

        root.addWidget(param_grp)

        # ── 关联 / 标签 ───────────────────────────────────────────────
        rel_grp = QGroupBox("标签 / 关联资源")
        rf = QFormLayout(rel_grp)

        self._tags_edit = QLineEdit()
        self._tags_edit.setPlaceholderText("逗号分隔标签")
        rf.addRow("标签", self._tags_edit)

        self._features_edit = QLineEdit()
        self._features_edit.setPlaceholderText("因子 ID，逗号分隔")
        rf.addRow("依赖因子", self._features_edit)

        self._datasets_edit = QLineEdit()
        self._datasets_edit.setPlaceholderText("数据集 ID，逗号分隔")
        rf.addRow("依赖数据集", self._datasets_edit)

        self._models_edit = QLineEdit()
        self._models_edit.setPlaceholderText("模型 ID，逗号分隔")
        rf.addRow("依赖模型", self._models_edit)

        root.addWidget(rel_grp)

        # ── 按钮 ──────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _on_strategy_changed(self, index):
        """策略下拉选择变化时，自动填充策略名称"""
        strategy_id = self._strategy_combo.currentData()
        if strategy_id and self._engine:
            try:
                s = self._engine.get_strategy(strategy_id)
                if s:
                    self._strategy_name_edit.setText(s.name)
            except Exception:
                pass

    def _load_record(self):
        r = self._record
        self._name_edit.setText(r.name)
        # 在下拉中查找匹配的策略ID
        found = False
        for i in range(self._strategy_combo.count()):
            if self._strategy_combo.itemData(i) == r.strategy_id:
                self._strategy_combo.setCurrentIndex(i)
                found = True
                break
        if not found and r.strategy_id:
            self._strategy_combo.setEditText(r.strategy_id)
        self._strategy_name_edit.setText(r.strategy_name)
        self._universe_edit.setText(r.universe)
        self._author_edit.setText(r.created_by)
        self._desc_edit.setPlainText(r.description)
        self._start_edit.setText(r.start_date)
        self._end_edit.setText(r.end_date)
        self._capital_spin.setValue(r.initial_capital)
        self._comm_spin.setValue(r.commission)
        self._slippage_spin.setValue(r.slippage)
        self._tags_edit.setText(", ".join(r.tags))
        self._features_edit.setText(", ".join(r.feature_ids))
        self._datasets_edit.setText(", ".join(r.dataset_ids))
        self._models_edit.setText(", ".join(r.model_ids))

    def _on_accept(self):
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    def _split(self, t: str) -> List[str]:
        return [x.strip() for x in t.split(",") if x.strip()]

    def get_name(self)            -> str:         return self._name_edit.text().strip()
    def get_strategy_id(self)     -> str:
        # 优先用下拉选中的data，否则用编辑文本（手动输入的ID）
        data = self._strategy_combo.currentData()
        if data:
            return data
        text = self._strategy_combo.currentText().strip()
        if text == "（不关联策略）":
            return ""
        return text
    def get_strategy_name(self)   -> str:         return self._strategy_name_edit.text().strip()
    def get_universe(self)        -> str:         return self._universe_edit.text().strip()
    def get_author(self)          -> str:         return self._author_edit.text().strip()
    def get_description(self)     -> str:         return self._desc_edit.toPlainText().strip()
    def get_start_date(self)      -> str:         return self._start_edit.text().strip()
    def get_end_date(self)        -> str:         return self._end_edit.text().strip()
    def get_initial_capital(self) -> float:       return self._capital_spin.value()
    def get_commission(self)      -> float:       return self._comm_spin.value()
    def get_slippage(self)        -> float:       return self._slippage_spin.value()
    def get_tags(self)            -> List[str]:   return self._split(self._tags_edit.text())
    def get_feature_ids(self)     -> List[str]:   return self._split(self._features_edit.text())
    def get_dataset_ids(self)     -> List[str]:   return self._split(self._datasets_edit.text())
    def get_model_ids(self)       -> List[str]:   return self._split(self._models_edit.text())


class BacktestCompleteDialog(QDialog):
    """手动填入回测结果对话框（用于离线回测）。"""

    def __init__(self, bt_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"填入回测结果 — {bt_name}")
        self.setMinimumWidth(480)
        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)

        form = QFormLayout()

        def _pct(lo=-1.0, hi=20.0):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(4); s.setSingleStep(0.01)
            return s

        def _ratio(lo=-20.0, hi=20.0):
            s = QDoubleSpinBox()
            s.setRange(lo, hi); s.setDecimals(4); s.setSingleStep(0.01)
            return s

        self._ann_spin    = _pct()
        self._dd_spin     = _pct(-1.0, 0.0)
        self._sharpe_spin = _ratio()
        self._sortino_spin= _ratio()
        self._calmar_spin = _ratio()
        self._wr_spin     = _pct(0.0, 1.0)
        self._turn_spin   = _ratio(0.0, 200.0)
        self._pf_spin     = _ratio(0.0, 20.0)
        self._total_ret_spin = _pct(-1.0, 100.0)
        self._alpha_spin  = _pct()
        self._beta_spin   = _ratio(-5.0, 5.0)
        self._ir_spin     = _ratio()

        self._trades_spin = QSpinBox()
        self._trades_spin.setRange(0, 1_000_000)
        self._ahd_spin    = QDoubleSpinBox()
        self._ahd_spin.setRange(0, 3650); self._ahd_spin.setDecimals(1)
        self._ahd_spin.setSuffix("  天")
        self._mpc_spin    = _pct(0.0, 1.0)

        form.addRow("年化收益",    self._ann_spin)
        form.addRow("最大回撤",    self._dd_spin)
        form.addRow("Sharpe",      self._sharpe_spin)
        form.addRow("Sortino",     self._sortino_spin)
        form.addRow("Calmar",      self._calmar_spin)
        form.addRow("胜率",        self._wr_spin)
        form.addRow("换手率",      self._turn_spin)
        form.addRow("盈亏比",      self._pf_spin)
        form.addRow("总收益",      self._total_ret_spin)
        form.addRow("Alpha",       self._alpha_spin)
        form.addRow("Beta",        self._beta_spin)
        form.addRow("信息比率",    self._ir_spin)
        form.addRow("总交易次数",  self._trades_spin)
        form.addRow("平均持仓天数",self._ahd_spin)
        form.addRow("最大仓位集中度", self._mpc_spin)

        root.addLayout(form)

        root.addWidget(QLabel("月度收益 JSON（格式：{\"2024-01\": 0.023}，可留空）："))
        self._monthly_edit = QPlainTextEdit()
        self._monthly_edit.setPlaceholderText("{}")
        self._monthly_edit.setFixedHeight(56)
        root.addWidget(self._monthly_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确认")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def get_annual_return(self)     -> float: return self._ann_spin.value()
    def get_max_drawdown(self)      -> float: return self._dd_spin.value()
    def get_sharpe(self)            -> float: return self._sharpe_spin.value()
    def get_sortino(self)           -> float: return self._sortino_spin.value()
    def get_calmar(self)            -> float: return self._calmar_spin.value()
    def get_win_rate(self)          -> float: return self._wr_spin.value()
    def get_turnover(self)          -> float: return self._turn_spin.value()
    def get_profit_factor(self)     -> float: return self._pf_spin.value()
    def get_total_return(self)      -> float: return self._total_ret_spin.value()
    def get_alpha(self)             -> float: return self._alpha_spin.value()
    def get_beta(self)              -> float: return self._beta_spin.value()
    def get_information_ratio(self) -> float: return self._ir_spin.value()
    def get_total_trades(self)      -> int:   return self._trades_spin.value()
    def get_avg_holding_days(self)  -> float: return self._ahd_spin.value()
    def get_max_position_conc(self) -> float: return self._mpc_spin.value()

    def get_monthly_returns(self) -> Dict[str, float]:
        try:
            return json.loads(self._monthly_edit.toPlainText() or "{}")
        except Exception:
            return {}
