"""
quant_research/event.py

所有事件类型常量。
"""

APP_NAME = "QuantResearch"

# Experiment Center
EVENT_EXPERIMENT_CREATED  = "eResearchExperimentCreated"
EVENT_EXPERIMENT_UPDATED  = "eResearchExperimentUpdated"
EVENT_EXPERIMENT_DELETED  = "eResearchExperimentDeleted"

# Dataset Registry
EVENT_DATASET_CREATED     = "eResearchDatasetCreated"
EVENT_DATASET_UPDATED     = "eResearchDatasetUpdated"
EVENT_DATASET_DELETED     = "eResearchDatasetDeleted"

# Feature Registry
EVENT_FEATURE_CREATED     = "eResearchFeatureCreated"
EVENT_FEATURE_UPDATED     = "eResearchFeatureUpdated"
EVENT_FEATURE_DELETED     = "eResearchFeatureDeleted"

# Strategy Registry
EVENT_STRATEGY_CREATED    = "eResearchStrategyCreated"
EVENT_STRATEGY_UPDATED    = "eResearchStrategyUpdated"
EVENT_STRATEGY_DELETED    = "eResearchStrategyDeleted"

# Model Registry
EVENT_MODEL_CREATED       = "eResearchModelCreated"
EVENT_MODEL_UPDATED       = "eResearchModelUpdated"
EVENT_MODEL_DELETED       = "eResearchModelDeleted"

# Backtest Registry
EVENT_BACKTEST_CREATED    = "eResearchBacktestCreated"
EVENT_BACKTEST_UPDATED    = "eResearchBacktestUpdated"
EVENT_BACKTEST_DELETED    = "eResearchBacktestDeleted"

# Report Center
EVENT_REPORT_CREATED      = "eResearchReportCreated"
EVENT_REPORT_UPDATED      = "eResearchReportUpdated"

# Pipeline Center
EVENT_PIPELINE_CREATED    = "eResearchPipelineCreated"
EVENT_PIPELINE_UPDATED    = "eResearchPipelineUpdated"
EVENT_PIPELINE_STARTED    = "eResearchPipelineStarted"
EVENT_PIPELINE_COMPLETED  = "eResearchPipelineCompleted"
EVENT_PIPELINE_FAILED     = "eResearchPipelineFailed"

# Artifact Center
EVENT_ARTIFACT_CREATED    = "eResearchArtifactCreated"
EVENT_ARTIFACT_DELETED    = "eResearchArtifactDeleted"

# Workspace Manager
EVENT_WORKSPACE_SWITCHED  = "eResearchWorkspaceSwitched"
EVENT_PROJECT_CREATED     = "eResearchProjectCreated"
EVENT_PROJECT_UPDATED     = "eResearchProjectUpdated"
