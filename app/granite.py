"""
IBM Granite (watsonx.ai) client — centralized, chat-API based.
Uses ModelInference.chat() from ibm_watsonx_ai==1.9.x
"""
import os
import logging
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import ModelInference

logger = logging.getLogger(__name__)

_model: ModelInference | None = None


def get_model() -> ModelInference:
    global _model
    if _model is None:
        api_key = os.getenv('WATSONX_API_KEY')
        project_id = os.getenv('WATSONX_PROJECT_ID')
        url = os.getenv('WATSONX_URL', 'https://us-south.ml.cloud.ibm.com')
        model_id = os.getenv('WATSONX_MODEL_ID', 'ibm/granite-4-h-small')

        if not api_key or not project_id:
            raise EnvironmentError(
                'WATSONX_API_KEY and WATSONX_PROJECT_ID must be set in environment.'
            )

        credentials = Credentials(url=url, api_key=api_key)
        _model = ModelInference(
            model_id=model_id,
            credentials=credentials,
            project_id=project_id,
        )
        logger.info('Granite model initialized: %s', model_id)
    return _model


def chat(system_prompt: str, user_message: str, max_tokens: int = 1500) -> str:
    """
    Call IBM Granite via chat endpoint.
    Returns the assistant's text content.
    Raises on failure — callers must handle.
    """
    model = get_model()
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_message},
    ]
    params = {
        'max_new_tokens': min(max_tokens, 4096),
        'temperature': 0.7,
    }
    response = model.chat(messages=messages, params=params)
    # Extract text from response
    choices = response.get('choices', [])
    if not choices:
        raise ValueError('Empty response from Granite model.')
    return choices[0]['message']['content'].strip()


def test_connection() -> dict:
    """Test Granite connectivity. Returns status dict."""
    try:
        result = chat(
            system_prompt='You are a helpful assistant.',
            user_message='Respond with exactly: "TeachWise AI connected."',
            max_tokens=20,
        )
        return {'status': 'ok', 'response': result}
    except Exception as exc:
        logger.error('Granite connection test failed: %s', exc)
        return {'status': 'error', 'error': str(exc)}
