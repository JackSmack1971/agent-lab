"""AI-powered parameter optimization service for intelligent model parameter suggestions."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import functools
import hashlib

from src.models.parameter_optimization import (
    UseCaseType,
    UseCaseDetectionResult,
    ParameterRecommendation,
    OptimizationContext,
    HistoricalPattern,
    ParameterOptimizationRequest,
    ParameterOptimizationResponse,
    SmartDefaultsRequest,
    SmartDefaultsResponse,
)

# Import existing services for historical data
from services.persist import list_sessions, load_session
from agents.models import RunRecord

logger = logging.getLogger(__name__)

# Performance optimization: cache compiled regex patterns
_USE_CASE_KEYWORDS = {
    UseCaseType.CREATIVE_WRITING: [
        r'\b(creative|story|fiction|poem|novel|write|writing|author|imaginative|artistic)\b',
        r'\b(original|innovative|brainstorm|ideate|generate ideas|inspire)\b',
        r'\b(fantasy|tale|narrative|plot|character|scene)\b'
    ],
    UseCaseType.CODE_GENERATION: [
        r'\b(code|program|function|script|programming|algorithm|implementation)\b',
        r'\b(python|javascript|java|c\+\+|html|css|sql|typescript|go|rust)\b',
        r'\b(syntax|compile|test|deploy|build|develop)\b'
    ],
    UseCaseType.ANALYSIS: [
        r'\b(analyze|analysis|examine|review|evaluate|assess|investigate)\b',
        r'\b(data|dataset|statistics|metrics|research|pattern|trend|insight|document|documents)\b',
        r'\b(understand|interpret|break down|explain|compare|visualize)\b'
    ],
    UseCaseType.SUMMARIZATION: [
        r'\b(summarize|summary|condense|abstract|tl;dr|recap|overview)\b',
        r'\b(key points|main ideas|brief|concise|compress|shorten)\b',
        r'\b(article|document|text|content|report|notes)\b'
    ],
    UseCaseType.CONVERSATION: [
        r'\b(chat|talk|conversation|dialogue|discuss|communicate|interact|lets)\b',
        r'\b(friendly|casual|informal|social|converse|engage|respond|favorite)\b',
        r'\b(reply|answer|question|opinion|thoughts|feelings|movies|about)\b'
    ],
    UseCaseType.REASONING: [
        r'\b(reason|logic|think|step by step|logical|deduce|conclude|solve)\b',
        r'\b(problem.solving|puzzle|mathematical|calculate|compute|complex)\b',
        r'\b(accurate|precise|correct|truthful|systematic|methodical|problem)\b'
    ],
    UseCaseType.DEBUGGING: [
        r'\b(debug|error|fix|issue|problem|troubleshoot|diagnose)\b',
        r'\b(bug|crash|failure|exception|trace|log|stack)\b',
        r'\b(identify|resolve|solve|repair|patch|update)\b'
    ],
    UseCaseType.TRANSLATION: [
        r'\b(translate|translation|language|foreign|convert|transform)\b',
        r'\b(english|german|french|spanish|chinese|japanese|korean|italian)\b',
        r'\b(text|document|message|content|language pair|linguistic)\b'
    ]
}

# Pre-compile regex patterns for performance
_COMPILED_PATTERNS = {}
for use_case, patterns in _USE_CASE_KEYWORDS.items():
    _COMPILED_PATTERNS[use_case] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

# Parameter optimization rules by use case
_PARAMETER_RULES = {
    UseCaseType.CREATIVE_WRITING: {
        "temperature": {"min": 0.7, "max": 1.2, "default": 0.9},
        "top_p": {"min": 0.8, "max": 1.0, "default": 0.95},
        "max_tokens": {"min": 500, "max": 4000, "default": 2000}
    },
    UseCaseType.CODE_GENERATION: {
        "temperature": {"min": 0.1, "max": 0.5, "default": 0.3},
        "top_p": {"min": 0.7, "max": 0.9, "default": 0.8},
        "max_tokens": {"min": 1000, "max": 8000, "default": 3000}
    },
    UseCaseType.ANALYSIS: {
        "temperature": {"min": 0.1, "max": 0.4, "default": 0.2},
        "top_p": {"min": 0.8, "max": 0.95, "default": 0.9},
        "max_tokens": {"min": 1000, "max": 6000, "default": 2500}
    },
    UseCaseType.SUMMARIZATION: {
        "temperature": {"min": 0.1, "max": 0.3, "default": 0.2},
        "top_p": {"min": 0.7, "max": 0.9, "default": 0.8},
        "max_tokens": {"min": 200, "max": 2000, "default": 500}
    },
    UseCaseType.CONVERSATION: {
        "temperature": {"min": 0.6, "max": 0.9, "default": 0.7},
        "top_p": {"min": 0.8, "max": 1.0, "default": 0.9},
        "max_tokens": {"min": 500, "max": 3000, "default": 1000}
    },
    UseCaseType.REASONING: {
        "temperature": {"min": 0.0, "max": 0.3, "default": 0.1},
        "top_p": {"min": 0.7, "max": 0.9, "default": 0.8},
        "max_tokens": {"min": 1000, "max": 8000, "default": 3000}
    },
    UseCaseType.DEBUGGING: {
        "temperature": {"min": 0.0, "max": 0.2, "default": 0.1},
        "top_p": {"min": 0.8, "max": 0.95, "default": 0.9},
        "max_tokens": {"min": 500, "max": 4000, "default": 1500}
    },
    UseCaseType.TRANSLATION: {
        "temperature": {"min": 0.1, "max": 0.4, "default": 0.2},
        "top_p": {"min": 0.8, "max": 0.95, "default": 0.9},
        "max_tokens": {"min": 500, "max": 4000, "default": 1500}
    },
    UseCaseType.OTHER: {
        "temperature": {"min": 0.5, "max": 0.8, "default": 0.7},
        "top_p": {"min": 0.8, "max": 0.95, "default": 0.9},
        "max_tokens": {"min": 500, "max": 3000, "default": 1000}
    }
}


class UseCaseDetector:
    """Lightweight rule-based use case detection engine."""

    @staticmethod
    def detect_use_case(text: str) -> UseCaseDetectionResult:
        """Detect use case from text description using keyword matching."""
        start_time = time.time()
        text_lower = text.lower()

        # Score each use case based on keyword matches
        scores = defaultdict(float)
        matched_keywords = defaultdict(list)

        for use_case, patterns in _COMPILED_PATTERNS.items():
            for pattern in patterns:
                matches = pattern.findall(text_lower)
                if matches:
                    # Weight by number of matches and pattern specificity
                    # Increased base score and cap for better accuracy
                    score = min(len(matches) * 0.3, 1.0)  # Cap at 1.0, 0.3 per match
                    scores[use_case] += score
                    matched_keywords[use_case].extend(matches[:3])  # Limit keywords

        # Determine primary use case
        max_score = max(scores.values()) if scores else 0.0
        if not scores or max_score < 0.5:
            primary_use_case = UseCaseType.OTHER
            confidence = 0.5 if not scores else max_score  # Use actual score for low-confidence detections
            logger.debug(f"Classified as OTHER due to low confidence (max_score={max_score:.2f}) for text: {text_lower[:50]}...")
        else:
            primary_use_case = max(scores.items(), key=lambda x: x[1])[0]
            confidence = min(scores[primary_use_case], 0.95)  # Cap at 0.95
            logger.debug(f"Detected {primary_use_case.value} with confidence {confidence:.2f} for text: {text_lower[:50]}...")

        # Find secondary use cases (those with score > 0.3)
        secondary_use_cases = [
            use_case for use_case, score in scores.items()
            if use_case != primary_use_case and score > 0.3
        ][:2]  # Limit to 2 secondary

        # Generate context hints
        context_hints = {}
        if "creative" in text_lower or "write" in text_lower:
            context_hints["creativity"] = 0.8
        if "code" in text_lower or "program" in text_lower:
            context_hints["technical"] = 0.9
        if "analyze" in text_lower or "research" in text_lower:
            context_hints["analytical"] = 0.8
        if "fast" in text_lower or "quick" in text_lower:
            context_hints["speed"] = 0.7

        detection_time = (time.time() - start_time) * 1000

        return UseCaseDetectionResult(
            detected_use_case=primary_use_case,
            confidence_score=confidence,
            secondary_use_cases=secondary_use_cases,
            keywords_matched=matched_keywords.get(primary_use_case, []),
            context_hints=context_hints
        )


class ParameterRecommender:
    """Parameter recommendation engine with rule-based optimization."""

    @staticmethod
    def recommend_parameters(
        use_case: UseCaseType,
        context: OptimizationContext,
        historical_patterns: Optional[List[HistoricalPattern]] = None
    ) -> ParameterRecommendation:
        """Recommend optimal parameters based on use case and context."""

        rules = _PARAMETER_RULES[use_case]

        # Base parameters from rules
        temperature = rules["temperature"]["default"]
        top_p = rules["top_p"]["default"]
        max_tokens = rules["max_tokens"]["default"]

        # Adjust based on context
        temperature, top_p, max_tokens = ParameterRecommender._adjust_for_context(
            temperature, top_p, max_tokens, context, rules
        )

        # Incorporate historical learning if available
        if historical_patterns:
            temperature, top_p, max_tokens = ParameterRecommender._incorporate_historical_learning(
                temperature, top_p, max_tokens, use_case, context.model_id, historical_patterns
            )

        # Generate reasoning
        reasoning = ParameterRecommender._generate_reasoning(use_case, context, temperature, top_p, max_tokens)

        return ParameterRecommendation(
            temperature=round(temperature, 2),
            top_p=round(top_p, 2),
            max_tokens=max_tokens,
            reasoning=reasoning
        )

    @staticmethod
    def _adjust_for_context(
        temperature: float,
        top_p: float,
        max_tokens: int,
        context: OptimizationContext,
        rules: dict
    ) -> Tuple[float, float, int]:
        """Adjust parameters based on context factors."""

        # Adjust for input length
        if context.user_input_length > 500:
            # Longer inputs suggest more complex tasks
            temperature = min(temperature + 0.1, rules["temperature"]["max"])
            max_tokens = min(max_tokens + 500, rules["max_tokens"]["max"])
        elif context.user_input_length < 50:
            # Short inputs suggest simpler tasks
            temperature = max(temperature - 0.1, rules["temperature"]["min"])
            max_tokens = max(max_tokens - 200, rules["max_tokens"]["min"])

        # Adjust for conversation history
        if context.conversation_history_length > 10:
            # Long conversations suggest building context
            top_p = min(top_p + 0.05, rules["top_p"]["max"])
            max_tokens = min(max_tokens + 300, rules["max_tokens"]["max"])

        # Adjust for time pressure
        if context.time_pressure == "high":
            temperature = max(temperature - 0.2, rules["temperature"]["min"])
            max_tokens = max(max_tokens - 500, rules["max_tokens"]["min"])
        elif context.time_pressure == "low":
            temperature = min(temperature + 0.1, rules["temperature"]["max"])
            max_tokens = min(max_tokens + 500, rules["max_tokens"]["max"])

        # Adjust for task complexity
        if context.task_complexity_hint == "complex":
            temperature = min(temperature + 0.1, rules["temperature"]["max"])
            max_tokens = min(max_tokens + 1000, rules["max_tokens"]["max"])
        elif context.task_complexity_hint == "simple":
            temperature = max(temperature - 0.1, rules["temperature"]["min"])
            max_tokens = max(max_tokens - 500, rules["max_tokens"]["min"])

        return temperature, top_p, max_tokens

    @staticmethod
    def _incorporate_historical_learning(
        temperature: float,
        top_p: float,
        max_tokens: int,
        use_case: UseCaseType,
        model_id: str,
        historical_patterns: List[HistoricalPattern]
    ) -> Tuple[float, float, int]:
        """Incorporate insights from historical successful patterns."""

        # Filter relevant patterns
        relevant_patterns = [
            p for p in historical_patterns
            if p.use_case == use_case and p.model_id == model_id and p.success_score > 0.7
        ]

        if not relevant_patterns:
            return temperature, top_p, max_tokens

        # Weight by recency and success score
        total_weight = 0
        weighted_temp = 0
        weighted_top_p = 0
        weighted_max_tokens = 0

        now = datetime.now()
        for pattern in relevant_patterns:
            # Weight by recency (newer patterns have higher weight)
            days_old = (now - pattern.last_used).days
            recency_weight = max(0.1, 1.0 - (days_old / 30.0))  # Decay over 30 days

            # Weight by success and usage
            success_weight = pattern.success_score * min(pattern.usage_count / 10.0, 1.0)

            weight = recency_weight * success_weight
            total_weight += weight

            weighted_temp += pattern.temperature * weight
            weighted_top_p += pattern.top_p * weight
            weighted_max_tokens += pattern.max_tokens * weight

        if total_weight > 0:
            # Blend historical insights with rule-based defaults (70% historical, 30% rules)
            historical_ratio = 0.7
            temperature = (weighted_temp / total_weight) * historical_ratio + temperature * (1 - historical_ratio)
            top_p = (weighted_top_p / total_weight) * historical_ratio + top_p * (1 - historical_ratio)
            max_tokens = int((weighted_max_tokens / total_weight) * historical_ratio + max_tokens * (1 - historical_ratio))

        return temperature, top_p, max_tokens

    @staticmethod
    def _generate_reasoning(
        use_case: UseCaseType,
        context: OptimizationContext,
        temperature: float,
        top_p: float,
        max_tokens: int
    ) -> str:
        """Generate human-readable reasoning for parameter recommendations."""

        reasoning_parts = []

        # Use case specific reasoning
        if use_case == UseCaseType.CREATIVE_WRITING:
            reasoning_parts.append("High temperature encourages creative and diverse outputs")
        elif use_case == UseCaseType.CODE_GENERATION:
            reasoning_parts.append("Lower temperature ensures accurate and syntactically correct code")
        elif use_case == UseCaseType.ANALYSIS:
            reasoning_parts.append("Low temperature promotes precise and factual responses")
        elif use_case == UseCaseType.REASONING:
            reasoning_parts.append("Very low temperature maximizes logical consistency")
        elif use_case == UseCaseType.CONVERSATION:
            reasoning_parts.append("Balanced temperature for natural, engaging conversation")

        # Context adjustments
        if context.user_input_length > 500:
            reasoning_parts.append("Extended max tokens for longer, more detailed responses")
        if context.conversation_history_length > 10:
            reasoning_parts.append("Higher top_p maintains coherence in extended conversations")
        if context.time_pressure == "high":
            reasoning_parts.append("Optimized for speed with conservative parameter settings")
        if context.task_complexity_hint == "complex":
            reasoning_parts.append("Increased creativity and response length for complex tasks")

        return ". ".join(reasoning_parts)


class HistoricalLearner:
    """Component for learning from historical parameter success patterns."""

    def __init__(self):
        self._patterns: Dict[str, HistoricalPattern] = {}
        self._cache_file = Path("data/parameter_patterns.json")
        self._load_patterns()

    def _load_patterns(self) -> None:
        """Load historical patterns from persistent storage."""
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r') as f:
                    data = json.load(f)
                    for key, pattern_data in data.items():
                        try:
                            pattern = HistoricalPattern(**pattern_data)
                            self._patterns[key] = pattern
                        except Exception as e:
                            logger.warning(f"Failed to load pattern {key}: {e}")
        except Exception as e:
            logger.warning(f"Failed to load historical patterns: {e}")

    def _save_patterns(self) -> None:
        """Save historical patterns to persistent storage."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            data = {key: pattern.model_dump() for key, pattern in self._patterns.items()}
            with open(self._cache_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.warning(f"Failed to save historical patterns: {e}")

    def get_relevant_patterns(self, use_case: UseCaseType, model_id: str, limit: int = 10) -> List[HistoricalPattern]:
        """Get relevant historical patterns for a use case and model."""
        relevant = [
            pattern for pattern in self._patterns.values()
            if pattern.use_case == use_case and pattern.model_id == model_id
        ]

        # Sort by success score and recency
        relevant.sort(key=lambda p: (p.success_score, p.last_used), reverse=True)
        return relevant[:limit]

    def record_success_pattern(
        self,
        use_case: UseCaseType,
        model_id: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        success_score: float,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0
    ) -> None:
        """Record a successful parameter pattern."""

        # Create pattern key
        key = f"{use_case.value}_{model_id}_{temperature:.2f}_{top_p:.2f}_{max_tokens}"

        if key in self._patterns:
            # Update existing pattern
            pattern = self._patterns[key]
            pattern.usage_count += 1
            pattern.last_used = datetime.now()

            # Update rolling averages
            total_weight = pattern.usage_count - 1
            pattern.success_score = (pattern.success_score * total_weight + success_score) / pattern.usage_count
            if latency_ms > 0:
                pattern.avg_latency_ms = (pattern.avg_latency_ms * total_weight + latency_ms) / pattern.usage_count
            if cost_usd > 0:
                pattern.avg_cost_usd = (pattern.avg_cost_usd * total_weight + cost_usd) / pattern.usage_count
        else:
            # Create new pattern
            pattern = HistoricalPattern(
                use_case=use_case,
                model_id=model_id,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                success_score=success_score,
                usage_count=1,
                last_used=datetime.now(),
                avg_latency_ms=latency_ms,
                avg_cost_usd=cost_usd
            )
            self._patterns[key] = pattern

        # Save periodically (every 10 updates)
        if len(self._patterns) % 10 == 0:
            self._save_patterns()

    async def learn_from_session_data(self) -> None:
        """Learn patterns from existing session data."""
        try:
            sessions = await asyncio.to_thread(list_sessions)
            for session_info in sessions[:50]:  # Limit to recent sessions
                try:
                    session = await asyncio.to_thread(load_session, session_info[1])

                    # Extract patterns from successful runs
                    # This is a simplified implementation - in practice you'd analyze
                    # user feedback, run metrics, etc.
                    if session.agent_config and len(session.transcript) > 0:
                        # Assume successful if session has meaningful conversation
                        success_score = min(len(session.transcript) / 10.0, 1.0)

                        # Try to infer use case from agent name or notes
                        use_case = self._infer_use_case_from_session(session)

                        self.record_success_pattern(
                            use_case=use_case,
                            model_id=session.agent_config.model,
                            temperature=session.agent_config.temperature,
                            top_p=session.agent_config.top_p,
                            max_tokens=1000,  # Default assumption
                            success_score=success_score
                        )
                except Exception as e:
                    logger.debug(f"Failed to learn from session {session_info[0]}: {e}")

        except Exception as e:
            logger.warning(f"Failed to learn from session data: {e}")

    def _infer_use_case_from_session(self, session) -> UseCaseType:
        """Infer use case from session data."""
        text = f"{session.notes or ''} {session.agent_config.name or ''}"
        detection = UseCaseDetector.detect_use_case(text)
        return detection.detected_use_case


class ParameterOptimizer:
    """Main parameter optimization service with performance optimizations."""

    def __init__(self):
        self.detector = UseCaseDetector()
        self.recommender = ParameterRecommender()
        self.learner = HistoricalLearner()

        # Performance optimizations
        self._optimization_cache: Dict[str, Tuple[ParameterOptimizationResponse, float]] = {}
        self._defaults_cache: Dict[str, Tuple[SmartDefaultsResponse, float]] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
        self._max_cache_size = 1000

        # Async locks for thread safety
        self._cache_lock = asyncio.Lock()
        self._learning_lock = asyncio.Lock()

    def _generate_cache_key(self, request: ParameterOptimizationRequest) -> str:
        """Generate a cache key for optimization requests."""
        # Include key factors that affect the result
        key_data = {
            "model_id": request.model_id,
            "description": request.user_description,
            "context": {
                "use_case": request.context.use_case.value,
                "input_length": request.context.user_input_length,
                "history_length": request.context.conversation_history_length,
                "complexity": request.context.task_complexity_hint,
                "time_pressure": request.context.time_pressure
            },
            "historical": request.include_historical_learning
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Tuple) -> bool:
        """Check if cache entry is still valid."""
        _, timestamp = cache_entry
        return time.time() - timestamp < self._cache_ttl

    def _cleanup_cache(self, cache: Dict[str, Tuple]) -> None:
        """Clean up expired cache entries and enforce size limits."""
        current_time = time.time()

        # Remove expired entries
        expired_keys = [
            key for key, (_, timestamp) in cache.items()
            if current_time - timestamp >= self._cache_ttl
        ]
        for key in expired_keys:
            del cache[key]

        # Enforce size limit by removing oldest entries
        if len(cache) > self._max_cache_size:
            # Sort by timestamp and remove oldest half
            sorted_entries = sorted(cache.items(), key=lambda x: x[1][1])
            keys_to_remove = [key for key, _ in sorted_entries[:len(sorted_entries)//2]]
            for key in keys_to_remove:
                del cache[key]

    async def optimize_parameters(self, request: ParameterOptimizationRequest) -> ParameterOptimizationResponse:
        """Optimize parameters for the given request with caching."""
        # Check cache first
        cache_key = self._generate_cache_key(request)
        async with self._cache_lock:
            if cache_key in self._optimization_cache:
                cached_response, timestamp = self._optimization_cache[cache_key]
                if self._is_cache_valid((cached_response, timestamp)):
                    # Update processing time to reflect cache hit
                    cached_response.processing_time_ms = 0.001  # Near-instant cache response
                    return cached_response

        start_time = time.time()

        # Detect use case
        use_case_detection = self.detector.detect_use_case(request.user_description)

        # Get historical patterns if requested
        historical_patterns = None
        if request.include_historical_learning:
            async with self._learning_lock:
                historical_patterns = self.learner.get_relevant_patterns(
                    use_case_detection.detected_use_case,
                    request.model_id
                )

        # Generate recommendations
        recommendation = self.recommender.recommend_parameters(
            use_case_detection.detected_use_case,
            request.context,
            historical_patterns
        )

        # Calculate historical insights
        historical_insights = None
        if historical_patterns:
            historical_insights = self._calculate_historical_insights(historical_patterns)

        # Calculate overall confidence
        confidence = min(
            use_case_detection.confidence_score,
            0.9 if historical_patterns else 0.7
        )

        processing_time = (time.time() - start_time) * 1000

        response = ParameterOptimizationResponse(
            recommended_parameters=recommendation,
            use_case_detection=use_case_detection,
            historical_insights=historical_insights,
            optimization_confidence=confidence,
            processing_time_ms=processing_time
        )

        # Cache the result
        async with self._cache_lock:
            self._optimization_cache[cache_key] = (response, time.time())
            self._cleanup_cache(self._optimization_cache)

        return response

    def _calculate_historical_insights(self, patterns: List[HistoricalPattern]) -> Dict[str, float]:
        """Calculate insights from historical patterns."""
        if not patterns:
            return {}

        insights = {}
        successful_patterns = [p for p in patterns if p.success_score > 0.7]

        if successful_patterns:
            insights["avg_success_score"] = sum(p.success_score for p in successful_patterns) / len(successful_patterns)
            insights["total_usage"] = sum(p.usage_count for p in successful_patterns)
            insights["avg_latency_ms"] = sum(p.avg_latency_ms for p in successful_patterns if p.avg_latency_ms > 0) / len([p for p in successful_patterns if p.avg_latency_ms > 0]) if any(p.avg_latency_ms > 0 for p in successful_patterns) else 0

        return insights

    async def get_smart_defaults(self, request: SmartDefaultsRequest) -> SmartDefaultsResponse:
        """Get smart default parameters for a model with caching."""
        # Check cache first
        cache_key = f"{request.model_id}_{request.user_context or ''}"
        async with self._cache_lock:
            if cache_key in self._defaults_cache:
                cached_response, timestamp = self._defaults_cache[cache_key]
                if self._is_cache_valid((cached_response, timestamp)):
                    return cached_response

        start_time = time.time()

        # Try to detect use case from context
        use_case = UseCaseType.OTHER
        confidence = 0.5

        if request.user_context:
            detection = self.detector.detect_use_case(request.user_context)
            use_case = detection.detected_use_case
            confidence = detection.confidence_score

        # Get historical patterns for this model and use case
        async with self._learning_lock:
            historical_patterns = self.learner.get_relevant_patterns(use_case, request.model_id, limit=5)

        # Create optimization context
        context = OptimizationContext(
            model_id=request.model_id,
            use_case=use_case,
            user_input_length=0,
            conversation_history_length=0,
            task_complexity_hint=None,
            time_pressure=None
        )

        # Get recommendations
        recommendation = self.recommender.recommend_parameters(use_case, context, historical_patterns)

        # Generate reasoning
        reasoning = f"Smart defaults for {use_case.value.replace('_', ' ')} based on successful patterns"
        if historical_patterns:
            reasoning += f" (learned from {len(historical_patterns)} historical successes)"

        processing_time = (time.time() - start_time) * 1000

        response = SmartDefaultsResponse(
            default_parameters=recommendation,
            reasoning=reasoning,
            confidence_score=min(confidence, 0.8)  # Conservative confidence for defaults
        )

        # Cache the result
        async with self._cache_lock:
            self._defaults_cache[cache_key] = (response, time.time())
            self._cleanup_cache(self._defaults_cache)

        return response

    async def record_feedback(
        self,
        model_id: str,
        use_case: UseCaseType,
        temperature: float,
        top_p: float,
        max_tokens: int,
        success_score: float,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0
    ) -> None:
        """Record user feedback for continuous learning with thread safety."""
        async with self._learning_lock:
            self.learner.record_success_pattern(
                use_case=use_case,
                model_id=model_id,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                success_score=success_score,
                latency_ms=latency_ms,
                cost_usd=cost_usd
            )


# Global optimizer instance
_optimizer_instance: Optional[ParameterOptimizer] = None

def get_parameter_optimizer() -> ParameterOptimizer:
    """Get the global parameter optimizer instance."""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = ParameterOptimizer()
    return _optimizer_instance


async def optimize_parameters(request: ParameterOptimizationRequest) -> ParameterOptimizationResponse:
    """Convenience function for parameter optimization."""
    optimizer = get_parameter_optimizer()
    return await optimizer.optimize_parameters(request)


async def get_smart_defaults(request: SmartDefaultsRequest) -> SmartDefaultsResponse:
    """Convenience function for smart defaults."""
    optimizer = get_parameter_optimizer()
    return await optimizer.get_smart_defaults(request)


if __name__ == "__main__":
    # Test the service
    async def test():
        optimizer = get_parameter_optimizer()

        # Test use case detection
        detection = optimizer.detector.detect_use_case("I want to write a creative story about AI")
        print(f"Detected use case: {detection.detected_use_case}")
        print(f"Confidence: {detection.confidence_score}")

        # Test parameter optimization
        request = ParameterOptimizationRequest(
            model_id="openai/gpt-4o",
            user_description="I want to write a creative story about AI",
            context=OptimizationContext(
                model_id="openai/gpt-4o",
                use_case=UseCaseType.CREATIVE_WRITING,
                user_input_length=100,
                conversation_history_length=2,
                task_complexity_hint=None,
                time_pressure=None
            )
        )

        response = await optimizer.optimize_parameters(request)
        print(f"Recommended temperature: {response.recommended_parameters.temperature}")
        print(f"Recommended top_p: {response.recommended_parameters.top_p}")
        print(f"Recommended max_tokens: {response.recommended_parameters.max_tokens}")
        print(f"Processing time: {response.processing_time_ms:.2f}ms")

    asyncio.run(test())