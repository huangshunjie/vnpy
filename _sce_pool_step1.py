"""优化SCE股票池 - 第1步：替换UI部分"""
filepath = r'C:\Users\11229\Documents\GitHub\vnpy\vnpy\strategy_condition\ui\widget.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_ui = '''        # ── 股票池 ──
        pool_hdr = QtWidgets.QHBoxLayout()
        pool_hdr.addWidget(_lbl("股票池  Universe", _YLW, 13, True))
        pool_hdr.addStretch()
        self._pool_count_lbl = _lbl("0 只", _MUT, 11)
        pool_hdr.addWidget(self._pool_count_lbl)
        left_col.addLayout(pool_hdr)

        # 预设池快选（改为2x2布局更紧凑）
        left_col.addWidget(_lbl("快速预设", _MUT, 11))
        preset_grid = QtWidgets.QGridLayout()
        preset_grid.setSpacing(4)
        preset_btns = [
            ("沪深300", _POOL_CSI300),
            ("中证500", _POOL_CSI500),
            ("科创板",  _POOL_STAR),
            ("自定义",  []),
        ]
        for idx, (label, symbols) in enumerate(preset_btns):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(
                f"QPushButton{{background:{_PAN2};color:{_FG};"
                f"border:1px solid {_BORD};border-radius:4px;"
                f"padding:4px 6px;font-size:11px;}}"
                f"QPushButton:hover{{border-color:{_BLU};color:{_BLU};}}"
            )
            pool = list(symbols)
            b.clicked.connect(lambda checked, s=pool: self._set_pool(s))
            preset_grid.addWidget(b, idx // 2, idx % 2)
        left_col.addLayout(preset_grid)'''

new_ui = '''        # ── 股票池（完整版）──
        pool_hdr = QtWidgets.QHBoxLayout()
        pool_hdr.addWidget(_lbl("股票池  Universe", _YLW, 13, True))
        pool_hdr.addStretch()
        self._pool_count_lbl = _lbl("0 只", _MUT, 11)
        pool_hdr.addWidget(self._pool_count_lbl)
        left_col.addLayout(pool_hdr)
        self._current_pool_name = ""

        # ━━ 市场/板块 ━━
        left_col.addWidget(_lbl("市场/板块", _MUT, 11))
        _sbtn = (f"QPushButton{{background:{_PAN2};color:{_FG};border:1px solid {_BORD};"
                 f"border-radius:4px;padding:4px 6px;font-size:10px;}}"
                 f"QPushButton:hover{{border-color:{_BLU};color:{_BLU};}}")
        exch_row = QtWidgets.QHBoxLayout()
        exch_row.setSpacing(3)
        for label, key in [("全市场","ALL"),("沪市","SSE"),("深市","SZSE"),("北交所","BSE")]:
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, k=key, n=label: self._set_exchange_pool(k, n))
            exch_row.addWidget(b)
        left_col.addLayout(exch_row)
        board_row = QtWidgets.QHBoxLayout()
        board_row.setSpacing(3)
        for label in ["沪主板","科创板","深主板","创业板"]:
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, n=label: self._set_board_pool(n))
            board_row.addWidget(b)
        left_col.addLayout(board_row)

        # ━━ 指数成分 ━━
        left_col.addWidget(_lbl("指数成分", _MUT, 11))
        idx_grid = QtWidgets.QGridLayout()
        idx_grid.setSpacing(4)
        for idx, (label, pool_key) in enumerate([("上证50","IDX:000016"),("沪深300","IDX:000300"),("中证500","IDX:000905"),("中证1000","IDX:000852"),("创业板指","IDX:399006")]):
            b = QtWidgets.QPushButton(label)
            b.setStyleSheet(_sbtn)
            b.clicked.connect(lambda checked, p=pool_key, n=label: self._set_index_pool(p, n))
            idx_grid.addWidget(b, idx // 3, idx % 3)
        left_col.addLayout(idx_grid)

        # 更多指数下拉框
        more_row = QtWidgets.QHBoxLayout()
        more_row.setSpacing(6)
        more_row.addWidget(_lbl("更多:", _MUT, 11))
        self._sce_index_combo = QtWidgets.QComboBox()
        self._sce_index_combo.setStyleSheet(_COMBO_SS)
        self._sce_index_combo.setFixedHeight(26)
        self._sce_index_combo.addItem("-- 选择指数 --", "")
        try:
            from vnpy.trader.index_constituents import SUPPORTED_INDICES as _ALL_IDX
            _added = {"000016","000300","000905","000852","399006"}
            for cat in ["规模指数","板块指数","风格策略","行业主题"]:
                hdr = False
                for code, info in _ALL_IDX.items():
                    if info.get("category") != cat or code in _added:
                        continue
                    if not hdr:
                        self._sce_index_combo.addItem(f"━━ {cat} ━━", "")
                        hdr = True
                    self._sce_index_combo.addItem(f"  {info['name']} ({code})", f"IDX:{code}")
        except Exception:
            pass
        self._sce_index_combo.currentIndexChanged.connect(self._on_sce_index_changed)
        more_row.addWidget(self._sce_index_combo, 1)
        left_col.addLayout(more_row)

        # ━━ 行业筛选 ━━
        left_col.addWidget(_lbl("行业筛选", _MUT, 11))
        ind_row = QtWidgets.QHBoxLayout()
        ind_row.setSpacing(6)
        self._sce_industry_combo = QtWidgets.QComboBox()
        self._sce_industry_combo.setStyleSheet(_COMBO_SS)
        self._sce_industry_combo.setFixedHeight(26)
        self._sce_industry_combo.addItem("-- 选择行业 --", "")
        try:
            from vnpy.trader.stock_pool import get_all_industries
            for ind in get_all_industries():
                self._sce_industry_combo.addItem(ind, ind)
        except Exception:
            for ind in ["银行","医药生物","电子","计算机","食品饮料","家用电器","汽车","化工"]:
                self._sce_industry_combo.addItem(ind, ind)
        self._sce_industry_combo.currentIndexChanged.connect(self._on_sce_industry_changed)
        ind_row.addWidget(self._sce_industry_combo, 1)
        left_col.addLayout(ind_row)'''

if old_ui in content:
    content = content.replace(old_ui, new_ui)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("[OK] Step 1: UI replaced")
else:
    print("[FAIL] Could not find old UI pattern")
