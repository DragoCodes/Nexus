"""Gemini API client for entity and relationship extraction."""
import time
import logging
import google.generativeai as genai
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiClient:
    """Handle Gemini API communication with retry logic and rate limiting."""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash"):
        """Initialize Gemini client.
        
        Args:
            api_key: Google Gemini API key
            model_name: Model to use (default: gemini-1.5-flash)
        """
        genai.configure(api_key=api_key)
        self.model_name = model_name
        # Note: response_mime_type may not be available in all versions
        # We'll rely on prompt instructions to get JSON output
        self.model = genai.GenerativeModel(
            model_name=model_name,
            generation_config={
                "temperature": 0,
                "max_output_tokens": 8192  # Increased to handle articles with many relationships
            }
        )
        self.api_call_count = 0
        self.last_call_time = 0
        logger.info(f"Initialized GeminiClient with model: {model_name}")
    
    def extract(self, prompt_text: str) -> Optional[str]:
        """Extract relationships from article text using Gemini API.
        
        Args:
            prompt_text: Complete prompt with article text and instructions
            
        Returns:
            JSON response string, or None if all retries failed
        """
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Rate limiting: wait 4-5 seconds between calls
                time_since_last_call = time.time() - self.last_call_time
                if time_since_last_call < 4.5:
                    wait_time = 4.5 - time_since_last_call
                    time.sleep(wait_time)
                
                # Make API call
                start_time = time.time()
                response = self.model.generate_content(prompt_text)
                elapsed_time = time.time() - start_time
                
                self.api_call_count += 1
                self.last_call_time = time.time()
                
                # Extract response text - handle different response formats
                response_text = ""
                
                # Check for blocked/filtered responses first
                blocked = False
                truncated = False
                finish_reason_map = {
                    1: "STOP",  # Normal completion
                    2: "MAX_TOKENS",  # Response truncated
                    3: "SAFETY",  # Content blocked
                    4: "RECITATION",  # Copyright issue
                    5: "OTHER"
                }
                
                if hasattr(response, 'candidates') and response.candidates:
                    for candidate in response.candidates:
                        # Check finish_reason for blocked content
                        if hasattr(candidate, 'finish_reason'):
                            finish_reason = candidate.finish_reason
                            finish_name = finish_reason_map.get(finish_reason, f"UNKNOWN({finish_reason})")
                            if finish_reason and finish_reason != 1:  # 1 = STOP (normal)
                                logger.warning(f"Response finish_reason={finish_name} (code={finish_reason})")
                                if finish_reason == 3:  # SAFETY - content blocked
                                    blocked = True
                                elif finish_reason == 2:  # MAX_TOKENS - response truncated but may have partial text
                                    truncated = True
                
                # Try response.text first (works for simple responses)
                try:
                    response_text = response.text
                except Exception as e:
                    # If response.text fails (e.g., multi-part response, blocked content), extract from candidates
                    logger.debug(f"response.text failed ({type(e).__name__}: {e}), extracting from candidates")
                    
                    # Extract from candidates
                    if hasattr(response, 'candidates') and response.candidates:
                        parts = []
                        for candidate in response.candidates:
                            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                                for part in candidate.content.parts:
                                    if hasattr(part, 'text') and part.text:
                                        parts.append(part.text)
                                    elif hasattr(part, 'function_call'):
                                        # Handle function calling responses if needed
                                        logger.debug("Received function call response, skipping")
                                        continue
                        response_text = ''.join(parts)
                    
                    # Fallback: try parts attribute directly
                    if not response_text and hasattr(response, 'parts') and response.parts:
                        response_text = ''.join(
                            part.text for part in response.parts 
                            if hasattr(part, 'text') and part.text
                        )
                
                # Handle blocked/empty responses
                if not response_text or len(response_text.strip()) == 0:
                    if blocked:
                        logger.warning("Response was blocked by safety filters - returning empty result")
                        return None  # Return None for blocked content instead of raising error
                    elif truncated:
                        logger.warning("Response was truncated (MAX_TOKENS) but no text extracted - returning empty result")
                        return None  # Return None for truncated responses with no text
                    else:
                        # Log detailed error information for debugging
                        logger.error(f"Could not extract text from response: {type(response)}")
                        if hasattr(response, 'candidates'):
                            logger.error(f"Response has {len(response.candidates) if response.candidates else 0} candidates")
                            for i, cand in enumerate(response.candidates or []):
                                logger.error(f"  Candidate {i}: finish_reason={getattr(cand, 'finish_reason', 'N/A')}")
                                if hasattr(cand, 'content'):
                                    logger.error(f"    Has content: True")
                                    if hasattr(cand.content, 'parts'):
                                        logger.error(f"    Parts: {len(cand.content.parts)}")
                                        for j, part in enumerate(cand.content.parts):
                                            logger.error(f"      Part {j}: type={type(part)}, has text={hasattr(part, 'text')}")
                        raise ValueError("Could not extract text from API response")
                
                # Warn if response was truncated but we got some text
                if truncated:
                    logger.warning("Response was truncated (MAX_TOKENS) - extracted text may be incomplete")
                
                logger.info(
                    f"API call #{self.api_call_count} - "
                    f"Prompt length: {len(prompt_text)} chars, "
                    f"Response length: {len(response_text)} chars, "
                    f"Attempt: {attempt + 1}, "
                    f"Time: {elapsed_time:.2f}s"
                )
                
                # Log first 200 chars of response for debugging
                logger.debug(f"Response preview: {response_text[:200]}")
                
                return response_text
                
            except Exception as e:
                error_code = getattr(e, 'status_code', None)
                error_message = str(e)
                error_type = type(e).__name__
                
                logger.error(f"API call exception: {error_type} - {error_message}")
                
                # Handle specific error types
                if error_code == 401:
                    logger.error("Invalid API key. Please check your GEMINI_API_KEY.")
                    raise ValueError("Invalid Gemini API key") from e
                
                elif error_code == 429:
                    wait_time = 60
                    logger.warning(
                        f"Rate limit hit (429). Waiting {wait_time}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                elif error_code and 500 <= error_code < 600:
                    wait_time = 10
                    logger.warning(
                        f"Server error ({error_code}). Waiting {wait_time}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                else:
                    # Exponential backoff for other errors
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"API call failed: {error_message}. "
                        f"Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})"
                    )
                    if attempt < max_retries - 1:
                        time.sleep(wait_time)
                        continue
                
                # If we've exhausted retries
                if attempt == max_retries - 1:
                    logger.error(
                        f"All {max_retries} retry attempts failed. "
                        f"Last error: {error_message}"
                    )
                    return None
        
        return None
    
    def get_api_call_count(self) -> int:
        """Get total number of API calls made."""
        return self.api_call_count

