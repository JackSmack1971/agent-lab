# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-10-05

### Added
- Initial release of Agent Lab, a Gradio-based platform for testing AI agents
- Agent configuration with name, model selector, system prompt, decoding parameters, and tool toggles
- Streaming chat interface with SSE support and stop functionality
- Telemetry tracking per run including timestamps, tokens, latency, and cost
- Pricing and cost estimation for models
- Web tool status badge with allow-list enforcement
- Export functionality for run data to CSV
- Session persistence with save/load capabilities
- Run tagging with experiment ID, task label, and notes
- Dynamic model catalog with refresh and fallback support