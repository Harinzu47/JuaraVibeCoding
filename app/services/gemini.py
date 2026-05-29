import asyncio
import json
import logging

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("app.gemini")

# Define the structured output schema for the Gemini model
GEMINI_RESPONSE_SCHEMA = types.Schema(
    type=types.Type.OBJECT,
    properties={
        "response": types.Schema(
            type=types.Type.STRING,
            description="Friendly, warm, and supportive conversational response in Bahasa Indonesia.",
        ),
        "intent": types.Schema(
            type=types.Type.STRING,
            enum=[
                "RECORD_SPENDING",
                "CORRECT_SPENDING",
                "RECORD_SALES",
                "ASK_INFO",
                "NEED_CLARIFICATION",
                "OTHER",
            ],
            description=(
                "The classified main intent of the user's message. "
                "Use NEED_CLARIFICATION when required data slots are missing "
                "and AI must ask a follow-up question before calculating."
            ),
        ),
        "correction_item": types.Schema(
            type=types.Type.STRING,
            description="Name of the item being corrected. Filled only if intent == CORRECT_SPENDING. E.g. 'ayam', 'telur'.",
        ),
        "correction_old_price": types.Schema(
            type=types.Type.INTEGER,
            description="The incorrect price of the item in Rupiah. Filled only if intent == CORRECT_SPENDING.",
        ),
        "correction_new_price": types.Schema(
            type=types.Type.INTEGER,
            description="The correct price of the item in Rupiah. Filled only if intent == CORRECT_SPENDING.",
        ),
        "total_spending": types.Schema(
            type=types.Type.INTEGER,
            description="Total money spent to buy all ingredients. Morning phase only.",
        ),
        "used_capital": types.Schema(
            type=types.Type.INTEGER,
            description="Monetary value of ingredients actually used for production. Morning phase only.",
        ),
        "cogs_per_unit": types.Schema(
            type=types.Type.INTEGER,
            description="Cost of Goods Sold (COGS) / Harga Pokok Penjualan per portion. Morning phase only.",
        ),
        "portions_sold": types.Schema(
            type=types.Type.INTEGER,
            description="Quantity of food portions sold. Evening phase only.",
        ),
        "selling_price": types.Schema(
            type=types.Type.INTEGER,
            description="Selling price per portion. Evening phase only.",
        ),
        "total_revenue": types.Schema(
            type=types.Type.INTEGER,
            description="Total gross revenue. Evening phase only.",
        ),
        "net_profit": types.Schema(
            type=types.Type.INTEGER,
            description="Net operational profit. Evening phase only.",
        ),
        "break_even": types.Schema(
            type=types.Type.BOOLEAN,
            description="Whether total revenue today is >= total spending. Evening phase only.",
        ),
    },
    required=["response"],
)


class GeminiService:
    """Service handling interactions with the Google Gemini API, including fallback models and structured output."""

    def __init__(self):
        self.model_chain = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-flash-latest",
            "gemini-flash-lite-latest",
        ]
        self.active_model = self.model_chain[-1]  # Default fallback model
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS

    async def detect_active_model(self, api_key: str) -> str:
        """
        Probe each model in the preference chain in order.
        Saves and returns the first model that successfully responds.
        """
        if not api_key:
            logger.warning("Empty API key provided. Skipping model detection.")
            return self.active_model

        client = genai.Client(api_key=api_key)

        for model_name in self.model_chain:
            try:
                # Run the probe with a short timeout
                await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents="ping",
                        config=types.GenerateContentConfig(
                            max_output_tokens=1,
                        ),
                    ),
                    timeout=5.0,
                )
                logger.info(f"Successfully selected Gemini model: {model_name}")
                self.active_model = model_name
                return model_name
            except asyncio.TimeoutError:
                logger.warning(f"Probe timeout for Gemini model: {model_name}")
                continue
            except Exception as e:
                logger.warning(
                    f"Gemini model {model_name} probe failed: {str(e)[:120]}"
                )
                continue

        logger.error(
            f"All models failed in fallback chain. Defaulting to: {self.active_model}"
        )
        return self.active_model

    async def generate_content(
        self, api_key: str, system_instruction: str, chat_history: list, message: str
    ) -> dict:
        """
        Send a request to Gemini, automatically falling back through the model
        chain if any model returns 503 (overload), 429 (quota), or times out.
        """
        client = genai.Client(api_key=api_key)

        # Build contents from history
        contents = []
        for msg in chat_history:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(role=role, parts=[types.Part(text=msg.content)])
            )
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        # Build a prioritised trial list: active model first, then the rest
        if self.active_model in self.model_chain:
            trial_models = [self.active_model] + [
                m for m in self.model_chain if m != self.active_model
            ]
        else:
            trial_models = self.model_chain

        last_error: Exception = RuntimeError("No models available.")

        for model_name in trial_models:
            try:
                logger.info(f"Trying Gemini model: {model_name}")
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.models.generate_content,
                        model=model_name,
                        contents=contents,  # type: ignore[arg-type]
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            response_mime_type="application/json",
                            response_schema=GEMINI_RESPONSE_SCHEMA,
                        ),
                    ),
                    timeout=self.timeout,
                )
                resp_text = response.text or "{}"
                result = json.loads(resp_text)
                # Update active model to the one that succeeded
                if model_name != self.active_model:
                    logger.info(
                        f"Switching active model from {self.active_model} → {model_name}"
                    )
                    self.active_model = model_name
                return result

            except asyncio.TimeoutError:
                last_error = TimeoutError(f"Model {model_name} timed out.")
                logger.warning(f"Timeout on model {model_name}, trying next...")
                continue

            except json.JSONDecodeError as e:
                # JSON error is likely model-agnostic; raise immediately
                logger.error(f"Failed to decode JSON from Gemini response: {e}")
                raise ValueError("Gemini returned invalid JSON structure.")

            except Exception as e:
                err_str = str(e)
                # 503 = overloaded, 429 = quota — try next model
                if "503" in err_str or "UNAVAILABLE" in err_str or "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    last_error = e
                    logger.warning(
                        f"Model {model_name} unavailable ({err_str[:80]}), trying next..."
                    )
                    continue
                else:
                    # Other errors (auth, bad request, etc.) — raise immediately
                    logger.error(f"Gemini generation error on {model_name}: {e}")
                    raise e

        # All models exhausted
        logger.error(f"All Gemini models failed. Last error: {last_error}")
        raise last_error


gemini_service = GeminiService()
