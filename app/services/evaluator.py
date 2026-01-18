"""
Phoenix LLM Evaluator Service for DDoS and Malicious Prompt Detection.
Uses Phoenix evaluator SDK with LLM-as-judge to evaluate prompt validity.
"""
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
from phoenix.evals import ClassificationEvaluator
from phoenix.evals.llm import LLM

# Initialize the tracer for this service
tracer = trace.get_tracer(__name__)


class PromptEvaluator:
    """
    Evaluator service that uses Phoenix LLM-as-judge to detect
    DDoS attacks, malicious prompts, and nonsensical inputs.
    """
    
    def __init__(self, gemini_api_key: str, evaluator_model: str = "gemini-2.5-flash-lite"):
        """
        Initialize the evaluator with Gemini API key and model.
        
        Args:
            gemini_api_key: Gemini API key for the judge model
            evaluator_model: Model to use as judge (default: gemini-2.5-flash-lite for cost efficiency)
        """
        self.gemini_api_key = gemini_api_key
        self.evaluator_model = evaluator_model
        
        # Initialize Phoenix LLM for evaluator with Gemini provider
        llm_kwargs = {
            "provider": "google",
            "model": evaluator_model,
            "api_key": gemini_api_key,
        }
        self.llm = LLM(**llm_kwargs)
        
        # Create classification evaluator with prompt template
        self.evaluator = ClassificationEvaluator(
            name="ecoshield_ddos_detector",
            prompt_template=self._get_evaluation_prompt_template(),
            llm=self.llm,
            choices={
                "valid": 0,  # Valid, legitimate prompt
                "invalid": 1,  # DDoS, malicious, or nonsensical prompt
            },
        )
    
    def _get_evaluation_prompt_template(self) -> str:
        """
        Get the prompt template for the LLM judge evaluator.
        Evaluates both DDoS patterns and general validity.
        """
        return """You are a security evaluator for an AI agent system protecting startups from economic DDoS attacks.

Your task is to analyze the following user prompt and determine if it is:
1. A VALID, legitimate request that makes sense and is appropriate for an AI agent
2. An INVALID request that is either:
   - A DDoS/token stuffing attack (repetitive content, noise, excessive tokens)
   - Malicious or abusive content
   - Random nonsense or gibberish that doesn't make sense
   - Content that would waste resources without providing value

Prompt to evaluate:
{input}

Respond with ONLY one word: "valid" or "invalid"

Important considerations:
- Legitimate questions or requests about any topic = valid
- Repetitive words, token stuffing, or obvious noise = invalid
- Random characters, gibberish, or nonsensical text = invalid
- Prompts that make no logical sense = invalid
- Clear attempts to waste API resources = invalid"""
    
    def evaluate(self, prompt: str) -> dict:
        """
        Evaluate a prompt using Phoenix LLM-as-judge evaluator.
        
        Args:
            prompt: The user prompt to evaluate
            
        Returns:
            dict with keys:
                - is_valid (bool): True if prompt is valid, False if invalid/DDoS
                - label (str): "valid" or "invalid"
                - score (float): Confidence score (0-1)
                - reason (str): Brief explanation of the evaluation
        """
        # Create evaluation span for Phoenix tracing
        with tracer.start_as_current_span("EcoShield_LLM_Evaluator") as span:
            span.set_attribute("openinference.span.kind", "CHAIN")
            span.set_attribute("security.layer", "llm_evaluation")
            span.set_attribute("evaluator.model", self.evaluator_model)
            span.set_attribute("input.value", prompt[:500] + "..." if len(prompt) > 500 else prompt)
            
            try:
                # Run Phoenix evaluator
                # The evaluator expects a dict with "input" key
                result = self.evaluator.evaluate({"input": prompt})
                
                # Extract results from Phoenix evaluator response
                if result and len(result) > 0:
                    eval_result = result[0]
                    label = eval_result.label  # "valid" or "invalid"
                    score = eval_result.score if hasattr(eval_result, 'score') else (0.0 if label == "invalid" else 1.0)
                    
                    is_valid = label == "valid"
                    
                    # Set span attributes
                    span.set_attribute("evaluation.label", label)
                    span.set_attribute("evaluation.is_valid", is_valid)
                    span.set_attribute("evaluation.score", float(score))
                    
                    return {
                        "is_valid": is_valid,
                        "label": label,
                        "score": float(score),
                        "reason": f"Evaluator classified as: {label}"
                    }
                else:
                    # Fallback: if evaluator fails, default to invalid (block)
                    span.set_status(Status(StatusCode.ERROR, "Evaluator returned no result"))
                    span.set_attribute("evaluation.label", "invalid")
                    span.set_attribute("evaluation.is_valid", False)
                    return {
                        "is_valid": False,
                        "label": "invalid",
                        "score": 0.0,
                        "reason": "Evaluator returned no result - blocking by default"
                    }
                    
            except Exception as e:
                # On error, block by default (fail-safe)
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.set_attribute("evaluation.label", "invalid")
                span.set_attribute("evaluation.is_valid", False)
                
                return {
                    "is_valid": False,
                    "label": "invalid",
                    "score": 0.0,
                    "reason": f"Evaluator error: {str(e)} - blocking by default"
                }
