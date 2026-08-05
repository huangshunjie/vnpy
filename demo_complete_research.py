"""
量化研究平台 - 完整策略研究演示

演示场景：双均线交叉策略从零到完成的全流程
策略逻辑：5日均线上穿20日均线买入，下穿卖出
目标市场：沪深300成分股
回测周期：2020-2024年

运行方式：python demo_complete_research.py
"""

from datetime import datetime
from vnpy.event import EventEngine
from vnpy.trader.engine import MainEngine
from vnpy.quant_research.engine import ResearchEngine
from vnpy.quant_research.constant import (
    ExperimentStatus, LogLevel, LogSource
)

print("=" * 80)
print("🚀 量化研究平台 - 完整策略研究流程演示")
print("=" * 80)

# 步骤1：初始化平台
event_engine = EventEngine()
main_engine = MainEngine(event_engine)
research_engine = ResearchEngine(main_engine, event_engine)
print("\n✅ 平台初始化完成\n")

# 步骤2：创建研究实验
print("=" * 80)
print("📝 步骤1：创建研究实验")
print("=" * 80)

experiment = research_engine.create_experiment(
    name="双均线交叉策略研究",
    description="验证5日和20日均线交叉策略在沪深300的有效性",
    tags=["均线", "趋势跟踪", "A股"],
    params={"fast_period": 5, "slow_period": 20, "stop_loss": 0.05},
    created_by="张研究员"
)

print(f"✅ 实验创建成功")
print(f"   实验ID: {experiment.experiment_id}")
print(f"   实验名称: {experiment.name}")
print(f"   状态: {experiment.status.value}")

# 步骤3：注册数据集
print("\n" + "=" * 80)
print("📊 步骤2：注册历史数据集")
print("=" * 80)

dataset = research_engine.register_dataset(
    name="沪深300日线数据2020-2024",
    version="v1.0",
    source="Wind",
    start_date="2020-01-01",
    end_date="2024-12-31",
    row_count=365000,
    size_mb=45.6,
    created_by="张研究员"
)

print(f"✅ 数据集注册成功")
print(f"   数据集ID: {dataset.dataset_id}")
print(f"   时间范围: {dataset.start_date} 至 {dataset.end_date}")
print(f"   数据量: {dataset.row_count:,} 行")

# 步骤4：创建技术指标
print("\n" + "=" * 80)
print("🧩 步骤3：创建技术指标特征")
print("=" * 80)

feature_ma5 = research_engine.register_feature(
    name="MA5",
    version="v1.0",
    description="5日移动平均线",
    category="momentum",
    formula="talib.MA(close, 5)",
    author="张研究员",
    dataset_ids=[dataset.dataset_id]
)

feature_ma20 = research_engine.register_feature(
    name="MA20",
    version="v1.0",
    description="20日移动平均线",
    category="momentum",
    formula="talib.MA(close, 20)",
    author="张研究员",
    dataset_ids=[dataset.dataset_id]
)

feature_cross = research_engine.register_feature(
    name="MA_CROSS_SIGNAL",
    version="v1.0",
    description="均线交叉信号",
    category="technical",
    formula="np.where(MA5 > MA20, 1, -1)",
    author="张研究员",
    dependencies=[feature_ma5.feature_id, feature_ma20.feature_id]
)

print(f"✅ 特征创建成功")
print(f"   特征1: {feature_ma5.name}")
print(f"   特征2: {feature_ma20.name}")
print(f"   特征3: {feature_cross.name}")

# 步骤5：构建交易策略
print("\n" + "=" * 80)
print("📈 步骤4：构建交易策略")
print("=" * 80)

strategy = research_engine.register_strategy(
    name="双均线趋势跟踪策略",
    version="v1.0",
    description="MA5上穿MA20买入，下穿卖出",
    strategy_type="trend_following",
    author="张研究员",
    universe="沪深300",
    params={"fast_period": 5, "slow_period": 20, "stop_loss": 0.05},
    feature_ids=[feature_ma5.feature_id, feature_ma20.feature_id, feature_cross.feature_id],
    dataset_ids=[dataset.dataset_id]
)

print(f"✅ 策略创建成功")
print(f"   策略ID: {strategy.strategy_id}")
print(f"   策略名称: {strategy.name}")
print(f"   股票池: {strategy.universe}")

# 步骤6：提交回测
print("\n" + "=" * 80)
print("⏮ 步骤5：提交回测任务")
print("=" * 80)

backtest = research_engine.submit_backtest(
    name="双均线策略_2020-2024_首次回测",
    strategy_id=strategy.strategy_id,
    strategy_name=strategy.name,
    start_date="2020-01-01",
    end_date="2024-12-31",
    initial_capital=1000000.0,
    commission=0.0003,
    created_by="张研究员"
)

print(f"✅ 回测任务提交")
print(f"   回测ID: {backtest.backtest_id}")
print(f"   初始资金: ¥{backtest.initial_capital:,.0f}")

# 模拟回测执行
print(f"\n⏳ 回测执行中...")
research_engine.run_backtest(backtest.backtest_id)

research_engine.complete_backtest(
    backtest.backtest_id,
    annual_return=0.158,
    max_drawdown=0.123,
    sharpe=1.45,
    win_rate=0.58,
    total_trades=156
)

backtest = research_engine.get_backtest(backtest.backtest_id)

print(f"✅ 回测完成！")
print(f"\n📊 回测结果：")
print(f"   ├─ 年化收益率: {backtest.annual_return:.2%}")
print(f"   ├─ 最大回撤: {backtest.max_drawdown:.2%}")
print(f"   ├─ 夏普比率: {backtest.sharpe:.2f}")
print(f"   ├─ 胜率: {backtest.win_rate:.2%}")
print(f"   └─ 交易次数: {backtest.total_trades}次")

# 步骤7：更新策略绩效
print("\n" + "=" * 80)
print("📊 步骤6：更新策略绩效")
print("=" * 80)

research_engine.update_performance(
    strategy.strategy_id,
    annual_return=backtest.annual_return,
    max_drawdown=backtest.max_drawdown,
    sharpe=backtest.sharpe,
    win_rate=backtest.win_rate
)

research_engine.set_experiment_status(experiment.experiment_id, ExperimentStatus.COMPLETED)

print(f"✅ 策略和实验状态已更新")

# 步骤8：生成报告
print("\n" + "=" * 80)
print("📄 步骤7：生成研究报告")
print("=" * 80)

report = research_engine.create_report(
    title="双均线交叉策略研究报告",
    report_type="research",
    author="张研究员",
    summary=f"回测年化收益{backtest.annual_return:.2%}，夏普比率{backtest.sharpe:.2f}",
    experiment_id=experiment.experiment_id,
    strategy_id=strategy.strategy_id,
    backtest_id=backtest.backtest_id
)

research_engine.add_report_section(report.report_id, "研究背景", "验证双均线策略有效性", 1)
research_engine.add_report_section(report.report_id, "回测结果", f"年化{backtest.annual_return:.2%}", 2)
research_engine.publish_report(report.report_id)

print(f"✅ 报告生成并发布")
print(f"   报告ID: {report.report_id}")

# 步骤9：研究摘要
print("\n" + "=" * 80)
print("📊 研究成果摘要")
print("=" * 80)

print(f"\n✅ 平台状态：")
print(f"   ├─ 实验: {len(research_engine.list_experiments())}个")
print(f"   ├─ 数据集: {len(research_engine.list_datasets())}个")
print(f"   ├─ 特征: {len(research_engine.list_features())}个")
print(f"   ├─ 策略: {len(research_engine.list_strategies())}个")
print(f"   ├─ 回测: {len(research_engine.list_backtests())}个")
print(f"   └─ 报告: {len(research_engine.list_reports())}个")

# 完成
print("\n" + "=" * 80)
print("🎉 策略研究流程演示完成！")
print("=" * 80)

print(f"\n📈 研究成果：")
print(f"   实验: {experiment.name}")
print(f"   策略: {strategy.name}")
print(f"   回测: 年化{backtest.annual_return:.2%}, 夏普{backtest.sharpe:.2f}")
print(f"   报告: {report.title}")

print(f"\n💡 下一步建议：")
print(f"   1. 启动UI界面查看可视化结果")
print(f"   2. 尝试优化参数（调整均线周期）")
print(f"   3. 在更多股票池上验证")
print(f"   4. 导出研究报告PDF")

print(f"\n📚 查看文档：")
print(f"   - USER_GUIDE.md: 使用教程")
print(f"   - PLATFORM_OVERVIEW.md: 功能说明")
print(f"   - OPTIMIZATION_REPORT.md: 技术文档")

print("\n" + "=" * 80)
print("感谢使用量化研究平台！祝研究顺利！ 🚀")
print("=" * 80)
